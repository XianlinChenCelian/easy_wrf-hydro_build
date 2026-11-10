"""Assemble the two pinned GFS examples from prepared domains and regional GRIB2."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from urllib.parse import urlencode

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from easy_wrf_hydro_build.atmosphere import ATMOSPHERE_PROFILES, sha256  # noqa: E402
from easy_wrf_hydro_build.basin import BASINS, DOMAIN_FILES  # noqa: E402

CYCLE = "2026-11-08T00:00:00"
FILES = tuple(f"gfs.t00z.pgrb2.0p25.f{hour:03}" for hour in (0, 6, 12))
REGIONS = {"jing": (100, 115, 29, 43), "gasconade": (260, 275, 31, 45)}


def assemble(version, domains, forcing, output):
    output.mkdir(parents=True, exist_ok=False)
    for name in BASINS:
        source = domains / name
        domain = json.loads((source / "domain-manifest.json").read_text())
        if domain["wrf_hydro_version"] != version or domain["land_cover"]["scheme"] != "MODIS":
            raise ValueError(f"Expected a MODIS domain prepared for WRF-Hydro {version}: {source}")
        dest = output / name
        (dest / "GFS").mkdir(parents=True)
        (dest / "DOMAIN").mkdir()
        west, east, south, north = REGIONS[name]
        records = {}
        for filename in FILES:
            original = forcing / name / filename
            with original.open("rb") as stream:
                if stream.read(4) != b"GRIB":
                    raise ValueError(f"Expected GRIB2: {original}")
            shutil.copyfile(original, dest / "GFS" / filename)
            query = urlencode({"file": filename, "all_lev": "on", "all_var": "on", "subregion": "",
                               "leftlon": west, "rightlon": east, "bottomlat": south, "toplat": north,
                               "dir": "/gfs.20261108/00/atmos"})
            records[filename] = {
                "url": f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?{query}",
                "sha256": sha256(original),
            }
        for filename in (*DOMAIN_FILES, "Gage_Crosswalk.csv"):
            shutil.copyfile(source / "DOMAIN" / filename, dest / "DOMAIN" / filename)
        shutil.copyfile(source / "parameter-tables/HYDRO.TBL", dest / "HYDRO.TBL")
        case = {
            "basin": name, "wrf_hydro": version, **ATMOSPHERE_PROFILES[version],
            "cycle_utc": CYCLE, "interval_seconds": 21600,
            "grib2": FILES, "weather_source": "NOAA/NCEP GFS 0.25-degree pgrb2, regional subsets",
            "weather_files": records, "domain": domain["domain"], "routing": domain["routing_grid"],
            "land_cover": domain["land_cover"], "reference": domain["config"]["reference"],
            "station_mapping": domain["station_mapping"],
        }
        (dest / "case.json").write_text(json.dumps(case, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrf-hydro-version", choices=ATMOSPHERE_PROFILES, required=True)
    for argument in ("domains", "forcing", "output"):
        parser.add_argument(f"--{argument}", type=Path, required=True)
    args = parser.parse_args()
    assemble(args.wrf_hydro_version, args.domains, args.forcing, args.output)
