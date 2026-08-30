# Troubleshooting WRF-Hydro Builds

This page records practical WRF-Hydro build issues that `easy_wrf-hydro_build`
tries to prevent or make easier to reproduce.

## Pick One Compiler Family

Do not mix compiler families inside one dependency prefix.

Good layouts:

```text
~/wrfhydro_build/intel_libs
~/wrfhydro_build/gnu_libs
```

Risky layout:

```text
~/wrfhydro_build/libs
```

If NetCDF-Fortran was built with `ifort`, compile WRF-Hydro with Intel Fortran
and Intel MPI. If NetCDF-Fortran was built with `gfortran`, compile WRF-Hydro
with a GNU-compatible MPI wrapper.

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

The Intel bootstrap profile applies this flag automatically to C and C++
dependency builds.

## Environment Is Not Loaded

WRF-Hydro runs need the matching environment loaded in each shell.

Intel:

```bash
source ~/wrfhydro_build/wrf_hydro_intel_env.sh
```

GNU:

```bash
source ~/wrfhydro_build/wrf_hydro_gnu_env.sh
```

You can add the matching `source` line to `~/.bashrc` on a dedicated model
environment. Avoid sourcing both Intel and GNU environments in the same shell.

## WSL2 Path Layout

Prefer building large source trees inside the Linux filesystem, for example:

```text
/home/<user>/wrfhydro_build
```

Shared archives can stay under `/mnt/d/...`, but repeated compilation is usually
more predictable from the Linux filesystem.

## NetCDF ABI Checks

Use `doctor` before compiling.

Intel:

```bash
ewhb doctor \
  --compiler-family intel \
  --wrf-hydro-root ~/wrfhydro_build/sources/wrf_hydro_nwm_public-5.1.2/trunk/NDHMS \
  --netcdf ~/wrfhydro_build/intel_libs \
  --intel-home ~/intel/parallel_studio_xe_2018
```

GNU:

```bash
ewhb doctor \
  --compiler-family gnu \
  --wrf-hydro-root ~/wrfhydro_build/sources/wrf_hydro_nwm_public-5.1.2/trunk/NDHMS \
  --netcdf ~/wrfhydro_build/gnu_libs
```

At minimum, it should find:

- `nc-config`
- `nf-config`
- the selected MPI wrapper
- the selected compiler family tools

After compilation, check the final executable with:

```bash
ldd Run/wrf_hydro_NoahMP.exe
```

No required library should report `not found`.
