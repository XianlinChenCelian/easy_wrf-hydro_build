from pathlib import Path
import json

import pytest

from easy_wrf_hydro_build.forcing import _to_model_units, prepare_forcing


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


def test_era5_land_midnight_uses_previous_cycle_and_01_resets(tmp_path: Path):
    np = pytest.importorskip("numpy")
    nc = pytest.importorskip("netCDF4")
    xr = pytest.importorskip("xarray")

    with nc.Dataset(tmp_path / "geo.nc", "w") as geo:
        for dim, size in (("Time", 1), ("y", 2), ("x", 2)):
            geo.createDimension(dim, size)
        geo.createVariable("XLAT_M", "f4", ("Time", "y", "x"))[0] = [[35, 35], [36, 36]]
        geo.createVariable("XLONG_M", "f4", ("Time", "y", "x"))[0] = [[107, 108], [107, 108]]

    start = np.datetime64("2020-06-01T22:00:00")
    time = start + np.arange(5) * np.timedelta64(1, "h")
    fields = {
        "tp": ([.022, .024, .030, .004, .007], "m"),
        "ssrd": ([10000, 20000, 30000, 20000, 25000], "J m**-2"),
        "strd": ([220000, 230000, 240000, 10000, 20000], "J m**-2"),
        "t2m": ([280] * 5, "K"), "d2m": ([273.16] * 5, "K"),
        "u10": ([2] * 5, "m s**-1"), "v10": ([-1] * 5, "m s**-1"),
        "sp": ([100000] * 5, "Pa"),
    }
    xr.Dataset({
        name: (("valid_time", "latitude", "longitude"),
               np.broadcast_to(np.array(values)[:, None, None], (5, 2, 2)), {"units": units})
        for name, (values, units) in fields.items()
    }, coords={"valid_time": time, "latitude": [35, 36], "longitude": [107, 108]}).to_netcdf(
        tmp_path / "era5-land.nc"
    )
    config = tmp_path / "forcing.json"
    config.write_text(json.dumps({"source": "era5-land", "geogrid": "geo.nc",
                                  "files": ["era5-land.nc"], "start": "2020-06-01T22:00:00Z",
                                  "end": "2020-06-02T02:00:00Z"}))
    output = tmp_path / "FORCING"
    report = prepare_forcing(config, output)
    assert report["first_file"] == "2020060123.LDASIN_DOMAIN1"
    assert report["forcing_file_count"] == 4
    for file, rainfall_mm in zip(sorted(output.glob("*.LDASIN_DOMAIN1")), (2, 6, 4, 3)):
        with nc.Dataset(file) as data:
            assert float(data["RAINRATE"][0, 0, 0]) * 3600 == pytest.approx(rainfall_mm)
            assert float(data["LWDOWN"][0, 0, 0]) == pytest.approx(10000 / 3600)
            assert float(data["Q2D"][0, 0, 0]) == pytest.approx(0.0038104, rel=1e-3)
