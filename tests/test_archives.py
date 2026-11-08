from pathlib import Path

from easy_wrf_hydro_build.archives import find_archive


def test_wrf_hydro_prefers_nwm_public_archive(tmp_path: Path):
    (tmp_path / "wrf-hydro_uncouple.tar.gz").write_text("", encoding="utf-8")
    (tmp_path / "wrf_hydro_nwm_public-5.1.2.tar.gz").write_text("", encoding="utf-8")

    archive = find_archive(tmp_path, "wrf_hydro")

    assert archive is not None
    assert archive.path.name == "wrf_hydro_nwm_public-5.1.2.tar.gz"


def test_explicit_version_matches_only_its_model_and_croton(tmp_path: Path):
    older_model = tmp_path / "wrf_hydro_nwm_public-5.1.2.tar.gz"
    older_example = tmp_path / "croton_NY_example_testcase.tar.gz"
    model = tmp_path / "wrf_hydro_nwm_public-5.2.0.tar.gz"
    example = tmp_path / "croton_NY_training_example_v5.2.tar.gz"
    for archive in (older_model, older_example, model, example):
        archive.touch()

    assert find_archive(tmp_path, "wrf_hydro", wrf_hydro_version="5.2.0").path == model
    assert find_archive(tmp_path, "croton_example", wrf_hydro_version="5.2.0").path == example
    assert find_archive(tmp_path, "croton_example", wrf_hydro_version="5.4.0") is None
