"""Check, install, and resume a version-specific offline WRF-Hydro bundle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time


class InstallError(Exception):
    """An actionable installation error, safe to show without a traceback."""


def fail(code, detail, action):
    raise InstallError(f'[{code}] {detail}\nNext step: {action}')


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def mount_info(path, text=None):
    """Return the longest matching mount, including escaped mount point names."""
    if text is None:
        source = Path('/proc/self/mountinfo')
        text = source.read_text() if source.exists() else ''
    result = ('', set())
    length = -1
    for line in text.splitlines():
        left, separator, right = line.partition(' - ')
        fields, fs = left.split(), right.split()
        if not separator or len(fields) < 6 or not fs:
            continue
        location = fields[4]
        for escaped, plain in [('\\040', ' '), ('\\011', '\t'), ('\\134', '\\')]:
            location = location.replace(escaped, plain)
        if (str(path) == location or str(path).startswith(location.rstrip('/') + '/')) and len(location) > length:
            result = (fs[0], set(fields[5].split(',')))
            length = len(location)
    return result


def check_location(prefix):
    if any(char.isspace() or char in "\\:$#(){}[]&;|<>`\"'" for char in str(prefix)):
        fail('E_PATH', 'The build directory contains spaces, Windows path syntax, or shell/Make special characters.', 'Choose a path without spaces, such as ~/ewhb/5.4.0.')
    ancestor = prefix
    while not ancestor.exists():
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        fail('E_PATH', f'{ancestor} is not a directory.', 'Choose a new directory under your Linux home.')
    filesystem, options = mount_info(ancestor)
    if filesystem in {'9p', 'drvfs', 'ntfs', 'ntfs3', 'fuseblk', 'exfat', 'vfat', 'cifs', 'virtiofs'}:
        fail('E_FILESYSTEM', f'Installation directory is on {filesystem}.',
             'Keep the download on the shared disk, but install inside the Linux home or an ext4 filesystem. On WSL use ~/ewhb, not /mnt/c. Do not try chmod 777.')
    if 'noexec' in options or 'ro' in options:
        fail('E_MOUNT', f'Mount options prevent installation: {sorted(options)}.', 'Choose a writable Linux filesystem that permits execution, or ask its administrator.')
    if prefix.exists() and prefix.stat().st_uid != os.geteuid():
        fail('E_OWNER', f'Installation directory belongs to another user: {prefix}.', 'Choose a new directory owned by your normal user. Do not rerun the installer with sudo.')
    try:
        with tempfile.TemporaryDirectory(prefix='.ewhb-check-', dir=ancestor) as temporary:
            probe = Path(temporary) / 'execute.sh'
            probe.write_text('#!/bin/sh\nexit 0\n')
            probe.chmod(0o700)
            link = Path(temporary) / 'link'
            link.symlink_to(probe.name)
            subprocess.run([str(link)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError) as exc:
        fail('E_PERMISSION', f'Cannot write, create links, or execute in {ancestor}: {exc}.',
             'Use a new directory under your normal Linux home. For a managed shared disk, ask the administrator about ownership and noexec; do not use sudo or chmod 777 as a workaround.')
    free = shutil.disk_usage(ancestor).free
    if free < 4 * 1024**3:
        fail('E_SPACE', f'Only {free / 1024**3:.1f} GiB is free.', 'Free at least 4 GiB or choose a larger Linux disk; 6 GiB per installation is recommended.')
    print(f'Writable/executable directory: {ancestor}; free space: {free / 1024**3:.1f} GiB', flush=True)


def save_state(path, state):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(path)


def run_logged(command, env, log, stage):
    print(f'{stage}. Log: {log}', flush=True)
    with log.open('a') as stream:
        stream.write(f'\n--- {stage} ---\n'); stream.flush()
        process = subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        start = time.monotonic()
        last = start
        try:
            while process.poll() is None:
                time.sleep(1)
                now = time.monotonic()
                if now - last >= 30:
                    print(f'{stage}: still running ({int(now - start)} seconds). Log: {log}', flush=True)
                    last = now
        except KeyboardInterrupt:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
        if process.returncode:
            tail = log.read_text(errors='replace')[-4000:]
            print(tail, file=sys.stderr)
            fail('E_STAGE', f'{stage} failed (exit {process.returncode}).',
                 f'Inspect {log}. For compiler/library errors also inspect model/logs/toolchain.log; for MPI errors inspect model/logs/run_croton_NWM.log. Fix the reported cause, then use the resume command below.')


def restore_identity(state_path, identity, resume):
    if not state_path.exists():
        fail('E_EXISTING', 'The destination exists without this installer’s state file.', 'Choose a new directory. Existing files will not be replaced.')
    state = json.loads(state_path.read_text())
    if state.get('bundle') != identity:
        fail('E_BUNDLE', 'This directory was created by a different bundle.', 'Use the original bundle to resume, or choose a new installation directory.')
    if not resume:
        fail('E_RESUME', 'This installation already has a state file.', 'Add --resume to continue the same installation.')
    return state


def install(args, root):
    if sys.version_info < (3, 9):
        fail('E_PYTHON', 'Python 3.9 or newer is required.', 'Use python3 from a supported Linux distribution.')
    if args.jobs < 1:
        fail('E_JOBS', '--jobs must be positive.', 'Use --jobs 2 or --jobs 4.')
    manifest = json.loads((root / 'manifest.json').read_text())
    target_platform = manifest['platform']
    expected = {'osx-arm64': ('Darwin', 'arm64'), 'linux-aarch64': ('Linux', 'aarch64'), 'linux-64': ('Linux', 'x86_64')}
    if expected.get(target_platform) != (platform.system(), platform.machine()):
        fail('E_ARCH', f'This bundle requires {target_platform}; choose a matching platform bundle.', 'Run uname -m inside Linux. x86_64 and aarch64 require different downloads.')
    if os.geteuid() == 0:
        fail('E_ROOT', 'Run this installer as a normal user, not root.', 'Exit sudo/root and install under your own home. If WSL starts as root, select your normal Linux user before installing.')
    is_mac = target_platform == 'osx-arm64'
    if not is_mac:
        kernel = platform.release().lower()
        if 'microsoft' in kernel and 'wsl2' not in kernel and 'microsoft-standard' not in kernel:
            fail('E_WSL1', 'This appears to be WSL1, which is not validated.', 'In Windows PowerShell inspect wsl --list --verbose and use a WSL2 distribution.')
        libc, version = platform.libc_ver()
        minimum = manifest['glibc_min']
        if libc != 'glibc' or tuple(map(int, version.split('.'))) < tuple(map(int, minimum.split('.'))):
            fail('E_GLIBC', f'Requires glibc >= {minimum}; detected {libc} {version}.', 'Choose a compatible Linux distribution. Do not replace the system glibc manually.')
    host_tools = ('xcrun', 'make', 'csh', 'bash', 'codesign') if is_mac else ('bash', 'tar', 'gzip', 'sed', 'awk', 'find', 'ldd')
    for tool in host_tools:
        if not shutil.which(tool):
            fail('E_TOOL', f'Missing host tool: {tool}.', 'See README.txt. On a managed machine ask the administrator to install the missing base tool, then rerun the same command.')
    if is_mac:
        subprocess.run(['xcrun', '--show-sdk-path'], check=True, stdout=subprocess.DEVNULL)
    prefix = args.prefix.expanduser().resolve()
    check_location(prefix)
    for relative, expected_hash in json.loads((root / 'checksums.json').read_text()).items():
        path = (root / relative).resolve()
        if root not in path.parents or checksum(path) != expected_hash:
            fail('E_CHECKSUM', f'Invalid or corrupted file: {relative}.', 'Download and extract the same release again. Do not edit the checksum manifest.')
    identity = checksum(root / 'checksums.json')
    state_path = prefix / '.ewhb-install-state.json'
    if prefix.exists():
        state = restore_identity(state_path, identity, args.resume or args.check_only)
    else:
        state = {'bundle': identity, 'stage': 'pending'}
    if args.check_only:
        print('Preflight passed. No dependencies or model have been installed.', flush=True)
        return
    prefix.mkdir(parents=True, exist_ok=True)
    lockfile = prefix / '.ewhb-install.lock'
    import fcntl
    with lockfile.open('a') as lockstream:
        try:
            fcntl.flock(lockstream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail('E_BUSY', 'Another installer is using this directory.', 'Wait for it to finish. Use a different destination for a separate installation.')
        # Re-read after acquiring the lock in case another process finished first.
        if state_path.exists():
            state = restore_identity(state_path, identity, args.resume)
        save_state(state_path, state)
        explicit = prefix / 'explicit-local.txt'
        explicit.write_text('@EXPLICIT\n' + '\n'.join((root / 'packages' / p['fn']).as_uri() + '#' + p['md5'] for p in manifest['dependencies']) + '\n')
        executable_dir = prefix / '.installer-bin'; executable_dir.mkdir(exist_ok=True)
        mamba = executable_dir / 'micromamba'
        shutil.copyfile(root / 'bin' / 'micromamba', mamba); mamba.chmod(0o700)
        env = os.environ.copy()
        env.update(MAMBA_ROOT_PREFIX=str(prefix / 'package-cache'), XDG_CACHE_HOME=str(prefix / 'cache'), CONDA_PKGS_DIRS=str(prefix / 'package-cache' / 'pkgs'), PYTHONPATH=str(root / 'tool'))
        target = prefix / 'environment'
        log = prefix / 'install.log'
        state['stage'] = 'dependencies'; save_state(state_path, state)
        operation = 'install' if (target / 'conda-meta' / 'history').exists() else 'create'
        run_logged([str(mamba), operation, '--yes', '--offline', '--no-rc', '--prefix', str(target), '--file', str(explicit)], env, log, '1/2 Restoring dependencies')
        if is_mac:
            macho = {b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}
            for binary in target.rglob('*'):
                if binary.is_symlink() or not binary.is_file():
                    continue
                with binary.open('rb') as stream:
                    magic = stream.read(4)
                if magic in macho:
                    subprocess.run(['codesign', '--force', '--sign', '-', str(binary)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        state['stage'] = 'model'; save_state(state_path, state)
        command = [sys.executable, '-m', 'easy_wrf_hydro_build.cli', 'bootstrap', '--wrf-hydro-version', manifest['wrf_hydro_version'], '--shared-dir', str(root / 'archives'), '--prefix', str(prefix / 'model'), '--netcdf', str(target), '--jobs', str(args.jobs)]
        if args.run_example:
            command.append('--run-example')
        if args.dry_run:
            command.append('--dry-run')
        hook = subprocess.run([str(mamba), 'shell', 'hook', '--shell', 'bash'], env=env, check=True, capture_output=True, text=True).stdout
        activation = hook + '\nmicromamba activate "$1" || exit $?\nshift\nexec "$@"\n'
        run_logged(['bash', '-c', activation, 'ewhb-install', str(target)] + command, env, log, '2/2 Building model and requested example')
        state['stage'] = 'script_generated' if args.dry_run else 'complete'; save_state(state_path, state)
    print(f'Installation directory: {prefix}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('--run-example', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help='Restore dependencies, then only generate model build script.')
    parser.add_argument('--check-only', action='store_true', help='Check permissions, filesystem, architecture, space, and bundle integrity.')
    parser.add_argument('--resume', action='store_true', help='Resume the same bundle in its managed installation directory.')
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    try:
        install(args, root)
        return 0
    except (InstallError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        if isinstance(exc, (KeyError, TypeError, json.JSONDecodeError)):
            exc = InstallError("[E_METADATA] Bundle or state metadata is incomplete. Re-extract the original bundle; use a new installation directory if its state file is damaged.")
        print(f'\nInstallation stopped: {exc or "interrupted"}', file=sys.stderr)
        prefix = args.prefix.expanduser().resolve()
        if (prefix / '.ewhb-install-state.json').exists():
            command = [sys.executable, str(root / 'install.py'), str(prefix), '--resume', '--jobs', str(args.jobs)]
            if args.run_example:
                command.append('--run-example')
            if args.dry_run:
                command.append('--dry-run')
            print('After correcting the cause, continue with:\n' + shlex.join(command), file=sys.stderr)
            print(f'Logs: {prefix / "install.log"} and {prefix / "model/logs"}', file=sys.stderr)
        else:
            print('No managed installation was created. Correct the reported issue and rerun the same command.\nFor permissions, use a directory owned by your normal user; do not use sudo/chmod 777 to bypass the check.', file=sys.stderr)
        return 130 if isinstance(exc, KeyboardInterrupt) else 1


if __name__ == '__main__':
    raise SystemExit(main())
