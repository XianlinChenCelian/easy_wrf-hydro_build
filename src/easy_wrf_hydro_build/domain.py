"""Prepare an offline Noah-MP domain with WPS and NCAR's open GIS scripts."""

from __future__ import annotations

import csv
from importlib.util import find_spec
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.request import urlopen
import zipfile

from .atmosphere import ATMOSPHERE_PROFILES, sha256, unpack

GEO = "geo_em.d01.nc"
FULLDOM = "Fulldom_hires.nc"
WRFINPUT = "wrfinput_d01.nc"
GIS_SCRIPTS = (
    "Build_Routing_Stack.py", "wrfhydro_functions.py",
    "Create_SoilProperties_and_Hydro2D.py", "Create_wrfinput_from_Geogrid.py",
)
TABLES = ("SOILPARM.TBL", "MPTABLE.TBL", "GENPARM.TBL", "HYDRO.TBL")
STATIC_URL = "https://www2.mmm.ucar.edu/wrf/src/wps_files/geog_{resolution}_res_mandatory.tar.gz"
STATIC_SHA256 = {
    "high": "89b026b9db0a03c0c995e53b4a1d99663af1f6bda21b3b34c3c2c07386da5493",
    "low": "cbdbcc43554d946a38cbce658b7d563afd7a2889f2c0735b8aa3f2206c7256e7",
}
# The Python wrapper honors WBT_PATH for downloads but still defaults to its own
# package directory when it launches the binary.
ROUTING_LAUNCHER = """
import os, runpy, subprocess, sys
from pathlib import Path
from whitebox import whitebox_tools

class ConfiguredWhitebox(whitebox_tools.WhiteboxTools):
    def __init__(self):
        super().__init__()
        self.set_whitebox_dir(os.environ['WBT_PATH'])

    def run_tool(self, tool_name, args, callback=None):
        command = [str(Path(self.exe_path) / self.exe_name),
                   '--run=' + whitebox_tools.to_camelcase(tool_name),
                   '--wd=' + self.work_dir, *args,
                   '-v=false', '--compress_rasters=False']
        result = subprocess.run(command, cwd=self.exe_path, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'WhiteboxTools {tool_name} exited {result.returncode}: {result.stdout.strip()}')
        return 0

whitebox_tools.WhiteboxTools = ConfiguredWhitebox
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(sys.argv[0]).parent))
runpy.run_path(sys.argv[0], run_name='__main__')
"""

# GDAL can choose the projected x/y fields in Route_Link.nc while assigning a
# geographic CRS. Construct the midpoint geometry from the explicit lon/lat fields.
ROUTE_MIDPOINTS = """
def ewhb_route_midpoints(path, id_field):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds = ogr.GetDriverByName('Memory').CreateDataSource('reach-midpoints')
    layer = ds.CreateLayer('midpoints', srs, ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn(id_field, ogr.OFTInteger64))
    with netCDF4.Dataset(path) as data:
        for reach, lon, lat in zip(data[id_field][:], data['lon'][:], data['lat'][:]):
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint_2D(float(lon), float(lat))
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField(id_field, int(reach))
            feature.SetGeometry(point)
            layer.CreateFeature(feature)
    return ds
"""


def _path(base: Path, value: str) -> Path:
    return (base / Path(value).expanduser()).resolve()


def _require(path: Path, *, directory: bool = False) -> Path:
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError(f"Missing {'directory' if directory else 'file'}: {path}")
    return path


