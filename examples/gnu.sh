#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  printf 'Usage: bash %s SHARED_DIR PREFIX [bootstrap options...]\n' "$0" >&2
  exit 2
fi

shared_dir="$1"
prefix="$2"
shift 2

exec ewhb bootstrap --compiler-family gnu \
  --shared-dir "$shared_dir" --prefix "$prefix" --jobs 4 "$@"
