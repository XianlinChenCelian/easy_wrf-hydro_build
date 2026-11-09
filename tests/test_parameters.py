import json
from pathlib import Path

import pytest

from easy_wrf_hydro_build.cli import main
from easy_wrf_hydro_build.parameters import prepare_parameters


def _template(tmp_path):
    nc = pytest.importorskip("netCDF4")
    np = pytest.importorskip("numpy")
    template = tmp_path / "template"
    domain = template / "domain"
    domain.mkdir(parents=True)
    weather = tmp_path / "weather files"
    weather.mkdir()
    (weather / "2011082601.LDASIN_DOMAIN1").write_text("weather")
    (template / "forcing").symlink_to(weather, target_is_directory=True)
    with nc.Dataset(domain / "soil_properties.nc", "w", format="NETCDF4_CLASSIC") as ds:
        ds.title = "template metadata"
        ds.createDimension("x", 4)
        field = ds.createVariable("refkdt", "f4", ("x",), zlib=True, fill_value=-9998)
        field[:] = np.array([1, 3, -9998, -9999], dtype="f4")
        field.units = "1"
        other = ds.createVariable("other", "i4", ("x",))
        other[:] = [1, 2, 3, 4]
    with nc.Dataset(domain / "GWBUCKPARM.nc", "w") as ds:
        ds.createDimension("feature_id", 2)
        for name, values in (("Zmax", [50, 70]), ("Zinit", [10, 20]), ("Expon", [2, 4])):
            ds.createVariable(name, "f4", ("feature_id",))[:] = values
    (domain / "gage.csv").write_text("station")
    (template / "HYDRO.TBL").write_text("MODIS table")
    return template, weather


def test_prepare_parameters_copies_domain_and_reuses_forcing(tmp_path, capsys):
    nc = pytest.importorskip("netCDF4")
    np = pytest.importorskip("numpy")
    template, weather = _template(tmp_path)
    config = tmp_path / "change.json"
    edits = {"refkdt": {"scale": 2}, "gw_exponent": {"set": 3.5}}
    config.write_text(json.dumps(edits))
    original = template / "domain/soil_properties.nc"
    original_bytes = original.read_bytes()

    assert main(["prepare-parameters", "--template", str(template), "--list"]) == 0
    discovered = json.loads(capsys.readouterr().out)["parameters"]
    assert discovered["refkdt"]["template_range"] == [1, 3]
    assert not discovered["channel_manning_n"]["available"]

    output = tmp_path / "experiments/trial"
    assert main(["prepare-parameters", "--template", str(template), "--config", str(config),
                 "--output", str(output)]) == 0
    assert (output / "FORCING").is_symlink()
    assert (output / "FORCING").samefile(weather)
    assert (output / "DOMAIN/gage.csv").read_text() == "station"
    assert (output / "HYDRO.TBL").read_text() == "MODIS table"
    assert original.read_bytes() == original_bytes
    assert json.loads((output / "parameters.json").read_text()) == edits
    manifest = json.loads((output / "parameter-manifest.json").read_text())
    assert manifest["edits"]["refkdt"]["result_range"] == [2, 6]
    assert manifest["edits"]["refkdt"]["changed_values"] == 2
    assert manifest["edits"]["gw_exponent"]["result_range"] == [3.5, 3.5]
    hashes = manifest["netcdf_files"]["soil_properties.nc"]
    assert hashes["template_sha256"] != hashes["result_sha256"]
    with nc.Dataset(output / "DOMAIN/soil_properties.nc") as result:
        assert result.data_model == "NETCDF4_CLASSIC"
        assert result.title == "template metadata"
        assert result["refkdt"].filters()["zlib"]
        assert result["refkdt"].units == "1"
        np.testing.assert_array_equal(result["other"][:], [1, 2, 3, 4])
        result["refkdt"].set_auto_mask(False)
        np.testing.assert_array_equal(result["refkdt"][:], [2, 6, -9998, -9999])
    with nc.Dataset(output / "DOMAIN/GWBUCKPARM.nc") as result:
        np.testing.assert_array_equal(result["Expon"][:], [3.5, 3.5])

    # A sibling case starts from the same original field instead of multiplying the prior result.
    another = tmp_path / "experiments/another"
    assert prepare_parameters(template, config, another)["edits"]["refkdt"]["result_range"] == [2, 6]


def test_invalid_parameters_do_not_publish_a_partial_case(tmp_path):
    template, _ = _template(tmp_path)
    config = tmp_path / "change.json"
    config.write_text('{"refkdt": {"scale": 2}, "gw_max_depth": {"set": 15}}')
    output = tmp_path / "trial"
    with pytest.raises(ValueError, match="Zmax must be at least Zinit"):
        prepare_parameters(template, config, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".ewhb-parameters-*"))

    config.write_text('{"refkdt": {"scale": 2}, "refkdt": {"scale": 3}}')
    with pytest.raises(ValueError, match="Duplicate parameter configuration key"):
        prepare_parameters(template, config, output)
    config.write_text("{}")
    output.mkdir()
    with pytest.raises(ValueError, match="Choose a new"):
        prepare_parameters(template, config, output)


def test_forcing_link_permission_error_points_to_a_supported_output(tmp_path, monkeypatch):
    template, _ = _template(tmp_path)
    config = tmp_path / "baseline.json"
    config.write_text("{}")

    def no_symlinks(*args, **kwargs):
        raise PermissionError("operation not supported")

    monkeypatch.setattr(Path, "symlink_to", no_symlinks)
    output = tmp_path / "trial"
    with pytest.raises(ValueError, match="Use APFS or a Linux filesystem"):
        prepare_parameters(template, config, output)
    assert not output.exists()
