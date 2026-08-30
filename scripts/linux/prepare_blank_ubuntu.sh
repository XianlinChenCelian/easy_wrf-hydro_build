#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

SHARED_DIR="/mnt/d/wrf-hydro-packages"
PREFIX="$HOME/wrfhydro_build"
INTEL_HOME="$HOME/intel/parallel_studio_xe_2018"
PYTHON_ENV_HOME="$HOME/wrfhydro_env"
INSTALL_INTEL=1
INSTALL_PYTHON_ENV=1
RUN_EXAMPLE=0
DRY_RUN=0
SKIP_DEPS=0
JOBS=$(nproc 2>/dev/null || echo 2)

usage() {
  cat <<'EOF'
Usage:
  prepare_blank_ubuntu.sh --shared-dir /mnt/d/wrf-hydro-packages [options]

Options:
  --shared-dir PATH      Directory containing Intel, WRF-Hydro, and dependency archives.
  --prefix PATH          Build prefix. Default: ~/wrfhydro_build
  --intel-home PATH      Intel install prefix. Default: ~/intel/parallel_studio_xe_2018
  --python-env-home PATH Python/Jupyter env prefix. Default: ~/wrfhydro_env
  --repo-dir PATH        easy_wrf-hydro_build checkout. Default: detected from this script.
  --no-install-intel     Do not install Intel; require --intel-home to already exist.
  --no-python-env        Do not restore hydro_env_packed.tar.gz.
  --run-example          Stage and run the Croton NY example after compilation.
  --skip-deps            Skip dependency builds when NetCDF already exists.
  --dry-run              Generate scripts only; do not compile.
  --jobs N               Parallel make jobs. Default: nproc.
  -h, --help             Show this help.
EOF
}

expand_path() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${1#~/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

while [ $# -gt 0 ]; do
  case "$1" in
    --shared-dir) SHARED_DIR="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --intel-home) INTEL_HOME="$2"; shift 2 ;;
    --python-env-home) PYTHON_ENV_HOME="$2"; shift 2 ;;
    --repo-dir) REPO_DIR="$2"; shift 2 ;;
    --no-install-intel) INSTALL_INTEL=0; shift ;;
    --no-python-env) INSTALL_PYTHON_ENV=0; shift ;;
    --run-example) RUN_EXAMPLE=1; shift ;;
    --skip-deps) SKIP_DEPS=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --jobs) JOBS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

SHARED_DIR=$(expand_path "$SHARED_DIR")
PREFIX=$(expand_path "$PREFIX")
INTEL_HOME=$(expand_path "$INTEL_HOME")
PYTHON_ENV_HOME=$(expand_path "$PYTHON_ENV_HOME")
REPO_DIR=$(expand_path "$REPO_DIR")

log() {
  printf '\n[%s] %s\n' "$(date '+%F %T')" "$*"
}

find_first() {
  local root="$1"
  shift
  local pattern
  for pattern in "$@"; do
    find "$root" -type f -name "$pattern" -print -quit
  done
}

require_file() {
  local path="$1"
  local label="$2"
  if [ -z "$path" ] || [ ! -f "$path" ]; then
    echo "Missing $label" >&2
    exit 1
  fi
}

install_system_packages() {
  log "install Ubuntu build prerequisites"
  sudo apt-get update
  sudo apt-get install -y \
    build-essential \
    ca-certificates \
    csh \
    file \
    gawk \
    git \
    gzip \
    m4 \
    make \
    patch \
    perl \
    pkg-config \
    python3 \
    python3-venv \
    tar \
    tcsh \
    unzip \
    xz-utils
}

