import json
from pathlib import Path
import runpy
from urllib.parse import parse_qs, urlsplit

import pytest

from easy_wrf_hydro_build.atmosphere import sha256
from easy_wrf_hydro_build.basin import BASINS, DOMAIN_FILES


ASSEMBLER = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts/release/assemble_basin_cases.py"),
)


def _section_one_fixture(cycle):
    indicator = b"GRIB\x00\x00\x00\x02" + (41).to_bytes(8, "big")
    section = ((21).to_bytes(4, "big") + b"\x01" + bytes(7)
               + cycle.year.to_bytes(2, "big")
               + bytes((cycle.month, cycle.day, cycle.hour, 0, 0, 0, 1)))
    return indicator + section + b"7777"


def test_case_assembly_uses_selected_cycle_and_checks_local_input(tmp_path):
    cycle = ASSEMBLER["parse_cycle"]("2025-02-03T18:00:00Z")
    domains = tmp_path / "domains"
    forcing = tmp_path / "forcing"
    output = tmp_path / "cases"
    filenames = [f"gfs.t18z.pgrb2.0p25.f{lead:03}" for lead in (0, 6, 12)]
    for name in BASINS:
        domain = domains / name
        (domain / "DOMAIN").mkdir(parents=True)
        (domain / "parameter-tables").mkdir()
        for filename in (*DOMAIN_FILES, "Gage_Crosswalk.csv"):
            (domain / "DOMAIN" / filename).touch()
        (domain / "parameter-tables/HYDRO.TBL").touch()
        (domain / "domain-manifest.json").write_text(json.dumps({
            "wrf_hydro_version": "5.1.2", "land_cover": {"scheme": "MODIS"},
            "domain": {}, "routing_grid": {}, "config": {"reference": {}}, "station_mapping": {},
        }))
        (forcing / name).mkdir(parents=True)
        for filename in filenames:
            (forcing / name / filename).write_bytes(_section_one_fixture(cycle))

    previous_day = ASSEMBLER["parse_cycle"]("2025-02-02T18:00:00Z")
    with pytest.raises(ValueError, match=r"Expected cycle 2025-02-02.*found 2025-02-03"):
        ASSEMBLER["assemble"]("5.1.2", domains, forcing, output, previous_day)
    assert not output.exists()

    # The download option also works offline when the matching files are in the cache.
    ASSEMBLER["assemble"]("5.1.2", domains, forcing, output, cycle, download=True)
    for name in BASINS:
        case = json.loads((output / name / "case.json").read_text())
        assert case["cycle_utc"] == "2025-02-03T18:00:00"
        assert case["grib2"] == filenames
        for filename, source in case["weather_files"].items():
            params = parse_qs(urlsplit(source["url"]).query)
            assert params["dir"] == ["/gfs.20250203/18/atmos"]
            assert params["file"] == [filename]
            assert source["sha256"] == sha256(output / name / "GFS" / filename)
