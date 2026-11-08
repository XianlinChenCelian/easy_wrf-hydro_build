"""Build one self-contained, platform-specific release candidate from a tested environment."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import tarfile

CASES = {
    '5.1.2': 'croton_NY_example_testcase.tar.gz',
    '5.2.0': 'croton_NY_training_example_v5.2.tar.gz',
    '5.4.0': 'croton_NY_training_example_v5.4.tar.gz',
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def build(args):
    records = [json.loads(p.read_text()) for p in sorted((args.environment / 'conda-meta').glob('*.json'))]
    platforms = {r['subdir'] for r in records} - {'noarch'}
    if len(platforms) != 1 or not platforms <= {'osx-arm64', 'linux-aarch64', 'linux-64'}:
        raise ValueError('Expected one supported platform: osx-arm64, linux-aarch64, or linux-64.')
    target_platform = platforms.pop()
    label = 'linux-x86_64' if target_platform == 'linux-64' else target_platform
    is_mac = target_platform == 'osx-arm64'
    glibc_min = max([tuple(map(int, m.groups())) for record in records
                     for dep in record.get('depends', [])
                     if (m := re.match(r'__glibc >=(\d+)\.(\d+)', dep))] + [(2, 17)])
    if not records:
        raise ValueError('An installed, tested conda environment is required.')
    name = f'ewhb-wrf-hydro-{args.version}-{label}-offline-preview'
    root = args.output / name
    root.mkdir(parents=True, exist_ok=False)
    for directory in ('packages', 'archives', 'bin', 'tool'):
        (root / directory).mkdir()
    locked = []
    for record in records:
        filename = record['fn']
        matches = list(args.cache.rglob(filename))
        if len(matches) != 1:
            raise ValueError(f'Expected one cached artifact for {filename}, found {len(matches)}')
        artifact = matches[0]
        checksum = sha256(artifact)
        if checksum != record['sha256']:
            raise ValueError(f'Package checksum mismatch: {filename}')
        shutil.copy2(artifact, root / 'packages' / filename)
        locked.append({k: record.get(k) for k in ('name', 'version', 'build', 'subdir', 'fn', 'url', 'sha256', 'md5', 'license', 'depends')})
    repo = Path(__file__).resolve().parents[2]
    shutil.copytree(repo / 'src' / 'easy_wrf_hydro_build', root / 'tool' / 'easy_wrf_hydro_build', ignore=shutil.ignore_patterns('__pycache__', '._*'))
    shutil.copy2(repo / 'LICENSE', root / 'tool' / 'LICENSE')
    shutil.copy2(args.micromamba, root / 'bin' / 'micromamba')
    for filename in (f'wrf_hydro_nwm_public-{args.version}.tar.gz', CASES[args.version]):
        shutil.copy2(args.archives / filename, root / 'archives' / filename)
    shutil.copy2(Path(__file__).with_name('install_bundle.py'), root / 'install.py')
    shutil.copy2(repo / 'docs' / 'installation-recovery.md', root / 'TROUBLESHOOTING.md')
    manifest = {'wrf_hydro_version': args.version, 'platform': target_platform, 'status': 'preview',
                'dependencies': locked, 'host_requirements': (['macOS arm64', 'Python >=3.9', 'Apple Command Line Tools (SDK, make, C compiler)', 'Bash and csh'] if is_mac else ['matching Linux architecture', 'Python >=3.9', 'Bash, tar, gzip, sed, awk, find, ldd', 'glibc >= ' + '.'.join(map(str, glibc_min))]),
                'glibc_min': None if is_mac else '.'.join(map(str, glibc_min)),
                'validation': 'Candidate only. See the separate platform and version validation records.'}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (root / 'README.txt').write_text(
        f'WRF-Hydro {args.version} / {label} / OFFLINE PREVIEW\n\n'
        f'Host requirements: {manifest["host_requirements"]}\n'
        f'Only this WRF-Hydro version, its matching Croton case, and all {len(locked)} locked conda packages are included.\n'
        'Check: python3 install.py /absolute/path/to/new-install --check-only\n'
        'Run: python3 install.py /absolute/path/to/new-install --run-example --jobs 4\n'
        'Resume after fixing errors: repeat the command with --resume. See TROUBLESHOOTING.md.\n'
        'Use a normal user, not sudo/root. Logs and state are saved in the installation directory.\n'
        'Use a native filesystem (APFS on Mac, ext4 or equivalent inside Linux/WSL2/VM).\n'
        'No root access, network dependency resolution, or existing conda installation is needed.\n'
        'Dependencies retain upstream licenses inside package archives; inspect manifest.json.\n'
        'Public release requires license review and clean-host testing.\n')
    checksums = {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob('*')) if p.is_file()}
    (root / 'checksums.json').write_text(json.dumps(checksums, indent=2) + '\n')
    destination = args.output / (name + '.tar.gz')
    with tarfile.open(destination, 'w:gz') as archive:
        archive.add(root, arcname=name, filter=lambda info: None if Path(info.name).name.startswith('._') else info)
    destination.with_name(destination.name + '.sha256').write_text(f'{sha256(destination)}  {destination.name}\n')
    print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=CASES, required=True)
    for arg in ('environment', 'cache', 'archives', 'micromamba', 'output'):
        parser.add_argument('--' + arg, type=Path, required=True)
    build(parser.parse_args())
