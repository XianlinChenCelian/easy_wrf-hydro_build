# WRF 与 WPS 扩展

本扩展覆盖 WRF/WPS 编译和双向耦合构建。原有三版本离线 WRF-Hydro 包仍可独立使用。默认的 `build-atmosphere` 构建普通 WRF-ARW 和 WPS，设置 `WRF_HYDRO=0`。加 `--coupled` 构建含 Hydro 的 WRF-ARW。两种模式都使用与编译器及 MPI 配套的 NetCDF。

## 默认组合及证据

| WRF-Hydro | WRF | WPS | 选择依据 |
| --- | --- | --- | --- |
| 5.1.2 | 4.2 | 4.2 | [WRF 4.2 发布说明](https://github.com/wrf-model/WRF/releases/tag/v4.2)明确更新 Hydro 5.1.2，并发布 WPS 4.2；也是项目作者已有实践组合 |
| 5.2.0 | 4.3 | 4.3 | [WRF 4.3 发布说明](https://github.com/wrf-model/WRF/releases/tag/v4.3)明确更新 Hydro 5.2.0；搭配同期 [WPS 4.3](https://github.com/wrf-model/WPS/releases/tag/v4.3)作为项目默认组合 |
| 5.4.0 | 4.6.1 | 4.6.0 | [Hydro v5.4.0 标签内附录](https://github.com/NCAR/wrf_hydro_nwm_public/blob/v5.4.0/docs/userguide/appendices.rest)的耦合教程明确指定这两个标签 |

表中的组合用于本项目的构建和算例。使用表外的 WRF 与 WPS 版本时，按所选物理方案检查地理字段。NCAR 给出了 WRF 和 WPS 4.x 的搭配建议。[NCAR 支持答复](https://forum.mmm.ucar.edu/threads/compatibility-of-wrf-wps.18370/)

独立水文模式以外部气象数据驱动陆面和水文过程，生成陆面、河道等配置启用的输出。双向耦合时，WRF 为陆面和水文过程提供气象条件，水文过程改变的陆面状态可通过陆面方案影响大气。根据输出设置，同一次运行可生成大气场 `wrfout` 和河道路由结果 `CHRTOUT`。参见 [NCAR 耦合算例与输出变量说明](https://wrf-hydro.readthedocs.io/en/latest/appendices.html)。

## 使用

激活 GNU 或 Intel Classic 工具链。Ubuntu（含 WSL2）使用系统 GNU 工具链时，先按[快速开始](quickstart.md)安装 MPI 和 NetCDF，再安装 WRF/WPS 的系统工具。

```bash
sudo apt-get install -y csh perl make m4 cpp binutils libtirpc-dev libhdf5-dev
ewhb fetch-sources --atmosphere --wrf-hydro-version 5.1.2 --output ~/wrf-hydro-packages
```

```bash
ewhb build-atmosphere \
  --wrf-hydro-version 5.1.2 \
  --compiler-family gnu \
  --shared-dir ~/wrf-hydro-packages \
  --netcdf /usr \
  --prefix ~/ewhb/5.1.2-atmosphere-gnu \
  --jobs 4
```

`--dry-run` 显示版本、源码清单和工作目录。GNU 构建需要 GNU Fortran 9 或更新版本，以及配套的 MPI 和 NetCDF。Intel 构建用 `--compiler-family intel`，载入 `icc`、`ifort`、`mpiicc`、`mpiifort`，并指定与该工具链匹配的 NetCDF。

在 Debian 和 Ubuntu 上，构建工具在工作目录内为系统 NetCDF 创建 WRF 所需的 `lib/` 布局。对 WRF 4.2 和 4.3，它还把 `nc-config --libs` 中缺少的库搜索目录加入 `configure.wrf`。Ubuntu 的 `libhdf5-dev` 在多架构目录下的 `hdf5/serial/` 提供 WRF 所用的 HDF5 库名。用 `build-manifest.json` 中的 `wrf_netcdf_dependency_dirs` 核对搜索路径。

构建脚本先运行 Fortran 探针，再编译 GRIB2 库、WRF 和 WPS。要复现 WSL2 上已完成的 WRF/WPS 可执行文件验证，可把 `--netcdf` 指向 `bootstrap --build-netcdf` 生成的 `<prefix>/gnu_libs`。也可复用同一工具链的 GNU 离线包环境。[验证记录](verified-builds.md#windows-wsl2-x86_64)

使用一个新的构建目录。构建和 NetCDF 路径需要使用不带空格的目录。阶段日志在 `PREFIX/logs/`，依赖路径和构建结果在 `PREFIX/build-manifest.json`。修复失败原因后，用新的 `--prefix` 重跑。

在 Ubuntu 或 WSL2 的 Ubuntu 来宾中，`csh`、`m4`、`cpp`、`perl`、`make` 和 `binutils` 由系统包提供。没有管理员权限时，向系统管理员说明缺失的具体命令。Mac 路线需要 Command Line Tools 与 GNU Fortran 环境；构建目标应位于支持符号链接、区分大小写的文件系统上。

在约 4 GiB 内存的虚拟机上，用 `--jobs 1` 逐个构建。有些 WRF Fortran 文件单独编译就需要数 GiB 内存。日志出现 `Killed signal terminated program` 时，检查来宾或调度器的内存限制，并降低并行度。WSL2 可在 Windows 的 `%UserProfile%\.wslconfig` 中调整内存。例如，16 GB 的电脑可给 WSL2 配置 8 GB 内存和 4 GB 交换空间。

```ini
[wsl2]
memory=8GB
swap=4GB
```

结束运行中的 WSL 任务后，在 PowerShell 执行 `wsl --shutdown`，然后重新打开 Ubuntu。[Microsoft WSL 配置](https://learn.microsoft.com/windows/wsl/wsl-config)

首次运行 `geogrid.exe` 前，用 `ewhb fetch-geog --cache ~/wrf-hydro-geog` 获取静态数据，或使用已有的 WPS_GEOG 目录。把 `namelist.wps` 的 `geog_data_path` 指到解压后的数据目录。

Apple Silicon 的 Fortran 源码预处理使用 GNU `cpp`。随原 GNU 环境激活时会寻找同目录的工具；自备工具链可用 `CPP` 指定 GNU `cpp` 的路径。

## 双向耦合

带配套气象和区域静态输入的 [GFS 流域算例](coupled-basin-examples.md) 可直接用于泾河和 Gasconade 的 WPS、WRF 和水文联调。

按 [NCAR 耦合构建指南](https://ral.ucar.edu/sites/default/files/docs/water/howtobuildandrunwrfhydrov511coupledtowrf.pdf)，可先分别编译和运行独立的 WRF 和 WRF-Hydro，确认工具链正常。构建耦合版时，工具将所选 Hydro 标签的原始源码接入新解压的 WRF 的 `hydro/`。5.1.2 和 5.2.0 使用 `trunk/NDHMS`，5.4.0 使用 `src`。随后设置 `WRF_HYDRO=1`，以 `dmpar` 配置执行 `compile em_real`。旧构建目录及其目标文件独立保存。

```bash
ewhb build-atmosphere --coupled \
  --wrf-hydro-version 5.4.0 --compiler-family gnu \
  --shared-dir /path/to/atmosphere-archives \
  --hydro-archives /path/to/offline-package/archives \
  --netcdf /path/to/matching/netcdf \
  --prefix /path/to/new/coupled-build --jobs 4
```

Hydro 源码已放在 `--shared-dir` 时可省略 `--hydro-archives`。已有相容的 WPS 时，可加 `--skip-wps` 复用。耦合预览采用常规 Noah-MP 算例的编译设置，关闭空间化土壤参数和径流同化编译选项。

`build-manifest.json` 中的 `coupled_validation: linked` 表示已找到 Hydro 库，并确认 `wrf.exe` 含有 Hydro 耦合入口。运行验收另用 [NCAR Front Range 输入](https://ral.ucar.edu/projects/wrf_hydro/testcases)。用 WPS 和 `real.exe` 生成 `wrfinput_d0*` 和 `wrfbdy_d01`，并配套提供 `hydro.namelist`（`sys_cpl=2`）、Hydro 域文件及参数表。官方 Front Range 算例使用 24 类 USGS 土地覆盖，`namelist.wps`、`num_land_cat` 和参数表须与域文件一致。验证时检查同一次运行生成的大气和水文输出，以及两个模块的运行日志。独立模式的 `FORCING/` 制备流程用于独立水文运行。

5.2.0 的构建会修复已由 WRF 启动 MPI 时的 Hydro 通信组初始化，并传入嵌套域尺寸。5.4.0 的构建会修复传统 Makefile 中 `fortglob.f90` 的文件名大小写，以及多进程土壤水分输出和河道网格元数据中的数组越界。Intel Classic 构建会给 Hydro 显式指定与 WRF 一致的 `mpiifort` 和适用的 `mpiicc`。修复应用于新构建目录里的源码。

在测试用的 Apple Silicon 工具链上，WRF 4.3 写出 NetCDF4 大气历史文件时可能在关闭文件阶段崩溃。使用同一算例时，可在 `namelist.input` 的 `&time_control` 中设置 `use_netcdf_classic = .true.`，以 NetCDF classic 写出大气结果。

## 离线材料

使用 `scripts/release/build_atmosphere_bundle.py` 按单个 Hydro 版本组装附加包。普通附加包包含 WRF、WPS 和构建工具。加 `--coupled` 可打包该版本的 Hydro 源码和耦合安装入口。两类包均复用用户已激活的编译环境。

解压附加包并激活对应工具链后，在包目录执行 `JOBS=8 bash install.sh NEW_PREFIX NETCDF_PREFIX intel`，或将末尾的 `intel` 换为 `gnu`。如复用 WPS，在命令前加 `SKIP_WPS=1`。GNU 环境的 NetCDF 通常位于原安装目录的 `environment/`，Intel 源码配方构建的库位于原安装目录的 `model/intel_libs/`。用包外的 `.sha256` 核对下载文件。检查解包结果可用 `sha256sum -c SHA256SUMS`，macOS 可用 `shasum -a 256 -c SHA256SUMS`。

固定来源与校验值由 `src/easy_wrf_hydro_build/atmosphere.py` 管理。

- WRF/WPS 标签源码来自 `https://codeload.github.com/wrf-model/WRF/tar.gz/refs/tags/v4.2` 等对应官方标签端点。
- Hydro 使用 [NCAR 的版本标签源码](https://github.com/NCAR/wrf_hydro_nwm_public/tags)，校验值与相应的独立水文源码包一致。
- WRF 4.6.1 必须补齐 Noah-MP 提交 `848f54ad3d28c4303151fe5ad83724e232694422`，来源为 NCAR/noahmp。自动生成的 WRF 标签压缩包不含子模块源码。
- GRIB2 依赖为官方旧版教程的 zlib 1.2.11、libpng 1.2.50 和 JasPer 1.900.1，来源为 [NCAR 编译教程](https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compilation_tutorial.php)的 tar_files。这里固定旧版复现基线；新库替换须另行通过 ungrib 回归测试。
- GNU ARM64 的 WPS 构建从 [Automake 1.17 归档](https://ftp.gnu.org/gnu/automake/automake-1.17.tar.gz) 读取 `config.guess` 和 `config.sub`，更新旧 GRIB2 依赖的架构识别。
- WRF、WPS 与 NetCDF 必须使用相容编译器及 ABI。WPS 用传统 configure/compile，与 WRF 保持一致；不能将 CMake 构建的 WPS 随意接到传统 WRF 构建目录。
- 地理数据、GRIB 气象数据和流域输入单独管理，避免每个安装包携带庞大的相同数据。

## 验收与课程路线

普通 WRF/WPS 的三套版本在以下四种环境均生成 `wrf.exe`、`real.exe`、`geogrid.exe`、`ungrib.exe` 和 `metgrid.exe`。十二组 `ungrib` 对同一个 NOAA GFS 小型 GRIB2 样本生成了字节一致的 WPS 中间文件。

| 环境 | 工具链 | 三版本验收 |
| --- | --- | --- |
| 超算 x86_64 Linux | GNU Fortran 9.3 + OpenMPI 4.1.5 | 通过编译、动态库检查和样本解码 |
| 超算 x86_64 Linux | Intel Classic ifort 2021.3 + Intel MPI | 通过编译、动态库检查和样本解码 |
| Apple Silicon 原生 macOS | 原 GNU 离线包环境 | 通过原生编译和样本解码。5.1.2 先完成 WRF，再用修正后的选项重跑 WPS |
| Ubuntu ARM64 虚拟机 | 原 GNU 离线包环境 | 通过编译、动态库检查和样本解码。5.1.2 分阶段重跑 WPS，5.2.0 在内存不足后以单进程补齐 WRF，再构建 WPS |

上述普通 WRF/WPS 的 GRIB2 样本包含单时次 2 米气温。Windows WSL2 上使用自建 NetCDF 完成了 WRF 4.2、WPS 4.2 的 GNU 构建和可执行文件启动，并核对了 WRF-Hydro 5.1.2 的耦合链接。[WSL2 实测记录](verified-builds.md#windows-wsl2-x86_64)

双向耦合在 Apple Silicon GNU 环境使用 NCAR Front Range 算例另外验收。三个版本分别使用表中的 WPS，运行两层嵌套域，水文过程运行在内层域。5.1.2 使用 5.2.0 发布页提供的同一场事件输入。三组均通过 `real.exe`，用两个 MPI 进程完成 12 小时模拟，各写出 13 个时次的 `wrfout` 和 `CHRTOUT_DOMAIN2`，并核对末时次 `RTOUT_DOMAIN2` 的四层土壤含水量。重现算例需使用 [WPS 静态数据](https://www2.mmm.ucar.edu/wrf/site/geog_data.html)中的 `landuse_30s`、`usgs_30s+default` 设置和 NAM 数据对应的 `Vtable.NAM`。

1. 模块一、二：版本锁定、依赖、平台编译、环境诊断和安装恢复。
2. 模块三：建立固定地理数据清单，完成 namelist.wps → geogrid → ungrib → metgrid；验证坐标、分辨率与时间轴。
3. 模块四、五：管理 DEM/土地利用/土壤替换，运行 real.exe 生成 wrfinput，保留数据来源与参数记录。
4. 模块六、七：流域水文预处理、路由网格、土壤参数；评估开放 GIS 实现并与参考工具对照。
5. 模块八、九：强迫数据处理与校验、spin-up、连续模拟、重启一致性。
6. 模块十：Python 可视化、观测对比、NSE/KGE/偏差和可复现图表。
7. 模块十一：在独立模式和单向驱动验证后加入双向耦合，用官方 Front Range 案例单独验收。
8. 模块十二：最后加入 nudging；DART 属于后续独立扩展。
