import shlex
import subprocess

from easy_wrf_hydro_build.cli import main


def test_doctor_accepts_compiler_from_oneapi_and_cmake_tree(tmp_path, capsys):
    root = tmp_path / "sources" / "wrf_hydro_nwm_public-5.4.0"
    root.mkdir(parents=True)
    (root / "CMakeLists.txt").touch()
    netcdf = tmp_path / "netcdf"
    for directory in ("bin", "include", "lib"):
        (netcdf / directory).mkdir(parents=True)
    for tool in ("nc-config", "nf-config"):
        (netcdf / "bin" / tool).symlink_to("/usr/bin/true")

    oneapi = tmp_path / "oneAPI toolkit"
    bin_dir = oneapi / "compiler" / "2023.2.4" / "linux" / "bin" / "intel64"
    bin_dir.mkdir(parents=True)
    for tool in ("ifort", "icc", "mpiifort", "cmake"):
        (bin_dir / tool).symlink_to("/usr/bin/true")
    (oneapi / "setvars.sh").write_text(f"export PATH={shlex.quote(str(bin_dir))}:$PATH\n")

    assert main(["doctor", "--intel-home", str(oneapi), "--netcdf", str(netcdf),
                 "--wrf-hydro-root", str(root)]) == 0
    diagnostics = capsys.readouterr().out
    assert "CMakeLists.txt" in diagnostics
    assert str(bin_dir / "ifort") in diagnostics


def test_write_env_exports_the_cmake_run_directory(tmp_path):
    prefix = tmp_path / "build with spaces"
    root = prefix / "sources" / "wrf_hydro_nwm_public-5.4.0"
    root.mkdir(parents=True)
    (root / "CMakeLists.txt").touch()
    output = tmp_path / "runtime.sh"
    assert main(["write-env", "--compiler-family", "gnu", "--netcdf", str(tmp_path / "netcdf"),
                 "--wrf-hydro-root", str(root), "--output", str(output)]) == 0
    result = subprocess.check_output(
        ["bash", "-c", 'source "$1"; printf "%s" "$WRFHYDRO_RUN_DIR"', "check", str(output)],
        text=True,
    )
    assert result == str(prefix / "build" / "Run")
