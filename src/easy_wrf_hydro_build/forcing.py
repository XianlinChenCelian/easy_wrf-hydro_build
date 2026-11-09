"""Convert local or downloaded weather data into offline WRF-Hydro forcing."""
from __future__ import annotations

from asyncio import TimeoutError as AsyncTimeoutError
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from glob import glob
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import zipfile

from .atmosphere import sha256

UNITS = {
    "T2D": "K", "Q2D": "kg kg-1", "U2D": "m s-1", "V2D": "m s-1",
    "PSFC": "Pa", "SWDOWN": "W m-2", "LWDOWN": "W m-2", "RAINRATE": "mm s-1",
}
NLDAS = dict(zip(UNITS, ("Tair", "Qair", "Wind_E", "Wind_N", "PSurf", "SWdown", "LWdown", "Rainf")))
ERA5_FIELDS = dict(zip(UNITS, ("t2m", "d2m", "u10", "v10", "sp", "ssrd", "strd", "tp")))
AORC = dict(zip(UNITS, ("TMP_2maboveground", "SPFH_2maboveground", "UGRD_10maboveground",
                       "VGRD_10maboveground", "PRES_surface", "DSWRF_surface", "DLWRF_surface",
                       "APCP_surface")))
AORC_STORE = "https://noaa-nws-aorc-v1-1-1km.s3.amazonaws.com/{year}.zarr"
CDS_VARIABLES = (
    "2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind",
    "10m_v_component_of_wind", "surface_pressure", "surface_solar_radiation_downwards",
    "surface_thermal_radiation_downwards", "total_precipitation",
)
ERA5_PRODUCTS = {"era5", "era5-land"}
ERA5_ACCUMULATION_UNITS = {"SWDOWN": {"jm-2", "j/m2"}, "LWDOWN": {"jm-2", "j/m2"},
                           "RAINRATE": {"m", "mofwaterequivalent"}}
# Source units: 0.01 mm liquid water, or 0.25 W/m² averaged over an hour.
ERA5_NEGATIVE_TOLERANCE = {"RAINRATE": 1e-5, "SWDOWN": 900.0, "LWDOWN": 900.0}
PRODUCTS = {"nldas2": NLDAS, "era5": ERA5_FIELDS, "era5-land": ERA5_FIELDS, "aorc": AORC}
DOWNLOAD_PRODUCTS = ("nldas2", "era5-land", "aorc")
COORDS = {
    "time": ("time", "valid_time", "Time"),
    "latitude": ("latitude", "lat", "XLAT_M", "XLAT"),
    "longitude": ("longitude", "lon", "XLONG_M", "XLONG"),
}


