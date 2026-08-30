"""End-to-end WRF-Hydro bootstrap workflow."""

from __future__ import annotations

import os
import shlex
import stat
from dataclasses import dataclass
from pathlib import Path

from .archives import SourceArchive, discover_archives, require_archives
from .shell import CommandResult, run
from .templates import intel_environment_block


@dataclass(frozen=True)
class BootstrapConfig:
    shared_dir: Path
    prefix: Path
    compiler_family: str = "intel"
    intel_home: Path | None = None
    profile: str | None = None
    jobs: int = max(1, os.cpu_count() or 2)
    compiler_option: str = "ifort"
    mpi_wrapper: str = "mpiifort"
    land_model: str = "NoahMP"
    skip_deps: bool = False
    run_example: bool = False
    example_config: str = "NWM"
    example_np: int = 1

    @property
    def netcdf(self) -> Path:
        return self.prefix / f"{self.compiler_family}_libs"

    @property
    def script_path(self) -> Path:
        return self.prefix / "bootstrap_easy_wrf_hydro.sh"

    @property
    def profile_name(self) -> str:
        if self.profile:
            return self.profile
        if self.compiler_family == "gnu":
            return "gnu-linux"
        return "intel2018-linux"

    @property
    def env_script_name(self) -> str:
        return f"wrf_hydro_{self.compiler_family}_env.sh"


def _quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _archive_exports(archives: dict[str, SourceArchive]) -> str:
    lines = []
    for name, archive in archives.items():
        variable = f"{name.upper()}_ARCHIVE"
        lines.append(f"{variable}={_quote(archive.path)}")
    return "\n".join(lines)


def _example_block(config: BootstrapConfig) -> str:
    if not config.run_example:
        return ""

    executable = f"wrf_hydro_{config.land_model}.exe"
    return f"""
CROTON_CASE_ROOT=$(unpack "$CROTON_EXAMPLE_ARCHIVE")
EXAMPLE_CONFIG={_quote(config.example_config)}
EXAMPLE_RUN_DIR="$PREFIX/runs/croton_NY_$EXAMPLE_CONFIG"

stage_croton_example() {{
  mkdir -p "$PREFIX/runs"
  if [ ! -d "$CROTON_CASE_ROOT/$EXAMPLE_CONFIG" ]; then
    echo "Croton example configuration not found: $CROTON_CASE_ROOT/$EXAMPLE_CONFIG" >&2
    exit 1
  fi
  mkdir -p "$EXAMPLE_RUN_DIR"
  cp -a "$WRF_HYDRO_ROOT/Run/." "$EXAMPLE_RUN_DIR/"
  cp -a "$CROTON_CASE_ROOT/$EXAMPLE_CONFIG/." "$EXAMPLE_RUN_DIR/"
  if [ ! -e "$EXAMPLE_RUN_DIR/FORCING" ]; then
    ln -s "$CROTON_CASE_ROOT/FORCING" "$EXAMPLE_RUN_DIR/FORCING"
  fi
  cp "$WRF_HYDRO_ROOT/Run/{executable}" "$EXAMPLE_RUN_DIR/{executable}"
}}

run_croton_example() {{
  source "$PREFIX/{config.env_script_name}"
  cd "$EXAMPLE_RUN_DIR"
  mpirun -np {config.example_np} ./{executable} 2>&1 | tee "$LOG_DIR/run_croton_$EXAMPLE_CONFIG.log"
}}

run_step stage_croton_$EXAMPLE_CONFIG stage_croton_example
run_step run_croton_$EXAMPLE_CONFIG run_croton_example
"""


