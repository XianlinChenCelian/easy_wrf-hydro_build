"""Local source archive discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceArchive:
    name: str
    path: Path
    required: bool = True


ARCHIVE_PATTERNS: dict[str, tuple[str, ...]] = {
    "zlib": ("zlib-*.tar.gz", "zlib-*.tgz", "zlib-*.tar.xz"),
    "hdf5": ("hdf5-*.tar.gz", "hdf5-*.tgz", "hdf5-*.tar.bz2", "hdf5-*.tar.xz"),
    "netcdf_c": (
        "netcdf-c-*.tar.gz",
        "netcdf-c-*.tgz",
        "netcdf-c-*.tar.bz2",
        "netcdf-c-*.tar.xz",
    ),
    "netcdf_fortran": (
        "netcdf-fortran-*.tar.gz",
        "netcdf-fortran-*.tgz",
        "netcdf-fortran-*.tar.bz2",
        "netcdf-fortran-*.tar.xz",
    ),
    "wrf_hydro": (
        "wrf_hydro_nwm_public-*.tar.gz",
        "wrf-hydro*.tar.gz",
        "*wrf*hydro*.tar.gz",
    ),
    "intel_parallel_studio": ("parallel_studio_xe_*cluster_edition.tgz",),
    "intel_license": ("parallel_studio_xe_*.lic", "*.lic"),
    "croton_example": ("croton_NY_example_testcase.tar.gz", "*croton*example*testcase*.tar.gz"),
}


REQUIRED_BOOTSTRAP_ARCHIVES = (
    "zlib",
    "hdf5",
    "netcdf_c",
    "netcdf_fortran",
    "wrf_hydro",
)

WRF_HYDRO_RELEASES = {
    "5.1.2": "croton_NY_example_testcase.tar.gz",
    "5.2.0": "croton_NY_training_example_v5.2.tar.gz",
    "5.4.0": "croton_NY_training_example_v5.4.tar.gz",
}


def _archive_sort_key(path: Path) -> tuple[int, str]:
    # Prefer archives closer to the shared directory root, then stable lexical order.
    return (len(path.parts), str(path).lower())


def find_archive(
    shared_dir: Path, name: str, *, wrf_hydro_version: str | None = None
) -> SourceArchive | None:
    patterns = ARCHIVE_PATTERNS[name]
    if wrf_hydro_version is not None:
        if name == "wrf_hydro":
            patterns = (f"wrf_hydro_nwm_public-{wrf_hydro_version}.tar.gz",)
        elif name == "croton_example":
            patterns = (WRF_HYDRO_RELEASES[wrf_hydro_version],)
    for pattern in patterns:
        matches = [path for path in shared_dir.rglob(pattern) if path.is_file()]
        if matches:
            return SourceArchive(name=name, path=sorted(set(matches), key=_archive_sort_key)[0])
    return None


def discover_archives(
    shared_dir: Path, *, wrf_hydro_version: str | None = None
) -> dict[str, SourceArchive | None]:
    return {
        name: find_archive(shared_dir, name, wrf_hydro_version=wrf_hydro_version)
        for name in ARCHIVE_PATTERNS
    }


def require_archives(
    discovered: dict[str, SourceArchive | None],
    names: tuple[str, ...] = REQUIRED_BOOTSTRAP_ARCHIVES,
) -> dict[str, SourceArchive]:
    missing = [name for name in names if discovered.get(name) is None]
    if missing:
        formatted = ", ".join(missing)
        raise FileNotFoundError(f"Missing required source archive(s): {formatted}")
    return {name: discovered[name] for name in names if discovered[name] is not None}
