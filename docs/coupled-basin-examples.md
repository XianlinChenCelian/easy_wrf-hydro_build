# GFS 双向耦合流域算例

耦合算例采用泾河与 Gasconade 的区域 GFS GRIB2、WPS 静态瓦片和版本匹配的水文路由输入。泾河沿用张家山站和已确认的矩形建域范围，Gasconade 沿用论文公开的出口流域边界。两个算例使用 MODIS 地类、10 倍水文网格细化和 200 格起河阈值，并启用 Muskingum–Cunge 河段路由。项目的 12 小时验证使用 2026-11-08 00 至 12 UTC 的输入。使用新时段时，地理和水文域可以复用，气象输入随所选起报时间变化。

## 准备和运行

按 [WRF/WPS 构建指南](wrf-wps.md) 编译对应版本的耦合程序，按[流域制备](domain-preparation.md)准备两个使用 MODIS 的域。把域制备结果放在 `$WORK/domains/jing` 和 `$WORK/domains/gasconade`。

**用 NOAA 最近的预报试跑**。将 `CYCLE` 设为一个已发布 12 小时预报的 UTC 起报时次，可以选择 00、06、12 或 18 UTC。为该时次使用独立的 GRIB2 目录，便于重试时复用已经下完的文件。[NOMADS 可用时段](https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl)

```bash
python3 scripts/release/assemble_basin_cases.py --wrf-hydro-version 5.1.2 \
  --cycle "${CYCLE:?Set CYCLE to an available GFS cycle in UTC}" --download-gfs \
  --domains "$WORK/domains" --forcing "$WORK/gfs-selected" --output "$WORK/cases"
```

**复现固定的验证时段**。从 [固定数据 Release](https://github.com/XianlinChenCelian/easy_wrf-hydro_build/releases/tag/basin-data-20261108-r1) 下载 GFS 包及其 `.sha256` 文件。下载到同一目录后核对校验值，再解压到 `$WORK`。macOS 可用 `shasum -a 256` 代替 `sha256sum`。

```bash
sha256sum -c ewhb-gfs-20261108t00z-r1.tar.gz.sha256
tar -xzf ewhb-gfs-20261108t00z-r1.tar.gz -C "$WORK"
```

三种模型版本共用这六份 GFS 输入。按[流域制备](domain-preparation.md)用官方的 WPS 静态地理数据和 HydroSHEDS v1 CON 高程生成所选版本的水文域。包内 `manifest.json` 给出高程文件名和 SHA-256，以及两个流域使用的区域静态瓦片清单。

```bash
python3 scripts/release/assemble_basin_cases.py --wrf-hydro-version 5.1.2 \
  --cycle 2026-11-08T00:00:00Z \
  --domains "$WORK/domains" \
  --forcing "$WORK/ewhb-gfs-20261108t00z-r1/gfs" --output "$WORK/cases"
```

任选上述一种准备方式，用同一份耦合构建运行两流域。

```bash
ewhb run-basin --case "$WORK/cases/jing" --build "$WORK/coupled-build" \
  --geog-data "$WPS_GEOG" --output "$WORK/jing-run"
ewhb run-basin --case "$WORK/cases/gasconade" --build "$WORK/coupled-build" \
  --geog-data "$WPS_GEOG" --output "$WORK/gasconade-run"
```

运行使用与编译一致的 GNU 或 Intel Classic 环境，默认一个 MPI 进程。独立安装的 WPS 可用 `--wps "$WPS_DIR"` 指定。可用 `scripts/release/build_atmosphere_bundle.py --coupled --cases` 将已准备的流域输入和源码组包。组包时用 `--case-geog` 加入区域静态瓦片后，包内的 `run-case.sh` 可直接使用这些瓦片。

流程会执行 `geogrid.exe → ungrib.exe → metgrid.exe → real.exe → wrf.exe`。输出目录中的 `wps/` 保留 `geo_em.d01.nc` 和三个 `met_em` 时次。`run/` 保留初始场、边界文件、每小时大气输出、河道流量、站点流量和地形路由输出。结束时间和输出文件见 `run-manifest.json`。包内的 `static/WPS_GEOG` 覆盖这两个固定域，自建流域可通过 `--geog-data` 指定完整版 NCAR 缓存。

三个 WRF-Hydro 版本均在 Apple Silicon GNU 环境以单 MPI 进程完成两流域的 12 小时冷启动。5.2.0 和 5.4.0 的构建包含耦合模式读取 `Route_Link.nc` 的修正。

## 数据与来源

GFS 采用 NOAA/NCEP 的 0.25° `pgrb2`，取同一起报的 `f000`、`f006`、`f012`，保留区域内的高空层、地面和土壤变量。使用 WPS 自带的 `Vtable.GFS` 解码。`cases/<流域>/case.json` 记录起报时间、区域 NOAA NOMADS 请求和实际使用文件的 SHA-256。复现实测结果时，保留这份清单和对应的 GRIB2 副本。[NOAA GFS 数据说明](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast) · [NOAA 开放数据与署名](https://registry.opendata.aws/noaa-gfs-bdp-pds/)

NCAR 列出的其它高空驱动包括 0.25° GDAS Final Analysis、1° GFS-FNL 和 CFSR/CFSv2。GDAS 与 FNL 的分析场常用 6 小时间隔，同样对应 `Vtable.GFS`。CFSR/CFSv2 的压力层和地面场有各自的 Vtable。NAM 覆盖北美，适用于 Gasconade。 [NCAR WRF 气象输入清单](https://www2.mmm.ucar.edu/wrf/site/input_data.html) · [WPS 用户指南](https://www2.mmm.ucar.edu/wrf/site/documentation/users_guide/wps.html)

静态瓦片来自 NCAR 高分辨率地理资料。水文域文件由 HydroSHEDS v1 高程、NCAR WRF-Hydro GIS 处理流程及示例站点生成。HydroSHEDS v1 © World Wildlife Fund, Inc.（2006–2022），适用原数据许可与署名条款。引用 Lehner, Verdin & Jarvis (2008)。流域参考几何和站点来源见 Easy VIC Build 示例记录。 [NCAR 地理资料](https://www2.mmm.ucar.edu/wrf/site/geog_data.html) · [HydroSHEDS 技术文档及许可](https://data.hydrosheds.org/file/technical-documentation/HydroSHEDS_TechDoc_v1_4.pdf) · [Easy VIC Build 档案](https://zenodo.org/records/21771543)
