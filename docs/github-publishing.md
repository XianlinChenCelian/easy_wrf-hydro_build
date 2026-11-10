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

## Public release checklist

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
Preview for WRF-Hydro 5.1.2, 5.2.0 and 5.4.0 with a system/compiler/version
chooser. Intel users can use a loaded HPC toolchain or install Intel oneAPI
from the vendor on their own x86_64 Linux or WSL2 system. The repository
includes a per-version source recipe builder and documents the validation
status of each toolchain.
```

Keep Intel installers and licenses on the vendor site. The private preview
uses release attachments for the project’s versioned offline, source and
example bundles. Review third-party redistribution terms before making
those attachments public.

Link the release to the [download matrix](release-bundles.md) and the
[oneAPI installation guide](oneapi-install.md).
