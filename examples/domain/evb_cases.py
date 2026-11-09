"""Generate WRF-Hydro case configurations from Zheng's published VIC archive."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from netCDF4 import Dataset
import numpy as np
from shapely.geometry import box, mapping
from shapely.ops import unary_union

from easy_wrf_hydro_build.atmosphere import ATMOSPHERE_PROFILES, sha256

EVB_SHA256 = "06b1b18435814644c94b448277a9d9195288e3cbc44715277eeda29bf334c0b4"
EVB_RECORD = "https://zenodo.org/records/21771543"
GASCONADE_BOUNDARY = (
    "zenodo_upload/GRB/GRB_06934000_12km/Hydroanalysis/"
    "wbw_working_directory_level0/basin_vector_main_outlet"
)
JING_DOMAIN = "zenodo_upload/JRB/JRB_Zhangjiashan_1_8_deg/DomainFile/domain.nc"


def build_configs(args):
    if sha256(args.archive) != EVB_SHA256:
        raise ValueError("Archive does not match the published EVB v1 dataset.")
    for item in (args.wps, args.geog_data, args.ncar_gis, args.parameter_tables):
        if not item.is_dir():
            raise ValueError(f"Missing directory: {item}")
    for item in (args.gasconade_dem, args.jing_dem):
        if not item.is_file():
            raise ValueError(f"Missing DEM: {item}")
    args.output.mkdir(parents=True)
    with zipfile.ZipFile(args.archive) as archive:
        for suffix in (".shp", ".shx", ".prj", ".dbf"):
            (args.output / f"gasconade{suffix}").write_bytes(archive.read(GASCONADE_BOUNDARY + suffix))
        archived_domain = args.output / "jing-vic-domain.nc"
        archived_domain.write_bytes(archive.read(JING_DOMAIN))

    with Dataset(archived_domain) as nc:
        lat, lon = nc["lat"][:], nc["lon"][:]
        rows, cols = np.where(nc["mask"][:] == 1)
        dy, dx = abs(lat[1] - lat[0]) / 2, abs(lon[1] - lon[0]) / 2
        grid = unary_union([box(lon[x] - dx, lat[y] - dy, lon[x] + dx, lat[y] + dy)
                            for y, x in zip(rows, cols)])
    (args.output / "jing-vic-mask.geojson").write_text(json.dumps(mapping(grid)), encoding="utf-8")

    cases = {
        "gasconade": (12000, 37.85, -92.45, "gasconade.shp", args.gasconade_dem,
                      "06934000,38.38881,-91.81989", [1998, 1999], [2000, 2007], [2008, 2010]),
        "jing": (13800, 36.0, 107.5, "jing-vic-mask.geojson", args.jing_dem,
                 "Zhangjiashan,34.63,108.60", [2008, 2009], [2010, 2015], [2016, 2018]),
    }
    for name, (cell, lat, lon, boundary, dem, station, spinup, calibration, validation) in cases.items():
        stations = f"{name}-stations.csv"
        (args.output / stations).write_text(f"FID,LAT,LON\n{station}\n", encoding="utf-8")
        config = {
            "wrf_hydro_version": args.wrf_hydro_version,
            "wps": str(args.wps.resolve()),
            "geog_data": str(args.geog_data.resolve()),
            "geog_data_res": args.geog_data_res,
            "ncar_gis": str(args.ncar_gis.resolve()),
            "parameter_tables": str(args.parameter_tables.resolve()),
            "initialization_month": 1,
            "domain": {"cell_m": cell, "ref_lat": lat, "ref_lon": lon, "truelat1": 30,
                       "truelat2": 60, "boundary": boundary, "padding_cells": 3},
            "routing": {"dem": str(dem.resolve()), "stations": stations, "reach": True,
                        "ratio": 24, "threshold_cells": 100},
            "reference": {
                "archive": EVB_RECORD, "archive_sha256": EVB_SHA256,
                "boundary_kind": "published polygon" if name == "gasconade" else "published VIC mask",
                "spinup_years": spinup, "calibration_years": calibration, "validation_years": validation,
            },
        }
        (args.output / f"{name}.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("archive", "output", "wps", "geog-data", "ncar-gis", "parameter-tables",
                   "gasconade-dem", "jing-dem"):
        parser.add_argument(f"--{option}", required=True, type=Path)
    parser.add_argument("--wrf-hydro-version", required=True, choices=ATMOSPHERE_PROFILES)
    parser.add_argument("--geog-data-res", default="default")
    try:
        build_configs(parser.parse_args())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
