"""Fetch the source archives for a selected build."""

from __future__ import annotations

import os
import platform
import shutil
from http.client import HTTPException
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit
from urllib.request import urlopen

from .atmosphere import ATMOSPHERE_PROFILES, CONFIG_TOOLS, SOURCE_HASHES, SUBMODULES, sha256, source_names


GITHUB_CODELOAD = "https://codeload.github.com"
NCAR_GRIB = "https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compile_tutorial/tar_files"
DEPENDENCIES = {
    "zlib-1.2.11.tar.gz": "https://zlib.net/fossils/zlib-1.2.11.tar.gz",
    "hdf5-1.12.0.tar.gz": (
        "https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.12/hdf5-1.12.0/src/hdf5-1.12.0.tar.gz"
    ),
    "netcdf-c-4.7.4.tar.gz": f"{GITHUB_CODELOAD}/Unidata/netcdf-c/tar.gz/refs/tags/v4.7.4",
    "netcdf-fortran-4.5.3.tar.gz": f"{GITHUB_CODELOAD}/Unidata/netcdf-fortran/tar.gz/refs/tags/v4.5.3",
}
DEPENDENCY_HASHES = {
    "hdf5-1.12.0.tar.gz": "a62dcb276658cb78e6795dd29bf926ed7a9bc4edf6e77025cd2c689a8f97c17a",
    "netcdf-c-4.7.4.tar.gz": "99930ad7b3c4c1a8e8831fb061cb02b2170fc8e5ccaeda733bd99c3b9d31666b",
    "netcdf-fortran-4.5.3.tar.gz": "c6da30c2fe7e4e614c1dff4124e857afbd45355c6798353eccfa60c0702b495a",
}


def fetch_sources(version: str, output: Path, *, build_netcdf: bool = False,
                  atmosphere: bool = False, arm_config_tools: bool = False,
                  github_mirror: str | None = None) -> None:
    github = (github_mirror or GITHUB_CODELOAD).rstrip("/")
    parsed = urlsplit(github)
    if parsed.scheme != "https" or not parsed.hostname or parsed.query or parsed.fragment:
        raise ValueError("Use an HTTPS base URL for --github-mirror.")
    hydro = f"wrf_hydro_nwm_public-{version}.tar.gz"
    urls = {hydro: f"{GITHUB_CODELOAD}/NCAR/wrf_hydro_nwm_public/tar.gz/refs/tags/v{version}"}
    if build_netcdf:
        urls.update(DEPENDENCIES)
    if atmosphere:
        profile = ATMOSPHERE_PROFILES[version]
        wrf, wps = profile["wrf"], profile["wps"]
        candidates = {
            f"WRF-{wrf}.tar.gz": f"{GITHUB_CODELOAD}/wrf-model/WRF/tar.gz/refs/tags/v{wrf}",
            f"WPS-{wps}.tar.gz": f"{GITHUB_CODELOAD}/wrf-model/WPS/tar.gz/refs/tags/v{wps}",
            **{name: f"{NCAR_GRIB}/{name}" for name in ("libpng-1.2.50.tar.gz", "jasper-1.900.1.tar.gz")},
            CONFIG_TOOLS: f"https://ftp.gnu.org/gnu/automake/{CONFIG_TOOLS}",
            "zlib-1.2.11.tar.gz": DEPENDENCIES["zlib-1.2.11.tar.gz"],
            **{name: f"{GITHUB_CODELOAD}/NCAR/noahmp/tar.gz/{name[7:-7]}"
               for name in SUBMODULES.values()},
        }
        arm = arm_config_tools or platform.machine() in {"arm64", "aarch64"}
        urls.update((name, candidates[name]) for name in source_names(version, arm_config_tools=arm))
    checksums = SOURCE_HASHES | DEPENDENCY_HASHES
    output.mkdir(parents=True, exist_ok=True)
    for name, url in urls.items():
        path = output / name
        expected = checksums[name]
        if path.is_file():
            if sha256(path) != expected:
                raise ValueError(f"SHA256 mismatch for {path}. Move that archive aside or select another --output.")
            print(f"Using {path}", flush=True)
            continue
        if url.startswith(GITHUB_CODELOAD + "/"):
            url = github + url[len(GITHUB_CODELOAD):]
        print(f"Downloading {name}", flush=True)
        temporary = None
        try:
            with NamedTemporaryFile(dir=output, prefix=f".{name}.", suffix=".part", delete=False) as stream:
                temporary = Path(stream.name)
                with urlopen(url, timeout=60) as response:
                    shutil.copyfileobj(response, stream)
                    if response.length not in (None, 0) or stream.tell() == 0:
                        raise OSError("Incomplete archive")
            if sha256(temporary) != expected:
                raise ValueError(f"SHA256 mismatch for {name} from {url}.")
            os.replace(temporary, path)
        except (OSError, HTTPException) as exc:
            raise OSError(f"Download failed for {name} from {url}: {exc}. "
                          "Run the same command to reuse completed files.") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
