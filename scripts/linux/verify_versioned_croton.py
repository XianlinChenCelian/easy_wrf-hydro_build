"""Verify the pinned three-version Croton cases and save reviewable evidence."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import struct
import subprocess


VERSIONS = ('5.1.2', '5.2.0', '5.4.0')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_version(base, output, version, execution_mode, host_architecture):
    root = base / version
    model = root / 'model'
    destination = output / version
    destination.mkdir(parents=True, exist_ok=True)
    state_path = root / '.ewhb-install-state.json'
    if state_path.exists():
        require(json.loads(state_path.read_text())['stage'] == 'complete', f'{version}: installer did not complete')
    files = sorted((model / 'runs').rglob('*CHANOBS_DOMAIN1'))
    diagnostics = list((model / 'runs').rglob('diag_hydro.00000'))
    require(len(files) == 168, f'{version}: expected 168 hourly outputs, found {len(files)}')
    require(len(diagnostics) == 1, f'{version}: expected one Croton diagnostic log')
    require('The model finished successfully' in diagnostics[0].read_text(), f'{version}: missing success marker')
    require(files[-1].name == '201109020000.CHANOBS_DOMAIN1', f'{version}: incorrect final timestamp')
    executables = list((model / 'runs').rglob('wrf_hydro_NoahMP.exe'))
    require(len(executables) == 1, f'{version}: expected one runtime executable')
    with executables[0].open('rb') as stream:
        header = stream.read(20)
    require(header[:4] == b'\x7fELF', f'{version}: runtime executable is not ELF')
    machine = struct.unpack('<H' if header[5] == 1 else '>H', header[18:20])[0]
    require(machine == {'x86_64': 62, 'aarch64': 183}[platform.machine()], f'{version}: executable architecture mismatch')
    result = subprocess.run(
        [str(root / 'environment/bin/ncdump'), '-v', 'streamflow', str(files[-1])],
        check=True, capture_output=True, text=True,
    )
    (destination / 'final-streamflow.txt').write_text(result.stdout)
    shutil.copy2(files[-1], destination / files[-1].name)
    shutil.copy2(diagnostics[0], destination / diagnostics[0].name)
    shutil.copytree(model / 'logs', destination / 'logs', dirs_exist_ok=True)
    records = [json.loads(path.read_text()) for path in (root / 'environment/conda-meta').glob('*.json')]
    versions = {record['name']: record['version'] for record in records}
    (destination / 'dependency-versions.json').write_text(json.dumps(versions, indent=2) + '\n')
    return {
        'wrf_hydro': version, 'hourly_outputs': len(files),
        'final_time': '2011-09-02 00:00', 'status': 'success',
        'architecture': platform.machine(), 'execution_mode': execution_mode,
        'host_architecture': host_architecture, 'elf_machine': machine,
        'glibc': platform.libc_ver()[1], 'kernel': platform.release(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path, help='Directory containing VERSION/model and VERSION/environment.')
    parser.add_argument('output', type=Path)
    parser.add_argument('--execution-mode', choices=('native', 'qemu-user'), required=True)
    parser.add_argument('--host-architecture')
    args = parser.parse_args()
    if args.execution_mode == 'qemu-user' and not args.host_architecture:
        parser.error('Specify the real host architecture for emulation evidence.')
    host = args.host_architecture or platform.machine()
    args.output.mkdir(parents=True, exist_ok=True)
    results = [verify_version(args.base, args.output, version, args.execution_mode, host) for version in VERSIONS]
    (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
