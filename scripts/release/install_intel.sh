#!/usr/bin/env bash
set -euo pipefail
umask 077

if (( $# < 2 || $# > 3 )); then
  printf 'Usage: bash install.sh ABSOLUTE_NEW_PREFIX INTEL_HOME_OR_--site-toolchain [ifort|ifx]\n' >&2
  exit 2
fi
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  printf 'Use this Intel recipe inside x86_64 Linux, WSL2 or an x86_64 Linux VM.\n' >&2
  exit 2
fi
if (( EUID == 0 )); then
  printf 'Run as a normal user. Choose a directory you own.\n' >&2
  exit 2
fi
prefix=$1
toolchain=$2
compiler=${3:-ifort}
root=$(cd -- "$(dirname -- "$0")" && pwd -P)
version=$(cat "$root/model-version.txt")
jobs=${EWHB_JOBS:-4}
if [[ ! $prefix =~ ^/[a-zA-Z0-9_./+-]+$ || -e $prefix || -L $prefix ]]; then
  printf 'Choose a new absolute install directory without spaces or shell characters.\n' >&2
  exit 2
fi
if [[ $toolchain == --site-toolchain ]]; then
  intel_args=(--site-toolchain)
else
  if [[ ! -d $toolchain ]]; then
    printf 'Provide the toolkit directory or use --site-toolchain after loading the site modules.\n' >&2
    exit 2
  fi
  intel_args=(--intel-home "$toolchain")
fi
case "$compiler" in
  ifort|ifx) ;;
  *) printf 'Choose ifort or ifx.\n' >&2; exit 2 ;;
esac
if [[ -n ${EWHB_NETCDF:-} ]]; then
  netcdf_args=(--netcdf "$EWHB_NETCDF")
elif [[ $compiler == ifx ]]; then
  printf 'Set EWHB_NETCDF to a NetCDF installation built for ifx, or use ifort to build the bundled libraries.\n' >&2
  exit 2
else
  netcdf_args=(--build-netcdf)
fi
if [[ ! $jobs =~ ^[1-9][0-9]*$ ]]; then
  printf 'EWHB_JOBS must be a positive integer.\n' >&2
  exit 2
fi
python=${EWHB_PYTHON:-python3}
if ! "$python" -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  printf 'Provide Python 3.9+ using EWHB_PYTHON.\n' >&2
  exit 2
fi
(cd "$root" && sha256sum -c SHA256SUMS)
mkdir -m 700 -p -- "$(dirname -- "$prefix")"
mkdir -m 700 -- "$prefix"
export PYTHONPATH="$root/tool"
"$python" -m easy_wrf_hydro_build.cli bootstrap \
  --compiler-family intel --compiler-option "$compiler" "${intel_args[@]}" \
  --wrf-hydro-version "$version" --shared-dir "$root/archives" \
  --prefix "$prefix/model" "${netcdf_args[@]}" --jobs "$jobs" --run-example \
  2>&1 | tee "$prefix/install.log"
