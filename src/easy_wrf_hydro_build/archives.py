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


def _archive_sort_key(path: Path) -> tuple[int, str]:
    # Prefer archives closer to the shared directory root, then stable lexical order.
    return (len(path.parts), str(path).lower())


def find_archive(shared_dir: Path, name: str) -> SourceArchive | None:
    for pattern in ARCHIVE_PATTERNS[name]:
        matches = [path for path in shared_dir.rglob(pattern) if path.is_file()]
        if matches:
            return SourceArchive(name=name, path=sorted(set(matches), key=_archive_sort_key)[0])
    return None


def discover_archives(shared_dir: Path) -> dict[str, SourceArchive | None]:
    return {name: find_archive(shared_dir, name) for name in ARCHIVE_PATTERNS}


def require_archives(
    discovered: dict[str, SourceArchive | None],
    names: tuple[str, ...] = REQUIRED_BOOTSTRAP_ARCHIVES,
) -> dict[str, SourceArchive]:
    missing = [name for name in names if discovered.get(name) is None]
    if missing:
        formatted = ", ".join(missing)
        raise FileNotFoundError(f"Missing required source archive(s): {formatted}")
    return {name: discovered[name] for name in names if discovered[name] is not None}
