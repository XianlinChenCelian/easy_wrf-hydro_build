"""Copy the WPS tiles covering the two bundled basin examples."""
import argparse
import json
from pathlib import Path
import re
import shutil

from assemble_basin_cases import REGIONS

TILE = re.compile(r"(\d{5})-(\d{5})\.(\d{5})-(\d{5})")


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
                "source_url": "https://www2.mmm.ucar.edu/wrf/site/geog_data.html",
                "region_lon_west_east_lat_south_north": REGIONS, "tiles_per_dataset": datasets}
    (output / "static-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geog-data", type=Path, required=True)
    parser.add_argument("--table", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assemble(args.geog_data, args.table, args.output)
