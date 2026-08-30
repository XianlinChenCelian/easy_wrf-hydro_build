# GitHub Publishing Guide

This file contains the repository-page metadata and release checklist. It does
not contain model sources, dependency archives, or private environment data.

## Repository settings

Repository name:

```text
easy_wrf-hydro_build
```

Suggested About description:

```text
Reproducible WRF-Hydro dependency builds, Intel/GNU compiler routing, runtime environments, and example verification for Linux, WSL2, and VMs.
```

Suggested topics:

```text
wrf-hydro hydrology netcdf mpi intel-fortran gfortran openmpi wsl2 linux reproducible-build scientific-computing
```

Use `docs/social-preview.png` as the repository social preview image. Use
`docs/logo_small_size.svg` as the project logo in documents.

## Before the first push

1. Add the final `repository-code` URL to `CITATION.cff` after the repository
   exists.
2. Optionally add the final `Homepage` and `Repository` URLs to
   `pyproject.toml`.
3. Run `python -m compileall src tests -q` and `python -m pytest`.
4. Confirm that no archives, licenses, passwords, build trees, or WSL home
   directories are tracked.
5. Create the repository with default branch `main` and enable GitHub Actions.
6. Enable Issues, private vulnerability reporting, and Discussions if they are
   useful for the intended community.

## First release

Suggested tag:

```text
v0.1.0
```

Suggested title:

```text
easy_wrf-hydro_build v0.1.0 - initial beta
```

Suggested release summary:

```text
Initial beta release with an end-to-end verified Intel classic WRF-Hydro 5.1.2
route, an isolated dependency stack, runtime environment generation, Croton NWM
verification, and a GNU build branch ready for clean-host integration testing.
```

Do not attach Intel installers, Intel licenses, WRF-Hydro source archives,
dependency source archives, example datasets, or packed personal environments
to the GitHub release.
