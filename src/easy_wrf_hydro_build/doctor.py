"""Environment diagnostics for WRF-Hydro builds."""

from __future__ import annotations

import shlex
from pathlib import Path

from .config import BuildConfig
from .shell import run


def _exists(path: Path) -> tuple[bool, str]:
    return path.exists(), str(path)


def run_doctor(config: BuildConfig) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    checks.append(("wrf_hydro_root", *_exists(config.wrf_hydro_root)))
    checks.append(("configure", *_exists(config.wrf_hydro_root / "configure")))
    checks.append(("compile_script", *_exists(config.wrf_hydro_root / config.compile_script.strip("./"))))
    checks.append(("netcdf_include", *_exists(config.netcdf_inc)))
    checks.append(("netcdf_lib", *_exists(config.netcdf_lib)))
    checks.append(("nf-config", *_exists(config.netcdf / "bin" / "nf-config")))
    checks.append(("nc-config", *_exists(config.netcdf / "bin" / "nc-config")))

    if config.intel_home is not None:
        checks.append(("intel_home", *_exists(config.intel_home)))
        checks.append(("ifort", *_exists(config.intel_home / "bin" / "ifort")))

    setup = ""
    if config.intel_home is not None:
        intel_home = shlex.quote(str(config.intel_home))
        setup = (
            f"INTEL_HOME={intel_home}; "
            'if [ -f "$INTEL_HOME/setvars.sh" ]; then '
            'source "$INTEL_HOME/setvars.sh" --force >/dev/null 2>&1 || '
            'source "$INTEL_HOME/setvars.sh" >/dev/null 2>&1 || true; '
            "else "
            'compiler_vars=$(find "$INTEL_HOME" -path "*/bin/compilervars.sh" '
            "-print -quit 2>/dev/null); "
            '[ -n "$compiler_vars" ] && source "$compiler_vars" intel64 >/dev/null 2>&1 || true; '
            'mpi_vars=$(find "$INTEL_HOME" \\( -path "*/linux/mpi/intel64/bin/mpivars.sh" '
            '-o -path "*/mpi/latest/env/vars.sh" -o -path "*/mpi/*/env/vars.sh" \\) '
            "-print -quit 2>/dev/null); "
            '[ -n "$mpi_vars" ] && source "$mpi_vars" >/dev/null 2>&1 || true; '
            "fi; "
        )

    compiler_tools = [config.mpi_wrapper, "make", "gcc"]
    if config.compiler_family == "intel":
        compiler_tools.extend(["ifort", "icc"])
    else:
        compiler_tools.extend(["gfortran", "g++"])

    for tool in compiler_tools:
        result = run(["bash", "-lc", f"{setup}command -v {tool}"], check=False)
        checks.append((tool, result.returncode == 0, result.stdout.strip() or result.stderr.strip()))

    for config_tool in ["nc-config", "nf-config"]:
        tool_path = config.netcdf / "bin" / config_tool
        if tool_path.exists():
            result = run([str(tool_path), "--version"], check=False)
            checks.append((f"{config_tool} version", result.returncode == 0, result.stdout.strip()))

    return checks
