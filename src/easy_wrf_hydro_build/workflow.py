"""WRF-Hydro build workflow helpers."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from .config import BuildConfig
from .shell import CommandResult, run
from .templates import compile_driver_script, compile_options_script, runtime_env_script


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_compile_options(config: BuildConfig, output: Path | None = None) -> Path:
    output = output or config.wrf_hydro_root / "setEnvar_easy_wrf_hydro.sh"
    output.write_text(compile_options_script(config), encoding="utf-8")
    return output


def write_runtime_env(config: BuildConfig, output: Path) -> Path:
    output.write_text(runtime_env_script(config), encoding="utf-8")
    _make_executable(output)
    return output


def write_compile_driver(config: BuildConfig, output: Path | None = None) -> Path:
    env_file = write_compile_options(config)
    output = output or config.wrf_hydro_root / "compile_easy_wrf_hydro.sh"
    output.write_text(compile_driver_script(config, str(env_file)), encoding="utf-8")
    _make_executable(output)
    return output


def compile_wrf_hydro(config: BuildConfig, *, dry_run: bool = False) -> CommandResult | Path:
    script = write_compile_driver(config)
    if dry_run:
        return script
    return run(["bash", str(script)], cwd=config.wrf_hydro_root, env=os.environ, check=True)
