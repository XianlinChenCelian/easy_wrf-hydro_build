# Command Reference

[Documentation](index.md) · [Build guide](bootstrap.md)

`ewhb --help` lists commands. Use `ewhb <command> --help` for current options.
The CLI accepts command-line arguments; it does **not** load YAML configuration files.

| Command | Purpose | Required paths |
| --- | --- | --- |
| `bootstrap` | Build local dependencies and WRF-Hydro | `--shared-dir`, `--prefix` |
| `build-atmosphere` | Build the optional [WRF/WPS pair](wrf-wps.md) | `--shared-dir`, `--prefix`, `--netcdf` |
| `fetch-geog` | Cache NCAR WPS static fields for reuse | `--cache` |
| `prepare-domain` | Generate [offline domain inputs](domain-preparation.md) from JSON | `--config`, `--output` |
| `fetch-forcing` | Download [weather source files](forcing.md) for a simulation period | `--source`, `--geogrid`, `--start`, `--end`, `--output` |
| `prepare-forcing` | Convert and link [local offline weather files](forcing.md) | `--source`, `--input`, `--geogrid`, `--start`, `--end`, `--output` (or use `--config`) |
| `doctor` | Check an existing source and library environment | `--wrf-hydro-root`, `--netcdf` |
| `compile` | Compile an existing WRF-Hydro tree | `--wrf-hydro-root`, `--netcdf` |
| `write-env` | Write a runtime shell script | `--wrf-hydro-root`, `--netcdf`, `--output` |
| `init-case` | Create case directories; does not prepare model input data | `--cases-home`, `--case-name` |

## Bootstrap Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--wrf-hydro-version` | Unset | Select `5.1.2`, `5.2.0`, or `5.4.0` and match the model and Croton archive names |
| `--netcdf` | Unset | Reuse NetCDF-C and NetCDF-Fortran from an existing prefix with both config tools in `bin` |
| `--build-netcdf` | Off | Build zlib, HDF5 and NetCDF from local sources. Available for the 5.4.0 CMake route as well. |
| `--compiler-family` | `gnu` for an explicit version, otherwise `intel` | GNU or Intel route |
| `--site-toolchain` | Off | Use the Intel compiler and MPI already loaded by the HPC site for a selected model version. |
| `--intel-home` | `~/intel/parallel_studio_xe_2018` | Intel installation root for bootstrap |
| `--jobs` | Available CPU count | Parallel jobs for dependency `make` commands |
| `--land-model` | `NoahMP` | `NoahMP` or `Noah` |
| `--compiler-option` | Intel: `ifort`; GNU: `gfort` | WRF-Hydro configure label |
| `--mpi-wrapper` | Intel: `mpiifort`; GNU: `mpif90` | Fortran wrapper written to `COMPILER90` |
| `--dry-run` | Off | Discover archives and write the script without executing it |
| `--skip-deps` | Off | Skip dependency builds if `nf-config` exists in this prefix |
| `--run-example` | Off | Stage and run the local Croton testcase |
| `--example-config` | `NWM` | `NWM`, `Gridded`, `Gridded_no_lakes`, `Reach`, `ReachLakes` |
| `--example-np` | `1` | MPI process count for the example; distinct from build jobs |
| `--profile` | `intel2018-linux` / `gnu-linux` | Script metadata label; does not select a different compatibility implementation |

`--skip-deps` is for matching libraries already in `<prefix>/<family>_libs` and still requires the source archive inventory. It does not select an arbitrary external NetCDF directory. Use `compile` for that workflow.

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
`doctor` checks paths and commands; it does not prove ABI compatibility by compiling a test program.

`compile`, `doctor` and `write-env` additionally accept `--spatial-soil`, `--nudging`, `--rapid` and `--debug`, each `0` or `1`. Bootstrap uses built-in model flags; these four flags are not bootstrap options.

## Environment and Case Directories

```bash
ewhb write-env --compiler-family gnu \
  --wrf-hydro-root /path/to/wrf-hydro/trunk/NDHMS \
  --netcdf /path/to/gnu-netcdf \
  --output ~/wrf_hydro_gnu_env.sh

ewhb init-case --cases-home ~/wrfhydro-cases --case-name example
```

Environment scripts must be sourced in the shell where the model runs. Creating case directories alone does not supply forcing, parameters or namelists.
