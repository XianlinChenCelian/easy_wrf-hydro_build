# Verified Builds

This document separates completed end-to-end tests from static branch checks.
It should be updated whenever a new compiler or operating-system combination is
reproduced from a clean prefix.

## macOS arm64 versioned builds

On 2026-11-06, the [versioned bootstrap](versioned-install.md) built native arm64
Noah-MP executables and ran the matching Croton NWM case with one MPI process.
The test used macOS 27.0.1, GNU Fortran 15.3.0, OpenMPI 5.0.11, NetCDF-C
4.10.1, NetCDF-Fortran 4.6.4, and CMake 3.31.8 for the CMake build.

| WRF-Hydro | Build system | Croton result |
| --- | --- | --- |
| 5.1.2 | configure / Make | 168 hourly gauge outputs through 2011-09-02 00:00 |
| 5.2.0 | configure / Make | 168 hourly gauge outputs through 2011-09-02 00:00 |
| 5.4.0 | CMake | 168 hourly gauge outputs through 2011-09-02 00:00 |

The final `streamflow` variable was read from each NetCDF gauge output. These
are installation and runtime checks. Cross-version numerical agreement,
scientific evaluation, and the three-version Linux/WSL2/virtual machine matrix
are still pending.

## Intel classic

Status: **end-to-end verified** on 2026-08-27.

Verified components:

- Intel Parallel Studio XE 2018 environment loading.
- Intel `ifort`, `icc`, and `mpiifort` route.
- zlib 1.2.11, HDF5 1.12.0, NetCDF-C 4.7.4, and NetCDF-Fortran 4.5.3.
- WRF-Hydro 5.1.2 NoahMP offline build.
- Generated executable dynamic-library check with `ldd`.
- Croton, NY NWM example completed successfully with one MPI process.
- Successful cleanup of the isolated test prefix.

The run used `scripts/linux/run_isolated_full_loop.sh`; it did not modify the
pre-existing WRF, WPS, or WRF-Hydro directories.

## Original GNU branch check (historical)

Status on the original host: **branch verified; end-to-end build pending**.
Later macOS and Linux GNU end-to-end results are recorded separately in this document.

Completed checks:

- GNU bootstrap script generation and Bash syntax validation.
- `gnu_libs` dependency-prefix isolation.
- `gcc`, `g++`, `gfortran`, and `mpif90` command generation.
- WRF-Hydro official `gfort` configure option and `macros.mpp.gfort`
  `COMPILER90=mpif90` agreement.

The original validation host did not have `gfortran` and `mpif90` installed, so
that host could not provide a clean GNU dependency build and Croton run. This is
an explicit release limitation, not a claim of end-to-end GNU validation.

## Intel oneAPI

Status: **environment compatibility work in progress**.

The generated environment loader recognizes oneAPI `setvars.sh`. A successful
environment load alone is not sufficient to claim a supported WRF-Hydro build,
especially for ifx-only installations. See [Intel compiler matrix](intel-compiler-matrix.md).

## Offline bundle relocation checks (2026-11-07)

Three independent osx-arm64 candidate bundles contain one model release, its
matching Croton case, and 88 exact conda dependency artifacts each. Dependencies
were restored from local package files into new prefixes on the same Mac.
All three models completed Croton with 168 hourly CHANOBS outputs ending at
2011-09-02 00:00; the final streamflow variable was read with ncdump.
The 5.4.0 check exposed shell-launch and Mach-O signature relocation issues;
it completed after those fixes. Versions 5.1.2 and 5.2.0 passed from new prefixes
using the corrected installer. This is a same-host relocation test, not a clean
host or cross-platform certification. See [release bundles](release-bundles.md).

## Ubuntu ARM64 offline bundles (2026-11-07)

All three versions (5.1.2, 5.2.0, 5.4.0) were built and ran their matching
Croton NWM case on Ubuntu 24.04.5 ARM64, kernel 6.8.0-147-generic, inside a
Lima/VZ virtual machine on Apple Silicon. The VM, cache, and build directories
reside on an external drive.

