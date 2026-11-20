"""Copy the WPS tiles covering the two bundled basin examples."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
from tempfile import TemporaryDirectory

from assemble_basin_cases import REGIONS, sha256

TILE = re.compile(r"(\d{5})-(\d{5})\.(\d{5})-(\d{5})")
FIXED_INVENTORY = Path(__file__).resolve().parents[2] / "examples/domain/wps-geog-modis.sha256"
NCAR_GEOG = "https://www2.mmm.ucar.edu/wrf/site/access_code/geog_data.html"


def _index_limits(metadata, bounds):
    west, east, south, north = bounds
    dx, dy = float(metadata["dx"]), float(metadata["dy"])
    lon, lat = float(metadata["known_lon"]), float(metadata["known_lat"])
    x, y = float(metadata["known_x"]), float(metadata["known_y"])
    xs = [x + ((edge - lon + dx / 2) % 360 - dx / 2) / dx for edge in (west, east)]
    ys = [y + (edge - lat) / dy for edge in (south, north)]
    return min(xs) - 2, max(xs) + 2, min(ys) - 2, max(ys) + 2


def assemble(geog, tables, output):
    sources = set()
    for table in tables:
        sources.update(re.findall(r"(?m)^\s*rel_path\s*=\s*default:([^\s]+)", table.read_text()))
    output.mkdir(parents=True, exist_ok=False)
    root = output / "WPS_GEOG"
    datasets = {}
    for relative in sorted(sources):
        source = geog / relative
        index = source / "index"
        if not index.is_file():
            continue
        fields = {}
        for line in index.read_text().splitlines():
            key, separator, value = line.partition("=")
            if separator:
                fields[key.strip()] = value.strip().strip('"')
        if fields["projection"] != "regular_ll" or float(fields["dx"]) <= 0:
            raise ValueError(f"Unexpected grid projection or longitude orientation: {index}")
        windows = [_index_limits(fields, bounds) for bounds in REGIONS.values()]
        dest = root / relative
        dest.mkdir(parents=True)
        shutil.copyfile(index, dest / "index")
        count = 0
        for tile in sorted(source.iterdir()):
            match = TILE.fullmatch(tile.name)
            if match is None:
                continue
            x1, x2, y1, y2 = map(int, match.groups())
            if any(x1 <= east and x2 >= west and y1 <= north and y2 >= south
                   for west, east, south, north in windows):
                shutil.copyfile(tile, dest / tile.name)
                count += 1
        if not count:
            raise ValueError(f"No tiles for either basin in {source}")
        datasets[relative] = count
    if not datasets:
        raise ValueError(f"No matching WPS geography in {geog}")
    manifest = {"source": "NCAR WPS high-resolution mandatory geographic data",
                "source_url": NCAR_GEOG,
                "region_lon_west_east_lat_south_north": REGIONS, "tiles_per_dataset": datasets}
    (output / "static-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def extract_fixed(output, *, archive=None, geog=None, inventory=FIXED_INVENTORY):
    """Restore the exact regional files used in the fixed cases."""
    if output.exists():
        raise ValueError(f"Choose a fresh output directory: {output}")
    inventory_text = inventory.read_text(encoding="ascii")
    expected = {}
    for line in inventory_text.splitlines():
        checksum, _, name = line.partition("  ")
        path = PurePosixPath(name)
        if (len(path.parts) < 3 or path.parts[0] != "WPS_GEOG" or ".." in path.parts
                or not re.fullmatch(r"[0-9a-f]{64}", checksum) or name in expected
                or path.as_posix() != name or (path.name != "index" and not TILE.fullmatch(path.name))):
            raise ValueError(f"Invalid WPS inventory entry: {line}")
        expected[name] = checksum
    if not expected:
        raise ValueError(f"Empty WPS inventory: {inventory}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".ewhb-geog-", dir=output.parent) as temporary:
        stage = Path(temporary) / "regional"
        remaining = set(expected)
        if archive is not None:
            with tarfile.open(archive, mode="r|gz", bufsize=1024**2) as stream:
                for member in stream:
                    name = PurePosixPath(member.name).as_posix()
                    if not member.isfile() or name not in remaining:
                        continue
                    target = stage / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with stream.extractfile(member) as source, target.open("wb") as dest:
                        shutil.copyfileobj(source, dest, length=1024**2)
                    remaining.remove(name)
                    if not remaining:
                        break
        else:
            for name in sorted(expected):
                source = geog / PurePosixPath(name).relative_to("WPS_GEOG")
                if source.is_file():
                    target = stage / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    remaining.remove(name)
        if remaining:
            name = min(remaining)
            raise ValueError(f"Source is missing {len(remaining)} required WPS files, including {name}. "
                             "Use the NCAR high-resolution data or a complete fixed regional subset.")
        for name, checksum in expected.items():
            if sha256(stage / name) != checksum:
                raise ValueError(f"Incorrect SHA-256 for regional WPS file: {name}")
        (stage / "SHA256SUMS").write_text(inventory_text, encoding="ascii")
        stage.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--geog-data", type=Path, help="Existing WPS_GEOG directory.")
    source.add_argument("--archive", type=Path, help="NCAR high-resolution .tar.gz archive.")
    parser.add_argument("--table", type=Path, action="append",
                        help="Select by GEOGRID.TBL instead of restoring the fixed inventory.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.table and args.archive:
        parser.error("--table requires an extracted --geog-data directory.")
    try:
        if args.table:
            assemble(args.geog_data, args.table, args.output)
        else:
            extract_fixed(args.output, archive=args.archive, geog=args.geog_data)
        print(args.output / "WPS_GEOG")
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.error(str(exc))
