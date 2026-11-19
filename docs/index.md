# 文档 / Documentation

[项目首页](../README.md) · [English overview](../README_EN.md)

| 要运行的任务 | 安装入口 |
| --- | --- |
| 在 Ubuntu、WSL2 或 Ubuntu 虚拟机上编译离线水文模型 | `ewhb bootstrap --netcdf /usr`，指定模型版本。[快速开始](quickstart.md) |
| 在 macOS 上构建，或为单个版本准备固定依赖 | 按平台准备工具链，再运行 `ewhb bootstrap`。也可使用 GNU 离线包的 `python3 install.py`。[三版本安装](versioned-install.md) · [离线包](release-bundles.md) |
| 使用 Intel Classic | 在 x86_64 Linux 或 WSL2 上安装 oneAPI 2023.2.4 与 Intel MPI 2021.10，或加载超算模块。[Intel 安装](oneapi-install.md) |
| 编译 WRF 和 WPS，或运行双向耦合 | `ewhb build-atmosphere`。双向耦合加 `--coupled`。[WRF 与 WPS](wrf-wps.md) |

## 安装与构建 / Installation and builds

- [快速开始 / Quick start](quickstart.md)
- [三版本安装 / Versioned installation](versioned-install.md)
- [系统与编译器选择 / Platforms and toolchains](release-bundles.md)
- [WRF、WPS 与双向耦合构建 / Atmospheric and coupled builds](wrf-wps.md)
- [源码归档与官方算例 / Upstream sources and test cases](source-archives.md)

## 从输入到运行 / From inputs to a run

- [流域制备 / Domain preparation](domain-preparation.md)
- [离线气象驱动 / Standalone meteorological forcing](forcing.md)
- [参数试验与分布图 / Parameter experiments and maps](parameters.md)
- [本机图形工作台 / Local browser workbench](workbench.md)
- [泾河与 Gasconade 耦合算例 / Coupled basin examples](coupled-basin-examples.md)

## 运行检查 / Run checks

- [实测构建与算例 / Verified builds and cases](verified-builds.md)
- [Linux、WSL2 与虚拟机 / Linux, WSL2, and VMs](linux-validation.md)
- [Intel 工具链 / Intel toolchains](intel-compiler-matrix.md)
- [安装恢复 / Installation recovery](installation-recovery.md)
- [命令参考 / CLI reference](cli.md) · [问题排查 / Troubleshooting](troubleshooting.md)

## 参与开发 / Development

- [仓库结构 / Repository layout](repository-layout.md)
- [贡献指南 / Contributing](../CONTRIBUTING.md)
- [路线图 / Roadmap](roadmap.md) · [变更记录 / Changelog](../CHANGELOG.md)
- [GitHub 发布 / Publishing](github-publishing.md)
