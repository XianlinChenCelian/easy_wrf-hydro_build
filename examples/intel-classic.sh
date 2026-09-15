#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  printf 'Usage: bash %s SHARED_DIR PREFIX INTEL_HOME [bootstrap options...]\n' "$0" >&2
  exit 2
fi

shared_dir="$1"
prefix="$2"
intel_home="$3"
shift 3

exec ewhb bootstrap --compiler-family intel \
  --shared-dir "$shared_dir" --prefix "$prefix" \
  --intel-home "$intel_home" --jobs 4 "$@"
