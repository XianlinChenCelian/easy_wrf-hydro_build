<p align="center"><img src="docs/assets/brand/logo.png" width="104" alt="easy_wrf-hydro_build 项目标识"></p>

# easy_wrf-hydro_build

用于部署 WRF-Hydro、制备流域输入和组织参数试验的开源 Python 工具包。支持独立水文模拟和 WRF 双向耦合。用户可从已有的 WPS 网格生成水文域，将气象数据转换为模型输入，并从同一模板创建使用不同参数或气象驱动的试验。

[English](README_EN.md) · [文档](docs/index.md) · [版本与平台](docs/release-bundles.md) · [工作台](docs/workbench.md) · [验证记录](docs/verified-builds.md)

## 安装

需要 Python 3.9 或以上版本。以下命令安装命令行工具。

```bash
git clone https://github.com/XianlinChenCelian/easy_wrf-hydro_build.git
cd easy_wrf-hydro_build
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
ewhb --help
```

在已有流域制备环境中，可直接从仓库安装。参数试验、绘图与气象转换的 Python 依赖可通过 `python -m pip install '.[parameters,forcing]'` 安装。流域制备所需的 GDAL、WhiteboxTools 和 NCAR GIS 脚本见[环境准备](docs/domain-preparation.md)。

## 建模流程

| 步骤 | 输入与产物 | 使用入口 |
| --- | --- | --- |
| 编译模型 | 按版本配置编译器、MPI 和 NetCDF，生成 WRF-Hydro 或耦合 WRF 可执行文件 | [版本安装](docs/versioned-install.md) · [WRF/WPS](docs/wrf-wps.md) |
| 制备水文域 | 用 WPS 网格、DEM 和可选站点生成路由网格、土壤参数和初始场。可指定细化比例、起河阈值和湖库多边形 | [流域制备](docs/domain-preparation.md) |
| 准备离线驱动 | 将 ERA5-Land、NLDAS-2、AORC 或自定义数据对齐到陆面网格，按来源处理单位和时间，写出 HRLDAS 驱动 | [气象驱动](docs/forcing.md) |
| 创建参数试验 | 从模板复制 `DOMAIN`，缩放或设定 NetCDF 参数，链接所选的 `FORCING`，并保存参数分布图 | [参数试验](docs/parameters.md) |
| 运行耦合算例 | 用包含高空和地面字段的 GFS 驱动 WPS，经 `real.exe` 初始化，由耦合 `wrf.exe` 输出大气与水文结果 | [耦合算例](docs/coupled-basin-examples.md) |

`ewhb ui` 打开本机浏览器工作台。流域制备页从 `geo_em.d01.nc` 读取陆面网格，显示细化后的水文间距和名义起河面积。参数率定页显示模板的参数值和单位，可为每组试验指定新目录和已制备的驱动，并浏览生成的 PNG 图。超算批处理可使用相同流程的[命令行入口](docs/cli.md)。

## 版本与工具链

| WRF-Hydro | 配套 WRF | 配套 WPS |
| --- | --- | --- |
| 5.1.2 | 4.2 | 4.2 |
| 5.2.0 | 4.3 | 4.3 |
| 5.4.0 | 4.6.1 | 4.6.0 |

Apple Silicon macOS 与 Linux ARM64 使用 GNU。x86_64 Linux 可选择 GNU 或 Intel Classic，超算可调用站点提供的编译器和 MPI。Windows 上在 WSL2 或 Linux 虚拟机中使用对应的 Linux 构建路线。依赖版本及安装方式见[平台矩阵](docs/release-bundles.md)和 [Intel 工具链说明](docs/intel-compiler-matrix.md)。

## 流域示例与运行验证

- **Croton** 是 NCAR 提供的独立水文算例。三个模型版本均在 Apple Silicon macOS 和 Ubuntu ARM64 虚拟机完成 Croton 运行，每次生成 168 个逐小时站点输出。原生 x86_64 Linux 超算上的 Intel Classic 构建也完成了这三个版本的 Croton 运行。[验证记录](docs/verified-builds.md)
- **Gasconade 与泾河**沿用 Easy VIC Build 论文的两个研究区域。使用区域 GFS 驱动和匹配的水文域，三个版本在 Apple Silicon GNU 环境分别完成了两流域的 12 小时耦合流程，生成大气、河段和站点输出。[耦合算例](docs/coupled-basin-examples.md) · [Easy VIC Build 论文](https://doi.org/10.5194/gmd-19-10503-2026)

## 引用与贡献

在研究或教学中使用本工具时，请通过 [CITATION.cff](CITATION.cff) 引用软件版本。流域与数据来源见[制备说明](docs/domain-preparation.md)。问题和可复现的运行记录可提交到 [GitHub Issues](https://github.com/XianlinChenCelian/easy_wrf-hydro_build/issues)。代码采用 [MIT 许可证](LICENSE)，贡献流程见[贡献指南](CONTRIBUTING.md)。
