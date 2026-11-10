# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- Versioned WRF-Hydro 5.1.2, 5.2.0, and 5.4.0 builds with matching WRF/WPS combinations.
- WPS-based hydrologic domain preparation with configurable routing resolution, stream thresholds, and lake polygons.
- HRLDAS forcing conversion for ERA5-Land, NLDAS-2, AORC, and custom inputs.
- Standalone parameter experiments with shared forcing, PNG maps, and a local browser workbench.
- Coupled Gasconade and Jing River examples with GFS forcing and run manifests.

### Documentation

- Present installation, modeling workflows, version selection, and validation in both project overviews.
- Document upstream sources, package assembly, and platform-specific installation.

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
