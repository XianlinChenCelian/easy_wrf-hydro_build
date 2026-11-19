# 源码与算例归档

[文档目录](index.md) · [快速开始](quickstart.md)

```bash
ewhb fetch-sources --wrf-hydro-version 5.1.2 --output ~/wrf-hydro-packages
```

默认下载所选 WRF-Hydro 版本的源码。加 `--build-netcdf` 下载 zlib、HDF5 和 NetCDF。加 `--atmosphere` 下载配套的 WRF、WPS 和 GRIB2 依赖。给 ARM64 机器准备编译归档时，可在 x86_64 下载端加 `--arm-config-tools`。构建时将 `--shared-dir` 指向同一个目录。

下载命令按项目记录的 SHA256 检查归档，重新运行时沿用已通过校验的文件。如果网络使用自管代理，设置 `HTTPS_PROXY`。如果使用与 codeload.github.com URL 结构相同的 HTTPS 镜像，设置 `EWHB_GITHUB_MIRROR`。镜像文件使用同一校验值。

## 从源码构建依赖

| 文件 | 下载地址 |
| --- | --- |
| `zlib-1.2.11.tar.gz` | [zlib 官方归档](https://zlib.net/fossils/zlib-1.2.11.tar.gz) |
| `hdf5-1.12.0.tar.gz` | [HDF Group 官方归档](https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.12/hdf5-1.12.0/src/hdf5-1.12.0.tar.gz) |
| `netcdf-c-4.7.4.tar.gz` | [Unidata v4.7.4 标签源码](https://codeload.github.com/Unidata/netcdf-c/tar.gz/refs/tags/v4.7.4) |
| `netcdf-fortran-4.5.3.tar.gz` | [Unidata v4.5.3 标签源码](https://codeload.github.com/Unidata/netcdf-fortran/tar.gz/refs/tags/v4.5.3) |

从 Unidata 的两个标签链接下载时，以表中的文件名保存。要一次下载所选模型及其依赖源码，运行以下命令。

```bash
ewhb fetch-sources --wrf-hydro-version 5.1.2 --build-netcdf --output ~/wrf-hydro-packages
```

## Croton 示例数据

从 [NCAR 测试算例页面](https://ral.ucar.edu/projects/wrf_hydro/testcases)选择与模型版本对应的归档。5.1.2 沿用 v5.1.1 的配置和驱动数据。[WRF-Hydro 5.1.2 发布说明](https://github.com/NCAR/wrf_hydro_nwm_public/releases/tag/v5.1.2)

| WRF-Hydro | Croton 归档 |
| --- | --- |
| 5.1.2 | `croton_NY_example_testcase.tar.gz` |
| 5.2.0 | `croton_NY_training_example_v5.2.tar.gz` |
| 5.4.0 | `croton_NY_training_example_v5.4.tar.gz` |

将 Croton 归档放入 `--shared-dir`，在构建命令中加 `--run-example`。同一资料目录可以存放多个 Hydro 版本，构建时用 `--wrf-hydro-version` 选定版本。