def fetch_geog(cache: Path, resolution: str, archive: Path | None = None) -> dict:
    """Populate a shared WPS data directory, using an existing archive if provided."""
    url = STATIC_URL.format(resolution=resolution)
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / resolution
    report = destination / "static-manifest.json"
    if report.is_file():
        result = json.loads(report.read_text(encoding="utf-8"))
        _require(Path(result["geog_data"]), directory=True)
        if archive and sha256(_require(archive)) != result["archive_sha256"]:
            raise ValueError(f"Cache has a different source archive: {destination}")
        return result
    if destination.exists():
        raise ValueError(f"Choose another cache; {destination} already exists without a manifest.")
    estimate = 36 if resolution == "high" else 2
    if shutil.disk_usage(cache).free < estimate * 1024**3:
        raise ValueError(f"Need about {estimate} GiB free in {cache} to prepare {resolution} WPS data.")
    with TemporaryDirectory(prefix=f".{resolution}-", dir=cache) as work:
        temporary = Path(work)
        if archive is None:
            archive = temporary / f"geog-{resolution}.tar.gz"
            with urlopen(url, timeout=90) as source, archive.open("wb") as stream:
                shutil.copyfileobj(source, stream, length=1024**2)
        digest = sha256(_require(archive))
        if digest != STATIC_SHA256[resolution]:
            raise ValueError(f"Static data SHA-256 mismatch for {archive}. Check the archive and resolution.")
        extracted = temporary / "extracted"
        source_root = unpack(archive, extracted)
        expected_root = "WPS_GEOG" if resolution == "high" else "WPS_GEOG_LOW_RES"
        if source_root.name != expected_root or not any(source_root.glob("*/index")):
            raise ValueError(f"Expected NCAR's {expected_root} archive for {resolution} resolution.")
        result = {"geog_data": str(destination / source_root.name),
                  "geog_data_res": "default" if resolution == "high" else "lowres",
                  "archive_sha256": digest, "source": url}
        (extracted / report.name).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        extracted.rename(destination)
    return result


def _number(value, name, minimum, maximum, *, integer=False):
    if (type(value) not in ((int,) if integer else (int, float))
            or not minimum <= value <= maximum):
        raise ValueError(f"{name} must be {'an integer' if integer else 'a number'} "
                         f"from {minimum} to {maximum}.")
    return value


def _domain_values(domain: dict) -> dict:
    values = {
        "cell_m": _number(domain["cell_m"], "cell_m", 1, 100000),
        "ref_lat": _number(domain["ref_lat"], "ref_lat", -89, 89),
        "ref_lon": _number(domain["ref_lon"], "ref_lon", -180, 180),
        "truelat1": _number(domain["truelat1"], "truelat1", -89, 89),
        "truelat2": _number(domain["truelat2"], "truelat2", -89, 89),
        "stand_lon": _number(domain.get("stand_lon", domain["ref_lon"]), "stand_lon", -180, 180),
    }
    if not values["truelat1"] * values["truelat2"] > 0:
        raise ValueError("Lambert standard parallels must be in the same hemisphere.")
    return values


def _projection(values):
    from pyproj import Proj
    return Proj(proj="lcc", lat_0=values["ref_lat"], lon_0=values["stand_lon"],
                lat_1=values["truelat1"], lat_2=values["truelat2"], R=6370000)


def _boundary_coords(path):
    from osgeo import gdal, osr
    from shapely import from_wkb, get_coordinates

    vector = gdal.OpenEx(str(path), gdal.OF_VECTOR)
    if vector is None or vector.GetLayerCount() != 1:
        raise ValueError(f"Use a boundary file with exactly one vector layer: {path}")
    layer = vector.GetLayer()
    source = layer.GetSpatialRef()
    if source is None:
        raise ValueError(f"Boundary has no coordinate reference system: {path}")
    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source, wgs84)
    coordinates = []
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is None or geometry.GetGeometryName() not in {"POLYGON", "MULTIPOLYGON"}:
            raise ValueError(f"Expected polygon geometry in {path}")
        geometry = geometry.Clone()
        if geometry.Transform(transform) != 0:
            raise ValueError(f"Could not transform boundary to WGS84: {path}")
        coordinates.extend(get_coordinates(from_wkb(bytes(geometry.ExportToWkb()))))
    if not coordinates:
        raise ValueError(f"Boundary has no vertices: {path}")
    return zip(*coordinates)


