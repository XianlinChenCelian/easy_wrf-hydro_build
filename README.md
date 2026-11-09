<p align="center"><img src="docs/assets/brand/logo.png" width="104" alt="easy_wrf-hydro_build：云、降水、流域与河流"></p>

# easy_wrf-hydro_build

为已有 Linux 环境准备 WRF-Hydro 离线模型的编译与运行环境。

[![CI](https://github.com/XianlinChenCelian/easy_wrf-hydro_build/actions/workflows/ci.yml/badge.svg)](https://github.com/XianlinChenCelian/easy_wrf-hydro_build/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-167C6B)](LICENSE)

[English](README_EN.md) · [快速开始](docs/quickstart.md) · [文档目录](docs/index.md) · [验证记录](docs/verified-builds.md) · [系统与编译器选择](docs/release-bundles.md)

WRF-Hydro 安装中比较费时间的，往往是编译器、MPI 和 NetCDF 之间的匹配。
这个项目把依赖编译、模型构建、环境脚本和示例运行整理为一套可以检查、重复执行的流程。
提供 **WRF-Hydro 5.1.2、5.2.0 和 5.4.0** 的离线构建路径，支持 Linux、WSL2 和 Linux 虚拟机，并提供 Apple Silicon 的 GNU 包。

[离线流域制备预览](docs/domain-preparation.md) 用一份配置连接 WPS、开源河网工具、空间土壤参数和初始场生成，附 Easy VIC Build 论文的 Gasconade 与泾河示例。
[离线气象驱动](docs/forcing.md) 将已下载的 ERA5-Land、ERA5、NLDAS-2 或 AORC 转换成模型可读的小时文件。
[参数试验](docs/parameters.md) 从同一模板生成独立的参数文件，并共享气象驱动。

![构建流程：准备本地源码，选择 Intel 或 GNU，编译独立依赖与 WRF-Hydro，可选运行 Croton 示例。](docs/assets/figures/build-workflow.png)

*流域插画为概念示意；编译流程与验证状态见下文。[查看高清图](docs/assets/figures/build-workflow.svg)*

## 当前支持

| 路线 | 编译器与 MPI | 验证状态 |
| --- | --- | --- |
| Intel classic | `ifort` / `icc` / `mpiifort` | Parallel Studio XE 2018 完成依赖编译、模型编译和 Croton NWM 单进程运行 |
| GNU | `gcc` / `gfortran` / OpenMPI `mpif90` | 脚本与配置分支已检查，干净环境完整运行待验证 |
| Intel oneAPI | 视安装版本而定 | 5.4.0 已在超算用 oneAPI 2021.3 `ifort` 构建并运行 Croton，`ifx` 路线为预览 |

CI 检查 Python 包、脚本和文档，**不代表所有编译器都完成了模型实测**。
具体组合见 [验证记录](docs/verified-builds.md) 和 [Intel 版本说明](docs/intel-compiler-matrix.md)。

## 三版本安装（开发预览）

可以显式选择 WRF-Hydro **5.1.2、5.2.0 或 5.4.0**。macOS 使用原生 GNU 路线，
Linux、WSL2 和 Windows 上的 Linux 虚拟机在各自的 Linux 终端使用同一命令。
先准备配套源码和工具链，详见[三版本安装指南](docs/versioned-install.md)。

三个版本均有可选的 WRF/WPS 源码扩展。编译会复用同一工具链的 NetCDF，版本组合与验收进度见 [WRF/WPS 扩展](docs/wrf-wps.md)。

## 安装

在 Linux 终端中安装 Python 3.9+、Git 和 `venv`。Ubuntu 用户可以先执行：

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git
```

然后安装本工具：

```bash
git clone https://github.com/XianlinChenCelian/easy_wrf-hydro_build.git
cd easy_wrf-hydro_build
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
ewhb --help
```

系统编译工具和 MPI 按路线准备，见 [快速开始](docs/quickstart.md)。Intel 路线可使用站点工具链，也可用 [oneAPI 安装指南](docs/oneapi-install.md) 安装个人工具链。

## 使用

先将 WRF-Hydro、zlib、HDF5、NetCDF-C 和 NetCDF-Fortran 源码包放在同一目录。
[源码清单](docs/source-archives.md) 列出了基线版本、官方获取入口和可选的 Croton 示例数据。

**Intel**，将 `--intel-home` 改为实际的编译器安装目录：

```bash
ewhb bootstrap --compiler-family intel \
  --shared-dir ~/wrf-hydro-packages \
  --prefix ~/wrfhydro-intel \
  --intel-home ~/intel/parallel_studio_xe_2018 \
  --jobs 4
source ~/wrfhydro-intel/wrf_hydro_intel_env.sh
```

**GNU**，使用系统安装的 GCC、GFortran 和 OpenMPI：

```bash
ewhb bootstrap --compiler-family gnu \
  --shared-dir ~/wrf-hydro-packages \
  --prefix ~/wrfhydro-gnu \
  --jobs 4
source ~/wrfhydro-gnu/wrf_hydro_gnu_env.sh
```

加入 `--dry-run` 可先生成脚本而不执行编译；准备好匹配版本的示例数据后，加入 `--run-example` 可运行 Croton NWM 示例。
不同路线或版本应使用**不同的 `--prefix`**，避免重用旧源码、日志和完成标记。

## 文档

| 你要做什么 | 入口 |
| --- | --- |
| 第一次从零编译 | [快速开始](docs/quickstart.md) |
| 准备依赖源码和示例数据 | [源码清单](docs/source-archives.md) |
| 查看完整构建流程和产物 | [构建说明](docs/bootstrap.md) |
| 使用现有 NetCDF / 调整编译选项 | [命令参考](docs/cli.md) |
| 直接运行一份命令示例 | [examples](examples/README.md) |
| 排查错误或验证新电脑 | [故障排查](docs/troubleshooting.md) · [隔离测试](docs/isolated-testing.md) |
| 了解代码放在哪里 | [仓库结构](docs/repository-layout.md) |

## 项目范围

本项目构建 WRF-Hydro 离线 NoahMP / Noah 可执行文件，生成运行环境脚本，可选运行官方示例。
WRF/WPS 编译、自定义流域预处理、率定及科学结果分析不在当前范围内。
第三方源码、数据、Intel 安装程序与许可证由用户自行准备，仓库不随包分发。

## 参与和引用

欢迎通过 [Issues](https://github.com/XianlinChenCelian/easy_wrf-hydro_build/issues) 提交错误或真实编译记录。
代码贡献见 [CONTRIBUTING.md](CONTRIBUTING.md)，后续计划见 [Roadmap](docs/roadmap.md)，版本变更见 [CHANGELOG.md](CHANGELOG.md)。

项目使用 [MIT License](LICENSE)。科研引用信息见 [CITATION.cff](CITATION.cff)；WRF-Hydro 和各依赖请分别遵循其许可证与引用要求。
页面组织参考了 [easy_vic_build](https://github.com/XudongZhengSteven/easy_vic_build) 和 [HydroMT](https://github.com/Deltares/hydromt)，本项目由作者独立维护。

**Author**: XianlinChen · **Email**: [chenxl@sehemodel.club](mailto:chenxl@sehemodel.club)

## 选择系统、编译器和版本

发布目录按系统架构、编译器、WRF-Hydro 版本组织。GNU 离线包包含锁定的二进制依赖，Intel 源码配方提供个人 oneAPI 安装入口和依赖源包。5.1.2、5.2.0、5.4.0 都可独立选择。超算 Intel 用户可直接使用已加载的站点模块，个人 Linux／WSL2 用户可安装到个人目录。入口见 [版本安装包](docs/release-bundles.md) 和 [Intel 编译器矩阵](docs/intel-compiler-matrix.md)。