def _utc(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Forcing dates need an explicit UTC offset, e.g. 2011-08-26T00:00:00Z.")
    return stamp.astimezone(timezone.utc).replace(tzinfo=None)


def _period(config, hourly=False):
    start, end = _utc(config["start"]), _utc(config["end"])
    seconds = config.get("interval_seconds", 3600)
    if (type(seconds) is not int or seconds <= 0 or seconds % 3600
            or (hourly and seconds != 3600)):
        raise ValueError("Use a positive whole-hour forcing interval. This source requires 3600 s."
                         if hourly else "Use a positive whole-hour forcing interval.")
    if (start.minute or start.second or start.microsecond or end <= start
            or (end - start).total_seconds() % seconds):
        raise ValueError("Forcing start/end must be aligned to the requested whole-hour intervals.")
    step = timedelta(seconds=seconds)
    return start, end, step


def _model_grid(geo):
    import numpy as np
    from netCDF4 import Dataset
    with Dataset(geo) as data:
        names = ("XLAT_M", "XLONG_M")
        if not all(name in data.variables for name in names):
            raise ValueError(f"Use the WPS geo_em file containing XLAT_M and XLONG_M: {geo}")
        latitude, longitude = (np.ma.asarray(data[name][0], dtype="f8").filled(np.nan) for name in names)
    if latitude.ndim != 2 or longitude.shape != latitude.shape or not (
        np.isfinite(latitude).all() and np.isfinite(longitude).all()
        and (abs(latitude) <= 90).all() and (abs(longitude) <= 360).all()
    ):
        raise ValueError(f"Invalid geogrid coordinates: {geo}")
    return latitude, _wrap_longitudes(longitude)


def _wrap_longitudes(values):
    return (values + 180) % 360 - 180


def _coordinates(ds, overrides, source):
    choices = COORDS
    if source in ERA5_PRODUCTS:
        choices = {**COORDS, "time": ("valid_time", "time", "Time")}
    return {
        role: ds[overrides[role]] if role in overrides else ds[next(
            (name for name in names if name in ds.variables), names[0]
        )] for role, names in choices.items()
    }


def _interpolate(latitude, longitude, target_lat, target_lon):
    import numpy as np
    latitude, longitude = np.asarray(latitude), _wrap_longitudes(np.asarray(longitude))
    if latitude.ndim == longitude.ndim == 2:
        if (latitude.shape == longitude.shape == target_lat.shape
                and np.allclose(latitude, target_lat, rtol=0, atol=1e-4)
                and np.allclose(longitude, target_lon, rtol=0, atol=1e-4)):
            return lambda field: field, "matching model coordinates", (slice(None), slice(None))
        raise ValueError("Two-dimensional input coordinates must match the WPS land grid.")
    if latitude.ndim != 1 or longitude.ndim != 1:
        raise ValueError("Use a regular latitude/longitude grid or a matching WPS land grid.")

    def axis(source, target):
        order = np.argsort(source)
        ordered = source[order]
        if len(ordered) < 2 or not np.isfinite(ordered).all() or np.any(np.diff(ordered) <= 0):
            raise ValueError("Source latitude and longitude must be finite and unique.")
        if target.min() < ordered[0] or target.max() > ordered[-1]:
            raise ValueError("Source weather data do not cover the entire WPS land grid. "
                             "Download the domain with a margin.")
        high = np.searchsorted(ordered, target, side="right").clip(1, len(ordered) - 1)
        low = high - 1
        fraction = (target - ordered[low]) / (ordered[high] - ordered[low])
        return order[low], order[high], fraction

    y0, y1, wy = axis(latitude, target_lat)
    x0, x1, wx = axis(longitude, target_lon)
    south, west = min(y0.min(), y1.min()), min(x0.min(), x1.min())
    north, east = max(y0.max(), y1.max()), max(x0.max(), x1.max())
    window = (slice(south, north + 1), slice(west, east + 1))
    y0, y1, x0, x1 = y0 - south, y1 - south, x0 - west, x1 - west

    def remap(values):
        return ((1 - wy) * ((1 - wx) * values[y0, x0] + wx * values[y0, x1])
                + wy * ((1 - wx) * values[y1, x0] + wx * values[y1, x1]))

    return remap, "bilinear in latitude/longitude", window


def _unit_key(value):
    return str(value).strip().lower().replace(" ", "").replace("**", "").replace("^", "")


def _to_model_units(name, values, units, seconds):
    key = _unit_key(units)
    if name == "RAINRATE":
        if key in {"mm/s", "mms-1", "kgm-2s-1", "kg/m2/s"}:
            return values
        if key in {"mm/h", "mmh-1", "kgm-2h-1"}:
            return values / 3600
        if key in {"mm", "kgm-2", "kg/m2"}:
            return values / seconds
        if key in {"m", "mofwaterequivalent"}:
            return values * 1000 / seconds
    elif name in ("SWDOWN", "LWDOWN"):
        if key in {"wm-2", "w/m2"}:
            return values
        if key in {"jm-2", "j/m2"}:
            return values / seconds
    elif name == "PSFC":
        if key == "pa":
            return values
        if key in {"hpa", "mbar"}:
            return values * 100
    elif name in {"U2D", "V2D"} and key in {"ms-1", "m/s"}:
        return values
    elif name == "Q2D" and key in {"kgkg-1", "kg/kg", "g/g", "gg-1", "1", "dimensionless"}:
        return values
    elif name == "Q2D" and key in {"gkg-1", "g/kg"}:
        return values / 1000
    elif name in {"T2D", "dewpoint"}:
        if key in {"k", "kelvin"}:
            return values
        if key in {"c", "°c", "degc", "celsius", "degree_celsius", "degrees_celsius"}:
            return values + 273.15
    raise ValueError(f"Unsupported units for {name}: {units!r}. Check the source metadata.")


def _fields_for(config):
    source = config["source"]
    if source not in PRODUCTS and source != "custom":
        raise ValueError("Forcing source must be aorc, nldas2, era5, era5-land or custom.")
    mapping = {**PRODUCTS.get(source, {}), **config.get("variables", {})}
    if set(mapping) != set(UNITS):
        raise ValueError("Map all eight WRF-Hydro weather fields in variables.")
    fields = {name: ({"name": value} if isinstance(value, str) else value)
              for name, value in mapping.items()}
    if not all(isinstance(spec, dict) and isinstance(spec.get("name"), str)
               for spec in fields.values()):
        raise ValueError("Each variable needs a source name and optional source units.")
    if source in ERA5_PRODUCTS:
        for name, alias in zip(UNITS, CDS_VARIABLES):
            if name not in config.get("variables", {}):
                fields[name]["aliases"] = [alias]
    return source, fields


@contextmanager
def _weather_inputs(paths, parent):
    """Read CDS ZIP members in local scratch without modifying the source files."""
    with ExitStack() as stack:
        scratch = None
        resolved = {}
        for path in paths:
            if path.suffix.lower() in {".grib", ".grib2", ".grb", ".grb2"}:
                raise ValueError(f"GRIB input needs to be exported as hourly gridded NetCDF first: {path}")
            if path.is_dir() and not (path / ".zmetadata").is_file():
                raise ValueError(f"Expected a NetCDF, ZIP, or consolidated Zarr v2 store: {path}")
            if path.is_dir():
                resolved[path] = str(path)
                continue
            if not zipfile.is_zipfile(path):
                resolved[path] = str(path)
                continue
            if scratch is None:
                parent.mkdir(parents=True, exist_ok=True)
                scratch = Path(stack.enter_context(TemporaryDirectory(prefix=".ewhb-weather-input-", dir=parent)))
            with zipfile.ZipFile(path) as bundle:
                members = [entry for entry in bundle.infolist()
                           if Path(entry.filename).suffix.lower() in {".nc", ".nc4", ".netcdf"}
                           and not Path(entry.filename).name.startswith("._") and not entry.is_dir()]
                if not members:
                    raise ValueError(f"No NetCDF weather data in {path}. Use the CDS NetCDF download format.")
                for entry in members:
                    target = scratch / f"input-{len(resolved):06d}.nc"
                    with bundle.open(entry) as source, target.open("xb") as output:
                        shutil.copyfileobj(source, output)
                    resolved[target] = f"{path}!{entry.filename}"
        yield resolved


def _field_spec(ds, spec):
    for name in (spec["name"], *spec.get("aliases", ())):
        if name in ds.data_vars:
            return ds[name]
    return None


def _open_weather(path):
    import xarray as xr

    if path.is_dir():
        return xr.open_zarr(path, consolidated=True, chunks=None)
    return xr.open_dataset(path)


def _index(inputs, fields, coords, needed, model_grid, source):
    import numpy as np

    records = {name: {} for name in fields}
    reference = None
    for path, origin in inputs.items():
        with _open_weather(path) as ds:
            present = {name: variable for name, spec in fields.items()
                       if (variable := _field_spec(ds, spec)) is not None}
            if not present:
                continue
            co = _coordinates(ds, coords, source)
            if co["time"].ndim != 1 or not np.issubdtype(co["time"].dtype, np.datetime64):
                raise ValueError(f"Expected a one-dimensional decoded UTC time coordinate in {origin}.")
            lat, lon = co["latitude"].values, co["longitude"].values
            if reference is None:
                remap, method, window = _interpolate(lat, lon, *model_grid)
                reference = (lat, lon)
            elif not np.array_equal(reference[0], lat) or not np.array_equal(reference[1], lon):
                raise ValueError(f"Weather inputs use different source grids: {origin}.")
            time_dim = co["time"].dims[0]
            space_dims = tuple(dict.fromkeys((*co["latitude"].dims, *co["longitude"].dims)))
            if len(space_dims) != 2:
                raise ValueError(f"Expected exactly two horizontal weather dimensions in {origin}.")
            for name, variable in present.items():
                axes = set(variable.dims)
                if source in ERA5_PRODUCTS:
                    axes.discard("expver")
                if axes != {time_dim, *space_dims}:
                    raise ValueError(f"{variable.name} must use hourly time and two horizontal axes: {origin}")
                for index, value in enumerate(co["time"].values.astype("datetime64[us]")):
                    if value not in needed[name]:
                        continue
                    if value in records[name]:
                        raise ValueError(f"Duplicate time for {name}: {value}. Check source files.")
                    records[name][value] = (path, variable.name, index, time_dim, space_dims)
    for name, times in needed.items():
        missing = times - records[name].keys()
        if missing:
            raise ValueError(f"Missing {len(missing)} records for {name}; first missing UTC {min(missing)}.")
    return records, remap, method, window


def _write_hour(path, stamp, fields, model_grid):
    import numpy as np
    from netCDF4 import Dataset

    with Dataset(path, "w", format="NETCDF4_CLASSIC") as data:
        ny, nx = model_grid[0].shape
        for name, size in (("Time", None), ("south_north", ny), ("west_east", nx), ("DateStrLen", 19)):
            data.createDimension(name, size)
        times = data.createVariable("Times", "S1", ("Time", "DateStrLen"))
        times[0] = np.frombuffer(stamp.strftime("%Y-%m-%d_%H:%M:%S").encode("ascii"), "S1")
        valid_time = data.createVariable("valid_time", "f8", ("Time",))
        valid_time.units = "seconds since 1970-01-01 00:00:00"
        valid_time.calendar = "standard"
        valid_time[0] = (stamp - datetime(1970, 1, 1)).total_seconds()
        for name, values in fields.items():
            var = data.createVariable(name, "f4", ("Time", "south_north", "west_east"), zlib=True)
            var.units = UNITS[name]
            var[0] = values
        for name, units, values in zip(("XLAT", "XLONG"), ("degrees_north", "degrees_east"), model_grid):
            var = data.createVariable(name, "f4", ("south_north", "west_east"))
            var.units = units
            var[:] = values


def prepare_forcing(config_path: Path, output: Path, run_dir: Path | None = None):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return prepare_weather(config, config_path.parent, output, run_dir)


def _era5_expver(variable):
    if "expver" not in variable.dims:
        return variable
    versions = [int(value) for value in variable["expver"].values]
    if not versions or len(set(versions)) != len(versions) or not set(versions) <= {1, 5}:
        raise ValueError(f"Unsupported ECMWF expver values in {variable.name}: {versions}.")
    final = variable.isel(expver=versions.index(1), drop=True) if 1 in versions else None
    if 5 in versions:
        preliminary = variable.isel(expver=versions.index(5), drop=True)
        return final.fillna(preliminary) if final is not None else preliminary
    return final


def prepare_weather(config: dict, base: Path, output: Path, run_dir: Path | None = None):
    import numpy as np

    source, fields = _fields_for(config)
    start, end, step = _period(config, hourly=source != "custom")
    count = (end - start) // step
    stamps = [start + step * i for i in range(1, count + 1)]
    label = config.get("time_label", "end")
    if label not in {"start", "end"} or (source != "custom" and label != "end"):
        raise ValueError("Only custom forcing may change time_label from end to start.")
    offset = step if label == "start" else timedelta(0)
    model_grid_file = (base / Path(config["geogrid"]).expanduser()).resolve()
    model_grid = _model_grid(model_grid_file)
    patterns = config["files"]
    if not isinstance(patterns, list) or not patterns:
        raise ValueError("files must be a nonempty list of NetCDF, ZIP, Zarr, or glob paths.")
    paths = sorted({Path(file).resolve() for pattern in patterns
                    for file in glob(str(base / Path(pattern).expanduser()))
                    if not Path(file).name.startswith("._")})
    if not paths:
        raise ValueError("No weather inputs matched files.")
    if output.exists():
        raise ValueError(f"Choose a new forcing output directory: {output}")
    link = None
    if run_dir is not None:
        if not run_dir.is_dir():
            raise ValueError(f"Run directory does not exist: {run_dir}")
        link = run_dir / "FORCING"
        if link.exists() or link.is_symlink() or link == output:
            raise ValueError(f"FORCING already exists or overlaps the output: {link}")

    time_keys = {np.datetime64(s - offset, "us") for s in stamps}
    needed = {name: set(time_keys) for name in fields}
    accumulation = config.get("accumulation", "daily" if source == "era5-land" else "hourly")
    if "accumulation" in config and (source not in ERA5_PRODUCTS or accumulation not in {"daily", "hourly"}
                                     or (source == "era5" and accumulation != "hourly")):
        raise ValueError("ERA5 uses hourly accumulations. ERA5-Land accepts daily or hourly explicitly.")
    cumulative = {"SWDOWN", "LWDOWN", "RAINRATE"} if source == "era5-land" and accumulation == "daily" else set()
    for name in cumulative:
        needed[name].update(np.datetime64(s - step, "us") for s in stamps if s.hour != 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    with _weather_inputs(paths, output.parent) as inputs, TemporaryDirectory(
        prefix=".ewhb-forcing-", dir=output.parent
    ) as temporary:
        records, remap, method, window = _index(inputs, fields, config.get("coordinates", {}), needed, model_grid, source)
        staging = Path(temporary) / "FORCING"
        staging.mkdir()
        source_units = {name: set() for name in fields}
        source_fields = {name: set() for name in fields}
        packing_corrections = {}
        for stamp in stamps:
            key = np.datetime64(stamp - offset, "us")
            arrays = {}
            with ExitStack() as stack:
                opened = {}

                def read_field(name, time_key):
                    path, variable_name, index, time_dim, space_dims = records[name][time_key]
                    if path not in opened:
                        opened[path] = stack.enter_context(_open_weather(path))
                    spec = fields[name]
                    subset = {time_dim: index, **dict(zip(space_dims, window))}
                    var = opened[path][variable_name].isel(subset)
                    source_fields[name].add(variable_name)
                    if source in ERA5_PRODUCTS:
                        var = _era5_expver(var)
                    values = var.transpose(*space_dims).values.astype("f8")
                    return values, spec.get("units", var.attrs.get("units", ""))

                for name in fields:
                    values, units = read_field(name, key)
                    source_units[name].add(str(units))
                    allowed_units = ERA5_ACCUMULATION_UNITS.get(name) if source in ERA5_PRODUCTS else None
                    if allowed_units and _unit_key(units) not in allowed_units:
                        raise ValueError(f"Unexpected {source} accumulation units for {name}: {units!r}.")
                    if name in cumulative and stamp.hour != 1:
                        previous, previous_units = read_field(name, key - np.timedelta64(1, "h"))
                        if _unit_key(units) != _unit_key(previous_units):
                            raise ValueError(f"Units changed in the accumulation for {name} at {stamp}.")
                        values -= previous
                    if allowed_units and (negative := values < 0).any():
                        minimum = float(values[negative].min())
                        if minimum < -ERA5_NEGATIVE_TOLERANCE[name]:
                            raise ValueError(f"Negative hourly {name} ({minimum:g} {units}) at {stamp} UTC. "
                                             f"Check the source and accumulation={accumulation}.")
                        info = packing_corrections.setdefault(name, {"count": 0, "minimum_source_value": 0})
                        info["count"] += int(negative.sum())
                        info["minimum_source_value"] = min(info["minimum_source_value"], minimum)
                        values = np.maximum(values, 0)
                    target = "dewpoint" if source in ERA5_PRODUCTS and name == "Q2D" else name
                    arrays[name] = _to_model_units(target, values, units, step.total_seconds())
            if source in ERA5_PRODUCTS:
                # ECMWF IFS saturation over liquid water, evaluated at 2 m dew point.
                dewpoint = arrays["Q2D"]
                vapor_pressure = 611.21 * np.exp(17.502 * (dewpoint - 273.16) / (dewpoint - 32.19))
                epsilon = 0.621981
                arrays["Q2D"] = epsilon * vapor_pressure / (arrays["PSFC"] - (1 - epsilon) * vapor_pressure)
            arrays = {name: remap(values) for name, values in arrays.items()}
            for name, values in arrays.items():
                if not np.isfinite(values).all() or (
                    name in {"RAINRATE", "Q2D", "SWDOWN", "LWDOWN"} and (values < 0).any()
                ) or (name == "Q2D" and (values >= 1).any()) or (
                    name in {"PSFC", "T2D"} and (values <= 0).any()
                ):
                    raise ValueError(f"Missing or physically invalid {name} at {stamp} UTC.")
            _write_hour(staging / stamp.strftime("%Y%m%d%H.LDASIN_DOMAIN1"), stamp, arrays, model_grid)

        manifest = {
            "source": source, "variables": fields, "files": [str(path) for path in paths],
            "input_records": list(inputs.values()),
            "resolved_variables": {name: sorted(names) for name, names in source_fields.items()},
            "source_units": {name: sorted(units) for name, units in source_units.items()},
            "model_units": UNITS, "source_time_label": label,
            "geogrid": str(model_grid_file), "geogrid_sha256": sha256(model_grid_file),
            "regridding": method, "start_utc": start.isoformat() + "Z", "end_utc": end.isoformat() + "Z",
            "first_file": stamps[0].strftime("%Y%m%d%H.LDASIN_DOMAIN1"),
            "last_file": stamps[-1].strftime("%Y%m%d%H.LDASIN_DOMAIN1"),
            "forcing_file_count": count, "FORC_TYP": 1, "FORCING_TIMESTEP": int(step.total_seconds()),
            "INDIR": "./FORCING" if link else str(output),
        }
        if source in ERA5_PRODUCTS:
            manifest["accumulation"] = accumulation
            manifest["negative_accumulation_corrections"] = packing_corrections
        (staging / "forcing-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        staging.rename(output)
    if link is not None:
        try:
            link.symlink_to(output, target_is_directory=True)
        except OSError as exc:
            manifest["INDIR"] = str(output)
            (output / "forcing-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            raise ValueError(f"Forcing is ready at {output}. Set INDIR to this path or use a Linux filesystem "
                             f"that permits creating {link}. {exc}") from exc
    return manifest


def fetch_aorc(geo: Path, start: str, end: str, output: Path):
    """Download only NOAA AORC hours and spatial chunks surrounding the WPS grid."""
    import aiohttp
    import dask
    import fsspec
    import xarray as xr

    first, last, step = _period({"start": start, "end": end}, hourly=True)
    if output.exists():
        raise ValueError(f"Choose a new AORC cache directory: {output}")
    west, south, east, north = _bounds(geo, 0.03)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ewhb-aorc-", dir=output.parent) as temporary:
        staging = Path(temporary) / "aorc"
        staging.mkdir()
        times = first + step
        files = []
        while times <= last:
            year_end = datetime(times.year + 1, 1, 1)
            stop = min(last, times + timedelta(days=2) - step, year_end - step)
            url = AORC_STORE.format(year=times.year)
            for attempt in range(3):
                mapper = fsspec.get_mapper(url, client_kwargs={"trust_env": True,
                                                               "timeout": aiohttp.ClientTimeout(total=60)})
                try:
                    with xr.open_zarr(mapper, consolidated=True, chunks={}) as data:
                        coords = {}
                        for role, lo, hi in (("latitude", south, north), ("longitude", west, east)):
                            axis = data[role].values
                            coords[role] = slice(lo, hi) if axis[0] < axis[-1] else slice(hi, lo)
                        subset = data[list(AORC.values())].sel(time=slice(times, stop), **coords)
                        expected = (stop - times) // step + 1
                        if (subset.sizes["time"] != expected or subset.sizes["latitude"] < 2
                                or subset.sizes["longitude"] < 2):
                            raise ValueError(f"AORC does not cover requested region or time: {url}, {times}–{stop}.")
                        # Complete remote reads before creating the NetCDF file.
                        with dask.config.set(scheduler="synchronous"):
                            subset.load()
                    break
                except (aiohttp.ClientConnectionError, AsyncTimeoutError) as exc:
                    if attempt == 2:
                        raise ValueError(f"NOAA AORC download failed for {times}–{stop}: {exc}") from exc
            path = staging / f"aorc-{times:%Y%m%d%H}.nc"
            subset.to_netcdf(path, encoding={name: {"zlib": True} for name in AORC.values()})
            files.append({"name": path.name, "sha256": sha256(path), "source": url})
            times = stop + step
        manifest = {"source": "aorc", "files": files, "bounds_wgs84": [west, south, east, north]}
        (staging / "download-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        staging.rename(output)
    return manifest


def _bounds(geo, margin):
    lat, lon = _model_grid(geo)
    if lon.max() - lon.min() > 180:
        raise ValueError("Source downloading does not support domains crossing the antimeridian.")
    return [max(-180, float(lon.min()) - margin), max(-90, float(lat.min()) - margin),
            min(180, float(lon.max()) + margin), min(90, float(lat.max()) + margin)]


def fetch_weather(source, geo, start, end, output):
    if source == "aorc":
        return fetch_aorc(geo, start, end, output)
    first, last, step = _period({"start": start, "end": end}, hourly=True)
    if output.exists():
        raise ValueError(f"Choose a new weather cache directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ewhb-weather-", dir=output.parent) as temporary:
        staging = Path(temporary) / "data"
        staging.mkdir()
        if source == "era5-land":
            provider = _download_cds(staging, _bounds(geo, 0.25), first, last)
        elif source == "nldas2":
            provider = _download_nldas(staging, first + step, last, step)
        else:
            raise ValueError(f"Unknown weather download source: {source}")
        files = [{"name": path.name, "sha256": sha256(path)} for path in sorted(staging.glob("*.nc"))
                 if not path.name.startswith("._")]
        if not files:
            raise ValueError(f"The {source} provider returned no NetCDF files.")
        manifest = {"source": source, "provider": provider, "files": files,
                    "start_utc": first.isoformat() + "Z", "end_utc": last.isoformat() + "Z"}
        (staging / "download-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        staging.rename(output)
    return manifest


def _download_nldas(staging, first, last, step):
    import earthaccess

    if not earthaccess.login(strategy="netrc").authenticated:
        raise ValueError("Configure NASA Earthdata Login and authorize GES DISC first (docs/forcing.md).")
    concept = "C2033151148-GES_DISC"
    granules = earthaccess.search_data(concept_id=concept, temporal=(first.isoformat(), last.isoformat()))
    if not granules:
        raise ValueError("NASA found no matching NLDAS-2 FORA granules.")
    earthaccess.download(granules, local_path=str(staging), threads=4)
    stamp = first
    while stamp <= last:
        name = f"NLDAS_FORA0125_H.A{stamp:%Y%m%d.%H}00.020.nc"
        if not (staging / name).is_file():
            raise ValueError(f"Incomplete NASA download; missing {name}.")
        stamp += step
    return concept


def _download_cds(staging, bounds, first, last):
    import cdsapi

    client = cdsapi.Client(quiet=True)
    dataset = "reanalysis-era5-land"
    west, south, east, north = bounds
    # Include the previous hour needed to difference a daily accumulation.
    day = first.replace(hour=0)
    while day <= last:
        next_month = datetime(day.year + (day.month == 12), day.month % 12 + 1, 1)
        stop = min(last, next_month - timedelta(days=1))
        request = {"variable": list(CDS_VARIABLES), "year": f"{day:%Y}", "month": f"{day:%m}",
                   "day": [f"{i:02d}" for i in range(day.day, stop.day + 1)],
                   "time": [f"{i:02d}:00" for i in range(24)],
                   "area": [north, west, south, east], "data_format": "netcdf",
                   "download_format": "unarchived"}
        path = staging / f"era5-land-{day:%Y%m}.download"
        client.retrieve(dataset, request, str(path))
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as bundle:
                for index, member in enumerate(bundle.namelist()):
                    if member.endswith(".nc"):
                        with bundle.open(member) as src, (staging / f"era5-land-{day:%Y%m}-{index}.nc").open("xb") as dst:
                            shutil.copyfileobj(src, dst)
            path.unlink()
        else:
            path.rename(path.with_suffix(".nc"))
        day = next_month
    return dataset
