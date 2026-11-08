import io
import tarfile

import pytest

from easy_wrf_hydro_build.atmosphere import (
    ATMOSPHERE_PROFILES, SOURCE_HASHES, build_atmosphere, configuration_choice, unpack,
)


def test_each_profile_has_complete_pinned_offline_sources(tmp_path):
    for version in ATMOSPHERE_PROFILES:
        plan = build_atmosphere(tmp_path, tmp_path / version, tmp_path / "nc",
                                version, "intel", dry_run=True)
        assert all(len(SOURCE_HASHES[name]) == 64 for name in plan["sources"])
        assert plan["mode"] == "atmosphere-only"
        assert plan["coupled_validation"] == "pending"
        assert not (tmp_path / version).exists()
    assert len(plan["sources"]) == 7  # WRF 4.6.1 requires its pinned Noah-MP submodule.


def test_menu_counts_other_compilers_and_parallel_modes():
    defaults = """#ARCH Linux x86_64, PGI #serial smpar dmpar dm+sm
#ARCH Linux x86_64, ifort compiler with icc #serial smpar dmpar dm+sm
#ARCH Linux x86_64, ifort compiler with icc, SGI MPT #serial smpar dmpar dm+sm
#ARCH Linux x86_64, gfortran compiler with gcc #serial smpar dmpar dm+sm
"""
    assert configuration_choice(defaults, "WRF", "intel", "Linux", "x86_64") == 7
    assert configuration_choice(defaults, "WRF", "gnu", "Linux", "x86_64") == 15
    with pytest.raises(ValueError, match="separately validated"):
        configuration_choice(defaults, "WRF", "gnu", "Linux", "aarch64")


@pytest.mark.parametrize("kind", ["traversal", "symlink", "device"])
def test_archive_cannot_write_outside_build_directory(tmp_path, kind):
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        member = tarfile.TarInfo("../outside" if kind == "traversal" else "root/file")
        if kind == "symlink":
            member.type = tarfile.SYMTYPE
            member.linkname = "../../outside"
        elif kind == "device":
            member.type = tarfile.CHRTYPE
        stream.addfile(member, io.BytesIO(b""))
    with pytest.raises(ValueError):
        unpack(archive, tmp_path / "extract")
    assert not (tmp_path / "outside").exists()


def test_existing_build_is_not_overwritten(tmp_path):
    marker = tmp_path / "old-results"
    marker.write_text("retain")
    with pytest.raises(ValueError, match="fresh"):
        build_atmosphere(tmp_path, tmp_path, tmp_path / "nc", "5.1.2", "intel")
    assert marker.read_text() == "retain"


def test_upstream_appledouble_metadata_does_not_create_an_extra_source_root(tmp_path):
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        for name in ("./._source", "source/configure"):
            member = tarfile.TarInfo(name)
            stream.addfile(member, io.BytesIO(b""))
    root = unpack(archive, tmp_path / "extract")
    assert root.name == "source"
    assert not (root.parent / "._source").exists()
