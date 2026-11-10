import json

import pytest

from easy_wrf_hydro_build.parameters import PARAMETERS, prepare_parameters


def test_parameter_maps_use_the_adjusted_grid_and_join_groundwater_ids(tmp_path):
    nc = pytest.importorskip("netCDF4")
    np = pytest.importorskip("numpy")
    pytest.importorskip("matplotlib")
    from easy_wrf_hydro_build.parameter_maps import _read_parameter

    template = tmp_path / "template"
    domain = template / "DOMAIN"
    domain.mkdir(parents=True)
    (template / "FORCING").mkdir()
    soil = domain / "soil_properties.nc"
    with nc.Dataset(soil, "w") as data:
        for name, length in (("west_east", 2), ("Time", 1), ("south_north", 2), ("soil_layers_stag", 2)):
            data.createDimension(name, length)
        data.DX, data.DY = 1000, 1000
        field = data.createVariable("dksat", "f4", ("west_east", "Time", "south_north", "soil_layers_stag"))
        field[:, 0, :, 0] = [[1, 2], [3, -9999]]
        field[:, 0, :, 1] = [[4, 5], [6, 7]]
    with nc.Dataset(domain / "GWBUCKPARM.nc", "w") as data:
        data.createDimension("feature_id", 2)
        data.createVariable("Basin", "i4", ("feature_id",))[:] = [40, 10]
        data.createVariable("Coeff", "f4", ("feature_id",))[:] = [0.75, 0.2]
    with nc.Dataset(domain / "GWBASINS.nc", "w") as data:
        data.createDimension("y", 2)
        data.createDimension("x", 2)
        data.createVariable("BASIN", "i4", ("y", "x"))[:] = [[10, 40], [-9999, 999]]
    _, (grid,), _ = _read_parameter(domain, PARAMETERS["gw_coefficient"])
    np.testing.assert_allclose(grid[0], [0.2, 0.75])
    assert grid.mask[1].all()

    original = soil.read_bytes()
    config = tmp_path / "changes.json"
    config.write_text('{"dksat": {"scale": 2}}')
    output = tmp_path / "trial"
    report = prepare_parameters(template, config, output, maps=True)
    maps = report["parameter_maps"]
    assert maps["images"]["dksat"]["range"] == [2, 14]
    assert maps["images"]["dksat"]["layers"] == ["Soil layer 1", "Soil layer 2"]
    assert maps["images"]["gw_coefficient"]["kind"] == "groundwater_basins"
    assert "channel_manning_n" in maps["skipped"]
    _, layers, _ = _read_parameter(output / "DOMAIN", PARAMETERS["dksat"])
    assert layers[0][0, 1] == 6
    assert layers[0].mask[1, 1]
    for record in maps["images"].values():
        assert (output / "parameter-maps" / record["file"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert json.loads((output / "parameter-manifest.json").read_text())["parameter_maps"] == maps
    assert not (template / "parameter-maps").exists()
    assert soil.read_bytes() == original
