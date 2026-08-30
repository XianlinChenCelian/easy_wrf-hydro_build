# Intel Compiler Matrix

Intel product names and release years are not sufficient to select a safe
WRF-Hydro build path. The relevant combination is the Fortran compiler, C/C++
compiler, MPI wrapper, environment script, and the compiler used for
NetCDF-Fortran.

## Current profiles

| Profile | Environment entry | Fortran/MPI | Status |
|---|---|---|---|
| Classic Parallel Studio | `compilervars.sh` and `mpivars.sh` | `ifort` + `mpiifort` | Fully verified |
| oneAPI with classic Fortran | `setvars.sh` | `ifort` + `mpiifort` | Environment loading supported; more version tests needed |
| oneAPI LLVM Fortran | `setvars.sh` | `ifx` + Intel MPI wrapper | Experimental |

The current stable Intel command still generates the WRF-Hydro `ifort`
configuration and patches `COMPILER90` to `mpiifort`. This is why an ifx-only
installation should not yet be presented as equivalent to the tested classic
route.

## Recommended user interface

For novice users, the long-term default should be automatic diagnosis:

```text
auto -> inspect environment -> recommend intel-ifort, intel-ifx, or gnu
```

Manual choices should remain available for clusters and non-standard modules.
The detector must report the actual commands it found and stop when the MPI
wrapper or NetCDF ABI does not match. Until that detector and the ifx compile
patches are fully tested, the public stable choices remain `intel` and `gnu`.

## Before adding a new Intel profile

Record all of the following:

- Linux distribution and version.
- Intel compiler package and `ifort --version` or `ifx --version` output.
- Intel MPI wrapper path and backend compiler.
- zlib, HDF5, NetCDF-C, NetCDF-Fortran, and WRF-Hydro versions.
- WRF-Hydro configure option and generated `macros` changes.
- `ldd` result and example-run result.

Do not infer support only because `setvars.sh` loads successfully.
