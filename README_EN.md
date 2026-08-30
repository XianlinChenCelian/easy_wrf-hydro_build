# easy_wrf-hydro_build

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Linux](https://img.shields.io/badge/Platform-Linux%20%7C%20WSL2-FCC624?logo=linux&logoColor=black)](https://learn.microsoft.com/windows/wsl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-2ea44f.svg)](LICENSE)
[![Status: beta](https://img.shields.io/badge/Status-beta-f59e0b.svg)](CHANGELOG.md)

**Build WRF-Hydro dependencies, compile the offline model, and run a test case with a single workflow on Linux, WSL2, or a Linux virtual machine.**

[中文](README.md) | [Build Guide](docs/bootstrap.md) | [Troubleshooting](docs/troubleshooting.md) | [Verified Builds](docs/verified-builds.md)

![easy_wrf-hydro_build architecture](docs/ewhb_architecture.svg)

Installing WRF-Hydro is usually less about the model source itself and more about getting the compiler, MPI, NetCDF, and their ABIs to work together.

`easy_wrf-hydro_build` collects these steps into one workflow: building dependencies, preparing WRF-Hydro `macros`, generating a reusable runtime environment, and optionally running a test case. Everything is installed under a separate prefix by default, so an existing WRF, WPS, or WRF-Hydro setup is left untouched.

> The current version only targets the **WRF-Hydro offline model**. It does not build WRF or WPS.

## Features

- Build zlib, HDF5, NetCDF-C, and NetCDF-Fortran from local source archives.
- Keep Intel and GNU dependency stacks in separate directories.
- Compile the WRF-Hydro NoahMP or Noah offline executable.
- Load Intel classic Parallel Studio or oneAPI environments when needed.
- Handle the common Intel MPI case where `mpif90` needs to be replaced with `mpiifort`.
- Generate a reusable environment script and check linked libraries with `ldd`.
- Optionally run the Croton, NY example to test the full chain from dependency build to model execution.

## Quick Start

### 1. Install the command-line tool

Clone or download the repository from GitHub, then run:

```bash
cd easy_wrf-hydro_build
python3 -m pip install -e .
ewhb --help
```

### 2. Prepare the source archives

Place the following archives under the same directory. They may also be stored in subdirectories:

```text
zlib-1.2.11.tar.gz
hdf5-1.12.0.tar.gz
netcdf-c-4.7.4.tar.gz
netcdf-fortran-4.5.3.tar.gz
wrf_hydro_nwm_public-5.1.2.tar.gz
```

To run the Croton example automatically, also provide:

```text
croton_NY_example_testcase.tar.gz
```

Source packages and test data are not distributed with this repository. Please obtain them from the corresponding official projects and check their licenses and file integrity separately.

### 3A. Intel Toolchain

Use this route if Intel Fortran and Intel MPI are already installed.

The fully verified combination is currently:

```text
ifort + mpiifort
```

Example:

```bash
ewhb bootstrap \
  --compiler-family intel \
  --shared-dir /mnt/d/wrf-hydro-packages \
  --prefix ~/wrfhydro_build \
  --intel-home ~/intel/parallel_studio_xe_2018 \
  --run-example
```

After the build completes:

```bash
source ~/wrfhydro_build/wrf_hydro_intel_env.sh
```

For oneAPI, point `--intel-home` to the oneAPI directory containing `setvars.sh`.

Environments with `ifx` but no `ifort` are still considered experimental. See [Intel Compiler Notes](docs/intel-compiler-matrix.md) for details.

### 3B. GNU Toolchain

On Ubuntu or WSL2, install the GNU compilers and OpenMPI first:

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

After the build completes:

```bash
source ~/wrfhydro_build/wrf_hydro_gnu_env.sh
```

## Intel or GNU?

The current command-line interface only requires choosing a compiler family:

```text
intel
gnu
```

For Intel builds, the tool searches for common environment scripts such as `setvars.sh`, `compilervars.sh`, and the Intel MPI setup scripts. This avoids having to select a configuration based only on a particular Parallel Studio or oneAPI release year.

The most thoroughly tested Intel setup is still:

```text
ifort + mpiifort
```

`ifx` support is under testing and is not yet treated as a stable configuration.

A future `auto` mode is planned to inspect the available Fortran compiler, MPI wrapper, NetCDF ABI, and Intel environment before recommending a build route. See the [Roadmap](docs/roadmap.md).

## Build Output

By default, all generated files are stored under the directory given by `--prefix`.

For example:

```text
~/wrfhydro_build/
|-- intel_libs/ or gnu_libs/     # isolated dependency stack
|-- sources/                     # extracted source trees
|-- logs/                        # build logs and completion markers
|-- runs/                        # example run directories
|-- wrf_hydro_root.txt           # detected WRF-Hydro source root
`-- wrf_hydro_<family>_env.sh    # reusable runtime environment
```

No libraries are installed into system locations such as `/usr` or `/usr/local`.

To remove the environment, delete the corresponding `--prefix` directory.

## Verification Status

| Toolchain | Status | Verified |
| --- | --- | --- |
| Intel classic (`ifort` + `mpiifort`) | Full workflow | Dependency build, WRF-Hydro NoahMP compilation, `ldd` check, and Croton NWM example run |
| GNU (`gfortran` + `mpif90`) | Partially verified | Script generation, configuration handling, and matching against the official `gfort` / `mpif90` macros; standalone full build still pending |
| Intel oneAPI `ifort` | Compatibility path | `setvars.sh` loading is supported; more version-specific testing is needed |
| Intel oneAPI `ifx` | Experimental | Not currently treated as a stable build route |

See [Verified Builds](docs/verified-builds.md) for detailed environments and test records.

## Documentation

- [Complete Build Guide](docs/bootstrap.md)
- [Intel Compiler Notes](docs/intel-compiler-matrix.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Isolated End-to-End Testing](docs/isolated-testing.md)
- [Fresh Windows / WSL2 Setup](docs/blank-windows.md)
- [Roadmap](docs/roadmap.md)

## Project Scope

This repository contains the automation code, documentation, tests, and GitHub-related assets only.

It does not distribute:

- Intel installers or licenses;
- WRF-Hydro source code;
- third-party source packages such as zlib, HDF5, or NetCDF;
- Croton or other test datasets;
- existing user compiler or software environments.

These components remain subject to their respective licenses and distribution terms.

## Contributing

Build reports from other Ubuntu versions, Intel oneAPI releases, GNU/OpenMPI combinations, and WRF-Hydro versions are welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting code.

For security-related issues, see [SECURITY.md](SECURITY.md).

## Citation and License

If you use this project in research or teaching, the repository includes a [CITATION.cff](CITATION.cff) file with the recommended citation information.

The code in this repository is released under the [MIT License](LICENSE). WRF-Hydro and all third-party dependencies remain subject to their own licenses.
