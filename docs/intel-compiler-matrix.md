# Intel 编译器矩阵

| 运行环境 | 5.1.2 | 5.2.0 | 5.4.0 |
| --- | --- | --- | --- |
| Linux x86_64 / HPC | 站点 `ifort` 已实测，`ifx` 预览 | 站点 `ifort` 已实测，`ifx` 预览 | 站点 `ifort` 已实测，`ifx` 预览 |
| Windows x86_64 的 WSL2 或 Linux 虚拟机 | 选择 x86_64 Linux 配方 | 选择 x86_64 Linux 配方 | 选择 x86_64 Linux 配方 |
| Apple Silicon macOS / Linux ARM64 | GNU 或远程 x86_64 Intel | GNU 或远程 x86_64 Intel | GNU 或远程 x86_64 Intel |
| Windows 原生 | Linux 来宾路线 | Linux 来宾路线 | Linux 来宾路线 |

Intel 当前提供面向 x86_64 Linux 与 Windows 的 `ifx`，Intel 已于 oneAPI 2024.0 移除 Classic Fortran 的 macOS 支持。[Intel 平台要求](https://www.intel.com/content/www/us/en/developer/articles/release-notes/fortran-compiler/2026.html) · [macOS 支持变更](https://www.intel.com/content/www/us/en/developer/articles/release-notes/fortran-compiler/2024.html)

## 超算直接调用

按站点文档加载管理员提供的 Intel Fortran 和 MPI 模块。在同一个计算作业中执行以下命令，第三个参数选择站点实际提供的编译器。

```bash
bash install.sh /absolute/path/to/new-prefix --site-toolchain ifort
```

此入口沿用当前作业环境，从配方中的源码构建独立 NetCDF 和 WRF-Hydro。已有 ABI 匹配的 NetCDF 时，可在 `ewhb bootstrap` 中同时使用 `--site-toolchain --netcdf /path/to/netcdf`。运行生成的模型前，在作业中加载相同的站点工具链。

## 个人工具链

从 `releases/linux-x86_64/intel/<版本>/` 选择源码配方。需要已安装的 Intel C/Fortran、匹配的 Intel MPI 和 Python 3.9+。5.4.0 还需要 CMake 3.12+。源码配方包含模型、Croton 和四个固定依赖源包，会在新的目录中重新编译 zlib、HDF5、NetCDF-C 和 NetCDF-Fortran。

```bash
bash install.sh /absolute/path/to/new-prefix /path/to/oneapi ifort
```

个人电脑可使用 WSL2 已跑通的 oneAPI 2023.2.4 与 Intel MPI 2021.10 组合。配方默认使用 `ifort`。用 `ifx` 试编时，设置 `EWHB_NETCDF` 指向与 ifx 匹配的 NetCDF。[oneAPI 安装指南](oneapi-install.md)

通过 `EWHB_PYTHON` 指定 Python，通过 `EWHB_JOBS` 设置并行数。超算用户在调度系统的计算作业中执行。安装日志为 `PREFIX/install.log`，模型日志在 `PREFIX/model/logs/`。

每个编译器与版本使用新的目标路径。GNU 与 Intel 的 Fortran 模块和 MPI 环境各自构建。测试状态按实际编译器版本、模型版本和平台记录在[已验证构建](verified-builds.md)。

上游 WRF-Hydro 测试入口区分 `intel` 与 `gfort`。项目沿用这种显式选择，并参考 Spack 对外部编译器和工具链的独立记录方式。[WRF-Hydro 测试说明](https://github.com/NCAR/wrf_hydro_nwm_public/blob/main/tests/README.md) · [Spack 编译器配置](https://spack.readthedocs.io/en/latest/configuring_compilers.html)
