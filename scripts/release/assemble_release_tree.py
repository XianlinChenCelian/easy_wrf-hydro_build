"""Stage release artifacts by system architecture, compiler and model version."""
import argparse
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from build_offline_bundle import CASES, sha256


PLATFORMS = ('linux-x86_64', 'linux-aarch64', 'osx-arm64', 'windows-x86_64')
INTEL_SOURCES = (
    'zlib-1.2.11.tar.gz',
    'hdf5-1.12.0.tar.gz',
    'netcdf-c-4.7.4.tar.gz',
    'netcdf-fortran-4.5.3.tar.gz',
)
REPO = Path(__file__).resolve().parents[2]


def create_intel_recipe(output, version, model_archives, dependency_archives):
    name = f'ewhb-wrf-hydro-{version}-linux-x86_64-intel-source-preview'
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        root = Path(temporary) / name
        archives = root / 'archives'
        archives.mkdir(parents=True)
        for filename in (f'wrf_hydro_nwm_public-{version}.tar.gz', CASES[version]):
            shutil.copy2(model_archives / filename, archives / filename)
        for filename in INTEL_SOURCES:
            shutil.copy2(dependency_archives / filename, archives / filename)
        shutil.copytree(REPO / 'src/easy_wrf_hydro_build', root / 'tool/easy_wrf_hydro_build',
                        ignore=shutil.ignore_patterns('__pycache__', '._*'))
        shutil.copy2(REPO / 'LICENSE', root / 'LICENSE')
        shutil.copy2(Path(__file__).with_name('install_intel.sh'), root / 'install.sh')
        shutil.copy2(Path(__file__).with_name('install_oneapi.sh'), root / 'install-oneapi.sh')
        shutil.copy2(REPO / 'docs/oneapi-install.md', root / 'ONEAPI.md')
        (root / 'model-version.txt').write_text(version + '\n')
        (root / 'README.txt').write_text(
            f'WRF-Hydro {version} / Linux x86_64 / Intel source recipe\n\n'
            'Requires an installed Intel compiler and matching Intel MPI, Python 3.9+,\n'
            'and standard Linux build utilities. 5.4.0 also requires CMake 3.12+.\n'
            'On a cluster load its Intel compiler and MPI modules first, then run:\n'
            '  bash install.sh /absolute/new-prefix --site-toolchain ifort\n'
            'For personal oneAPI installation see ONEAPI.md and install-oneapi.sh.\n'
            'Run: bash install.sh /absolute/new-prefix /path/to/oneapi-environment ifx\n'
            'The ifx + mpiifx route is a preview. For classic toolchains choose ifort.\n'
            'Builds zlib, HDF5 and NetCDF from pinned source archives.\n'
            'Use a fresh prefix for each toolchain. Output is in PREFIX/install.log\n'
            'and PREFIX/model/logs. For a failed build review those logs and use a new prefix.\n'
        )
        manifest = {
            'platform': 'linux-x86_64', 'compiler_family': 'intel',
            'wrf_hydro_version': version, 'kind': 'source-recipe',
            'compiler_options': ['ifort', 'ifx'],
            'external_toolchain': True,
            'source_sha256': {p.name: sha256(p) for p in sorted(archives.iterdir())
                              if p.is_file() and not p.name.startswith('._')},
        }
        (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (root / 'SHA256SUMS').write_text(''.join(
            f'{sha256(p)}  {p.relative_to(root)}\n' for p in sorted(root.rglob('*'))
            if p.is_file() and p.name != 'SHA256SUMS' and not p.name.startswith('._')
        ))
        artifact = output / f'{name}.tar.gz'
        staged = Path(temporary) / artifact.name
        with tarfile.open(staged, 'w:gz') as archive:
            archive.add(root, arcname=name, filter=lambda entry: None if Path(entry.name).name.startswith('._') else entry)
        checksum = sha256(staged)
        staged.replace(artifact)
    artifact.with_name(artifact.name + '.sha256').write_text(f'{checksum}  {artifact.name}\n')
    return artifact


def stage(args):
    args.output.mkdir(parents=True, exist_ok=False)
    entries = []
    for platform in PLATFORMS:
        for compiler in ('gnu', 'intel'):
            for version in CASES:
                leaf = args.output / platform / compiler / version
                leaf.mkdir(parents=True)
                entry = {'platform': platform, 'compiler': compiler, 'version': version}
                if platform == 'windows-x86_64':
                    entry.update(kind='use-linux-guest', alternative=f'linux-x86_64/{compiler}/{version}')
                elif compiler == 'intel' and platform != 'linux-x86_64':
                    entry.update(kind='unsupported-native', alternative=f'{platform}/gnu/{version}',
                                 remote_alternative=f'linux-x86_64/intel/{version}')
                elif compiler == 'intel':
                    artifact = create_intel_recipe(leaf, version, args.model_archives, args.dependency_archives)
                    entry.update(kind='source-recipe', artifact=str(artifact.relative_to(args.output)))
                else:
                    name = f'ewhb-wrf-hydro-{version}-{platform}-offline-preview.tar.gz'
                    source = args.gnu_bundles / name
                    checksum = source.with_name(name + '.sha256')
                    expected = checksum.read_text().split()[0]
                    artifact = shutil.copy2(source, leaf / name)
                    if sha256(Path(artifact)) != expected:
                        raise ValueError(f'GNU bundle SHA256 mismatch: {source}')
                    shutil.copy2(checksum, leaf / checksum.name)
                    entry.update(kind='offline-bundle', artifact=str((leaf / name).relative_to(args.output)))
                if 'artifact' not in entry:
                    note = f"{entry['kind']}\nUse {entry['alternative']}.\n"
                    if 'remote_alternative' in entry:
                        note += f"Remote x86_64 Intel route: {entry['remote_alternative']}.\n"
                    (leaf / 'README.txt').write_text(note)
                entries.append(entry)
    (args.output / 'index.json').write_text(json.dumps(entries, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gnu-bundles', type=Path)
    parser.add_argument('--intel-version', choices=CASES, help='Stage just one Intel source recipe.')
    for name in ('model-archives', 'dependency-archives', 'output'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    args = parser.parse_args()
    if args.intel_version:
        leaf = args.output / 'linux-x86_64' / 'intel' / args.intel_version
        leaf.mkdir(parents=True, exist_ok=True)
        print(create_intel_recipe(leaf, args.intel_version, args.model_archives, args.dependency_archives))
    elif args.gnu_bundles:
        stage(args)
    else:
        parser.error('Provide --gnu-bundles for a full tree or --intel-version for one Intel recipe.')


if __name__ == '__main__':
    main()
