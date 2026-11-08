#!/usr/bin/env bash
# Use a user-supplied, official Intel offline installer.
set -euo pipefail
umask 077

if (( $# != 4 && $# != 5 )) || [[ ${4:-} != --accept-eula ]]; then
  printf '%s\n' 'Usage: bash install-oneapi.sh OFFICIAL_INSTALLER SHA256 NEW_TOOLKIT_DIR --accept-eula [ifx|ifort]' \
    'Read the Intel license before passing --accept-eula. See ONEAPI.md for download and component instructions.' >&2
  exit 2
fi
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 || $EUID == 0 ]]; then
  printf 'Run as a normal user inside x86_64 Linux or WSL2.\n' >&2
  exit 2
fi
installer=$1
expected=$2
target=$3
compiler=${5:-ifx}
case "$compiler" in
  ifx) cc=icx; wrapper=mpiifx ;;
  ifort) cc=icc; wrapper=mpiifort ;;
  *) printf 'Choose ifx or ifort.\n' >&2; exit 2 ;;
esac
if [[ ! -f $installer || ! $expected =~ ^[a-fA-F0-9]{64}$ ]]; then
  printf 'Supply the official installer file and its 64-character SHA256.\n' >&2
  exit 2
fi
if [[ ! $target =~ ^/[a-zA-Z0-9_./+-]+$ || -e $target || -L $target ]]; then
  printf 'Choose a new absolute toolkit directory under your Linux home.\n' >&2
  exit 2
fi
ancestor=$(dirname -- "$target")
while [[ ! -d $ancestor ]]; do ancestor=$(dirname -- "$ancestor"); done
if ! probe=$(mktemp -d "$ancestor/.ewhb-oneapi-check-XXXXXX"); then
  printf 'Cannot write to %s. Choose a toolkit directory in your Linux home.\n' "$ancestor" >&2
  exit 2
fi
rmdir -- "$probe"
if command -v findmnt >/dev/null; then
  read -r filesystem options < <(findmnt -n -o FSTYPE,OPTIONS -T "$ancestor")
  case "$filesystem" in
    9p|drvfs|ntfs|ntfs3|exfat|vfat|cifs|virtiofs)
      printf 'Choose a directory on the Linux filesystem. In WSL2 use your Linux home.\n' >&2
      exit 2 ;;
  esac
  case ",$options," in
    *,noexec,*|*,ro,*) printf 'Choose a writable filesystem that allows execution.\n' >&2; exit 2 ;;
  esac
fi
actual=$(sha256sum -- "$installer")
expected=$(printf '%s' "$expected" | tr 'A-F' 'a-f')
if [[ ${actual%% *} != "$expected" ]]; then
  printf 'Installer SHA256 mismatch. Download the correct file from Intel.\n' >&2
  exit 2
fi
# Intel accepts the install directory with silent user-local installation.
instance=$(printf '%s' "$target" | sha256sum)
args=(--silent --eula accept --install-dir "$target" --instance "ewhb-${instance:0:12}")
if [[ -n ${EWHB_ONEAPI_COMPONENTS:-} ]]; then
  args+=(--components "$EWHB_ONEAPI_COMPONENTS")
fi
sh "$installer" -a "${args[@]}"

if [[ -f $target/setvars.sh ]]; then
  env_file="$target/setvars.sh"
else
  shopt -s nullglob
  candidates=("$target"/*/oneapi-vars.sh)
  if [[ -f $target/oneapi-vars.sh ]]; then
    candidates=("$target/oneapi-vars.sh")
  fi
  if (( ${#candidates[@]} != 1 )); then
    printf 'Locate oneapi-vars.sh under %s and use its containing directory as INTEL_HOME.\n' "$target" >&2
    exit 1
  fi
  env_file=${candidates[0]}
fi
set +u
source "$env_file"
set -u
for command in "$compiler" "$cc" "$wrapper"; do
  if ! command -v "$command" >/dev/null; then
    printf 'Missing %s. Select the Intel C/C++, Fortran and MPI development components.\n' "$command" >&2
    exit 1
  fi
done
if ! "$wrapper" --version | grep -qi "$compiler"; then
  printf 'The installed MPI wrapper does not use %s. Check the selected toolkit components.\n' "$compiler" >&2
  exit 1
fi
"$compiler" --version
printf 'Use this INTEL_HOME for install.sh: %s\n' "$(dirname -- "$env_file")"
