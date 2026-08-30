"""Shell script templates used by the build workflow."""

from __future__ import annotations

from .config import BuildConfig


def intel_environment_block(intel_home: object) -> str:
    return f"""
export INTEL_HOME={intel_home}
source_easy_wrf_hydro_intel_env() {{
  local had_nounset=0
  case "$-" in
    *u*) had_nounset=1; set +u ;;
  esac

  if [ ! -d "$INTEL_HOME" ]; then
    echo "Intel compiler home not found: $INTEL_HOME" >&2
    if [ "$had_nounset" = "1" ]; then set -u; fi
    return 1
  fi

  if [ -f "$INTEL_HOME/setvars.sh" ]; then
    source "$INTEL_HOME/setvars.sh" --force >/dev/null 2>&1 || source "$INTEL_HOME/setvars.sh"
    if [ "$had_nounset" = "1" ]; then set -u; fi
    return 0
  fi

  local compiler_vars=""
  if [ -f "$INTEL_HOME/bin/compilervars.sh" ]; then
    compiler_vars="$INTEL_HOME/bin/compilervars.sh"
  else
    compiler_vars=$(find "$INTEL_HOME" -path "*/bin/compilervars.sh" -print -quit 2>/dev/null)
  fi
  if [ -z "$compiler_vars" ]; then
    echo "Cannot find Intel compilervars.sh or setvars.sh under $INTEL_HOME" >&2
    if [ "$had_nounset" = "1" ]; then set -u; fi
    return 1
  fi
  source "$compiler_vars" intel64

  local mpi_vars=""
  local candidate
  for candidate in \\
    "$INTEL_HOME"/compilers_and_libraries*/linux/mpi/intel64/bin/mpivars.sh \\
    "$INTEL_HOME"/mpi/latest/env/vars.sh \\
    "$INTEL_HOME"/mpi/*/env/vars.sh
  do
    if [ -f "$candidate" ]; then
      mpi_vars="$candidate"
      break
    fi
  done
  if [ -n "$mpi_vars" ]; then
    source "$mpi_vars"
  fi
  if [ "$had_nounset" = "1" ]; then set -u; fi
}}
source_easy_wrf_hydro_intel_env
"""


def compile_options_script(config: BuildConfig) -> str:
    return config.compile_options.to_shell_exports()


def runtime_env_script(config: BuildConfig) -> str:
    intel_lines = ""
    if config.intel_home is not None:
        intel_lines = intel_environment_block(config.intel_home)

    return f"""#!/usr/bin/env bash
export WRFHYDRO_ROOT={config.wrf_hydro_root}
export NETCDF={config.netcdf}
export NETCDF_INC="$NETCDF/include"
export NETCDF_LIB="$NETCDF/lib"
{intel_lines}
export PATH="$NETCDF/bin:$PATH"
export LD_LIBRARY_PATH="$NETCDF/lib:${{LD_LIBRARY_PATH:-}}"

{config.compile_options.to_shell_exports()}"""


def compile_driver_script(config: BuildConfig, env_file_name: str) -> str:
    intel_lines = ""
    if config.intel_home is not None:
        intel_lines = intel_environment_block(config.intel_home)

    return f"""#!/usr/bin/env bash
set -eo pipefail
{intel_lines}
set -u
export NETCDF={config.netcdf}
export NETCDF_INC="$NETCDF/include"
export NETCDF_LIB="$NETCDF/lib"
export PATH="$NETCDF/bin:$PATH"
export LD_LIBRARY_PATH="$NETCDF/lib:${{LD_LIBRARY_PATH:-}}"

cd {config.wrf_hydro_root}
./configure {config.compiler_option}
sed -i 's/^COMPILER90[[:space:]]*=.*/COMPILER90  = {config.mpi_wrapper}/' macros
grep '^COMPILER90' macros
{config.compile_script} {env_file_name} 2>&1 | tee compile_offline_{config.land_model}_easy.log
"""
