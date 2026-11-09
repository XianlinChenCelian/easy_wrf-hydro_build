# 离线流域制备（预览）

`ewhb prepare-domain` 在同一系统中执行 WPS、开源河网工具和 Noah-MP 初始化脚本。它读取一份 JSON 配置，生成 `namelist.wps`、`geo_em.d01.nc` 和 `DOMAIN/` 下的水文输入。适用于一个 Lambert 投影的离线 Noah-MP 区域。

## 1. 准备环境和数据

先完成 [WRF/WPS 编译](wrf-wps.md)，然后在自己可写的位置创建独立地理处理环境。可在 macOS、Linux、WSL2 或 Linux 虚拟机中的同一终端执行下面的流程。高分辨率数据可放在共享盘或移动硬盘，Windows 盘上的 Linux 安装环境和大量临时小文件宜放进 Linux 文件系统。

```bash
micromamba create -p "$WORK/domain-env" -f examples/domain/environment.yml
eval "$(micromamba shell hook -s bash)"
micromamba activate "$WORK/domain-env"
export PROJ_NETWORK=OFF
python -m pip install .
git clone https://github.com/NCAR/wrf_hydro_gis_preprocessor.git "$WORK/ncar-gis"
git -C "$WORK/ncar-gis" checkout fb48c11091841b9f0c2be399fc3660ab06f0ef31
ewhb fetch-geog --cache "$WORK/static"
```

