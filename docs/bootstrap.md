# Bootstrap Workflow

[Documentation](index.md) · [中文快速开始](quickstart.md) · [CLI reference](cli.md)

`ewhb bootstrap` builds a local WRF-Hydro environment from source archives on an
existing Linux system. It supports two compiler families:

- Intel: Intel Fortran/C and Intel MPI, defaulting to `ifort` and `mpiifort`.
- GNU: Linux package-manager compilers and MPI, defaulting to `gfort` and `mpif90`.

The workflow does not build WRF or WPS.

## Prerequisites

Install the Python helper in a virtual environment as shown in the
[README](../README_EN.md). On Ubuntu, both routes need:

```bash
sudo apt-get update
sudo apt-get install -y build-essential m4 perl csh tcsh
```

For Intel, supply an existing compiler and Intel MPI installation. GNU packages
are listed below. Use Python 3.9+ and run commands in Linux, including under WSL2.

## Required Local Archives

See [source archives](source-archives.md) for official download locations and
the matching Croton version. Keep one version of each component in the shared directory.

Put these files under one shared directory. Subdirectories are fine.

```text
zlib-1.2.11.tar.gz
hdf5-1.12.0.tar.gz
netcdf-c-4.7.4.tar.gz
netcdf-fortran-4.5.3.tar.gz
wrf_hydro_nwm_public-5.1.2.tar.gz
```

To run the Croton NY example, also include:

```text
croton_NY_example_testcase.tar.gz
```

## Intel Build

```bash
ewhb bootstrap \
  --compiler-family intel \
  --shared-dir /mnt/d/wrf-hydro-packages \
  --prefix ~/wrfhydro-intel \
  --intel-home ~/intel/parallel_studio_xe_2018 \
  --run-example
```

This writes and runs:

```text
~/wrfhydro-intel/bootstrap_easy_wrf_hydro.sh
```

It builds dependencies under:

```text
~/wrfhydro-intel/intel_libs
```

It writes the runtime environment script:

```text
~/wrfhydro-intel/wrf_hydro_intel_env.sh
```

## GNU Build

On Ubuntu, install the normal build tools first:

```bash
sudo apt-get update
sudo apt-get install -y build-essential gfortran g++ gcc make m4 perl csh tcsh \
  openmpi-bin libopenmpi-dev
```

Then run:

```bash
ewhb bootstrap \
  --compiler-family gnu \
  --shared-dir /mnt/d/wrf-hydro-packages \
  --prefix ~/wrfhydro-gnu \
  --run-example
```

It builds dependencies under:

```text
~/wrfhydro-gnu/gnu_libs
```

It writes the runtime environment script:

```text
~/wrfhydro-gnu/wrf_hydro_gnu_env.sh
```

## Dry Run

Use `--dry-run` to generate the script without executing it:

```bash
ewhb bootstrap \
  --compiler-family intel \
  --shared-dir /mnt/d/wrf-hydro-packages \
  --prefix ~/wrfhydro-intel \
  --intel-home ~/intel/parallel_studio_xe_2018 \
  --dry-run
```

## What It Does

- Finds local source archives.
- Builds zlib, HDF5, NetCDF-C, and NetCDF-Fortran with one compiler family.
- Applies Intel 2018 compatibility flags when using the Intel profile.
- Extracts WRF-Hydro.
- Runs WRF-Hydro `./configure`.
- Patches `COMPILER90` to the selected MPI wrapper.
- Builds the NoahMP or Noah offline executable.
- Checks the executable with `ldd`.
- Optionally stages and runs the Croton NY example with `mpirun`.

## Rebuild Behavior

Use a new prefix for a different compiler family or version. Sources and step
markers are shared within one prefix, even though library folders have family names.

Each major step writes a marker file under:

```text
<prefix>/logs
```

For an unchanged toolchain and source version, removing a step's `.done` marker
allows that step to rerun. Dependency changes can invalidate later steps too;
a fresh prefix is the reliable choice when changing the build configuration.
