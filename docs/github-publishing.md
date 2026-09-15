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
An open-source build helper for deploying the WRF-Hydro offline model on Linux, WSL2, and VMs.
```

Suggested topics:

```text
wrf-hydro hydrology netcdf mpi intel-fortran gfortran openmpi wsl2 linux reproducible-build scientific-computing
```

Use `docs/assets/brand/social-preview.png` as the repository social preview image.
Use `docs/assets/brand/logo.png` as the project logo. Editable figure layouts and
regeneration instructions are in [the artwork guide](assets/README.md).

## Before a release

1. Check the version, author, repository URL and date in `CITATION.cff`.
2. Check package metadata in `pyproject.toml` and update `CHANGELOG.md`.
3. Run `python -m pytest`, `python scripts/dev/check_docs.py` and `python -m build`.
4. Confirm that no archives, licenses, passwords, build trees, or WSL home
   directories are tracked.
5. Wait for the CI run on the release commit; inspect any failures.
6. Review [verified builds](verified-builds.md) and state integration-test limits
   in the release notes. Passing CI is not a full model run.

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