Each final offline bundle was then installed into a fresh prefix using its
local package artifacts. Each completed the model build and Croton run with
168 hourly CHANOBS outputs ending at 2011-09-02 00:00. The success diagnostic
and final streamflow variable were checked. The final bundles contain 86 exact
conda dependency artifacts including GNU Fortran 15.3.0, OpenMPI 5.0.11,
NetCDF-C 4.10.1 and NetCDF-Fortran 4.6.4. The build sysroot is pinned to glibc
2.28; the actual validation host uses Ubuntu 24.04's newer glibc. Older glibc
hosts, x86_64, WSL2 on Windows, and other VM implementations remain untested.

The minimal Ubuntu test exposed the legacy Makefiles' direct invocation of
`ar`; adding the conda binutils package resolves this without requiring a
system-wide development-tool installation. Architecture and minimum-glibc
checks are included in the installer. See [Linux validation](linux-validation.md).

## x86_64 and installer recovery (confirmed 2026-11-08)

Versions 5.1.2, 5.2.0 and 5.4.0 each passed fresh offline installation,
compilation and Croton execution in Ubuntu 24.04 x86_64 userspace under QEMU
10.2.3, hosted by the ARM64 Linux VM. ELF machine 62 was checked for each
runtime executable. Each produced 168 hourly CHANOBS outputs ending at
2011-09-02 00:00, with a successful diagnostic marker and readable final
streamflow. This does not certify native Windows WSL2, an x86_64 kernel, or
native x86_64 performance. The package sysroot baseline is glibc 2.28; the
validation userspace has glibc 2.39.

The installer now checks ownership, write/execute/symlink support, noexec and
shared filesystems, space, architecture and WSL1. It provides --check-only,
--resume, identity-checked state, an exclusive lock and progress messages.
Real ARM64 Linux tests passed for noexec, shared filesystem, denied writes,
root user, foreign ownership, concurrent installation, and an intentionally
failed MPI case followed by successful resume. The updated Mac 5.4.0 installer
also completed Croton. All three Mac and ARM64 Linux bundles were refreshed
with this common installer. See [recovery guide](installation-recovery.md).

## Linux x86_64 Intel source recipe

WRF-Hydro 5.4.0 was built on native x86_64 Linux (glibc 2.28) with the
cluster's Intel oneAPI 2021.3 `icc`, `ifort`, and `mpiifort`. zlib 1.2.11,
HDF5 1.12.0, NetCDF-C 4.7.4, and NetCDF-Fortran 4.5.3 were built from source in
an isolated prefix. The Croton run finished with 168 hourly files. The build
job `300214` exited with status 1 in its post-run check. Follow-up job
`300215` loaded the Intel runtime, verified the count and last timestamp,
and read the final streamflow successfully with exit status `0:0`.

The personal oneAPI installer helper was checked with a simulated installer.
Actual Intel toolkit installation on a personal Linux or WSL2 host, the
modern `ifx` model route, and 5.1.2/5.2.0 with this Intel recipe are pending.
See [oneAPI setup](oneapi-install.md) and the [matrix](intel-compiler-matrix.md).

### Direct use of a loaded HPC toolchain

A single native x86_64 Slurm allocation ran the three model versions with
`--site-toolchain` and the site's Intel oneAPI 2021.3 `ifort`, `icc`, and
`mpiifort`. Each model was compiled in a fresh prefix. The three builds
shared the compatible Intel NetCDF libraries built from source in the earlier
5.4.0 test, so this run verifies the loaded-toolchain and model path across
versions. Each Croton run produced 168 hourly files ending at 2011-09-02
00:00, and its final `streamflow` was readable. The allocation completed
with exit code `0:0` in 6 minutes 53 seconds. The standalone personal oneAPI
installation and the `ifx` routes remain previews.
