from pathlib import Path

from easy_wrf_hydro_build.archives import find_archive


def test_wrf_hydro_prefers_nwm_public_archive(tmp_path: Path):
    (tmp_path / "wrf-hydro_uncouple.tar.gz").write_text("", encoding="utf-8")
    (tmp_path / "wrf_hydro_nwm_public-5.1.2.tar.gz").write_text("", encoding="utf-8")

    archive = find_archive(tmp_path, "wrf_hydro")

    assert archive is not None
    assert archive.path.name == "wrf_hydro_nwm_public-5.1.2.tar.gz"
