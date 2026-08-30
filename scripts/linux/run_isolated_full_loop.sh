#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

COMPILER_FAMILY="intel"
SHARED_DIR="/mnt/d/wrf-hydro-packages"
PREFIX=""
INTEL_HOME="$HOME/intel/parallel_studio_xe_2018"
JOBS=$(nproc 2>/dev/null || echo 2)
RUN_EXAMPLE=1
CLEANUP_ON_SUCCESS=1

usage() {
  cat <<'EOF'
Usage:
  run_isolated_full_loop.sh [options]

Options:
  --compiler-family intel|gnu   Compiler path to test. Default: intel.
  --shared-dir PATH             Source archive directory. Default: /mnt/d/wrf-hydro-packages.
  --prefix PATH                 Isolated test prefix. Default: ~/ewhb_isolated_full_<family>_<timestamp>.
  --intel-home PATH             Intel compiler prefix. Default: ~/intel/parallel_studio_xe_2018.
  --jobs N                      Parallel make jobs. Default: nproc.
  --no-run-example              Build only; do not stage/run Croton NY.
  --keep                        Keep the isolated prefix after a successful run.
  -h, --help                    Show this help.
EOF
}

expand_path() {
  case "$1" in
    "~") printf "%s\n" "$HOME" ;;
    "~/"*) printf "%s/%s\n" "$HOME" "${1#~/}" ;;
    *) printf "%s\n" "$1" ;;
  esac
}

while [ $# -gt 0 ]; do
  case "$1" in
    --compiler-family) COMPILER_FAMILY="$2"; shift 2 ;;
    --shared-dir) SHARED_DIR="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --intel-home) INTEL_HOME="$2"; shift 2 ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --no-run-example) RUN_EXAMPLE=0; shift ;;
    --keep) CLEANUP_ON_SUCCESS=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ "$COMPILER_FAMILY" != "intel" ] && [ "$COMPILER_FAMILY" != "gnu" ]; then
  echo "--compiler-family must be intel or gnu" >&2
  exit 2
fi

SHARED_DIR=$(expand_path "$SHARED_DIR")
INTEL_HOME=$(expand_path "$INTEL_HOME")
if [ -z "$PREFIX" ]; then
  PREFIX="$HOME/ewhb_isolated_full_${COMPILER_FAMILY}_$(date +%Y%m%d_%H%M%S)"
else
  PREFIX=$(expand_path "$PREFIX")
fi

case "$PREFIX" in
  "$HOME"/ewhb_isolated_full_*|/tmp/ewhb_isolated_full_*) ;;
  *)
    echo "Refusing unsafe isolated prefix: $PREFIX" >&2
    echo "Use a prefix under ~/ewhb_isolated_full_* or /tmp/ewhb_isolated_full_*." >&2
    exit 2
    ;;
esac

cleanup() {
  local status=$?
  if [ "$status" -eq 0 ] && [ "$CLEANUP_ON_SUCCESS" = "1" ]; then
    rm -rf -- "$PREFIX"
    echo "Cleaned isolated prefix: $PREFIX"
  else
    echo "Kept isolated prefix for inspection: $PREFIX"
  fi
}
trap cleanup EXIT

args=(
  bootstrap
  --compiler-family "$COMPILER_FAMILY"
  --shared-dir "$SHARED_DIR"
  --prefix "$PREFIX"
  --jobs "$JOBS"
)

if [ "$COMPILER_FAMILY" = "intel" ]; then
  args+=(--intel-home "$INTEL_HOME")
fi
if [ "$RUN_EXAMPLE" = "1" ]; then
  args+=(--run-example --example-np 1)
fi

echo "Repository: $REPO_DIR"
echo "Compiler family: $COMPILER_FAMILY"
echo "Shared archives: $SHARED_DIR"
echo "Isolated prefix: $PREFIX"
PYTHONPATH="$REPO_DIR/src" python3 -m easy_wrf_hydro_build.cli "${args[@]}"
