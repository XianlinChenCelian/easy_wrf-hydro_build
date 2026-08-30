# easy_wrf-hydro_build [![easy_wrf-hydro_build Logo](docs/logo_small_size.svg)](https://github.com/XianlinChenCelian/easy_wrf-hydro_build)

This is an open-source build helper for deploying the WRF-Hydro offline model.

[中文](README.md) | [Build Guide](docs/bootstrap.md) | [Troubleshooting](docs/troubleshooting.md) | [Verified Builds](docs/verified-builds.md)

![EWHB_Architecture](docs/ewhb_architecture.svg)

`easy_wrf-hydro_build` is intended for users who already have Linux, WSL2, or a Linux virtual machine. It focuses on the dependency, compiler, MPI, and NetCDF issues that often make WRF-Hydro installation difficult.

The current version only targets the **WRF-Hydro offline model**. It does not build WRF or WPS.

## Installation

Clone or download the repository from GitHub:

```bash
cd easy_wrf-hydro_build
python3 -m pip install -e .
ewhb --help
```

On Ubuntu or WSL2, install basic build tools first:

```bash
sudo apt-get update
sudo apt-get install -y build-essential gfortran g++ gcc make m4 perl csh tcsh \
  openmpi-bin libopenmpi-dev
```

For a fresh laboratory Windows + WSL2 computer, see [Fresh Windows / WSL2 Setup](docs/blank-windows.md).

## Usage

### 1. Prepare source archives

Place these files under one directory. Subdirectories are supported:

```text
zlib-1.2.11.tar.gz
hdf5-1.12.0.tar.gz
netcdf-c-4.7.4.tar.gz
netcdf-fortran-4.5.3.tar.gz
wrf_hydro_nwm_public-5.1.2.tar.gz
```

To run the Croton, NY example automatically, also provide:

```text
croton_NY_example_testcase.tar.gz
```

Source packages and test data are not distributed with this repository. Please obtain them from the corresponding official projects and check their licenses and file integrity separately.

### 2A. Intel toolchain

Use this route if Intel Fortran and Intel MPI are already installed. The fully verified combination is currently:

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

### 2B. GNU toolchain

Example:

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

## Features

- Build zlib, HDF5, NetCDF-C, and NetCDF-Fortran from local source archives.
- Keep Intel and GNU dependency stacks in separate directories.
- Compile the WRF-Hydro NoahMP or Noah offline executable.
- Handle the common Intel MPI case where `mpif90` needs to be replaced with `mpiifort`.
- Generate a reusable runtime environment script.
- Optionally run the Croton, NY example to test the full chain from dependency build to model execution.

## Documentation

- [Complete Build Guide](docs/bootstrap.md)
- [Intel Compiler Notes](docs/intel-compiler-matrix.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Isolated End-to-End Testing](docs/isolated-testing.md)
- [Fresh Windows / WSL2 Setup](docs/blank-windows.md)
- [Roadmap](docs/roadmap.md)

## Notes

1. **Intel compilers**

   The Intel route searches for classic Parallel Studio or oneAPI environment scripts. The most thoroughly tested setup is still `ifort + mpiifort`. Environments with `ifx` but no `ifort` remain experimental.

2. **GNU compilers**

   The GNU route has passed generated-script checks, configuration handling, and matching against the official `gfort` / `mpif90` macros. More clean-host end-to-end testing is still needed.

3. **Repository boundary**

   This repository contains automation code, documentation, tests, and GitHub page assets only. It does not distribute Intel installers, license files, WRF-Hydro source code, third-party source archives, or example datasets.

## Contributing

Build reports from other Ubuntu versions, Intel oneAPI releases, GNU/OpenMPI combinations, and WRF-Hydro versions are welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting code. For security-related issues, see [SECURITY.md](SECURITY.md).

## License

The code in this repository is released under the [MIT License](LICENSE). WRF-Hydro and all third-party dependencies remain subject to their own licenses.

## Contact

- **Author**: XianlinChen
- **Email**: chenxl@sehemodel.club
- **GitHub**: [@XianlinChenCelian](https://github.com/XianlinChenCelian)
- **Issues**: [GitHub Issues](https://github.com/XianlinChenCelian/easy_wrf-hydro_build/issues)

## Citation

If you use this project in research or teaching, the repository includes a [CITATION.cff](CITATION.cff) file with the recommended citation information.
