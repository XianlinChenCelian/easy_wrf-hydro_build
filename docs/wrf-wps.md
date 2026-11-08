# WRF 与 WPS 扩展

本扩展对应课程中的环境安装与 WRF/WPS 编译阶段。原有三版本离线 WRF-Hydro 包仍可独立使用；WRF/WPS 作为按版本选择的附加源码包，使用相同编译器配套的 NetCDF。新增命令 `build-atmosphere` 目前构建普通 WRF-ARW 与完整 WPS，`WRF_HYDRO=0`。这一步为地理预处理、生成 wrfinput 和气象模拟准备程序，尚不构建双向耦合模型。

## 默认组合及证据

| WRF-Hydro | WRF | WPS | 选择依据 |
| --- | --- | --- | --- |
| 5.1.2 | 4.2 | 4.2 | [WRF 4.2 发布说明](https://github.com/wrf-model/WRF/releases/tag/v4.2)明确更新 Hydro 5.1.2，并发布 WPS 4.2；也是项目作者已有实践组合 |
| 5.2.0 | 4.3 | 4.3 | [WRF 4.3 发布说明](https://github.com/wrf-model/WRF/releases/tag/v4.3)明确更新 Hydro 5.2.0；搭配同期 [WPS 4.3](https://github.com/wrf-model/WPS/releases/tag/v4.3)作为项目默认组合 |
| 5.4.0 | 4.6.1 | 4.6.0 | [Hydro v5.4.0 标签内附录](https://github.com/NCAR/wrf_hydro_nwm_public/blob/v5.4.0/docs/userguide/appendices.rest)的耦合教程明确指定这两个标签 |

这些是有依据的默认测试组合，不代表其他版本均不兼容。NCAR [官方支持答复](https://forum.mmm.ucar.edu/threads/compatibility-of-wrf-wps.18370/)说明 WPS V4+ 与 WRF V4+ 通常可搭配；具体物理选项和地理字段仍需检查。发布说明中的 Hydro 更新也不能代替对独立 Hydro 标签与 WRF 内置 hydro 源码的差异检查。WRF 自带 hydro/.version 在部分标签中未同步更新，因此不能仅凭该文件判定源码版本。

独立水文模式只消费输入文件，不需要安装完整 WRF 才能运行已有 Croton 算例。双向耦合需要把指定 Hydro 源码接入 WRF 并重新构建，使用耦合专用 namelist、参数表和案例验收。不能把三个独立程序的编译成功当作耦合验收。

## 使用

先激活原离线包的 GNU 工具链，或个人 Intel Classic 工具链。在超算只加载管理员提供的 Intel 编译器与 MPI。然后运行工具的更新版。

```bash
ewhb build-atmosphere \
  --wrf-hydro-version 5.1.2 \
  --compiler-family intel \
  --shared-dir /path/to/atmosphere-archives \
  --netcdf /path/to/matching/netcdf \
  --prefix /path/to/new/atmosphere \
  --jobs 8
```

`--dry-run` 显示版本、源码清单和工作目录。GNU 使用 `--compiler-family gnu`，要求 GNU Fortran 9 或更新版本，以及配套的 MPI 和 NetCDF。Intel 当前构建后端为 `icc/ifort/mpiicc/mpiifort`。ifx、macOS ARM64 与 Linux ARM64 分别验收。Windows 使用 x86_64 WSL2 或 Linux 虚拟机，在 Linux 文件系统内编译。

构建依次检查工具、源码 SHA256、NetCDF 的 Fortran 编译与执行，再构建 GRIB2 库、WRF、WPS。菜单编号从所选源码的配置文件计算，避免跨版本硬编码。整个过程不安装编译器、不调用 sudo、不修改登录环境。WRF 的旧构建系统要求编译路径与库路径不含空格。

日志在 `PREFIX/logs/`，状态在 `PREFIX/build-manifest.json`。失败保留现场，修复原因后使用新的 PREFIX；当前版本不提供断点续编，避免残留目标文件被误算为成功。缺少工具时，个人 Linux 用户安装缺失工具，超算用户联系管理员或加载对应模块。运行 NetCDF 探针失败时检查编译器、动态库路径及文件系统 noexec 权限。

在 Ubuntu 或 WSL2 的 Ubuntu 来宾中，`csh`、`m4`、`cpp`、`perl`、`make` 和 `binutils` 由系统包提供。没有管理员权限时，向系统管理员说明缺失的具体命令。Mac 路线需要 Command Line Tools 与 GNU Fortran 环境；构建目标应位于支持符号链接、区分大小写的文件系统上。

Apple Silicon 的 Fortran 源码预处理使用 GNU `cpp`。随原 GNU 环境激活时会寻找同目录的工具；自备工具链可用 `CPP` 指定 GNU `cpp` 的路径。

## 离线材料

使用 `scripts/release/build_atmosphere_bundle.py` 按单个 Hydro 版本组装附加包。它携带更新工具和源码，不包含编译器，也不重复包含原 Hydro 包。

解压附加包并激活对应工具链后，在包目录执行 `JOBS=8 bash install.sh NEW_PREFIX NETCDF_PREFIX intel`，或将末尾的 `intel` 换为 `gnu`。GNU 环境的 NetCDF 通常位于原安装目录的 `environment/`；Intel 源码配方构建的库位于原安装目录的 `model/intel_libs/`。用包外的 `.sha256` 核对下载文件，并用 `sha256sum -c SHA256SUMS` 检查解包结果。

固定来源与校验值由 `src/easy_wrf_hydro_build/atmosphere.py` 管理。

- WRF/WPS 标签源码来自 `https://codeload.github.com/wrf-model/WRF/tar.gz/refs/tags/v4.2` 等对应官方标签端点。
- WRF 4.6.1 必须补齐 Noah-MP 提交 `848f54ad3d28c4303151fe5ad83724e232694422`，来源为 NCAR/noahmp。自动生成的 WRF 标签压缩包不含子模块源码。
- GRIB2 依赖为官方旧版教程的 zlib 1.2.11、libpng 1.2.50 和 JasPer 1.900.1，来源为 [NCAR 编译教程](https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compilation_tutorial.php)的 tar_files。这里固定旧版复现基线；新库替换须另行通过 ungrib 回归测试。
- ARM64 使用 [GNU Automake 1.17](https://ftp.gnu.org/gnu/automake/automake-1.17.tar.gz) 中的 `config.guess` 和 `config.sub` 更新旧 GRIB2 依赖的架构识别，无需安装 Automake。
- WRF、WPS 与 NetCDF 必须使用相容编译器及 ABI。WPS 用传统 configure/compile，与 WRF 保持一致；不能将 CMake 构建的 WPS 随意接到传统 WRF 构建目录。
- 地理数据、GRIB 气象数据和流域输入单独管理，避免每个安装包携带庞大的相同数据。

## 验收与课程路线

每组分别记录源码校验、编译、程序启动、真实数据流程、耦合科学结果五种状态。`compiled` 仅表示 wrf.exe、real.exe、geogrid.exe、ungrib.exe、metgrid.exe 生成，不代表已有真实流域运行结果。已通过的 Hydro Croton 验证也不能转用来证明 WRF/WPS 正确。

1. 模块一、二：版本锁定、依赖、平台编译、环境诊断和安装恢复。
2. 模块三：建立固定地理数据清单，完成 namelist.wps → geogrid → ungrib → metgrid；验证坐标、分辨率与时间轴。
3. 模块四、五：管理 DEM/土地利用/土壤替换，运行 real.exe 生成 wrfinput，保留数据来源与参数记录。
4. 模块六、七：流域水文预处理、路由网格、土壤参数；评估开放 GIS 实现并与参考工具对照。
5. 模块八、九：强迫数据处理与校验、spin-up、连续模拟、重启一致性。
6. 模块十：Python 可视化、观测对比、NSE/KGE/偏差和可复现图表。
7. 模块十一：在独立模式和单向驱动验证后加入双向耦合，用官方 Front Range 案例单独验收。
8. 模块十二：最后加入 nudging；DART 属于后续独立扩展。

课程截图提供任务顺序。论文贡献需要体现可复现安装、数据到结果的自动流程、跨平台验证、示例流域和量化对照；仅编译模型不构成完整软件论文。
