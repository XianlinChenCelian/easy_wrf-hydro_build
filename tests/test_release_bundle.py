import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import tarfile

import pytest

BUILD = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/release/build_offline_bundle.py'))['build']


def fixture_args(tmp_path):
    for name in ('environment/conda-meta', 'cache', 'archives'):
        (tmp_path / name).mkdir(parents=True)
    data = b'test package'
    (tmp_path / 'cache/library.conda').write_bytes(data)
    (tmp_path / 'environment/conda-meta/library.json').write_text(json.dumps({
        'name': 'library', 'version': '1', 'build': '0', 'subdir': 'osx-arm64',
        'fn': 'library.conda', 'sha256': hashlib.sha256(data).hexdigest(),
        'md5': hashlib.md5(data).hexdigest(),
    }))
    for name in ('wrf_hydro_nwm_public-5.4.0.tar.gz', 'croton_NY_training_example_v5.4.tar.gz',
                 'wrf_hydro_nwm_public-5.1.2.tar.gz'):
        (tmp_path / 'archives' / name).write_bytes(b'fixture')
    (tmp_path / 'micromamba').write_bytes(b'fixture executable')
    return SimpleNamespace(version='5.4.0', environment=tmp_path / 'environment',
                           cache=tmp_path / 'cache', archives=tmp_path / 'archives',
                           micromamba=tmp_path / 'micromamba', output=tmp_path / 'output')


def test_bundle_contains_only_selected_model_and_locked_dependencies(tmp_path):
    args = fixture_args(tmp_path)
    BUILD(args)
    with tarfile.open(next(args.output.glob('*.tar.gz'))) as archive:
        names = archive.getnames()
        assert any(name.endswith('packages/library.conda') for name in names)
        assert any(name.endswith('wrf_hydro_nwm_public-5.4.0.tar.gz') for name in names)
        assert not any('5.1.2' in name for name in names)
        checksums = json.load(archive.extractfile(next(n for n in names if n.endswith('/checksums.json'))))
        assert 'install.py' in checksums
        assert 'packages/library.conda' in checksums


def test_bundle_rejects_tampered_dependency(tmp_path):
    args = fixture_args(tmp_path)
    (args.cache / 'library.conda').write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='checksum mismatch'):
        BUILD(args)


@pytest.mark.parametrize('platform_name,label', [('linux-aarch64', 'linux-aarch64'), ('linux-64', 'linux-x86_64')])
def test_linux_bundle_records_glibc_and_architecture(tmp_path, platform_name, label):
    args = fixture_args(tmp_path)
    metadata = args.environment / 'conda-meta/library.json'
    record = json.loads(metadata.read_text())
    record.update(subdir=platform_name, depends=['__glibc >=2.28,<3.0.a0'])
    metadata.write_text(json.dumps(record))
    BUILD(args)
    root = next(p for p in args.output.iterdir() if p.is_dir())
    manifest = json.loads((root / 'manifest.json').read_text())
    assert manifest['platform'] == platform_name
    assert manifest['glibc_min'] == '2.28'
    assert label in root.name


def test_installer_rejects_wrong_platform_before_creating_prefix(tmp_path):
    import platform
    import shutil
    import subprocess
    import sys

    install = Path(__file__).parents[1] / 'scripts/release/install_bundle.py'
    shutil.copy2(install, tmp_path / 'install.py')
    wrong = 'linux-64' if platform.system() == 'Darwin' else 'osx-arm64'
    (tmp_path / 'manifest.json').write_text(json.dumps({'platform': wrong}))
    target = tmp_path / 'target'
    result = subprocess.run([sys.executable, str(tmp_path / 'install.py'), str(target)], capture_output=True, text=True)
    assert result.returncode != 0
    assert 'choose a matching platform bundle' in result.stderr
    assert not target.exists()