install_intel_if_needed() {
  if [ -x "$INTEL_HOME/bin/ifort" ]; then
    log "Intel compiler already exists at $INTEL_HOME"
    return 0
  fi
  if [ "$INSTALL_INTEL" != "1" ]; then
    echo "Intel compiler not found: $INTEL_HOME" >&2
    echo "Rerun without --no-install-intel, or install Intel manually." >&2
    exit 1
  fi

  local archive license work installer top silent_template cfg
  archive=$(find_first "$SHARED_DIR" "parallel_studio_xe_*cluster_edition.tgz")
  license=$(find_first "$SHARED_DIR" "parallel_studio_xe_*.lic" "*.lic")
  require_file "$archive" "Intel Parallel Studio archive"
  require_file "$license" "Intel license file"

  log "prepare Intel silent installer"
  work="$PREFIX/installers/intel"
  mkdir -p "$work"
  if [ -z "$(find "$work" -maxdepth 2 -name install.sh -print -quit)" ]; then
    tar -xf "$archive" -C "$work"
  fi
  installer=$(find "$work" -maxdepth 2 -name install.sh -print -quit)
  require_file "$installer" "Intel install.sh"
  top=$(dirname "$installer")
  silent_template="$top/silent.cfg"
  require_file "$silent_template" "Intel silent.cfg"

  cfg="$work/silent_easy_wrf_hydro.cfg"
  cp "$silent_template" "$cfg"
  sed -i \
    -e 's/^ACCEPT_EULA=.*/ACCEPT_EULA=accept/' \
    -e "s|^PSET_INSTALL_DIR=.*|PSET_INSTALL_DIR=$INTEL_HOME|" \
    -e 's/^ACTIVATION_TYPE=.*/ACTIVATION_TYPE=license_file/' \
    -e "s|^#ACTIVATION_LICENSE_FILE=.*|ACTIVATION_LICENSE_FILE=$license|" \
    -e "s|^ACTIVATION_LICENSE_FILE=.*|ACTIVATION_LICENSE_FILE=$license|" \
    "$cfg"
  if ! grep -q '^ACTIVATION_LICENSE_FILE=' "$cfg"; then
    printf 'ACTIVATION_LICENSE_FILE=%s\n' "$license" >> "$cfg"
  fi

  log "install Intel Parallel Studio to $INTEL_HOME"
  bash "$installer" --silent "$cfg" --cli-mode --user-mode

  if [ ! -x "$INTEL_HOME/bin/ifort" ]; then
    echo "Intel installation finished but ifort was not found at $INTEL_HOME/bin/ifort" >&2
    exit 1
  fi
}

restore_python_env_if_needed() {
  if [ "$INSTALL_PYTHON_ENV" != "1" ]; then
    log "skip Python/Jupyter environment restore"
    return 0
  fi

  local archive marker
  archive=$(find_first "$SHARED_DIR" "hydro_env_packed.tar.gz" "*hydro*env*packed*.tar.gz")
  if [ -z "$archive" ]; then
    log "skip Python/Jupyter environment; hydro_env_packed.tar.gz was not found"
    return 0
  fi

  marker="$PYTHON_ENV_HOME/.easy_wrf_hydro_env_ready"
  if [ -f "$marker" ] && [ -x "$PYTHON_ENV_HOME/bin/python" ]; then
    log "Python/Jupyter environment already exists at $PYTHON_ENV_HOME"
    return 0
  fi

  log "restore Python/Jupyter environment to $PYTHON_ENV_HOME"
  mkdir -p "$PYTHON_ENV_HOME"
  tar -xzf "$archive" -C "$PYTHON_ENV_HOME"
  env PATH="$PYTHON_ENV_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    "$PYTHON_ENV_HOME/bin/conda-unpack"
  env PATH="$PYTHON_ENV_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    "$PYTHON_ENV_HOME/bin/python" -m ipykernel install \
      --user \
      --name wrfhydro_env \
      --display-name "Python (wrfhydro_env)"
  touch "$marker"
}

write_ewhb_wrapper() {
  mkdir -p "$PREFIX/bin"
  cat > "$PREFIX/bin/ewhb" <<EOF
#!/usr/bin/env bash
PYTHONPATH="$REPO_DIR/src" python3 -m easy_wrf_hydro_build.cli "\$@"
EOF
  chmod +x "$PREFIX/bin/ewhb"
}

run_bootstrap() {
  local args=(
    bootstrap
    --shared-dir "$SHARED_DIR"
    --prefix "$PREFIX"
    --intel-home "$INTEL_HOME"
    --jobs "$JOBS"
  )
  if [ "$RUN_EXAMPLE" = "1" ]; then
    args+=(--run-example)
  fi
  if [ "$SKIP_DEPS" = "1" ]; then
    args+=(--skip-deps)
  fi
  if [ "$DRY_RUN" = "1" ]; then
    args+=(--dry-run)
  fi

  log "run ewhb ${args[*]}"
  PYTHONPATH="$REPO_DIR/src" python3 -m easy_wrf_hydro_build.cli "${args[@]}"
}

if [ ! -d "$SHARED_DIR" ]; then
  echo "Shared directory not found: $SHARED_DIR" >&2
  exit 1
fi
if [ ! -d "$REPO_DIR/src/easy_wrf_hydro_build" ]; then
  echo "Repository directory not found or incomplete: $REPO_DIR" >&2
  exit 1
fi

mkdir -p "$PREFIX"
install_system_packages
install_intel_if_needed
restore_python_env_if_needed
write_ewhb_wrapper
run_bootstrap

log "blank Ubuntu preparation complete"
echo "Add this to a shell when you want to use the compiled environment:"
echo "source $PREFIX/wrf_hydro_intel_env.sh"
echo ""
echo "Activate the Python/Jupyter environment with:"
echo "source $PYTHON_ENV_HOME/bin/activate"
