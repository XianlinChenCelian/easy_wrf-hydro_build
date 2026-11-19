# Troubleshooting WRF-Hydro Builds

## Resume a bootstrap build

Run the same command again with the same version, compiler, and prefix. The
bootstrap script uses the completed steps recorded in `<prefix>/logs/`.

For a build directory created before version tracking, choose a new prefix and
reuse matching libraries from the previous build with
`--netcdf /path/to/previous/gnu_libs`. Check that the directory contains
`bin/nc-config` and `bin/nf-config`.

When a legacy model compile fails, bootstrap prints the first compiler errors
from `logs/compile_offline_NoahMP.log`. Check that file for the source line and
compiler command.

## Pick One Compiler Family

Use one compiler family for the Fortran library, MPI wrappers, and model.

```text
~/wrfhydro-intel/intel_libs
~/wrfhydro-gnu/gnu_libs
```

If NetCDF-Fortran was built with `ifort`, compile WRF-Hydro with Intel Fortran
and Intel MPI. If NetCDF-Fortran was built with `gfortran`, compile WRF-Hydro
with a GNU-compatible MPI wrapper.

Use different bootstrap prefixes for these routes. Source directories and
completion markers also live under the prefix and must not be reused across
compiler/version changes.

## Intel MPI Uses the Wrong Fortran Backend

Symptom:

```text
gfortran: command not found
```

or a failed Intel build after WRF-Hydro generated a `macros` file containing:

```make
COMPILER90 = mpif90
```

For Intel MPI builds, use:

```make
COMPILER90  = mpiifort
```

`ewhb compile` and `ewhb bootstrap --compiler-family intel` patch the generated
`macros` file after `./configure ifort` and before running WRF-Hydro's compile
script.

## GNU MPI Wrapper Is Missing

Symptom:

```text
mpif90: command not found
```

On Ubuntu with OpenMPI:

```bash
sudo apt-get update
sudo apt-get install -y gfortran openmpi-bin libopenmpi-dev
```

Then check:

```bash
command -v mpif90
mpif90 --version
```

If your system uses `mpifort`, pass:

```bash
--mpi-wrapper mpifort
```

## Intel 2018 With Newer Ubuntu Headers

Symptom: `math.h` errors while compiling C dependencies such as HDF5 or NetCDF
with Intel 2018 on newer Ubuntu/glibc systems.

Use this C/C++ flag when building the dependency stack:

```bash
-D__PURE_INTEL_C99_HEADERS__
```

For this toolchain, add that flag to `CFLAGS` and `CXXFLAGS` before
building the dependencies.

## Environment Is Not Loaded

WRF-Hydro runs need the matching environment loaded in each shell.

Intel:

```bash
source ~/wrfhydro-intel/wrf_hydro_intel_env.sh
```

GNU:

```bash
source ~/wrfhydro-gnu/wrf_hydro_gnu_env.sh
```

You can add the matching `source` line to `~/.bashrc` on a dedicated model
environment. Avoid sourcing both Intel and GNU environments in the same shell.

## WSL2 Path Layout

Prefer building large source trees inside the Linux filesystem, for example:

```text
/home/<user>/wrfhydro_build
```

Store the shared archives under `/mnt/d/...` and build in the Linux home directory.

## NetCDF Environment Checks

Use `doctor` before compiling.

It checks paths and tool availability. Run `bootstrap --netcdf` to compile and
link a probe with the selected MPI wrapper and NetCDF-Fortran.

Intel:

```bash
ewhb doctor \
  --compiler-family intel \
  --wrf-hydro-root ~/wrfhydro-intel/sources/wrf_hydro_nwm_public-5.1.2/trunk/NDHMS \
  --netcdf ~/wrfhydro-intel/intel_libs \
  --intel-home ~/intel/parallel_studio_xe_2018
```

GNU:

```bash
ewhb doctor \
  --compiler-family gnu \
  --wrf-hydro-root ~/wrfhydro-gnu/sources/wrf_hydro_nwm_public-5.1.2/trunk/NDHMS \
  --netcdf ~/wrfhydro-gnu/gnu_libs
```

At minimum, it should find:

- `nc-config`
- `nf-config`
- the selected MPI wrapper
- the selected compiler family tools

After compilation, check the final executable with:

```bash
ldd "$WRFHYDRO_RUN_DIR/wrf_hydro_NoahMP.exe"
```

No required library should report `not found`.
