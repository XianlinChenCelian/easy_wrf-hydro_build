import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('installer_recovery', Path(__file__).parents[1] / 'scripts/release/install_bundle.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def test_mount_selection_uses_longest_path_and_escaped_names():
    mounts = '1 0 8:1 / / rw - ext4 /dev/sda rw\n2 1 0:1 / /mnt/c rw - 9p C: rw\n3 1 0:2 / /data/my\\040disk ro,noexec - ext4 /dev/sdb ro\n'
    assert installer.mount_info(Path('/mnt/c/project'), mounts)[0] == '9p'
    assert installer.mount_info(Path('/mnt/cc/project'), mounts)[0] == 'ext4'
    assert 'noexec' in installer.mount_info(Path('/data/my disk/project'), mounts)[1]


def test_windows_shared_directory_gives_recovery_guidance(tmp_path, monkeypatch):
    monkeypatch.setattr(installer, 'mount_info', lambda path: ('9p', {'rw'}))
    with pytest.raises(installer.InstallError, match='E_FILESYSTEM') as error:
        installer.check_location(tmp_path / 'new')
    assert 'not /mnt/c' in str(error.value)


def test_noexec_mount_is_detected_before_installation(tmp_path, monkeypatch):
    monkeypatch.setattr(installer, 'mount_info', lambda path: ('ext4', {'rw', 'noexec'}))
    with pytest.raises(installer.InstallError, match='E_MOUNT'):
        installer.check_location(tmp_path / 'new')


def test_unwritable_directory_gives_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setattr(installer, 'mount_info', lambda path: ('ext4', {'rw'}))
    def deny(**kwargs):
        raise PermissionError('read-only or permission denied')
    monkeypatch.setattr(installer.tempfile, 'TemporaryDirectory', deny)
    with pytest.raises(installer.InstallError, match='E_PERMISSION') as error:
        installer.check_location(tmp_path / 'new')
    assert 'normal Linux home' in str(error.value)


def test_resume_requires_owned_state_and_same_bundle(tmp_path):
    state_path = tmp_path / '.ewhb-install-state.json'
    with pytest.raises(installer.InstallError, match='E_EXISTING'):
        installer.restore_identity(state_path, 'bundle-a', True)
    installer.save_state(state_path, {'bundle': 'bundle-a', 'stage': 'model'})
    with pytest.raises(installer.InstallError, match='E_BUNDLE'):
        installer.restore_identity(state_path, 'bundle-b', True)
    with pytest.raises(installer.InstallError, match='E_RESUME'):
        installer.restore_identity(state_path, 'bundle-a', False)
    assert installer.restore_identity(state_path, 'bundle-a', True)['stage'] == 'model'
    assert json.loads(state_path.read_text())['bundle'] == 'bundle-a'


@pytest.mark.parametrize('name', ['with space', 'D:\\WRF', 'build$(test)', 'case(1)'])
def test_unsafe_build_paths_are_rejected(tmp_path, name):
    with pytest.raises(installer.InstallError, match='E_PATH'):
        installer.check_location(tmp_path / name)


def test_wsl1_has_specific_upgrade_guidance(tmp_path, monkeypatch):
    from types import SimpleNamespace
    (tmp_path / 'manifest.json').write_text(json.dumps({'platform': 'linux-64'}))
    monkeypatch.setattr(installer.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(installer.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(installer.platform, 'release', lambda: '4.4.0-19041-Microsoft')
    monkeypatch.setattr(installer.os, 'geteuid', lambda: 1000)
    with pytest.raises(installer.InstallError, match='E_WSL1') as error:
        installer.install(SimpleNamespace(jobs=2), tmp_path)
    assert 'wsl --list --verbose' in str(error.value)


def test_root_is_rejected_before_installation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    (tmp_path / 'manifest.json').write_text(json.dumps({'platform': 'linux-64'}))
    monkeypatch.setattr(installer.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(installer.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(installer.os, 'geteuid', lambda: 0)
    with pytest.raises(installer.InstallError, match='E_ROOT'):
        installer.install(SimpleNamespace(jobs=2), tmp_path)


def test_invalid_metadata_does_not_expose_traceback(tmp_path):
    import shutil
    import subprocess
    import sys
    shutil.copy2(Path(installer.__file__), tmp_path / 'install.py')
    (tmp_path / 'manifest.json').write_text('{}')
    target = tmp_path / 'destination'
    result = subprocess.run([sys.executable, str(tmp_path / 'install.py'), str(target)], capture_output=True, text=True)
    assert result.returncode == 1
    assert 'E_METADATA' in result.stderr
    assert 'Traceback' not in result.stderr
    assert not target.exists()