def _station_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"FID", "LAT", "LON"} <= set(reader.fieldnames or []):
            raise ValueError(f"Station CSV requires FID,LAT,LON columns: {path}")
        rows = []
        ids = set()
        for row in reader:
            station = row["FID"].strip()
            lon, lat = float(row["LON"]), float(row["LAT"])
            if (not station or not station.isascii() or len(station) > 15 or station in ids
                    or not (-180 <= lon <= 180 and -90 < lat < 90)):
                raise ValueError(f"Invalid or duplicate station {station!r} in {path}")
            rows.append((station, lon, lat))
            ids.add(station)
    if not rows:
        raise ValueError(f"Station CSV is empty: {path}")
    return rows


def _grid(domain, values, boundary, stations):
    projection = _projection(values)
    cell = values["cell_m"]
    x0, y0 = projection(values["ref_lon"], values["ref_lat"], errcheck=True)
    locations = [(lon, lat) for _, lon, lat in stations]
    if boundary:
        lons, lats = _boundary_coords(boundary)
        locations.extend(zip(lons, lats))
    x, y = projection(*zip(*locations), errcheck=True) if locations else ((), ())
    required_x = max((abs(p - x0) for p in x), default=0)
    required_y = max((abs(p - y0) for p in y), default=0)
    if "e_we" in domain or "e_sn" in domain:
        we = _number(domain.get("e_we"), "e_we", 3, 10000, integer=True)
        sn = _number(domain.get("e_sn"), "e_sn", 3, 10000, integer=True)
    elif boundary:
        pad = _number(domain.get("padding_cells", 3), "padding_cells", 1, 1000, integer=True)
        we = max(3, math.ceil(2 * required_x / cell) + 2 * pad + 1)
        sn = max(3, math.ceil(2 * required_y / cell) + 2 * pad + 1)
    else:
        raise ValueError("Supply a watershed boundary or both e_we and e_sn.")
    if required_x >= (we - 1) * cell / 2 or required_y >= (sn - 1) * cell / 2:
        raise ValueError("The grid does not contain the basin boundary and all stations. "
                         "Increase e_we/e_sn or change the domain center.")
    return we, sn


def _wps_string(value):
    if any(char in str(value) for char in ("'", "\n", "\r")):
        raise ValueError(f"WPS cannot use this value in namelist.wps: {value!r}")
    return f"'{value}'"


def _namelist(values, we, sn, static, resolution):
    return f"""&share
 wrf_core = 'ARW',
 max_dom = 1,
 start_date = '2000-01-01_00:00:00',
 end_date = '2000-01-01_00:00:00',
 io_form_geogrid = 2,
/
&geogrid
 parent_id = 1,
 parent_grid_ratio = 1,
 i_parent_start = 1,
 j_parent_start = 1,
 e_we = {we},
 e_sn = {sn},
 dx = {values['cell_m']},
 dy = {values['cell_m']},
 map_proj = 'lambert',
 ref_lat = {values['ref_lat']},
 ref_lon = {values['ref_lon']},
 truelat1 = {values['truelat1']},
 truelat2 = {values['truelat2']},
 stand_lon = {values['stand_lon']},
 geog_data_res = {_wps_string(resolution)},
 geog_data_path = {_wps_string(static)},
/
"""


def _run(command, folder, name, env=None):
    log = folder / f"{name}.log"
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=folder, stdout=stream, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        if name == "routing" and "Found 0 lakes on active channels." in log.read_text(errors="replace"):
            raise ValueError(f"No lake polygons intersect active channels. Check the lake layer, "
                             f"its projection, and the stream threshold. See {log}")
        raise ValueError(f"{name} failed (exit {result.returncode}). See {log}")


