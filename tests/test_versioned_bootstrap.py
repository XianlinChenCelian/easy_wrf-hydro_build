import json
from pathlib import Path
from subprocess import run

import pytest

from easy_wrf_hydro_build.archives import WRF_HYDRO_RELEASES
from easy_wrf_hydro_build.cli import main


@pytest.mark.parametrize("version", WRF_HYDRO_RELEASES)
def test_cli_generates_the_selected_release_script(tmp_path: Path, version: str):
    archives = tmp_path / "archives"
    archives.mkdir()
    (archives / f"wrf_hydro_nwm_public-{version}.tar.gz").touch()
    (archives / WRF_HYDRO_RELEASES[version]).touch()
    prefix = tmp_path / "build"
    args = [
        "bootstrap", "--shared-dir", str(archives), "--prefix", str(prefix),
        "--netcdf", str(tmp_path / "netcdf"), "--run-example", "--dry-run",
        "--wrf-hydro-version",
    ]

    assert main([*args, version]) == 0
    script = prefix / "bootstrap_easy_wrf_hydro.sh"
    content = script.read_text()
    assert f"wrf_hydro_nwm_public-{version}.tar.gz" in content
    assert WRF_HYDRO_RELEASES[version] in content
    assert "COMPILER_FAMILY=gnu" in content
    assert ("-dumpversion" in content) == (version == "5.1.2")
    assert ("cmake --build" in content) == (version == "5.4.0")
    run(["bash", "-n", str(script)], check=True)

    other = next(release for release in WRF_HYDRO_RELEASES if release != version)
    (archives / f"wrf_hydro_nwm_public-{other}.tar.gz").touch()
    (archives / WRF_HYDRO_RELEASES[other]).touch()
    with pytest.raises(SystemExit) as error:
        main([*args, other])
    assert error.value.code == 2
    assert script.read_text() == content


def test_inferred_release_selects_the_same_build_and_rejects_ambiguous_archives(tmp_path, capsys):
    archives = tmp_path / "archives"
    archives.mkdir()
    (archives / "wrf_hydro_nwm_public-5.1.2.tar.gz").touch()
    prefix = tmp_path / "build"
    args = ["bootstrap", "--shared-dir", str(archives), "--prefix", str(prefix),
            "--netcdf", "/usr", "--dry-run"]
    assert main(args) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["wrf_hydro_version"] == "5.1.2"
    script = Path(plan["script"])
    assert "-fallow-argument-mismatch" in script.read_text()

    (archives / "wrf_hydro_nwm_public-5.4.0.tar.gz").touch()
    with pytest.raises(SystemExit):
        main(args)
    assert "Select one with --wrf-hydro-version" in capsys.readouterr().err
    assert (prefix / "wrf_hydro_version.txt").read_text().strip() == "5.1.2"


@pytest.mark.parametrize("version", WRF_HYDRO_RELEASES)
def test_ifx_route_uses_existing_netcdf_and_rejects_the_old_hdf5_recipe(tmp_path, version, capsys):
    archives = tmp_path / "archives"
    archives.mkdir()
    for filename in (
        f"wrf_hydro_nwm_public-{version}.tar.gz", "zlib-1.2.11.tar.gz",
        "hdf5-1.12.0.tar.gz", "netcdf-c-4.7.4.tar.gz", "netcdf-fortran-4.5.3.tar.gz",
    ):
        (archives / filename).touch()
    prefix = tmp_path / "intel"
    args = [
        "bootstrap", "--shared-dir", str(archives), "--prefix", str(prefix),
        "--wrf-hydro-version", version, "--compiler-family", "intel",
        "--compiler-option", "ifx", "--intel-home", str(tmp_path / "oneapi"),
        "--dry-run",
    ]
    with pytest.raises(SystemExit):
        main([*args, "--build-netcdf"])
    assert "HDF5 1.12.0" in capsys.readouterr().err
    assert not prefix.exists()
    assert main([*args, "--netcdf", str(tmp_path / "netcdf")]) == 0
    script = prefix / "bootstrap_easy_wrf_hydro.sh"
    content = script.read_text()
    assert "USE_EXISTING_NETCDF=1" in content
    assert "NETCDF_FORTRAN_ARCHIVE=" not in content
    assert "MPI_WRAPPER=mpiifx" in content
    assert "-dumpversion" not in content
    assert "export CC=icx CXX=icpx FC=ifx" in content
    assert "oneapi-vars.sh" in content
    assert ("./configure ifort" in content) == (version != "5.4.0")
    assert ("cmake --build" in content) == (version == "5.4.0")
    run(["bash", "-n", str(script)], check=True)


def test_site_intel_route_keeps_the_loaded_environment(tmp_path):
    archives = tmp_path / "archives"
    archives.mkdir()
    (archives / "wrf_hydro_nwm_public-5.1.2.tar.gz").touch()
    prefix = tmp_path / "intel-site"
    args = [
        "bootstrap", "--shared-dir", str(archives), "--prefix", str(prefix),
        "--wrf-hydro-version", "5.1.2", "--site-toolchain", "--compiler-option", "ifort",
        "--netcdf", str(tmp_path / "netcdf"), "--dry-run",
    ]
    assert main(args) == 0
    script = prefix / "bootstrap_easy_wrf_hydro.sh"
    content = script.read_text()
    assert "COMPILER_FAMILY=intel" in content and "MPI_WRAPPER=mpiifort" in content
    assert "source_easy_wrf_hydro_intel_env" not in content
    assert "-dumpversion" not in content
    run(["bash", "-n", str(script)], check=True)
    with pytest.raises(SystemExit):
        main([*args, "--intel-home", str(tmp_path / "toolkit")])
