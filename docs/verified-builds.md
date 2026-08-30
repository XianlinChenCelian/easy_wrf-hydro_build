# Verified Builds

This document separates completed end-to-end tests from static branch checks.
It should be updated whenever a new compiler or operating-system combination is
reproduced from a clean prefix.

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

## GNU

Status: **branch verified; end-to-end build pending**.

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