def _nc(path, dimensions, variables):
    from netCDF4 import Dataset
    _require(path)
    with Dataset(path) as data:
        for name, size in dimensions.items():
            if name not in data.dimensions or (size is not None and len(data.dimensions[name]) != size):
                raise ValueError(f"Unexpected dimension {name} in {path}; expected {size}.")
        missing = set(variables) - data.variables.keys()
        if missing:
            raise ValueError(f"Missing fields {', '.join(sorted(missing))} in {path}.")


def _extract_routing(archive, folder):
    with zipfile.ZipFile(_require(archive)) as bundle:
        for member in bundle.infolist():
            name = PurePosixPath(member.filename)
            if member.is_dir():
                continue
            if len(name.parts) != 1 or "\\" in member.filename:
                raise ValueError(f"Unexpected routing archive entry: {member.filename}")
            with bundle.open(member) as source, (folder / name.name).open("xb") as target:
                shutil.copyfileobj(source, target)


def _whitebox_env(output):
    binary = shutil.which("whitebox_tools")
    if not binary:
        raise ValueError("Install WhiteboxTools in the domain environment and add it to PATH.")
    # Whitebox writes settings beside its executable. Keep those writes in the case.
    tools = output / "whitebox"
    tools.mkdir()
    shutil.copy2(binary, tools / Path(binary).name)
    env = dict(os.environ, WBT_PATH=str(tools))
    return env


def _routing_scripts(scripts, output):
    staged = output / "ncar-gis"
    staged.mkdir()
    for name, path in scripts.items():
        shutil.copyfile(path, staged / name)
    functions = staged / "wrfhydro_functions.py"
    code = functions.read_text(encoding="utf-8")
    changes = {
        # Preserve leading zeroes in fixed-width identifiers with NetCDF4 >= 1.7.
        "netCDF4.stringtochar(numpy.array(gage_strs, dtype='S15'))":
            "numpy.array(gage_strs, dtype='S15').view('S1').reshape(-1, 15)",
        # Use the snapped channel cell both for reach association and its basin.
        "FeatToRaster(frxst_FC, fac, 'RASTID'":
            "FeatToRaster(os.path.join(projdir, snapPour1), fac, 'RASTID'",
        "wbt.watershed(fdir, snapPour2, watershed_file":
            "wbt.watershed(fdir, snapPour1, watershed_file",
        "link_ds = ogr.Open(in_RL, 0)":
            "link_ds = ewhb_route_midpoints(in_RL, link_ID_field)",
    }
    for old, new in changes.items():
        if code.count(old) != 1:
            raise ValueError("Unsupported NCAR GIS script. Use the documented revision.")
        code = code.replace(old, new)
    functions.write_text(code + ROUTE_MIDPOINTS, encoding="utf-8")
    runner = staged / GIS_SCRIPTS[0]
    code = runner.read_text(encoding="utf-8")
    cleanup = "    if cleanUp:\n        shutil.rmtree(projdir)"
    if code.count(cleanup) != 1:
        raise ValueError("Unsupported NCAR routing script. Use the documented revision.")
    # On exFAT macOS can remove the AppleDouble sidecar during this traversal.
    # Keep the upstream scratch tree intact until its results are validated.
    runner.write_text(code.replace(cleanup, ""), encoding="utf-8")
    return runner


