"""Build a WRF/WPS or coupled source add-on for one Hydro version."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from easy_wrf_hydro_build.atmosphere import (  # noqa: E402
    ATMOSPHERE_PROFILES, SOURCE_HASHES, sha256, source_names,
)


def build(version, sources, output, *, coupled=False, hydro_archives=None):
    if hydro_archives is not None and not coupled:
        raise ValueError("--hydro-archives requires --coupled.")
    names = source_names(version, coupled=coupled)
    inputs = {name: (hydro_archives if hydro_archives is not None and name.startswith("wrf_hydro_")
                     else sources) / name for name in names}
    for filename, path in inputs.items():
        if sha256(path) != SOURCE_HASHES[filename]:
            raise ValueError(f"SHA256 mismatch: {filename}")
    output.mkdir(parents=True, exist_ok=True)
    variant = "coupled" if coupled else "wrf-wps"
    name = f"ewhb-hydro-{version}-{variant}-source-preview"
    artifact = output / (name + ".tar.gz")
    if artifact.exists():
        raise ValueError(f"Already exists: {artifact}; choose a new output directory")
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        root = Path(temporary) / name
        (root / "archives").mkdir(parents=True)
        for filename, path in inputs.items():
            shutil.copyfile(path, root / "archives" / filename)
        shutil.copytree(REPO / "src/easy_wrf_hydro_build", root / "tool/easy_wrf_hydro_build",
                        ignore=shutil.ignore_patterns("__pycache__", "._*"))
        shutil.copyfile(REPO / "docs/wrf-wps.md", root / "README.md")
        shutil.copyfile(REPO / "LICENSE", root / "LICENSE")
        (root / "install.sh").write_text('''#!/bin/bash
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo "Activate your toolchain first, then: bash install.sh NEW_PREFIX NETCDF_PREFIX gnu|intel" >&2
  exit 2
fi
root=$(cd "$(dirname "$0")" && pwd)
export PYTHONPATH="$root/tool${PYTHONPATH:+:$PYTHONPATH}"
extra=(--jobs "${JOBS:-4}")
if [[ ${SKIP_WPS:-0} == 1 ]]; then extra+=(--skip-wps); fi
exec "${PYTHON:-python3}" -m easy_wrf_hydro_build.cli build-atmosphere \\
  --shared-dir "$root/archives" --prefix "$1" --netcdf "$2" \\
  --compiler-family "$3" --wrf-hydro-version "''' + version + '''" \\
  "${extra[@]}"''' + (" --coupled" if coupled else "") + "\n"
        )
        manifest = {"wrf_hydro": version, **ATMOSPHERE_PROFILES[version],
                    "kind": "optional-source-addon", "requires_activated_toolchain": True,
                    "mode": "coupled" if coupled else "atmosphere-only",
                    "validation": "see external validation records",
                    "source_sha256": {name: SOURCE_HASHES[name] for name in names}}
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (root / "SHA256SUMS").write_text("".join(
            f"{sha256(path)}  {path.relative_to(root)}\n"
            for path in sorted(root.rglob("*")) if path.is_file() and not path.name.startswith("._")
        ))
        staged = Path(temporary) / artifact.name
        with tarfile.open(staged, "w:gz") as stream:
            stream.add(root, arcname=name, filter=lambda entry: None if Path(entry.name).name.startswith("._") else entry)
        checksum = sha256(staged)
        staged.replace(artifact)
    artifact.with_suffix(artifact.suffix + ".sha256").write_text(f"{checksum}  {artifact.name}\n")
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrf-hydro-version", choices=ATMOSPHERE_PROFILES, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--coupled", action="store_true", help="Include pinned Hydro source for coupled WRF.")
    parser.add_argument("--hydro-archives", type=Path, help="Optional directory containing the Hydro source archive.")
    args = parser.parse_args()
    print(build(args.wrf_hydro_version, args.sources, args.output,
                coupled=args.coupled, hydro_archives=args.hydro_archives))
