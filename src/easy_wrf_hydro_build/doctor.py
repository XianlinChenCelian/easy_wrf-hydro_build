"""Environment diagnostics for WRF-Hydro builds."""

from __future__ import annotations

import shlex
from pathlib import Path

from .config import BuildConfig
from .shell import run
from .templates import intel_environment_block


def _exists(path: Path) -> tuple[bool, str]:
    return path.exists(), str(path)


def run_doctor(config: BuildConfig) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    checks.append(("wrf_hydro_root", *_exists(config.wrf_hydro_root)))
    if config.uses_cmake:
        checks.append(("CMakeLists.txt", *_exists(config.wrf_hydro_root / "CMakeLists.txt")))
    else:
        checks.append(("configure", *_exists(config.wrf_hydro_root / "configure")))
        checks.append(("compile_script", *_exists(config.wrf_hydro_root / config.compile_script)))
    checks.append(("netcdf_include", *_exists(config.netcdf_inc)))
    checks.append(("netcdf_lib", *_exists(config.netcdf_lib)))
    checks.append(("nf-config", *_exists(config.netcdf / "bin" / "nf-config")))
    checks.append(("nc-config", *_exists(config.netcdf / "bin" / "nc-config")))

    setup = ""
    if config.compiler_family == "intel" and config.intel_home is not None:
        checks.append(("intel_home", *_exists(config.intel_home)))
        intel_home = shlex.quote(str(config.intel_home))
        activation = intel_environment_block(intel_home).rstrip()
        setup = f"{{{activation}\n}} >/dev/null || exit $?\n"

    compiler_tools = [config.mpi_wrapper, "cmake" if config.uses_cmake else "make"]
    if config.compiler_family == "intel":
        compiler_tools.extend(("ifx", "icx") if config.compiler_option == "ifx" else ("ifort", "icc"))
    else:
        compiler_tools.extend(("gcc", "gfortran", "g++"))

    for tool in compiler_tools:
        result = run(["bash", "-c", f'{setup}command -v -- "$1"', "ewhb-doctor", tool], check=False)
        detail = result.stdout.strip() or result.stderr.strip() or "Activate a toolchain that provides this command."
        checks.append((tool, result.returncode == 0, detail))

    for config_tool in ["nc-config", "nf-config"]:
        tool_path = config.netcdf / "bin" / config_tool
        if tool_path.exists():
            result = run([str(tool_path), "--version"], check=False)
            checks.append((f"{config_tool} version", result.returncode == 0, result.stdout.strip()))

    return checks
