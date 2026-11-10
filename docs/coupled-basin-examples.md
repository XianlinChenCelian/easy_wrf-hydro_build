# GFS 双向耦合流域算例

按 WRF-Hydro 版本选择一个耦合算例包。每个包均提供泾河和 Gasconade 的 GFS GRIB2、区域 WPS 静态瓦片、版本匹配的水文路由输入与运行入口。泾河沿用张家山站和已确认的矩形建域范围，Gasconade 沿用论文公开的出口流域边界。两个算例使用 MODIS 地类、10 倍水文网格细化和 200 格起河阈值，并启用 Muskingum–Cunge 河段路由。数据时间为 2026-11-08 00 至 12 UTC，供 12 小时流程复现。

## 解压后运行

激活与编译一致的 GNU 或 Intel Classic 环境，并在包目录执行以下命令。已有同版本的耦合安装时可直接使用它的构建目录。

```bash
bash install.sh "$WORK/coupled-build" "$NETCDF_PREFIX" gnu
bash run-case.sh jing --build "$WORK/coupled-build" --output "$WORK/jing-run"
bash run-case.sh gasconade --build "$WORK/coupled-build" --output "$WORK/gasconade-run"
```

如果构建时使用了 `SKIP_WPS=1`，在运行命令加 `--wps "$WPS_DIR"` 指向已经安装的配套 WPS。程序默认使用一个 MPI 进程。Windows 用户应在 WSL2 或 Linux 虚拟机的 Linux 文件系统内创建输出目录。macOS 移动硬盘可使用支持符号链接的 APFS 卷。失败日志保留在指定目录，重试时选择一个新的 `--output`。

流程会执行 `geogrid.exe → ungrib.exe → metgrid.exe → real.exe → wrf.exe`。输出目录中的 `wps/` 保留 `geo_em.d01.nc` 和三个 `met_em` 时次。`run/` 保留初始场、边界文件、每小时大气输出、河道流量、站点流量和地形路由输出。结束时间和输出文件见 `run-manifest.json`。包内的 `static/WPS_GEOG` 覆盖这两个固定域，自建流域可通过 `--geog-data` 指定完整版 NCAR 缓存。

Apple Silicon GNU 环境已用三个 WRF-Hydro 版本分别完成两流域的 12 小时算例。5.2.0 和 5.4.0 的耦合构建修复了河段输出读取 `Route_Link.nc` 的初始化问题。超算和 Windows WSL2 需要分别验收这两套流域数据。

## 数据与来源

GFS 采用 NOAA/NCEP 的 0.25° `pgrb2`，取同一起报的 `f000`、`f006`、`f012`，保留区域内的高空层、地面和土壤变量。使用 WPS 自带的 `Vtable.GFS` 解码。每个 GRIB2 的 NOAA NOMADS 请求和 SHA-256 保存在 `cases/<流域>/case.json`。原始在线服务的保留期与包内数据副本独立。 [NOAA GFS 数据说明](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast) · [NOAA 开放数据与署名](https://registry.opendata.aws/noaa-gfs-bdp-pds/)

NCAR 列出的其它高空驱动包括 0.25° GDAS Final Analysis、1° GFS-FNL 和 CFSR/CFSv2。GDAS 与 FNL 的分析场常用 6 小时间隔，同样对应 `Vtable.GFS`。CFSR/CFSv2 的压力层和地面场有各自的 Vtable。NAM 覆盖北美，适用于 Gasconade。 [NCAR WRF 气象输入清单](https://www2.mmm.ucar.edu/wrf/site/input_data.html) · [WPS 用户指南](https://www2.mmm.ucar.edu/wrf/site/documentation/users_guide/wps.html)

静态瓦片来自 NCAR 高分辨率地理资料。水文域文件由 HydroSHEDS v1 高程、NCAR WRF-Hydro GIS 处理流程及示例站点生成。HydroSHEDS v1 © World Wildlife Fund, Inc.（2006–2022），适用原数据许可与署名条款。引用 Lehner, Verdin & Jarvis (2008)。流域参考几何和站点来源见 Easy VIC Build 示例记录。 [NCAR 地理资料](https://www2.mmm.ucar.edu/wrf/site/geog_data.html) · [HydroSHEDS 技术文档及许可](https://data.hydrosheds.org/file/technical-documentation/HydroSHEDS_TechDoc_v1_4.pdf) · [Easy VIC Build 档案](https://zenodo.org/records/21771543)
