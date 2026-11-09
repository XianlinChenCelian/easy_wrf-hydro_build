from pathlib import Path
import json
from zipfile import ZipFile

import pytest

from easy_wrf_hydro_build.cli import main
from easy_wrf_hydro_build.forcing import AORC, NLDAS, _to_model_units, prepare_forcing


@pytest.mark.parametrize(
    ("field", "value", "units", "seconds", "expected"),
    [
        ("RAINRATE", 3.6, "kg/m^2", 3600, 0.001),
        ("RAINRATE", 0.0036, "m", 3600, 0.001),
        ("RAINRATE", 3.6, "mm/h", 10800, 0.001),
        ("SWDOWN", 720000, "J m**-2", 3600, 200),
        ("PSFC", 980, "hPa", 3600, 98000),
        ("Q2D", 6, "g kg-1", 3600, 0.006),
    ],
)
def test_weather_unit_conversions(field, value, units, seconds, expected):
    assert _to_model_units(field, value, units, seconds) == pytest.approx(expected)


def test_unknown_precipitation_units_are_rejected():
    with pytest.raises(ValueError, match="Unsupported units"):
        _to_model_units("RAINRATE", 10, "unknown", 3600)


def _geogrid(path):
    nc = pytest.importorskip("netCDF4")
    with nc.Dataset(path, "w") as geo:
        for dim, size in (("Time", 1), ("y", 2), ("x", 2)):
            geo.createDimension(dim, size)
        geo.createVariable("XLAT_M", "f4", ("Time", "y", "x"))[0] = [[35, 35], [36, 36]]
        geo.createVariable("XLONG_M", "f4", ("Time", "y", "x"))[0] = [[107, 108], [107, 108]]


@pytest.mark.parametrize(("source", "mode"), [("era5-land", None), ("era5", None), ("era5-land", "hourly")])
def test_ecmwf_hourly_rainfall_and_radiation_across_midnight(tmp_path: Path, source, mode, capsys):
    np = pytest.importorskip("numpy")
    nc = pytest.importorskip("netCDF4")
    xr = pytest.importorskip("xarray")
    _geogrid(tmp_path / "geo.nc")

    start = np.datetime64("2020-06-01T22:00:00")
    time = start + np.arange(5) * np.timedelta64(1, "h")
    fields = {
        "tp": ([.022, .024, .030, .004, .007], "m"),
        "ssrd": ([10000, 20000, 30000, 20000, 19875], "J m**-2"),
        "strd": ([220000, 230000, 240000, 10000, 20000], "J m**-2"),
        "t2m": ([280.0] * 5, "K"), "d2m": ([273.16] * 5, "K"),
        "u10": ([2] * 5, "m s**-1"), "v10": ([-1] * 5, "m s**-1"),
        "sp": ([100000] * 5, "Pa"),
    }
    if source == "era5" or mode == "hourly":
        fields.update({
            "tp": ([0, .002, .006, .004, .003], "m"),
            "ssrd": ([0, 10000, 10000, 20000, -125], "J m**-2"),
            "strd": ([0, 10000, 10000, 10000, 10000], "J m**-2"),
        })
    data = xr.Dataset({
        name: (("valid_time", "latitude", "longitude"),
               np.broadcast_to(np.array(values)[:, None, None], (5, 2, 2)), {"units": units})
        for name, (values, units) in fields.items()
    }, coords={"valid_time": time, "latitude": [35, 36], "longitude": [107, 108]})
    if source == "era5" or mode == "hourly":
        data = data.isel(valid_time=slice(1, None))
    if source == "era5":
        # Legacy expver is a separate axis; modern CDS uses valid_time.
        data = data.assign_coords(time=data.valid_time - np.timedelta64(1, "h"))
        final = data.copy(deep=True)
        final["t2m"][1, :, :] = np.nan
        preliminary = data.copy(deep=True)
        preliminary["t2m"][0, :, :] = 295
        data = xr.concat([final, preliminary], dim=xr.IndexVariable("expver", [1, 5]))
    rain_and_radiation = ["tp", "ssrd", "strd"]
    with ZipFile(tmp_path / "weather.zip", "w") as bundle:
        for label, part in (("accum", data[rain_and_radiation]), ("instant", data.drop_vars(rain_and_radiation))):
            filename = tmp_path / f"data_stream-oper_stepType-{label}.nc"
            part.to_netcdf(filename)
            bundle.write(filename, filename.name)
    output = tmp_path / "FORCING"
    args = ["prepare-forcing", "--source", source, "--input", str(tmp_path / "weather.zip"),
            "--geogrid", str(tmp_path / "geo.nc"), "--start", "2020-06-01T22:00:00Z",
            "--end", "2020-06-02T02:00:00Z", "--output", str(output)]
    if mode:
        args.extend(["--accumulation", mode])
    assert main(args) == 0
    report = json.loads((output / "forcing-manifest.json").read_text())
    assert report["first_file"] == "2020060123.LDASIN_DOMAIN1"
    assert report["forcing_file_count"] == 4
    assert report["accumulation"] == ("daily" if source == "era5-land" and mode is None else "hourly")
    assert report["negative_accumulation_corrections"]["SWDOWN"] == {"count": 4, "minimum_source_value": -125}
    assert len(report["input_records"]) == 2
    for file, rainfall_mm, shortwave in zip(sorted(output.glob("*.LDASIN_DOMAIN1")),
                                           (2, 6, 4, 3), (10000, 10000, 20000, 0)):
        with nc.Dataset(file) as data:
            assert float(data["T2D"][0, 0, 0]) == 280
            assert float(data["RAINRATE"][0, 0, 0]) * 3600 == pytest.approx(rainfall_mm)
            assert float(data["SWDOWN"][0, 0, 0]) == pytest.approx(shortwave / 3600)
            assert float(data["LWDOWN"][0, 0, 0]) == pytest.approx(10000 / 3600)
            assert float(data["Q2D"][0, 0, 0]) == pytest.approx(0.0038104, rel=1e-3)
    if source == "era5-land" and mode == "hourly":
        # Hourly exports must not be differenced again. This also lacks the prior record.
        rejected_output = tmp_path / "invalid"
        args = args[:-2]
        args[-1] = str(rejected_output)
        with pytest.raises(SystemExit) as error:
            main(args)
        assert error.value.code == 2
        assert "first missing UTC 2020-06-01T22:00:00" in capsys.readouterr().err
        assert not rejected_output.exists()


