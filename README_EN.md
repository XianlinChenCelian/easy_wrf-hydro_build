<p align="center"><img src="docs/assets/brand/logo.png" width="104" alt="easy_wrf-hydro_build project logo"></p>

# easy_wrf-hydro_build

An open-source Python toolkit for building WRF-Hydro, preparing basin inputs, and organizing parameter experiments. It supports standalone hydrologic simulations and two-way coupling with WRF. Starting from a WPS geogrid, users can build a hydrologic domain, prepare model-ready meteorological forcing, and create runs with different parameters or forcing datasets from a common template.

[简体中文](README.md) · [Documentation](docs/index.md) · [Versions and platforms](docs/release-bundles.md) · [Local workbench](docs/workbench.md) · [Validation records](docs/verified-builds.md)

## Installation

Install the command-line tools with Python 3.9 or later.

```bash
git clone https://github.com/XianlinChenCelian/easy_wrf-hydro_build.git
cd easy_wrf-hydro_build
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
ewhb --help
```

If you already have a domain-processing environment, install the toolkit there. Use `python -m pip install '.[parameters,forcing]'` for parameter experiments, plotting, and forcing conversion. The [domain setup guide](docs/domain-preparation.md) lists the GDAL, WhiteboxTools, and NCAR GIS requirements.

## Modeling workflow

| Step | Inputs and outputs | Guide |
| --- | --- | --- |
| Build the model | Match the compiler, MPI, and NetCDF to the selected release and build standalone WRF-Hydro or coupled WRF | [Versioned installation](docs/versioned-install.md) · [WRF/WPS](docs/wrf-wps.md) |
| Prepare the domain | Use a WPS geogrid, a DEM, and optional gauges to generate routing grids, soil parameters, and initial conditions. Set routing resolution, the stream threshold, and lake polygons | [Domain preparation](docs/domain-preparation.md) |
| Prepare standalone forcing | Process ERA5-Land, NLDAS-2, AORC, or custom inputs with source-specific unit and time handling, then write HRLDAS forcing on the land grid | [Meteorological forcing](docs/forcing.md) |
| Create a parameter experiment | Copy the template `DOMAIN`, scale or set NetCDF parameters, link the selected `FORCING`, and save parameter maps | [Parameter experiments](docs/parameters.md) |
| Run a coupled example | Process GFS upper-air and surface fields with WPS, initialize with `real.exe`, and produce atmospheric and hydrologic output with the coupled `wrf.exe` | [Coupled basin examples](docs/coupled-basin-examples.md) |

Run `ewhb ui` to open the local workbench in a browser. The domain page reads the land grid from `geo_em.d01.nc` and shows the routing spacing and nominal stream-initiation area. The parameter page shows template values and units, lets users choose a new run directory and prepared forcing, and displays the resulting PNG maps. The same workflows have [command-line entry points](docs/cli.md) for cluster jobs.

## Versions and toolchains

| WRF-Hydro | WRF | WPS |
| --- | --- | --- |
| 5.1.2 | 4.2 | 4.2 |
| 5.2.0 | 4.3 | 4.3 |
| 5.4.0 | 4.6.1 | 4.6.0 |

Apple Silicon macOS and ARM64 Linux use GNU. On x86_64 Linux, choose GNU or Intel Classic. HPC users can use the compiler and MPI provided by their site. On Windows, use the matching Linux build path inside WSL2 or a Linux virtual machine. See the [platform matrix](docs/release-bundles.md) and [Intel toolchain guide](docs/intel-compiler-matrix.md) for dependencies and setup.

## Basin examples and run checks

- **Croton** is NCAR’s standalone hydrology example. All three model releases completed the Croton run on Apple Silicon macOS and in an Ubuntu ARM64 VM, with 168 hourly gauge files per run. Intel Classic builds of all three releases also completed the run on a native x86_64 Linux cluster. [Validation records](docs/verified-builds.md)
- **Gasconade and Jing River** are the two study regions used in the Easy VIC Build paper. With regional GFS forcing and matching hydrologic domains, all three releases completed a 12-hour coupled run in each basin on Apple Silicon with GNU. These runs produced atmospheric, river-reach, and gauge output. [Coupled basin examples](docs/coupled-basin-examples.md) · [Easy VIC Build paper](https://doi.org/10.5194/gmd-19-10503-2026)

## Citation and contributions

Use [CITATION.cff](CITATION.cff) to cite the software version used in research or teaching. Basin and dataset sources are listed in the [domain preparation guide](docs/domain-preparation.md). Share reproducible cases and issues through [GitHub Issues](https://github.com/XianlinChenCelian/easy_wrf-hydro_build/issues). The code is available under the [MIT License](LICENSE). See the [contribution guide](CONTRIBUTING.md).
