# Command Reference

[Documentation](index.md) · [Build guide](bootstrap.md)

`ewhb --help` lists commands. Use `ewhb <command> --help` for current options.

| Command | Purpose | Required paths |
| --- | --- | --- |
| `fetch-sources` | Download [versioned source archives](source-archives.md) | `--wrf-hydro-version`, `--output` |
| `bootstrap` | Build WRF-Hydro with installed or source-built libraries | `--shared-dir`, `--prefix` |
| `build-atmosphere` | Build [WRF/WPS or coupled WRF](wrf-wps.md) | `--wrf-hydro-version`, `--shared-dir`, `--prefix`, `--netcdf` |
| `run-basin` | Run a bundled [GFS coupled example](coupled-basin-examples.md) through WPS and WRF-Hydro | `--case`, `--build`, `--output` |
| `fetch-geog` | Cache NCAR WPS static fields for reuse | `--cache` |
| `prepare-domain` | Generate [offline domain inputs](domain-preparation.md) from JSON | `--config`, `--output` |
| `fetch-forcing` | Download [weather source files](forcing.md) for a simulation period | `--source`, `--geogrid`, `--start`, `--end`, `--output` |
| `prepare-forcing` | Convert and link [local offline weather files](forcing.md) | `--source`, `--input`, `--geogrid`, `--start`, `--end`, `--output` (or use `--config`) |
| `prepare-parameters` | Inspect or create [parameter experiments](parameters.md) | `--template`, `--list` or `--config` and `--output` |
| `ui` | Start the [local domain and calibration workbench](workbench.md) | None |
| `doctor` | Check an existing source and library environment | `--wrf-hydro-root`, `--netcdf` |
| `compile` | Compile an existing WRF-Hydro tree | `--wrf-hydro-root`, `--netcdf` |
| `write-env` | Write a runtime shell script | `--wrf-hydro-root`, `--netcdf`, `--output` |
| `init-case` | Create the directories for a case | `--cases-home`, `--case-name` |

## Bootstrap Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--wrf-hydro-version` | Inferred from one recognized archive | Select `5.1.2`, `5.2.0`, or `5.4.0`. Required when several model archives are present. |
| `--netcdf` | Unset | Reuse NetCDF-C and NetCDF-Fortran from an existing prefix with both config tools in `bin` |
| `--build-netcdf` | Off | Build zlib, HDF5 and NetCDF from local sources. Available for the 5.4.0 CMake route as well. |
| `--compiler-family` | `gnu` (or `intel` when Intel settings are supplied) | GNU or Intel route |
| `--site-toolchain` | Off | Use the Intel compiler and MPI already loaded by the HPC site for a selected model version. |
| `--intel-home` | `~/intel/parallel_studio_xe_2018` | Intel installation root for bootstrap |
| `--jobs` | Available CPU count | Parallel jobs for dependency `make` commands |
| `--land-model` | `NoahMP` | `NoahMP` or `Noah` |
| `--compiler-option` | Intel: `ifort`; GNU: `gfort` | WRF-Hydro configure label |
| `--mpi-wrapper` | `mpif90` for GNU, `mpiifort` for ifort, `mpiifx` for ifx | MPI Fortran compiler wrapper |
| `--dry-run` | Off | Print the build plan as JSON and write the script for inspection |
| `--skip-deps` | Off | Skip dependency builds if `nf-config` exists in this prefix |
| `--run-example` | Off | Stage and run the local Croton testcase |
| `--example-config` | `NWM` | `NWM`, `Gridded`, `Gridded_no_lakes`, `Reach`, `ReachLakes` |
| `--example-np` | `1` | MPI process count for the example; distinct from build jobs |
| `--profile` | `intel2018-linux` / `gnu-linux` | Metadata label in the generated script |

`--skip-deps` reuses matching libraries in `<prefix>/<family>_libs` with the source archives available. Use `--netcdf` to select an external NetCDF directory. The ifx profile uses existing NetCDF libraries built for ifx.

The 5.4.0 CMake route normally uses installed libraries. It can find them through `nc-config` and `nf-config` on `PATH` when `--netcdf` is omitted. Use `--build-netcdf` for a source build in a fresh prefix. See the [versioned install guide](versioned-install.md).

## Existing Dependencies

These commands operate on the supplied WRF-Hydro source tree. The compile command runs configure, patches `macros` and writes build files there.

```bash
ewhb doctor --compiler-family gnu \
  --wrf-hydro-root /path/to/wrf-hydro/trunk/NDHMS \
  --netcdf /path/to/gnu-netcdf

ewhb compile --compiler-family gnu \
  --wrf-hydro-root /path/to/wrf-hydro/trunk/NDHMS \
  --netcdf /path/to/gnu-netcdf --dry-run
```

For Intel, pass `--compiler-family intel --intel-home /path/to/intel` and use a NetCDF-Fortran library built with the matching compiler.
`doctor` checks the selected compiler, NetCDF tools and the model's Make or CMake source layout. `bootstrap --netcdf` also compiles and links an MPI/NetCDF-Fortran probe.

`compile`, `doctor` and `write-env` additionally accept `--spatial-soil`, `--nudging`, `--rapid` and `--debug`, each `0` or `1`. Bootstrap uses built-in model flags; these four flags are not bootstrap options.

## Environment and Case Directories

```bash
ewhb write-env --compiler-family gnu \
  --wrf-hydro-root /path/to/wrf-hydro/trunk/NDHMS \
  --netcdf /path/to/gnu-netcdf \
  --output ~/wrf_hydro_gnu_env.sh

ewhb init-case --cases-home ~/wrfhydro-cases --case-name example
```

Source the environment script in the shell where the model runs. `WRFHYDRO_RUN_DIR` points to the executables and tables. For a CMake build outside the bootstrap layout, specify `write-env --run-dir /path/to/build/Run`.
