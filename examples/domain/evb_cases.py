"""Generate WRF-Hydro case configurations from Zheng's published VIC archive."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from easy_wrf_hydro_build.atmosphere import ATMOSPHERE_PROFILES, sha256
from easy_wrf_hydro_build.domain import ROUTING_DEFAULTS

EVB_SHA256 = "06b1b18435814644c94b448277a9d9195288e3cbc44715277eeda29bf334c0b4"
EVB_RECORD = "https://zenodo.org/records/21771543"
GASCONADE_BOUNDARY = (
    "zenodo_upload/GRB/GRB_06934000_12km/Hydroanalysis/"
    "wbw_working_directory_level0/basin_vector_main_outlet"
)
JING_DOMAIN = "zenodo_upload/JRB/JRB_Zhangjiashan_1_8_deg/DomainFile/domain.nc"
# Covers the published VIC domain and Zhangjiashan, with rounded limits.
JING_BOUNDS = [105.9, 34.4, 109.1, 37.6]


def build_configs(args):
    if sha256(args.archive) != EVB_SHA256:
        raise ValueError("Archive does not match the published EVB v1 dataset.")
    for item in (args.wps, args.geog_data, args.ncar_gis, args.parameter_tables):
        if not item.is_dir():
            raise ValueError(f"Missing directory: {item}")
    for item in (args.gasconade_dem, args.jing_dem):
        if not item.is_file():
            raise ValueError(f"Missing DEM: {item}")
    if args.jing_boundary and (not args.jing_boundary.is_file()
                               or args.jing_boundary.suffix.lower() != ".shp"):
        raise ValueError(f"Expected the original Jing River boundary .shp: {args.jing_boundary}")
    args.output.mkdir(parents=True)
    with zipfile.ZipFile(args.archive) as archive:
        for suffix in (".shp", ".shx", ".prj", ".dbf"):
            (args.output / f"gasconade{suffix}").write_bytes(archive.read(GASCONADE_BOUNDARY + suffix))
        archived_domain = args.output / "jing-vic-domain.nc"
        archived_domain.write_bytes(archive.read(JING_DOMAIN))

    if args.jing_boundary:
        jing_boundary = str(args.jing_boundary.resolve())
        jing_boundary_kind = "user-supplied Shapefile"
    else:
        jing_boundary = None
        jing_boundary_kind = "rectangle covering the published VIC domain"

    cases = {
        "gasconade": (12000, 37.85, -92.45, "gasconade.shp", args.gasconade_dem,
                      "06934000,38.38881,-91.81989", [1998, 1999], [2000, 2007], [2008, 2010]),
        "jing": (13800, 36.0, 107.5, jing_boundary, args.jing_dem,
                 "Zhangjiashan,34.63,108.60", [2008, 2009], [2010, 2015], [2016, 2018]),
    }
    for name, (cell, lat, lon, boundary, dem, station, spinup, calibration, validation) in cases.items():
        stations = f"{name}-stations.csv"
        (args.output / stations).write_text(f"FID,LAT,LON\n{station}\n", encoding="utf-8")
        coverage = {"boundary": boundary} if boundary else {"bounds_wgs84": JING_BOUNDS}
        reference_file = args.output / boundary if boundary else archived_domain
        config = {
            "wrf_hydro_version": args.wrf_hydro_version,
            "wps": str(args.wps.resolve()),
            "geog_data": str(args.geog_data.resolve()),
            "geog_data_res": args.geog_data_res,
            "ncar_gis": str(args.ncar_gis.resolve()),
            "parameter_tables": str(args.parameter_tables.resolve()),
            "initialization_month": 1,
            "domain": {"cell_m": cell, "ref_lat": lat, "ref_lon": lon, "truelat1": 30,
                       "truelat2": 60, "padding_cells": 3, **coverage},
            "routing": {"dem": str(dem.resolve()), "stations": stations, **ROUTING_DEFAULTS},
            "reference": {
                "archive": EVB_RECORD, "archive_sha256": EVB_SHA256,
                "boundary_kind": "published polygon" if name == "gasconade" else jing_boundary_kind,
                "reference_geometry_sha256": sha256(reference_file),
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
    parser.add_argument("--jing-boundary", type=Path, help="Use the original Jing boundary .shp if available.")
    try:
        build_configs(parser.parse_args())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
