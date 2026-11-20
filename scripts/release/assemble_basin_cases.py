"""Assemble the two GFS basin cases for a selected UTC forecast cycle."""
import argparse
from datetime import datetime, timedelta
from http.client import HTTPException
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from easy_wrf_hydro_build.atmosphere import ATMOSPHERE_PROFILES, sha256  # noqa: E402
from easy_wrf_hydro_build.basin import BASINS, DOMAIN_FILES  # noqa: E402

REGIONS = {"jing": (100, 115, 29, 43), "gasconade": (260, 275, 31, 45)}


def parse_cycle(value):
    if "T" not in value:
        raise argparse.ArgumentTypeError("Use an ISO 8601 UTC date and hour for --cycle.")
    try:
        cycle = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use an ISO 8601 UTC date and hour for --cycle.") from exc
    if (cycle.utcoffset() not in (None, timedelta(0)) or cycle.hour not in (0, 6, 12, 18)
            or cycle.minute or cycle.second or cycle.microsecond):
        raise argparse.ArgumentTypeError("Choose a UTC GFS cycle at 00, 06, 12 or 18 UTC.")
    return cycle.replace(tzinfo=None)


def gfs_requests(cycle, basin):
    west, east, south, north = REGIONS[basin]
    requests = {}
    for lead in (0, 6, 12):
        filename = f"gfs.t{cycle:%H}z.pgrb2.0p25.f{lead:03}"
        query = urlencode({"file": filename, "all_lev": "on", "all_var": "on", "subregion": "",
                           "leftlon": west, "rightlon": east, "bottomlat": south, "toplat": north,
                           "dir": f"/gfs.{cycle:%Y%m%d}/{cycle:%H}/atmos"})
        requests[filename] = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?{query}"
    return requests


def check_gfs(path, cycle):
    with path.open("rb") as stream:
        header = stream.read(37)
        if (len(header) != 37 or header[:4] != b"GRIB" or header[7] != 2
                or header[20] != 1 or int.from_bytes(header[16:20], "big") < 21
                or not 41 <= int.from_bytes(header[8:16], "big") <= path.stat().st_size):
            raise ValueError(f"Expected a complete GRIB2 file: {path}")
        stream.seek(-4, 2)
        if stream.read(4) != b"7777":
            raise ValueError(f"Truncated or invalid GRIB2 file: {path}")
    # GRIB2 section 1 records the UTC reference time, even when the filename has no date.
    try:
        reference = datetime(int.from_bytes(header[28:30], "big"), *header[30:35])
    except ValueError as exc:
        raise ValueError(f"Invalid GRIB2 reference time: {path}") from exc
    if reference != cycle:
        raise ValueError(f"Expected cycle {cycle.isoformat()} UTC, found {reference.isoformat()} in {path}.")


def download_gfs(path, url, cycle):
    if path.is_file():
        check_gfs(path, cycle)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {path.parent.name}/{path.name}", flush=True)
    try:
        with TemporaryDirectory(prefix=".ewhb-gfs-", dir=path.parent) as scratch:
            staged = Path(scratch) / path.name
            with urlopen(url, timeout=60) as response, staged.open("wb") as stream:
                shutil.copyfileobj(response, stream)
                if response.length not in (0, None):
                    raise OSError("Incomplete HTTP response")
            check_gfs(staged, cycle)
            staged.rename(path)
    except HTTPError as exc:
        if exc.code == 404:
            raise ValueError(f"NOMADS does not have {path.name} for {cycle.isoformat()} UTC. "
                             "Use an archived regional copy or select an available cycle.") from exc
        raise
    except (OSError, HTTPException) as exc:
        raise OSError(f"Could not download {url}: {exc}. Run the same command to reuse completed files.") from exc


def assemble(version, domains, forcing, output, cycle, *, download=False):
    if output.exists():
        raise ValueError(f"Choose a new case output directory: {output}")
    manifests = {}
    for name in BASINS:
        source = domains / name
        domain = json.loads((source / "domain-manifest.json").read_text())
        if domain.get("wrf_hydro_version") != version or domain.get("land_cover", {}).get("scheme") != "MODIS":
            raise ValueError(f"Prepare {name} with `ewhb prepare-domain` for WRF-Hydro {version}. "
                             f"Its domain-manifest.json must record the MODIS scheme: {source}")
        for item in (*(source / "DOMAIN" / file for file in (*DOMAIN_FILES, "Gage_Crosswalk.csv")),
                     source / "parameter-tables/HYDRO.TBL"):
            if not item.is_file():
                raise FileNotFoundError(f"Missing prepared domain input: {item}")
        manifests[name] = domain
    requests = {name: gfs_requests(cycle, name) for name in BASINS}
    for name, files in requests.items():
        for filename, url in files.items():
            path = forcing / name / filename
            if download:
                download_gfs(path, url, cycle)
            else:
                check_gfs(path, cycle)
    output.mkdir(parents=True, exist_ok=False)
    for name in BASINS:
        source = domains / name
        domain = manifests[name]
        dest = output / name
        (dest / "GFS").mkdir(parents=True)
        (dest / "DOMAIN").mkdir()
        records = {}
        for filename, url in requests[name].items():
            original = forcing / name / filename
            shutil.copyfile(original, dest / "GFS" / filename)
            records[filename] = {"url": url, "sha256": sha256(dest / "GFS" / filename)}
        for filename in (*DOMAIN_FILES, "Gage_Crosswalk.csv"):
            shutil.copyfile(source / "DOMAIN" / filename, dest / "DOMAIN" / filename)
        shutil.copyfile(source / "parameter-tables/HYDRO.TBL", dest / "HYDRO.TBL")
        case = {
            "basin": name, "wrf_hydro": version, **ATMOSPHERE_PROFILES[version],
            "cycle_utc": cycle.isoformat(timespec="seconds"), "interval_seconds": 21600,
            "grib2": list(records), "weather_source": "NOAA/NCEP GFS 0.25-degree pgrb2, regional subsets",
            "weather_files": records, "domain": domain["domain"], "routing": domain["routing_grid"],
            "land_cover": domain["land_cover"], "reference": domain["config"]["reference"],
            "station_mapping": domain["station_mapping"],
        }
        (dest / "case.json").write_text(json.dumps(case, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrf-hydro-version", choices=ATMOSPHERE_PROFILES, required=True)
    parser.add_argument("--cycle", required=True, type=parse_cycle, help="GFS forecast reference time in UTC.")
    parser.add_argument("--download-gfs", action="store_true", help="Fetch missing regional files from NOAA NOMADS.")
    for argument in ("domains", "forcing", "output"):
        parser.add_argument(f"--{argument}", type=Path, required=True)
    args = parser.parse_args()
    try:
        assemble(args.wrf_hydro_version, args.domains, args.forcing, args.output,
                 args.cycle, download=args.download_gfs)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
