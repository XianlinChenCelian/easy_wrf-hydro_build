# Build WRF-Hydro from source

[Documentation](index.md) · [中文快速开始](quickstart.md) · [CLI reference](cli.md)

On Ubuntu, including WSL2 and Ubuntu virtual machines, use GNU Fortran, Open MPI and the system NetCDF packages. Install the Python CLI in a virtual environment. [Installation](../README_EN.md#installation)

```bash
sudo apt-get install -y build-essential gfortran csh openmpi-bin libopenmpi-dev \
  libnetcdf-dev libnetcdff-dev netcdf-bin
ewhb fetch-sources --wrf-hydro-version 5.1.2 --output ~/wrf-hydro-packages
ewhb bootstrap --wrf-hydro-version 5.1.2 --compiler-family gnu \
  --shared-dir ~/wrf-hydro-packages --prefix ~/ewhb/5.1.2-gnu \
  --netcdf /usr --jobs 4
```

Install `cmake` when building 5.4.0. Use a separate prefix for each version and toolchain. WSL2 users can store archives on a Windows drive and build in their Linux home directory.

## Build the libraries from source

Add `--build-netcdf` to the download and build commands. Omit `--netcdf /usr` and install the build tools `m4` and `perl`. The build installs zlib, HDF5, NetCDF-C, and NetCDF-Fortran in `<prefix>/gnu_libs`. For Intel Classic, use `--compiler-family intel --intel-home /path/to/oneapi`. On a cluster, load the site modules and use `--site-toolchain`. [Intel toolchains](intel-compiler-matrix.md)

Use `--dry-run` to view the version, archive paths, compiler and library settings. To resume the same build after an interruption, repeat the command with the same prefix. [Troubleshooting](troubleshooting.md)

## Check the build and run Croton

```bash
source ~/ewhb/5.1.2-gnu/wrf_hydro_gnu_env.sh
test -x "$WRFHYDRO_RUN_DIR/wrf_hydro_NoahMP.exe"
ldd "$WRFHYDRO_RUN_DIR/wrf_hydro_NoahMP.exe"
```

To run Croton, add the [matching case archive](source-archives.md#croton-示例数据) to `--shared-dir` and rerun bootstrap with `--run-example`. Results are stored under `<prefix>/runs/croton_NY_NWM`. The Croton NWM case writes 168 hourly CHANOBS files, ending at 2011-09-02 00:00. [Validation records](verified-builds.md)

For atmospheric or two-way coupled runs, use the [WRF/WPS build guide](wrf-wps.md).
