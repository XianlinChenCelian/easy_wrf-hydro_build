# Source Archives / 源码清单

[Documentation](index.md) · [Quickstart](quickstart.md)

The versions below reproduce the recorded Intel classic build. They are a historical baseline, not a claim that these are the latest releases. Third-party sources are supplied separately by the user.

## Baseline Inventory

| Component | Archive name | Official source |
| --- | --- | --- |
| zlib 1.2.11 | `zlib-1.2.11.tar.gz` | [zlib archive](https://zlib.net/fossils/) |
| HDF5 1.12.0 | `hdf5-1.12.0.tar.gz` | [HDF Group archive](https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.12/hdf5-1.12.0/src/) |
| NetCDF-C 4.7.4 | `netcdf-c-4.7.4.tar.gz` | [Unidata release](https://github.com/Unidata/netcdf-c/releases/tag/v4.7.4) |
| NetCDF-Fortran 4.5.3 | `netcdf-fortran-4.5.3.tar.gz` | [Unidata release](https://github.com/Unidata/netcdf-fortran/releases/tag/v4.5.3) |
| WRF-Hydro 5.1.2 | `wrf_hydro_nwm_public-5.1.2.tar.gz` | [NCAR release](https://github.com/NCAR/wrf_hydro_nwm_public/releases/tag/v5.1.2) |
| Croton NY, optional | `croton_NY_example_testcase.tar.gz` | [NCAR test cases](https://ral.ucar.edu/projects/wrf_hydro/testcases) |

For Croton, select the **v5.1.1** test case linked by NCAR for this baseline. The [WRF-Hydro 5.1.2 release notes](https://github.com/NCAR/wrf_hydro_nwm_public/releases/tag/v5.1.2) state that the configuration and forcing requirements are unchanged from 5.1.1. Do not substitute the latest 5.4 data just because it has a similar filename.

这些版本对应项目已有记录，升级组件需要重新编译和验证。Croton 数据请在官方页面选择与 5.1 系列匹配的条目。
若下载后的文件名不匹配表中名称，可在确认内容和版本后重命名；不要通过改文件名冒充另一版本。

## Directory Layout

```text
wrf-hydro-packages/
  zlib-1.2.11.tar.gz
  hdf5-1.12.0.tar.gz
  netcdf-c-4.7.4.tar.gz
  netcdf-fortran-4.5.3.tar.gz
  wrf_hydro_nwm_public-5.1.2.tar.gz
  croton_NY_example_testcase.tar.gz    # only for --run-example
```

`--shared-dir` is searched recursively. Keep **one version of each component** there: discovery prefers shallower paths and then lexical order, not the newest or most compatible version.
Dependency archives must contain their release `configure` scripts. WRF-Hydro must contain `trunk/NDHMS/configure`; Croton must provide the selected configuration directory and forcing data.

## File Checks

Check each archive is readable and compare its hash against upstream checksums when supplied:

```bash
tar -tf ~/wrf-hydro-packages/wrf_hydro_nwm_public-5.1.2.tar.gz | head
sha256sum ~/wrf-hydro-packages/*.tar.gz
```

Computing a hash records the local bytes; it only authenticates a download when compared with a trusted upstream value.
This version does not automatically download archives or verify a checksum manifest. Preserve filenames and hashes with a build report.
