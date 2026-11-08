# 三版本安装（开发预览）

面向用户的发布规划见[按版本独立下载包](release-bundles.md)。以下说明开发者的本地源码安装方式。

选一个 WRF-Hydro 离线版本和一个独立安装目录。三版使用同一个命令，并按版本选择构建方式和配套的 Croton 文件。

| 版本 | 源码文件名 | Croton 文件名 |
| --- | --- | --- |
| [5.1.2](https://github.com/NCAR/wrf_hydro_nwm_public/releases/tag/v5.1.2) | `wrf_hydro_nwm_public-5.1.2.tar.gz` | `croton_NY_example_testcase.tar.gz` |
| [5.2.0](https://github.com/NCAR/wrf_hydro_nwm_public/releases/tag/v5.2.0) | `wrf_hydro_nwm_public-5.2.0.tar.gz` | `croton_NY_training_example_v5.2.tar.gz` |
| [5.4.0](https://github.com/NCAR/wrf_hydro_nwm_public/releases/tag/v5.4.0) | `wrf_hydro_nwm_public-5.4.0.tar.gz` | `croton_NY_training_example_v5.4.tar.gz` |

从相应发布页下载 **Source code (tar.gz)**。把源码和对应的 Croton 文件放进同一个资料目录。
只有 `--run-example` 需要 Croton 数据。

## 准备工具链

- **macOS**。可以用 Homebrew 安装 `gcc open-mpi netcdf-fortran cmake`，NetCDF-Fortran 会带上 NetCDF-C。确认 `mpif90`、`nc-config` 和 `nf-config` 在当前终端可用。将 `--netcdf` 指向包含两种配置工具的 Homebrew 前缀，也可以使用一套已激活且 ABI 匹配的独立环境。
- **Ubuntu Linux、WSL2 或 Windows 中的 Ubuntu 虚拟机**。在 Ubuntu 终端安装 `build-essential gfortran openmpi-bin libopenmpi-dev libnetcdf-dev libnetcdff-dev cmake csh`，然后将 `--netcdf` 设为 `/usr`。其他 Linux 发行版使用等效软件包或集群模块。

安装工具自身需要 Python 3.9 或更新版本，见[快速开始](quickstart.md)。
使用已有 NetCDF 时，生成的安装脚本会先试编译并链接一个使用 MPI 和 NetCDF-Fortran 的小程序，再编译模型。

## 编译并运行 Croton

```bash
ewhb bootstrap --wrf-hydro-version 5.4.0 \
  --shared-dir /path/to/archives \
  --prefix /path/to/build-5.4.0 \
  --netcdf /path/to/netcdf-prefix \
  --run-example
```

5.1.2 和 5.2.0 使用上游的 configure/Make 流程，5.4.0 使用上游的 CMake 流程。
每个版本和工具链使用独立的 `--prefix`。WSL 或 Linux 虚拟机中的安装目录应放在来宾系统自己的文件系统中，资料目录可以在共享硬盘。
加 `--dry-run` 可以先检查生成的安装脚本。正常运行的构建日志保存在安装目录的 `logs/`，算例结果保存在 `runs/croton_NY_NWM/`。
安装结束会打印可执行文件位置。加载安装目录中的 `wrf_hydro_gnu_env.sh` 后，`$WRFHYDRO_RUN_DIR` 指向模型运行模板目录。

各版本和平台的验证结果见[验证记录](verified-builds.md)。
