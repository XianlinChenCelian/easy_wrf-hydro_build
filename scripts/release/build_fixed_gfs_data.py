"""Build the public GFS snapshot for the 2026-11-08 coupled examples."""

import argparse
import gzip
import json
from pathlib import Path
import shutil
import tarfile
from tempfile import TemporaryDirectory

from assemble_basin_cases import (
    ATMOSPHERE_PROFILES, BASINS, REGIONS, check_gfs, gfs_requests, parse_cycle, sha256,
)


RELEASE = "ewhb-gfs-20261108t00z-r1"
CYCLE = parse_cycle("2026-11-08T00:00:00Z")
NOAA_TERMS = "https://www.weather.gov/disclaimer"
WPS_GEOG = "https://www2.mmm.ucar.edu/wrf/site/access_code/geog_data.html"
HYDROSHEDS = "https://www.hydrosheds.org/hydrosheds-core-downloads"
EVB = "https://doi.org/10.5281/zenodo.21771543"
DEM_RECORDS = {
    "jing": ("n30e100_con.tif", "d332430050a526cef5726e008e317ab823c52985f0571c2884f61065e72b5bb1"),
    "gasconade": ("n30w100_con.tif", "c2f06c6d705e51ad47286b5a3b8829172726da178b52dafa846cfeed0807b087"),
}


def build(source: Path, notes: Path, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=False)
    archive = output / f"{RELEASE}.tar.gz"
    with TemporaryDirectory(prefix=".ewhb-gfs-release-", dir=output) as temporary:
        root = Path(temporary) / RELEASE
        root.mkdir()
        shutil.copyfile(notes, root / "README.md")
        records = {}
        specs = {}
        for basin in BASINS:
            (root / "gfs" / basin).mkdir(parents=True)
            for filename, url in gfs_requests(CYCLE, basin).items():
                original = source / "inputs" / basin / filename
                check_gfs(original, CYCLE)
                relative = f"gfs/{basin}/{filename}"
                dest = root / relative
                shutil.copyfile(original, dest)
                records[relative] = {"sha256": sha256(dest), "size_bytes": dest.stat().st_size,
                                     "source_url": url}
        for version in ATMOSPHERE_PROFILES:
            profiles = {}
            for basin in BASINS:
                case_path = source / "cases" / version / basin / "case.json"
                case = json.loads(case_path.read_text(encoding="utf-8"))
                if case["cycle_utc"] != CYCLE.isoformat() or case["wrf_hydro"] != version:
                    raise ValueError(f"Incorrect reference case version or cycle: {case_path}")
                if case["grib2"] != list(gfs_requests(CYCLE, basin)):
                    raise ValueError(f"Unexpected GFS filenames: {case_path}")
                for filename in case["grib2"]:
                    expected = records[f"gfs/{basin}/{filename}"]["sha256"]
                    if case["weather_files"][filename]["sha256"] != expected:
                        raise ValueError(f"GFS differs from the archived case: {case_path}, {filename}")
                profiles[basin] = {field: case[field] for field in ("domain", "routing", "land_cover")}
            specs[version] = {**ATMOSPHERE_PROFILES[version], "basins": profiles}

        static = source / "static"
        layers = json.loads((static / "static-manifest.json").read_text())["tiles_per_dataset"]
        tiles = {}
        for layer, count in sorted(layers.items()):
            tile_names = sorted(item.name for item in (static / "WPS_GEOG" / layer).iterdir()
                                if item.is_file() and not item.name.startswith(".") and item.name != "index")
            if len(tile_names) != count:
                raise ValueError(f"WPS tile count changed for {layer}")
            tiles[layer.rstrip("/")] = tile_names
        manifest = {
            "id": RELEASE,
            "publisher": "easy_wrf-hydro_build",
            "cycle_utc": CYCLE.isoformat() + "Z",
            "valid_times_utc": [f"2026-11-08T{hour:02}:00:00Z" for hour in (0, 6, 12)],
            "product": "NOAA/NCEP GFS 0.25 degree pgrb2; original NOMADS regional subsets",
            "region_lon_west_east_lat_south_north": REGIONS,
            "gfs_terms_url": NOAA_TERMS,
            "gfs_files": records,
            "reference_case_specs": specs,
            "external_inputs": {
                "wps_geography": {"source_url": WPS_GEOG, "regional_tile_inventory": tiles},
                "hydrosheds_v1_conditioned_dem": {
                    "source_url": HYDROSHEDS, "resolution_arc_seconds": 3,
                    "files": {basin: {"filename": name, "sha256": digest}
                              for basin, (name, digest) in DEM_RECORDS.items()},
                },
                "basin_reference": EVB,
            },
        }
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        files = sorted(path for path in root.rglob("*") if path.is_file())
        checksums = root / "SHA256SUMS"
        checksums.write_text("".join(f"{sha256(path)}  {path.relative_to(root).as_posix()}\n" for path in files),
                             encoding="ascii")
        staged = Path(temporary) / archive.name
        with staged.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as stream:
                for path in sorted([*files, checksums]):
                    metadata = tarfile.TarInfo(f"{RELEASE}/{path.relative_to(root).as_posix()}")
                    metadata.size = path.stat().st_size
                    with path.open("rb") as data:
                        stream.addfile(metadata, data)
        staged.rename(archive)
    archive.with_suffix(".gz.sha256").write_text(f"{sha256(archive)}  {archive.name}\n", encoding="ascii")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Archived basin-cases directory.")
    parser.add_argument("--notes", type=Path, required=True, help="README to include in the archive.")
    parser.add_argument("--output", type=Path, required=True, help="New directory for the archive and checksum.")
    args = parser.parse_args()
    try:
        print(build(args.source, args.notes, args.output))
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
