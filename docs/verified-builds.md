# Verified Builds

## Windows WSL2 x86_64

The 2026-11-12 test used Windows 11, WSL 3.0.5 and Ubuntu 24.04 x86_64 in an
ext4 virtual disk. The GNU toolchain was GCC/GFortran 13.3 and Open MPI 4.1.6.
The Intel Classic toolchain used oneAPI 2023.2.4 with Intel MPI 2021.10.

| Build | NetCDF | Result |
| --- | --- | --- |
| WRF-Hydro 5.1.2, GNU | Ubuntu 4.9.2 (C) / 4.5.4 (Fortran) | Built in 16 s |
| WRF-Hydro 5.2.0, GNU | Ubuntu 4.9.2 / 4.5.4 | Built in 53 s |
| WRF-Hydro 5.4.0, GNU | Ubuntu 4.9.2 / 4.5.4 | Built in 55 s with CMake |
| WRF-Hydro 5.1.2, GNU | Source build, 4.7.4 / 4.5.3 | Built in 8 min, Croton ran in 28 s |
| WRF-Hydro 5.1.2, Intel Classic | Source build, 4.7.4 / 4.5.3 | Built in 324 s, Croton ran in 26 s |
| WRF 4.2 and WPS 4.2, GNU | Source build, flat `lib/` layout | Five executables built and launched |
| WRF 4.2 coupled with WRF-Hydro 5.1.2, GNU | Source build, flat `lib/` layout | Coupler symbols and dynamic libraries checked |

Both Croton runs produced 168 hourly `CHANOBS` files through
2011-09-02 00:00 with a readable `streamflow` variable. The coupled basin
runs are recorded in the [basin examples](coupled-basin-examples.md).

On 2026-11-19, the WSL2 regression at `142b708` built standalone WRF-Hydro
5.1.2 with the system NetCDF and completed Croton in 29 seconds including
the build. For WRF 4.2 with `--netcdf /usr`, the NetCDF probe and WRF
configuration passed. The WRF link completed after the tester added the
HDF5 search directory to `configure.wrf`. This test covered WRF only.
The WRF/WPS pair in the table used the source-built NetCDF installation.

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

The final `streamflow` variable was read from the last NetCDF gauge file for
each run.

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

## Offline bundle relocation checks (2026-11-07)

Three independent osx-arm64 candidate bundles contain one model release, its
matching Croton case, and 88 exact conda dependency artifacts each. Dependencies
were restored from local package files into new prefixes on the same Mac.
All three models completed Croton with 168 hourly CHANOBS outputs ending at
2011-09-02 00:00; the final streamflow variable was read with ncdump.
The 5.4.0 check exposed shell-launch and Mach-O signature relocation issues;
it completed after those fixes. Versions 5.1.2 and 5.2.0 passed from new prefixes
using the corrected installer. The relocation runs used the same Mac.
See [release bundles](release-bundles.md).

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
2.28. These runs used the glibc shipped with Ubuntu 24.04.

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
streamflow. The package sysroot baseline is glibc 2.28 and the emulated Ubuntu
userspace uses glibc 2.39.

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

OneAPI 2023.2.4 was installed through Intel APT for the Windows WSL2 test.
The offline installer helper was checked with a simulated installer. See
[oneAPI setup](oneapi-install.md).

### Direct use of a loaded HPC toolchain

A single native x86_64 Slurm allocation ran the three model versions with
`--site-toolchain` and the site's Intel oneAPI 2021.3 `ifort`, `icc`, and
`mpiifort`. Each model was compiled in a fresh prefix. The three builds
shared the compatible Intel NetCDF libraries built from source in the earlier
5.4.0 test, so this run verifies the loaded-toolchain and model path across
versions. Each Croton run produced 168 hourly files ending at 2011-09-02
00:00, and its final `streamflow` was readable. The allocation completed
with exit code `0:0` in 6 minutes 53 seconds.