def _compiler_setup_block(config: BootstrapConfig) -> str:
    if config.compiler_family == "gnu":
        return """export CC=gcc
export CXX=g++
export FC=gfortran
export F77=gfortran
export F90=gfortran
export CFLAGS="${CFLAGS:-} -O2"
export CXXFLAGS="${CXXFLAGS:-} -O2"
export FCFLAGS="${FCFLAGS:-} -O2"
"""

    if config.intel_home is None:
        raise ValueError("Intel compiler builds require intel_home")

    return f"""{intel_environment_block('$INTEL_HOME')}
if command -v ifort >/dev/null 2>&1; then
  export FC=ifort
  export F77=ifort
  export F90=ifort
elif command -v ifx >/dev/null 2>&1; then
  export FC=ifx
  export F77=ifx
  export F90=ifx
else
  echo "Cannot find ifort or ifx after loading Intel environment." >&2
  exit 1
fi
if command -v icc >/dev/null 2>&1; then
  export CC=icc
elif command -v icx >/dev/null 2>&1; then
  export CC=icx
else
  echo "Cannot find icc or icx after loading Intel environment." >&2
  exit 1
fi
if command -v icpc >/dev/null 2>&1; then
  export CXX=icpc
elif command -v icpx >/dev/null 2>&1; then
  export CXX=icpx
else
  export CXX="$CC"
fi
export CFLAGS="${{CFLAGS:-}} -O2 -D__PURE_INTEL_C99_HEADERS__"
export CXXFLAGS="${{CXXFLAGS:-}} -O2 -D__PURE_INTEL_C99_HEADERS__"
export FCFLAGS="${{FCFLAGS:-}} -O2"
"""


def _runtime_env_block(config: BootstrapConfig) -> str:
    intel_lines = ""
    if config.compiler_family == "intel":
        if config.intel_home is None:
            raise ValueError("Intel compiler builds require intel_home")
        intel_lines = """export INTEL_HOME="$INTEL_HOME"
source_easy_wrf_hydro_intel_env() {
  local had_nounset=0
  case "\\$-" in
    *u*) had_nounset=1; set +u ;;
  esac

  if [ ! -d "\\$INTEL_HOME" ]; then
    echo "Intel compiler home not found: \\$INTEL_HOME" >&2
    if [ "\\$had_nounset" = "1" ]; then set -u; fi
    return 1
  fi

  if [ -f "\\$INTEL_HOME/setvars.sh" ]; then
    source "\\$INTEL_HOME/setvars.sh" --force >/dev/null 2>&1 || source "\\$INTEL_HOME/setvars.sh"
    if [ "\\$had_nounset" = "1" ]; then set -u; fi
    return 0
  fi

  local compiler_vars=""
  if [ -f "\\$INTEL_HOME/bin/compilervars.sh" ]; then
    compiler_vars="\\$INTEL_HOME/bin/compilervars.sh"
  else
    compiler_vars=\\$(find "\\$INTEL_HOME" -path "*/bin/compilervars.sh" -print -quit 2>/dev/null)
  fi
  if [ -z "\\$compiler_vars" ]; then
    echo "Cannot find Intel compilervars.sh or setvars.sh under \\$INTEL_HOME" >&2
    if [ "\\$had_nounset" = "1" ]; then set -u; fi
    return 1
  fi
  source "\\$compiler_vars" intel64

  local mpi_vars=""
  local candidate
  for candidate in \\
    "\\$INTEL_HOME"/compilers_and_libraries*/linux/mpi/intel64/bin/mpivars.sh \\
    "\\$INTEL_HOME"/mpi/latest/env/vars.sh \\
    "\\$INTEL_HOME"/mpi/*/env/vars.sh
  do
    if [ -f "\\$candidate" ]; then
      mpi_vars="\\$candidate"
      break
    fi
  done
  if [ -n "\\$mpi_vars" ]; then
    source "\\$mpi_vars"
  fi
  if [ "\\$had_nounset" = "1" ]; then set -u; fi
}
source_easy_wrf_hydro_intel_env
"""

    return f"""cat > "$PREFIX/{config.env_script_name}" <<EOF
#!/usr/bin/env bash
export WRFHYDRO_ROOT="$WRF_HYDRO_ROOT"
export NETCDF="$NETCDF"
export NETCDF_INC="\\$NETCDF/include"
export NETCDF_LIB="\\$NETCDF/lib"
{intel_lines}export PATH="\\$NETCDF/bin:\\$PATH"
export LD_LIBRARY_PATH="\\$NETCDF/lib:\\${{LD_LIBRARY_PATH:-}}"
export WRF_HYDRO=1
export HYDRO_D=0
export SPATIAL_SOIL=1
export WRF_HYDRO_RAPID=0
export WRFIO_NCD_LARGE_FILE_SUPPORT=1
export NCEP_WCOSS=0
export WRF_HYDRO_NUDGING=0
EOF
chmod +x "$PREFIX/{config.env_script_name}"
"""


