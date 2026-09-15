# Roadmap

## 0.1

- Provide a stable command-line interface.
- Support Intel and GNU compiler-family profiles.
- Add an end-to-end `bootstrap` command for local WRF-Hydro source archives.
- Build zlib, HDF5, NetCDF-C, and NetCDF-Fortran from source with matching ABI.
- Keep Intel and GNU dependency prefixes separate.
- Diagnose compiler, MPI, NetCDF, and WRF-Hydro source layout.
- Generate inspectable runtime environment scripts.
- Generate a repeatable compile script for WRF-Hydro offline NoahMP/Noah builds.
- Preserve the Intel MPI `mpiifort` fix.
- Optionally stage and run the Croton NY offline example.
- Check the Python package, shell syntax, local documentation links and wheel installation in CI.

## 0.2

- Add an automatic diagnostic mode that recommends a compiler route from the
  detected Fortran compiler, MPI wrapper, environment scripts, and NetCDF ABI.
- Add separately tested Intel oneAPI `ifort` and `ifx` profiles.
- Add stronger GNU/OpenMPI and GNU/MPICH validation.
- Add checksums for known dependency tarballs.
- Add a richer example case layout.
- Add clearer prompts when WRF-Hydro configure labels differ by release.
- Add a project-level command that prints the exact archive inventory required.

## 0.3

- Add WRF-Hydro test-case download or import helpers.
- Add namelist validation.
- Add post-build runtime checks for common missing files and library paths.
- Add compatibility notes for common Ubuntu releases.

## Out Of Scope

- WRF and WPS compilation.
- Installing WSL2, creating VMs, or managing Windows system features as the main path.
- Shipping compiler installers or licensed third-party binaries in the repository.

## Later

- Add optional container recipes for users who prefer Docker or Apptainer.