def _check_stations(folder, stations, reach, spacing, domain):
    from netCDF4 import Dataset
    import numpy as np
    from pyproj import Geod

    with (folder / "Gage_Crosswalk.csv").open(newline="", encoding="utf-8") as stream:
        lookup = {row["GageID"]: int(row["frxst_pts"]) for row in csv.DictReader(stream)}
    wanted = {station for station, _, _ in stations}
    geodesic = Geod(ellps="WGS84")
    projection = _projection(domain)
    with Dataset(folder / FULLDOM) as data:
        points = data["frxst_pts"][:]
        channel = data["CHANNELGRID"][:]
        found = {key for key, value in lookup.items() if np.any((points == value) & (channel >= 0))}
        if wanted - found:
            raise ValueError(f"Stations did not snap to active channels: {', '.join(sorted(wanted - found))}. "
                             "Check the DEM, grid ratio, and stream threshold.")
        result = {}
        for station, lon, lat in stations:
            row, column = (int(index[0]) for index in np.where(points == lookup[station]))
            snapped_lat = float(data["LATITUDE"][row, column])
            snapped_lon = float(data["LONGITUDE"][row, column])
            _, _, distance = geodesic.inv(lon, lat, snapped_lon, snapped_lat)
            accumulation = int(data["FLOWACC"][row, column])
            result[station] = {"row": row, "column": column,
                               "latitude": snapped_lat, "longitude": snapped_lon,
                               "snap_distance_m": round(distance, 1),
                               "accumulation_cells": accumulation,
                               "nominal_upstream_km2": round(accumulation * spacing**2 / 1e6, 2)}
            if len(stations) == 1:
                basin = data["basn_msk"][:]
                basin_id = int(basin[row, column])
                if basin_id <= 0:
                    raise ValueError(f"No delineated upstream basin for station {station}.")
                mask = (basin == basin_id).filled(False)
                scale = projection.get_factors(data["LONGITUDE"][:][mask],
                                               data["LATITUDE"][:][mask]).areal_scale
                result[station]["upstream_km2_projection_corrected"] = round(
                    float(np.sum(spacing**2 / scale)) / 1e6, 2,
                )
    if reach:
        with Dataset(folder / "Route_Link.nc") as data:
            gauges = [b"".join(row).decode("ascii").strip()
                      for row in data["gages"][:].filled(b" ")]
            links = data["link"][:]
            for station in sorted(wanted):
                if gauges.count(station) != 1:
                    raise ValueError(f"Expected one Route_Link.nc association for station {station}.")
                result[station]["link"] = int(links[gauges.index(station)])
    return result


def _routing_summary(path):
    from netCDF4 import Dataset
    import numpy as np

    channels = 0
    with Dataset(path) as data:
        rows = len(data.dimensions["y"])
        for offset in range(0, rows, 256):
            section = slice(offset, offset + 256)
            elevation = data["TOPOGRAPHY"][section, :]
            if np.ma.getmaskarray(elevation).any() or not np.isfinite(elevation).all():
                raise ValueError("Routing DEM has missing elevations. Cover the entire WPS grid, "
                                 "including the area outside the watershed.")
            channels += np.count_nonzero(data["CHANNELGRID"][section, :].filled(-1) >= 0)
    if not channels:
        raise ValueError("No active channel cells. Check the DEM and stream threshold.")
    return int(channels)


def _check_lakes(folder, reach):
    from netCDF4 import Dataset
    import numpy as np

    with Dataset(_require(folder / "LAKEPARM.nc")) as lakes:
        ids = {int(value) for value in lakes["lake_id"][:].compressed() if value > 0}
    if reach:
        with Dataset(folder / "Route_Link.nc") as routing:
            links = routing["NHDWaterbodyComID"][:]
            mapped = {int(value) for value in links.compressed() if value > 0}
    else:
        with Dataset(folder / FULLDOM) as routing:
            lake_grid = routing["LAKEGRID"][:]
            mapped = {int(value) for value in np.unique(lake_grid.compressed()) if value > 0}
    if not ids or ids != mapped:
        raise ValueError("Lake IDs do not match the routing network. Check lake polygon coverage, "
                         f"the stream threshold and {folder.parent / 'routing.log'}.")
    return sorted(ids)


