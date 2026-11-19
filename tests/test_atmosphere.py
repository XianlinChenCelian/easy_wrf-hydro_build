import io
import shutil
import subprocess
import tarfile

import pytest

from easy_wrf_hydro_build.atmosphere import (
    ATMOSPHERE_PROFILES, CONFIG_TOOLS, SOURCE_HASHES, _add_wrf_netcdf_c_lib_dirs,
    _stage_netcdf_view, build_atmosphere, configuration_choice, netcdf_library_dir, unpack,
)


def test_each_profile_has_complete_pinned_offline_sources(tmp_path):
    for version in ATMOSPHERE_PROFILES:
        plan = build_atmosphere(tmp_path, tmp_path / version, tmp_path / "nc",
                                version, "intel", dry_run=True)
        assert all(len(SOURCE_HASHES[name]) == 64 for name in plan["sources"])
        assert plan["mode"] == "atmosphere-only"
        assert plan["coupled_validation"] == "pending"
        assert not (tmp_path / version).exists()
    assert any(name.startswith("noahmp-") for name in plan["sources"])


@pytest.mark.parametrize(("machine", "compiler", "needs_helpers"), [
    ("x86_64", "gnu", False), ("arm64", "gnu", True), ("aarch64", "gnu", True),
    ("x86_64", "intel", False),
])
def test_automake_archive_is_selected_only_for_arm_gnu(tmp_path, monkeypatch, machine, compiler, needs_helpers):
    monkeypatch.setattr("easy_wrf_hydro_build.atmosphere.platform.machine", lambda: machine)
    plan = build_atmosphere(tmp_path, tmp_path / "build", tmp_path / "nc",
                            "5.1.2", compiler, dry_run=True)
    assert (CONFIG_TOOLS in plan["sources"]) == needs_helpers


def test_debian_netcdf_view_exposes_both_libraries_to_wrf_configure(tmp_path):
    netcdf = tmp_path / "usr"
    multiarch = netcdf / "lib" / "x86_64-linux-gnu"
    multiarch.mkdir(parents=True)
    (netcdf / "include").mkdir()
    (netcdf / "bin").mkdir()
    for name in ("libnetcdf.so", "libnetcdff.so"):
        (multiarch / name).touch()
    nf_config = netcdf / "bin" / "nf-config"
    nf_config.write_text(f"#!/bin/sh\nprintf '%s\\n' '-L{multiarch} -lnetcdff -lnetcdf'\n")
    nf_config.chmod(0o755)
    prefix = tmp_path / "build"
    prefix.mkdir()
    view = _stage_netcdf_view(netcdf, netcdf_library_dir(netcdf), prefix)
    assert (view / "lib/libnetcdf.so").resolve() == multiarch / "libnetcdf.so"
    assert (view / "lib/libnetcdff.so").resolve() == multiarch / "libnetcdff.so"
    assert (view / "include").resolve() == netcdf / "include"
    assert not (netcdf / "lib/libnetcdf.so").exists()


def test_wrf_legacy_link_uses_hdf5_paths_from_netcdf_c(tmp_path):
    cc, ar, make = (shutil.which(tool) for tool in ("cc", "ar", "make"))
    if not all((cc, ar, make)):
        pytest.skip("C compiler, ar and make required for the link regression")

    # Debian installs the unqualified link names inside the HDF5 subdirectory.
    multiarch = tmp_path / "usr/lib/x86_64-linux-gnu"
    serial = multiarch / "hdf5/serial"
    serial.mkdir(parents=True)
    names = ("hdf5_hl", "hdf5")
    for name in names:
        obj = tmp_path / f"{name}.o"
        subprocess.run(
            [cc, "-x", "c", "-c", "-o", str(obj), "-"],
            input=f"void ewhb_test_{name}(void) {{}}\n", text=True, check=True,
        )
        library = multiarch / f"lib{name}_serial.a"
        subprocess.run([ar, "rcs", str(library), str(obj)], check=True)
        (serial / f"lib{name}.a").symlink_to(library)

    netcdf = tmp_path / "build/netcdf"
    (netcdf / "bin").mkdir(parents=True)
    nc_config = netcdf / "bin/nc-config"
    nc_config.write_text(
        f"#!/bin/sh\n[ \"$1\" = --libs ] || exit 2\n"
        f"printf '%s\\n' '-L{multiarch} -L {serial} -L{serial} -lnetcdf'\n"
    )
    nc_config.chmod(0o755)
    config = tmp_path / "configure.wrf"
    config.write_text(
        f"DEP_LIB_PATH = -L{multiarch}\n"
        "HDF5 = -lhdf5_hl -lhdf5\n"
        "NETCDF4_DEP_LIB = $(DEP_LIB_PATH) $(HDF5)\n"
    )
    (tmp_path / "probe.c").write_text(
        "void ewhb_test_hdf5_hl(void), ewhb_test_hdf5(void);\n"
        "int main(void) { ewhb_test_hdf5_hl(); ewhb_test_hdf5(); return 0; }\n"
    )
    makefile = f"include configure.wrf\nlink:\n\t{cc} probe.c $(NETCDF4_DEP_LIB) -o probe\n"
    assert subprocess.run([make, "-f", "-", "link"], input=makefile, cwd=tmp_path,
                          text=True, capture_output=True).returncode != 0

    assert _add_wrf_netcdf_c_lib_dirs(config, netcdf, {}) == [str(multiarch), str(serial)]
    assert _add_wrf_netcdf_c_lib_dirs(config, netcdf, {}) == [str(multiarch), str(serial)]
    assert config.read_text().count(f"-L{serial}") == 1
    assert "-lnetcdf" not in config.read_text()
    subprocess.run([make, "-f", "-", "link"], input=makefile, cwd=tmp_path, text=True, check=True)
    subprocess.run([str(tmp_path / "probe")], check=True)


def test_wrf_config_without_legacy_dependency_variable_is_unchanged(tmp_path):
    config = tmp_path / "configure.wrf"
    config.write_text("NETCDF4_IO_OPTS = -DUSE_NETCDF4_FEATURES\n")
    assert _add_wrf_netcdf_c_lib_dirs(config, tmp_path / "netcdf", {}) is None
    assert config.read_text() == "NETCDF4_IO_OPTS = -DUSE_NETCDF4_FEATURES\n"


@pytest.mark.parametrize(("version", "layout"), [
    ("5.1.2", "trunk/NDHMS"), ("5.2.0", "trunk/NDHMS"), ("5.4.0", "src"),
])
def test_coupled_plan_uses_the_selected_clean_source_and_can_reuse_wps(tmp_path, version, layout):
    archive_dir = tmp_path / "offline" / "archives"
    prefix = tmp_path / "coupled"
    plan = build_atmosphere(tmp_path, prefix, tmp_path / "nc", version, "gnu",
                            dry_run=True, coupled=True, build_wps=False, hydro_archives=archive_dir)
    name = f"wrf_hydro_nwm_public-{version}.tar.gz"
    assert plan["mode"] == "coupled"
    assert plan["hydro_source_layout"] == layout
    assert plan["hydro_source"] == str(archive_dir / name)
    assert plan["hydro_compile_options"]["WRF_HYDRO"] == "1"
    assert name in plan["sources"]
    assert all(len(SOURCE_HASHES[entry]) == 64 for entry in plan["sources"])
    assert not any(entry.startswith(("WPS-", "jasper-", "zlib-")) for entry in plan["sources"])
    assert not prefix.exists()


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
