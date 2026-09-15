# Repository Layout

[Documentation](index.md) · [Contributing](../CONTRIBUTING.md)

```text
easy_wrf-hydro_build/
  src/easy_wrf_hydro_build/    Python package and shell-script generation
  tests/                      Package, archive and template tests
  examples/                   Runnable Intel and GNU command examples
  scripts/
    linux/                    Host preparation and isolated integration testing
    windows/                  Optional Windows / WSL setup appendix
    dev/                      Documentation and asset maintenance
  docs/
    index.md                  Reader-oriented documentation entry point
    quickstart.md             First build, in Chinese
    bootstrap.md              Complete build guide, in English
    source-archives.md        Baseline versions and official sources
    cli.md                    Existing CLI commands and their limits
    assets/
      brand/                  Logo and social preview
      figures/                Workflow figure and watershed illustration
      source/                 Editable figure layouts
  .github/                    CI, issue forms and pull-request template
  pyproject.toml              Package metadata and development dependencies
  README.md / README_EN.md    Chinese and English project overviews
```

## Package Responsibilities

| Module | Responsibility |
| --- | --- |
| `cli.py` | Parse command arguments and select a workflow |
| `bootstrap.py` | Build dependencies, compile the model and optionally run Croton |
| `archives.py` | Discover the local source archive inventory |
| `config.py`, `templates.py` | Compile settings and generated shell scripts |
| `doctor.py` | Check source paths, compilers, MPI and NetCDF commands |
| `workflow.py`, `shell.py` | Execute build operations and write runtime environments |
| `paths.py` | Organize case directories |

Keep build logic in the Python package. Examples invoke the CLI; they should not become a second implementation of dependency builds. New compiler behavior belongs in the package with focused tests and an update to the [compiler matrix](intel-compiler-matrix.md).

## Repository vs. Build Output

The repository is source code and documentation. Each model environment belongs in an external `--prefix`:

```text
~/wrfhydro-intel/
  intel_libs/                     Installed dependency libraries
  sources/                       Extracted dependency and model sources
  build/                         Reserved build directory
  logs/                          Step logs and .done markers
  runs/croton_NY_NWM/             Optional example
  bootstrap_easy_wrf_hydro.sh     Generated build script
  wrf_hydro_intel_env.sh          Generated runtime environment
  wrf_hydro_root.txt              Resolved WRF-Hydro source path
```

The current dependency build executes inside the extracted source directories. Use separate prefixes for different compilers or versions. Do not commit generated model environments or source tarballs.

## Reference Projects

- [easy_vic_build](https://github.com/XudongZhengSteven/easy_vic_build): concise scientific-project overview and recognizable visual identity.
- [HydroMT](https://github.com/Deltares/hydromt): distinct examples, user guides and developer documentation; [workflow figures](https://deltares.github.io/hydromt/stable/user_guide/overview/hydromt_intro.html) connect inputs to model outputs.
- [WRF-Hydro-Py](https://github.com/NCAR/wrf_hydro_py): model-oriented Python package with documentation and tests.
- [Spack](https://github.com/spack/spack): explicit treatment of compiler and dependency configurations.

These are references for organization and communication, not dependencies or claims of feature parity. The project artwork is original; reference-project images are not redistributed here.