def prepare_domain(config_path: Path, output: Path, *, geogrid_only=False):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    base = config_path.parent
    version = config["wrf_hydro_version"]
    if version not in ATMOSPHERE_PROFILES:
        raise ValueError(f"Unsupported WRF-Hydro version: {version}")
    domain = config["domain"]
    values = _domain_values(domain)
    def resolve(value):
        return _path(base, value)

    boundary = _require(resolve(domain["boundary"])) if domain.get("boundary") else None
    routing = config.get("routing", {})
    csv_path = _require(resolve(routing["stations"])) if routing.get("stations") else None
    stations = _station_rows(csv_path) if csv_path else []
    we, sn = _grid(domain, values, boundary, stations)
    dimensions = {"west_east": we - 1, "south_north": sn - 1}
    geo_fields = ("HGT_M", "LU_INDEX", "XLAT_M", "XLONG_M", "SOILCTOP", "SOILCBOT")

    existing_geo = _require(resolve(config["geogrid"])) if config.get("geogrid") else None
    if existing_geo:
        if geogrid_only:
            raise ValueError("Remove geogrid from the configuration to run WPS.")
        _nc(existing_geo, dimensions, geo_fields)
        from netCDF4 import Dataset
        with Dataset(existing_geo) as data:
            attributes = {"DX": "cell_m", "DY": "cell_m", "CEN_LAT": "ref_lat",
                          "CEN_LON": "ref_lon", "TRUELAT1": "truelat1",
                          "TRUELAT2": "truelat2", "STAND_LON": "stand_lon"}
            if data.MAP_PROJ != 1 or any(not math.isclose(
                data.getncattr(key), values[value], abs_tol=0.001
            ) for key, value in attributes.items()):
                raise ValueError("Existing geogrid projection, location or spacing differs from domain.")
    else:
        wps = resolve(config["wps"])
        geogrid = _require(wps / "geogrid.exe")
        table = _require(wps / "geogrid" / "GEOGRID.TBL")
        static = _require(resolve(config["geog_data"]), directory=True)
        namelist = _namelist(values, we, sn, static, config.get("geog_data_res", "default"))

    if not geogrid_only:
        ratio = _number(routing["ratio"], "routing.ratio", 1, 1000, integer=True)
        threshold = _number(routing["threshold_cells"], "routing.threshold_cells",
                            1, (we - 1) * (sn - 1) * ratio ** 2, integer=True)
        if routing.get("mask_to_stations") and not csv_path:
            raise ValueError("mask_to_stations requires a station CSV.")
        dem = _require(resolve(routing["dem"]))
        lakes = _require(resolve(routing["lake_polygons"])) if routing.get("lake_polygons") else None
        for key in ("reach", "mask_to_stations"):
            if key in routing and type(routing[key]) is not bool:
                raise ValueError(f"routing.{key} must be true or false.")
        gis = resolve(config["ncar_gis"])
        scripts = {name: _require(gis / name) for name in GIS_SCRIPTS}
        tables = resolve(config["parameter_tables"])
        for name in TABLES:
            _require(tables / name)
        month = _number(config["initialization_month"], "initialization_month", 1, 12, integer=True)
        for dependency in ("f90nml", "pandas", "whitebox", "osgeo", "shapely", "xarray"):
            if find_spec(dependency) is None:
                raise ModuleNotFoundError(name=dependency)
        if lakes and routing.get("reach", True):
            from osgeo import ogr
            if ogr.GetDriverByName("netCDF") is None:
                raise ValueError("Install libgdal-netcdf for reach-based lake routing.")
        if not shutil.which("whitebox_tools"):
            raise ValueError("Activate the domain environment with whitebox_tools before running.")
    if output.exists():
        raise ValueError(f"Output directory already exists. Choose a new directory: {output}")
    output.mkdir(parents=True)
    manifest = {
        "wrf_hydro_version": version, "expected_wps_version": ATMOSPHERE_PROFILES[version]["wps"],
        "config": config, "config_path": str(config_path),
        "domain": {**values, "e_we": we, "e_sn": sn}, "completed": [],
    }
    report = output / "domain-manifest.json"

    def completed(stage):
        manifest["completed"].append(stage)
        report.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    report.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    geo = output / GEO
    if existing_geo:
        shutil.copyfile(existing_geo, geo)
    else:
        (output / "namelist.wps").write_text(namelist, encoding="utf-8")
        (output / "geogrid").mkdir()
        shutil.copyfile(table, output / "geogrid" / "GEOGRID.TBL")
        manifest["geogrid_table_sha256"] = sha256(table)
        _run([str(geogrid)], output, "wps-geogrid")
        if "Successful completion of geogrid" not in (output / "wps-geogrid.log").read_text(
            errors="replace"
        ):
            raise ValueError(f"geogrid did not report success. See {output / 'wps-geogrid.log'}")
    _nc(geo, dimensions, geo_fields)
    manifest["geogrid_sha256"] = sha256(geo)
    completed("geogrid")
    if geogrid_only:
        return manifest

    fine_m = values["cell_m"] / ratio
    manifest["routing_grid"] = {"spacing_m": fine_m,
                                "nominal_threshold_km2": threshold * fine_m ** 2 / 1e6}
    manifest["ncar_scripts_sha256"] = {name: sha256(path) for name, path in scripts.items()}
    manifest["tables_sha256"] = {name: sha256(tables / name) for name in TABLES}
    manifest["dem_sha256"] = sha256(dem)
    manifest["station_ids"] = [station for station, _, _ in stations]
    domain_files = output / "DOMAIN"
    domain_files.mkdir()
    # NCAR writes a log beside the ZIP using the same stem as the archive.
    archive = output / "routing-stack.zip"
    routing_script = _routing_scripts(scripts, output)
    cmd = [sys.executable, "-c", ROUTING_LAUNCHER, str(routing_script),
           "-i", str(geo), "-d", str(dem),
           "-R", str(ratio), "-t", str(threshold), "-o", str(archive),
           "-r", str(routing.get("reach", True)), "-b", str(routing.get("mask_to_stations", False))]
    if csv_path:
        cmd.extend(["--CSV", str(csv_path)])
    if lakes:
        cmd.extend(["-l", str(lakes)])
    _run(cmd, output, "routing", _whitebox_env(output))
    _extract_routing(archive, domain_files)
    _nc(domain_files / FULLDOM, {"x": (we - 1) * ratio, "y": (sn - 1) * ratio},
        ("CHANNELGRID", "FLOWDIRECTION", "FLOWACC", "TOPOGRAPHY"))
    manifest["routing_grid"]["active_channel_cells"] = _routing_summary(domain_files / FULLDOM)
    _nc(domain_files / "GWBASINS.nc", {}, ())
    _nc(domain_files / "GWBUCKPARM.nc", {}, ())
    if routing.get("reach", True):
        _nc(domain_files / "Route_Link.nc", {"feature_id": None}, ("link", "to"))
    if lakes:
        manifest["lake_ids"] = _check_lakes(domain_files, routing.get("reach", True))
    if stations:
        manifest["station_mapping"] = _check_stations(
            domain_files, stations, routing.get("reach", True), fine_m, values,
        )
    shutil.copyfile(geo, domain_files / GEO)
    completed("routing")
    _run([sys.executable, str(scripts[GIS_SCRIPTS[2]]), "-i", str(geo),
          "-p", str(tables), "-o", str(domain_files)], output, "soil")
    _nc(domain_files / "soil_properties.nc", {**dimensions, "soil_layers_stag": 4},
        ("smcmax", "smcwlt", "dksat"))
    _nc(domain_files / "hydro2dtbl.nc", dimensions, ("LKSAT", "OV_ROUGH2D"))
    completed("soil")
    _run([sys.executable, str(scripts[GIS_SCRIPTS[3]]), "-i", str(geo),
          "-m", str(month), "-o", str(domain_files / WRFINPUT)], output, "initialization")
    _nc(domain_files / WRFINPUT, {**dimensions, "soil_layers_stag": 4},
        ("SMOIS", "TSLB", "IVGTYP", "ISLTYP"))
    manifest["domain_netcdf_sha256"] = {
        path.name: sha256(path) for path in sorted(domain_files.glob("*.nc"))
    }
    completed("initialization")
    return manifest
