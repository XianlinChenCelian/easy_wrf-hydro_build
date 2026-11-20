# Contributing

Thanks for helping improve easy-wrf-hydro-build.

## Development Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

To run the forcing and parameter tests with their optional dependencies, install
`python -m pip install -e ".[dev,forcing,aorc,parameters]"` before running pytest.

If editable install is blocked by a local Python packaging issue, use
`PYTHONPATH` during early development:

```bash
PYTHONPATH=src python -m easy_wrf_hydro_build.cli --help
```

## Local Checks

Run these before opening a pull request:

```bash
python -m compileall src tests -q
python -m pytest
python scripts/dev/check_docs.py
python -m build
```

For real WRF-Hydro environments, also run:

```bash
ewhb doctor \
  --compiler-family intel \
  --wrf-hydro-root ~/wrfhydro-intel/sources/wrf_hydro_nwm_public-5.1.2/trunk/NDHMS \
  --netcdf ~/wrfhydro-intel/intel_libs \
  --intel-home /path/to/intel
```

For a clean integration check, use `scripts/linux/run_isolated_full_loop.sh`.
The script accepts only a dedicated `~/ewhb_isolated_full_*` or
`/tmp/ewhb_isolated_full_*` prefix and removes it after a successful run unless
`--keep` is supplied.

## Project Scope

See the [repository layout](docs/repository-layout.md) for module ownership and
the [artwork guide](docs/assets/README.md) for editing documentation figures.

This project aims to automate repeatable WRF-Hydro build preparation and checks.
It should stay conservative:

- Prefer explicit paths over hidden global state.
- Generate shell scripts that users can inspect and rerun.
- Keep compiler-specific fixes documented near the workflow that needs them.
- Avoid changing a user's WRF-Hydro source tree beyond generated helper scripts
  and intentional build files.

## Naming

The Python import package is `easy_wrf_hydro_build`.
The distribution name is `easy-wrf-hydro-build`.
The command-line entry point is `ewhb`.

## Verification reports

Compiler support should be based on reproducible evidence. Include the Linux
distribution, compiler and MPI versions, archive versions, exact command,
whether the example ran, and redacted failure logs. Do not include proprietary
installers, license files, passwords, or private paths.