`WORK` 是你设置的可写工作目录。已有管理员提供或自行解压的 `WPS_GEOG` 时，直接填入 `geog_data`。已有原始 tar.gz 时，可向 `fetch-geog` 传入 `--archive /path/to/geog_high_res_mandatory.tar.gz`。高分辨率档案约 2.6 GB，解包需要约 30 GB 或更多，建议留 36 GiB 余量。下载与解包成功后，同一缓存供多个流域和版本使用。仅做流程试跑时可选择 `--resolution low`，并将 `geog_data_res` 设为 `lowres`。NCAR 推荐正式模拟使用高分辨率静态资料。[NCAR 静态数据下载](https://www2.mmm.ucar.edu/wrf/site/access_code/geog_data.html)

水文高程另外提供覆盖**整个 WPS 网格**的一个 GeoTIFF，跨瓦片时可先用 GDAL 拼接。示例采用 HydroSHEDS v1 水文校正高程 CON 的 3 角秒瓦片。3 角秒约为赤道 90 m，输出的路由网格间距由配置决定。每个 HydroSHEDS 下载瓦片可在其官方索引中确认。[HydroSHEDS 下载](https://www.hydrosheds.org/hydrosheds-core-downloads)

## 2. 用一份配置制备流域

[示例生成器](../examples/domain/evb_cases.py) 校验 Easy VIC Build 论文的数据档案，并从中生成 Gasconade 和泾河两套配置。Gasconade 使用发布的原始出口流域 Shapefile。泾河使用发布的 `DomainFile/domain.nc` 区域掩膜和张家山原站点坐标。师兄的建域代码读取 `wbw_working_directory_level0/basin_vector_outlet_with_reference_1.shp`，该文件未收录在公开案例档案。拿到原始 Shapefile 后，可通过 `--jing-boundary` 指定它。两个流域的水文分水岭均由选用的 DEM 和吸附后的出口重新划分。[原论文](https://doi.org/10.5194/gmd-19-10503-2026) · [原始案例档案](https://zenodo.org/records/21771543) · [原始建域代码](https://github.com/XudongZhengSteven/easy_vic_build/blob/d6c237a987235e6f7f41536af8e927f565806c77/examples/JRB_modeling/JRB_build_dpc.py#L465)

```bash
python examples/domain/evb_cases.py \
  --archive "$WORK/zenodo_upload.zip" --output "$WORK/evb-configs" \
  --wps "$WPS_DIR" --geog-data "$WPS_GEOG" \
  --ncar-gis "$WORK/ncar-gis/wrfhydro_gis" \
  --parameter-tables "$HYDRO_NOAHMP_TABLES" --wrf-hydro-version 5.1.2 \
  --gasconade-dem "$WORK/n30w100_con.tif" --jing-dem "$WORK/n30e100_con.tif"
ewhb prepare-domain --config "$WORK/evb-configs/gasconade.json" --output "$WORK/gasconade-prep"
ewhb prepare-domain --config "$WORK/evb-configs/jing.json" --output "$WORK/jing-prep"
```

`WPS_DIR` 是含 `geogrid.exe` 和 `geogrid/GEOGRID.TBL` 的目录。`WPS_GEOG` 是含多个地理数据子目录的目录，可直接使用 `fetch-geog` 返回的 `geog_data`。`HYDRO_NOAHMP_TABLES` 是对应版本中含 `SOILPARM.TBL`、`MPTABLE.TBL`、`GENPARM.TBL`、`HYDRO.TBL` 的目录，例如编译后的 `Run`。命令用这些原表生成空间参数。配置中的相对文件路径以 JSON 所在目录为基准。

- `domain` 中填写陆面间距、中心和投影，可选择给定 `e_we` 和 `e_sn`，或用 `boundary` 流域多边形加 `padding_cells` 自动计算边框。工具会检查多边形和站点能否被模型网格包住。WPS 读 `namelist.wps`，网格划分与静态数据路径都写在其 `&geogrid` 段。[WPS 手册](https://www2.mmm.ucar.edu/wrf/site/documentation/users_guide/wps.html)
- `routing.stations` 使用 `FID,LAT,LON` 表头和 WGS84 坐标，站号按文本保存。工具检查站点是否吸附到活动河道并写入对应河段。`mask_to_stations` 为 `true` 时按站点上游汇水区限制活动河网。
- `routing.ratio` 默认 `10`，是陆面网格间距除以水文网格间距，取正整数。`routing.threshold_cells` 默认 `200`，是起河的累计水文格数。阈值越大，通常提取的河网越稀。同一格数在不同分辨率下对应不同面积。例如 12 km 的陆面网格除以 10 得到 1.2 km 的水文网格，200 格约为 288 km²。`domain-manifest.json` 会记录实际参数和阈值对应的名义面积。[NCAR 河网工具](https://github.com/NCAR/wrf_hydro_gis_preprocessor)
- `routing.reach` 默认 `true`，生成 `Route_Link.nc`。每行对应一段河道，表中有下游河段编号、河长、坡度、底宽、糙率和站点对应关系。运行时，在 `hydro.namelist` 选择 `channel_option = 1`（Muskingum）或 `2`（Muskingum–Cunge）时才读取这张表。`channel_option = 3` 是格网扩散波汇流，使用格网输入和 `CHANPARM.TBL`。[模型输入说明](https://wrf-hydro.readthedocs.io/en/stable/model-inputs-preproc.html) · [运行选项](https://wrf-hydro.readthedocs.io/en/latest/appendices.html)
- `routing.lakes` 默认 `false`。启用湖库时，把它改为 `true`，再将 `routing.lake_polygons` 指向用户选择的湖库多边形 `.shp`，同目录保留同名 `.shx`、`.dbf` 和 `.prj`。两项都满足时才制备 `LAKEPARM.nc`。关闭时可保留文件路径，工具会跳过湖库。两个论文案例默认关闭湖库。
- `initialization_month` 指定初始叶面积指数的月份。脚本根据静态地理资料构造离线初始场 `wrfinput_d01.nc`。后续模拟要准备气象驱动并留出预热期。[NCAR 初始化和参数脚本](https://ral.ucar.edu/projects/wrf_hydro/pre-processing-tools)

结果写入新的输出目录。可先用 `--geogrid-only` 生成网格，检查后在配置中设置 `geogrid` 指向该文件，再运行完整制备到另一个新目录。若失败，查看最近阶段的日志和 `domain-manifest.json` 中已完成的步骤。修正配置后换一个输出目录重跑，已下载的静态数据继续共用。

直接修改案例 JSON 的 `routing` 段即可调整选项。下面的设置主动开启了湖库，`dem` 和 `stations` 等已有字段照常保留。

```json
{
  "reach": true,
  "lakes": true,
  "lake_polygons": "data/reservoirs.shp",
  "ratio": 10,
  "threshold_cells": 200
}
```

## 3. 核对输出

检查 `DOMAIN/` 中的 `geo_em.d01.nc`、`Fulldom_hires.nc`、地下水文件、`soil_properties.nc`、`hydro2dtbl.nc`、`wrfinput_d01.nc`，以及按选项生成的河段或湖库文件。对照实际河网、流域边界和站点控制面积，确认阈值、吸附点和上游范围。配置生成器保留论文的预热、率定和验证年份，便于之后使用相同时段做评估。生成的是 WRF-Hydro 所需的新输入，论文中的 VIC 网格、土壤层和路由参数仍以原档案为准。

单站点案例额外记录根据 Lambert 投影面积变形校正后的上游面积。站点或湖库关联缺失时，流程会给出错误和日志位置。若 Linux 报坐标系数据库找不到，请重新激活环境，使 `PROJ_DATA` 等环境设置生效，然后换一个输出目录重试。
