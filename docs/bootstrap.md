# Bootstrap Workflow

`ewhb bootstrap` builds a local WRF-Hydro environment from source archives on an
existing Linux system. It supports two compiler families:

- Intel: Intel Fortran/C and Intel MPI, defaulting to `ifort` and `mpiifort`.
- GNU: Linux package-manager compilers and MPI, defaulting to `gfort` and `mpif90`.

The workflow does not build WRF or WPS.

## Required Local Archives

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
  --prefix ~/wrfhydro_build \
  --intel-home ~/intel/parallel_studio_xe_2018 \
  --run-example
```

This writes and runs:

```text
~/wrfhydro_build/bootstrap_easy_wrf_hydro.sh
```

It builds dependencies under:

```text
~/wrfhydro_build/intel_libs
```

It writes the runtime environment script:

```text
~/wrfhydro_build/wrf_hydro_intel_env.sh
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
  --prefix ~/wrfhydro_build \
  --run-example
```

It builds dependencies under:

```text
~/wrfhydro_build/gnu_libs
```

It writes the runtime environment script:

```text
~/wrfhydro_build/wrf_hydro_gnu_env.sh
```

## Dry Run

Use `--dry-run` to generate the script without executing it:

```bash
ewhb bootstrap \
  --compiler-family intel \
  --shared-dir /mnt/d/wrf-hydro-packages \
  --prefix ~/wrfhydro_build \
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

Each major step writes a marker file under:

```text
<prefix>/logs
```

Remove a step's `.done` marker if you want to rebuild that step.
