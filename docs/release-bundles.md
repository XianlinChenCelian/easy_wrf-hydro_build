# 版本、平台与安装包

选择 WRF-Hydro **5.1.2、5.2.0 或 5.4.0**，再按运行环境选择编译器。公开仓库提供源码、依赖清单和组包脚本。下载所选版本的官方归档后，可在自己的系统上构建或组包。

| 运行环境 | 编译器 | 安装入口 |
| --- | --- | --- |
| Apple Silicon macOS | GNU | [三版本安装](versioned-install.md) |
| Linux x86_64 | GNU | [Linux 安装](linux-validation.md) |
| Linux ARM64 | GNU | [Linux 安装](linux-validation.md) |
| Linux x86_64 和超算 | Intel Classic | [站点模块与个人工具链](intel-compiler-matrix.md) |
| Windows 的 WSL2 或 Linux 虚拟机 | 对应来宾的 GNU 或 x86_64 Intel | [Linux 来宾安装](linux-validation.md) |

独立水文模型使用对应版本的 Noah-MP 源码和气象驱动。普通 WRF/WPS 与双向耦合构建复用已激活的编译环境和匹配的 NetCDF。各版本搭配见 [WRF/WPS 构建](wrf-wps.md)，区域数据与运行方式见[耦合算例](coupled-basin-examples.md)。

## GNU 离线包

组包器从已验证的 conda 环境恢复精确的软件包记录，随选定的 WRF-Hydro 源码和 Croton 算例归档。每个版本包带有安装器、依赖清单和 SHA-256。主机需要 Python 3.9+ 及平台提供的构建工具。macOS 使用 Command Line Tools 和支持符号链接的构建目录。

```bash
python3 scripts/release/build_offline_bundle.py \
  --version 5.4.0 \
  --environment /path/to/validated/environment \
  --cache /path/to/mamba/pkgs \
  --archives /path/to/model-and-croton-archives \
  --micromamba /path/to/micromamba \
  --output /path/to/release-candidates
```

解压后先用 `python3 install.py /absolute/path/to/new-install --check-only` 检查目标目录，再加 `--run-example --jobs 4` 安装并运行 Croton。中断后可使用 `--resume`。见[安装恢复指南](installation-recovery.md)及[验证记录](verified-builds.md)。

## Intel 源码配方

从[官方源码归档清单](source-archives.md)取得依赖，再按[版本安装说明](versioned-install.md)下载所选模型及 Croton 算例。

```bash
python3 scripts/release/assemble_release_tree.py \
  --intel-version 5.4.0 \
  --model-archives /path/to/model-and-croton \
  --dependency-archives /path/to/dependency-sources \
  --output /path/to/releases
```

输出位于 `releases/linux-x86_64/intel/<版本>/`。超算先加载站点提供的编译器和 MPI。个人电脑可以使用 oneAPI 2023.2.4 与 Intel MPI 2021.10。配方默认用 `ifort` 构建库和模型，`ifx` 预览使用 `EWHB_NETCDF` 指定匹配的 NetCDF。WRF/WPS 的 Intel 构建采用 Intel Classic。[oneAPI 安装指南](oneapi-install.md)

完整本地发布树按 `系统-架构/编译器/WRF-Hydro 版本` 组织。`index.json` 记录附件、相应路线与可选的 WRF/WPS 扩展。