def bootstrap_script(config: BootstrapConfig, archives: dict[str, SourceArchive]) -> str:
    compile_script = "./compile_offline_NoahMP.sh"
    if config.land_model.lower() == "noah":
        compile_script = "./compile_offline_Noah.sh"
    intel_home = _quote(config.intel_home) if config.intel_home is not None else '""'

    return f"""#!/usr/bin/env bash
set -eo pipefail

PROFILE={_quote(config.profile_name)}
COMPILER_FAMILY={_quote(config.compiler_family)}
SHARED_DIR={_quote(config.shared_dir)}
PREFIX={_quote(config.prefix)}
INTEL_HOME={intel_home}
NETCDF="$PREFIX/{config.compiler_family}_libs"
SRC_DIR="$PREFIX/sources"
BUILD_DIR="$PREFIX/build"
LOG_DIR="$PREFIX/logs"
JOBS={config.jobs}
SKIP_DEPS={1 if config.skip_deps else 0}

{_archive_exports(archives)}

mkdir -p "$PREFIX" "$SRC_DIR" "$BUILD_DIR" "$LOG_DIR" "$NETCDF"

log() {{
  printf '\\n[%s] %s\\n' "$(date '+%F %T')" "$*"
}}

run_step() {{
  local name="$1"
  shift
  local done_file="$LOG_DIR/$name.done"
  if [ -f "$done_file" ]; then
    log "skip $name; remove $done_file to rebuild"
    return 0
  fi
  log "start $name"
  "$@" 2>&1 | tee "$LOG_DIR/$name.log"
  touch "$done_file"
  log "done $name"
}}

unpack() {{
  local archive="$1"
  local top
  top=$(tar -tf "$archive" | awk -F/ 'NR==1 {{gsub(/^\\.\\//, "", $1); print $1}}')
  if [ -z "$top" ]; then
    echo "Cannot identify top-level directory in $archive" >&2
    return 1
  fi
  if [ ! -d "$SRC_DIR/$top" ]; then
    tar -xf "$archive" -C "$SRC_DIR"
  fi
  printf '%s\\n' "$SRC_DIR/$top"
}}

{_compiler_setup_block(config)}
set -u

export CPPFLAGS="-I$NETCDF/include ${{CPPFLAGS:-}}"
export LDFLAGS="-L$NETCDF/lib ${{LDFLAGS:-}}"
export PATH="$NETCDF/bin:$PATH"
export LD_LIBRARY_PATH="$NETCDF/lib:${{LD_LIBRARY_PATH:-}}"

build_zlib() {{
  local src
  src=$(unpack "$ZLIB_ARCHIVE")
  cd "$src"
  ./configure --prefix="$NETCDF"
  make -j "$JOBS"
  make install
}}

build_hdf5() {{
  local src
  src=$(unpack "$HDF5_ARCHIVE")
  cd "$src"
  ./configure --prefix="$NETCDF" --with-zlib="$NETCDF" --enable-fortran --enable-hl --enable-shared
  make -j "$JOBS"
  make install
}}

build_netcdf_c() {{
  local src
  src=$(unpack "$NETCDF_C_ARCHIVE")
  cd "$src"
  ./configure --prefix="$NETCDF" --disable-dap --enable-netcdf-4 --enable-shared
  make -j "$JOBS"
  make install
}}

build_netcdf_fortran() {{
  local src
  src=$(unpack "$NETCDF_FORTRAN_ARCHIVE")
  cd "$src"
  ./configure --prefix="$NETCDF" --enable-shared
  make -j "$JOBS"
  make install
}}

if [ "$SKIP_DEPS" = "1" ] && [ -x "$NETCDF/bin/nf-config" ]; then
  log "skip dependency builds; NetCDF-Fortran already exists at $NETCDF"
else
  run_step zlib build_zlib
  run_step hdf5 build_hdf5
  run_step netcdf_c build_netcdf_c
  run_step netcdf_fortran build_netcdf_fortran
fi

WRF_TOP=$(unpack "$WRF_HYDRO_ARCHIVE")
WRF_HYDRO_ROOT=$(find "$WRF_TOP" -path '*/trunk/NDHMS/configure' -type f -print -quit)
if [ -z "$WRF_HYDRO_ROOT" ]; then
  WRF_HYDRO_ROOT=$(find "$SRC_DIR" -path '*/trunk/NDHMS/configure' -type f -print -quit)
fi
if [ -z "$WRF_HYDRO_ROOT" ]; then
  echo "Cannot find WRF-Hydro trunk/NDHMS/configure after extracting $WRF_HYDRO_ARCHIVE" >&2
  exit 1
fi
WRF_HYDRO_ROOT=$(dirname "$WRF_HYDRO_ROOT")
printf '%s\\n' "$WRF_HYDRO_ROOT" > "$PREFIX/wrf_hydro_root.txt"

{_runtime_env_block(config)}

compile_wrf_hydro() {{
  cd "$WRF_HYDRO_ROOT"
  cat > setEnvar_easy_wrf_hydro.sh <<EOF
export WRF_HYDRO=1
export HYDRO_D=0
export SPATIAL_SOIL=1
export WRF_HYDRO_RAPID=0
export WRFIO_NCD_LARGE_FILE_SUPPORT=1
export NCEP_WCOSS=0
export WRF_HYDRO_NUDGING=0
EOF
  ./configure {config.compiler_option}
  sed -i 's/^COMPILER90[[:space:]]*=.*/COMPILER90  = {config.mpi_wrapper}/' macros
  grep '^COMPILER90' macros
  {compile_script} setEnvar_easy_wrf_hydro.sh 2>&1 | tee "$LOG_DIR/compile_offline_{config.land_model}.log"
  test -x "Run/wrf_hydro_{config.land_model}.exe"
  ldd "Run/wrf_hydro_{config.land_model}.exe" | tee "$LOG_DIR/ldd_wrf_hydro_{config.land_model}.log"
  if grep -q 'not found' "$LOG_DIR/ldd_wrf_hydro_{config.land_model}.log"; then
    echo "Missing runtime libraries; inspect $LOG_DIR/ldd_wrf_hydro_{config.land_model}.log" >&2
    exit 1
  fi
}}

run_step wrf_hydro_compile compile_wrf_hydro
{_example_block(config)}

log "bootstrap complete"
echo "Environment script: $PREFIX/{config.env_script_name}"
echo "WRF-Hydro root: $WRF_HYDRO_ROOT"
"""


def write_bootstrap_script(config: BootstrapConfig) -> Path:
    discovered = discover_archives(config.shared_dir)
    required = require_archives(discovered)
    if config.run_example:
        example = discovered.get("croton_example")
        if example is None:
            raise FileNotFoundError("Missing required Croton example archive: croton_NY_example_testcase.tar.gz")
        required["croton_example"] = example
    config.prefix.mkdir(parents=True, exist_ok=True)
    path = config.script_path
    path.write_text(bootstrap_script(config, required), encoding="utf-8")
    _make_executable(path)
    return path


def bootstrap(config: BootstrapConfig, *, dry_run: bool = False) -> Path | CommandResult:
    script = write_bootstrap_script(config)
    if dry_run:
        return script
    return run(["bash", str(script)], cwd=config.prefix, env=os.environ, check=True)
