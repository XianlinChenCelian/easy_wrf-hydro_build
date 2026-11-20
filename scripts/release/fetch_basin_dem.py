"""Fetch and mosaic regional Copernicus GLO-90 elevation for a prepared WPS grid."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from easy_wrf_hydro_build.atmosphere import sha256  # noqa: E402

S3 = "https://copernicus-dem-90m.s3.eu-central-1.amazonaws.com"


def _tile(lat, lon):
    ns, ew = ("S" if lat < 0 else "N"), ("W" if lon < 0 else "E")
    return f"Copernicus_DSM_COG_30_{ns}{abs(lat):02}_00_{ew}{abs(lon):03}_00_DEM"


def fetch(geogrid, cache, output):
    from netCDF4 import Dataset
    from osgeo import gdal

    report = output.with_suffix(".json")
    if output.exists() or report.exists():
        raise ValueError(f"Choose a new DEM output path: {output}")
    with Dataset(geogrid) as grid:
        lons, lats = grid["XLONG_C"][:], grid["XLAT_C"][:]
        west, east = float(lons.min()) - 0.15, float(lons.max()) + 0.15
        south, north = float(lats.min()) - 0.15, float(lats.max()) + 0.15
    if not (-180 < west < east < 180 and east - west < 10 and
            -90 < south < north < 90 and north - south < 10):
        raise ValueError("Use a single regional grid smaller than 10 degrees per side.")
    cache.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    gdal.UseExceptions()

    def get(tile):
        path = cache / f"{tile}.tif"
        url = f"{S3}/{tile}/{path.name}"
        if not path.is_file():
            with TemporaryDirectory(dir=cache) as directory:
                staged = Path(directory) / path.name
                with urlopen(url, timeout=60) as response, staged.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
                    if response.length not in (0, None):
                        raise OSError(f"Incomplete response for {url}")
                gdal.Open(str(staged))
                staged.rename(path)
        return path, {"url": url, "sha256": sha256(path)}

    tiles = [_tile(lat, lon) for lat in range(math.floor(south), math.ceil(north))
             for lon in range(math.floor(west), math.ceil(east))]
    with ThreadPoolExecutor(max_workers=6) as pool:
        sources = list(pool.map(get, tiles))
    with TemporaryDirectory(dir=output.parent) as directory:
        staged = Path(directory) / output.name
        vrt = gdal.BuildVRT(str(Path(directory) / "tiles.vrt"), [str(path) for path, _ in sources])
        dem = gdal.Translate(str(staged), vrt, projWin=(west, north, east, south),
                             creationOptions=["COMPRESS=DEFLATE", "PREDICTOR=3"])
        dem = None
        vrt = None
        staged.rename(output)
    report.write_text(json.dumps({
        "dem": "Copernicus WorldDEM-90, AWS 2021 release (cloud-optimized GeoTIFF)",
        "source_doi": "10.5270/ESA-c5d3d65",
        "bounds_wgs84": [west, south, east, north],
        "sha256": sha256(output),
        "tiles": {path.name: record for path, record in sources},
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("geogrid", "cache", "output"):
        parser.add_argument(f"--{argument}", required=True, type=Path)
    args = parser.parse_args()
    try:
        fetch(args.geogrid, args.cache, args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
