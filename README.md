# easy_wrf-hydro_build

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Linux](https://img.shields.io/badge/Platform-Linux%20%7C%20WSL2-FCC624?logo=linux&logoColor=black)](https://learn.microsoft.com/windows/wsl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-2ea44f.svg)](LICENSE)
[![Status: beta](https://img.shields.io/badge/Status-beta-f59e0b.svg)](CHANGELOG.md)

**面向已有 Linux、WSL2 或 Linux 虚拟机环境的用户，用一套命令完成 WRF-Hydro 依赖构建、模型编译和示例验证。**

[English](README_EN.md) | [安装流程](docs/bootstrap.md) | [常见问题](docs/troubleshooting.md) | [验证记录](docs/verified-builds.md)

![easy_wrf-hydro_build architecture](docs/ewhb_architecture.svg)

安装 WRF-Hydro 时，真正容易出问题的通常不是源码本身，而是编译器、MPI、NetCDF 以及不同依赖之间的 ABI 是否匹配。

`easy_wrf-hydro_build` 把这些步骤集中起来处理，包括依赖编译、WRF-Hydro `macros` 配置、运行环境生成和示例测试。所有内容默认安装到独立目录，不会修改已有的 WRF、WPS 或 WRF-Hydro 环境。

> 当前版本只处理 **WRF-Hydro 离线模型**，不负责 WRF 和 WPS 的编译。

## 主要功能

- 从本地压缩包编译 zlib、HDF5、NetCDF-C 和 NetCDF-Fortran；
- Intel 和 GNU 编译环境使用独立的依赖目录，避免库文件混用；
- 编译 WRF-Hydro NoahMP 或 Noah 离线可执行文件；
- Intel 路线可自动加载 classic Parallel Studio 或 oneAPI 环境；
- 自动处理 Intel MPI 下 `mpif90` 与 `mpiifort` 的常见配置问题；
- 生成可重复 `source` 的运行环境脚本，并通过 `ldd` 检查动态库链接；
- 可选运行 Croton, NY 官方示例，检查从依赖编译到模型运行的完整流程。

## 快速开始

### 1. 安装命令行工具

通过 GitHub 的 **Code** 菜单克隆或下载仓库后：

```bash
cd easy_wrf-hydro_build
python3 -m pip install -e .
ewhb --help
```

### 2. 准备源码压缩包

将下面这些源码包放在同一个目录下。文件可以位于该目录的子目录中：

```text
zlib-1.2.11.tar.gz
hdf5-1.12.0.tar.gz
netcdf-c-4.7.4.tar.gz
netcdf-fortran-4.5.3.tar.gz
wrf_hydro_nwm_public-5.1.2.tar.gz
```

如果需要自动运行 Croton 示例，还需要：

```text
croton_NY_example_testcase.tar.gz
```

这些源码和测试数据不会随仓库分发，请从对应项目的官方渠道获取，并自行确认许可证和文件完整性。

### 3A. Intel 路线

适用于已经安装 Intel Fortran 和 Intel MPI 的环境。

目前完整验证过的组合为：

```text
ifort + mpiifort
```

示例：

```bash
ewhb bootstrap \
  --compiler-family intel \
  --shared-dir /mnt/d/wrf-hydro-packages \
  --prefix ~/wrfhydro_build \
  --intel-home ~/intel/parallel_studio_xe_2018 \
  --run-example
```

构建完成后加载运行环境：

```bash
source ~/wrfhydro_build/wrf_hydro_intel_env.sh
```

如果使用 oneAPI，可将 `--intel-home` 指向包含 `setvars.sh` 的 oneAPI 根目录。

目前只有 `ifx`、没有 `ifort` 的环境仍属于实验性支持，具体情况见 [Intel 编译器说明](docs/intel-compiler-matrix.md)。

### 3B. GNU 路线

Ubuntu / WSL2 下可先安装 GNU 编译器和 OpenMPI：

```bash
sudo apt-get update
sudo apt-get install -y build-essential gfortran g++ gcc make m4 perl csh tcsh \
  openmpi-bin libopenmpi-dev
```

然后执行：

```bash
ewhb bootstrap \
  --compiler-family gnu \
  --shared-dir /mnt/d/wrf-hydro-packages \
  --prefix ~/wrfhydro_build \
  --run-example
```

构建完成后：

```bash
source ~/wrfhydro_build/wrf_hydro_gnu_env.sh
```

## Intel 还是 GNU？

目前命令行只需要通过 `--compiler-family` 选择：

```text
intel
gnu
```

Intel 路线会自动查找常见的 `setvars.sh`、`compilervars.sh` 和 Intel MPI 环境脚本，因此不需要根据 Parallel Studio 或 oneAPI 的具体年份手动选择配置。

当前最成熟的 Intel 组合仍然是：

```text
ifort + mpiifort
```

`ifx` 支持还在测试中，因此暂时不作为稳定配置推荐。

后续计划加入 `auto` 模式，根据 Fortran 编译器、MPI wrapper、NetCDF ABI 和 Intel 环境脚本自动判断可用配置。进度见 [Roadmap](docs/roadmap.md)。

## 构建完成后有什么

默认情况下，所有文件都会放到 `--prefix` 指定的目录中。例如：

```text
~/wrfhydro_build/
|-- intel_libs/ or gnu_libs/     # 独立依赖环境
|-- sources/                     # 解压后的源码
|-- logs/                        # 编译日志和完成标记
|-- runs/                        # 示例运行目录
|-- wrf_hydro_root.txt           # WRF-Hydro 实际源码目录
`-- wrf_hydro_<family>_env.sh    # 运行环境脚本
```

构建过程不会向 `/usr`、`/usr/local` 等系统目录安装库。

如果不再需要这套环境，删除对应的 `--prefix` 目录即可。

## 当前验证情况

| 路线 | 状态 | 验证内容 |
| --- | --- | --- |
| Intel classic (`ifort` + `mpiifort`) | 完整闭环 | 依赖编译、WRF-Hydro NoahMP、`ldd` 检查、Croton NWM 示例运行 |
| GNU (`gfortran` + `mpif90`) | 分支验证 | 脚本生成、配置项、官方 `gfort` / `mpif90` 宏匹配；独立全编译待补 |
| Intel oneAPI `ifort` | 兼容入口 | 已支持加载 `setvars.sh`，仍需要更多版本实测 |
| Intel oneAPI `ifx` | 实验性 | 暂不作为稳定路线 |

详细测试环境和记录见 [验证记录](docs/verified-builds.md)。

## 文档

- [完整安装与编译流程](docs/bootstrap.md)
- [Intel 编译器版本与分流](docs/intel-compiler-matrix.md)
- [常见错误与排查](docs/troubleshooting.md)
- [隔离闭环测试](docs/isolated-testing.md)
- [空白 Windows / WSL2 环境说明](docs/blank-windows.md)
- [项目路线图](docs/roadmap.md)

## 项目范围

仓库只包含自动化脚本、文档、测试和 GitHub 页面相关文件。

以下内容不会随仓库分发：

- Intel 安装程序及许可证；
- WRF-Hydro 源码；
- zlib、HDF5、NetCDF 等第三方源码；
- Croton 等测试数据；
- 用户已有的编译环境和软件包。

这些内容仍遵循各自项目的许可证和分发规则。

## 参与贡献

如果你在其他 Ubuntu、Intel oneAPI、GNU/OpenMPI 或 WRF-Hydro 版本上完成了测试，欢迎提交验证结果或 issue。

提交代码前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

安全相关问题见 [SECURITY.md](SECURITY.md)。

## 引用与许可

如果在科研或教学工作中使用本项目，可通过仓库中的 [CITATION.cff](CITATION.cff) 获取推荐引用格式。

项目代码按 [MIT License](LICENSE) 发布。WRF-Hydro 及各第三方依赖仍遵循各自许可证。
