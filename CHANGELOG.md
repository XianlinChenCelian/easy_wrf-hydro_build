# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Documentation and Packaging

- Redesign the workflow figure, logo and social preview; group assets and editable layouts.
- Add quickstart, archive inventory, CLI reference and repository layout guides.
- Replace the non-executable YAML example with Intel classic and GNU CLI scripts.
- Use virtual environments in installation instructions and distinct build prefixes.
- Make compiler validation limits visible in both README languages.
- Add documentation-link checks, distribution builds and wheel smoke tests to CI.
- Use SPDX license metadata and a matching setuptools minimum.

No new full WRF-Hydro compiler validation is claimed by this documentation update.

## [0.1.0] - 2026-08-27

### Added

- Intel classic and GNU build routes with separate dependency prefixes.
- Local archive discovery for zlib, HDF5, NetCDF-C, NetCDF-Fortran, WRF-Hydro,
  and the optional Croton example.
- WRF-Hydro NoahMP and Noah offline build support.
- Intel MPI `COMPILER90 = mpiifort` correction.
- Runtime environment generation, `ldd` checks, and optional Croton NWM run.
- Isolated full-loop test runner and GitHub CI.
- Chinese and English project documentation.

### Verification

- Intel classic route completed a clean isolated full-loop run.
- GNU script and configure branches were verified; a clean GNU full-loop run is
  still pending.