@pytest.mark.parametrize(("source", "fields", "filename"),
                         [("nldas2", NLDAS, "NLDAS_FORA0125_H.A20190523.0400.020.nc"),
                          ("aorc", AORC, "2019.zarr")])
def test_north_american_forcing_on_regular_grid(tmp_path, source, fields, filename):
    np = pytest.importorskip("numpy")
    xr = pytest.importorskip("xarray")
    nc = pytest.importorskip("netCDF4")
    _geogrid(tmp_path / "geo.nc")
    rain = np.broadcast_to([0.0, 1.0, 3.0, 8.0, 9.0], (5, 5))
    weather = (("K", 280), ("kg kg-1", 0.003), ("m/s", 2), ("m/s", -1),
               ("Pa", 98000), ("W m-2", 25), ("W m-2", 300), ("kg/m^2", rain))
    data = xr.Dataset({
        variable: (("time", "lat", "lon"), np.broadcast_to(value, (1, 5, 5)), {"units": units})
        for variable, (units, value) in zip(fields.values(), weather)
    }, coords={"time": [np.datetime64("2019-05-23T04:00")],
               "lat": [37, 36.5, 35.5, 34.5, 34], "lon": [106, 106.5, 107.5, 108.5, 109]})
    if source == "aorc":
        pytest.importorskip("zarr")
        data.to_zarr(tmp_path / filename, consolidated=True)
    else:
        data.to_netcdf(tmp_path / filename)
    config = tmp_path / "forcing.json"
    config.write_text(json.dumps({"source": source, "geogrid": "geo.nc", "files": [filename],
                                  "start": "2019-05-23T03:00Z", "end": "2019-05-23T04:00Z"}))
    output = tmp_path / "forcing"
    prepare_forcing(config, output)
    with nc.Dataset(output / "2019052304.LDASIN_DOMAIN1") as result:
        np.testing.assert_allclose(result["RAINRATE"][0] * 3600, [[2, 5.5], [2, 5.5]])
        np.testing.assert_allclose(result["SWDOWN"][0], 25)
