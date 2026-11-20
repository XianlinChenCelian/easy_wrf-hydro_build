# 离线气象驱动制备

`ewhb prepare-forcing` 把已下载的小时格点气象资料转换到 `geo_em.d01.nc` 的陆面格点，生成 WRF-Hydro Noah-MP 离线模式使用的 `YYYYMMDDHH.LDASIN_DOMAIN1`。制备全程可以离线进行，原件、工作空间和输出可以放在移动硬盘。[WRF-Hydro 驱动手册](https://wrf-hydro.readthedocs.io/en/stable/model-inputs-preproc.html#meteorological-forcing-data)

## 已有数据，直接转换

在流域制备环境中运行。读取 NetCDF 时用 `python -m pip install '.[forcing]'`。读取本地 NOAA Zarr v2 或下载 AORC 子集时，用 `python -m pip install '.[forcing,aorc]'` 安装与 Zarr 2 匹配的 xarray 版本。

```bash
ewhb prepare-forcing --source era5-land \
  --input "$CASE/weather/era5-land.zip" \
  --geogrid "$CASE/DOMAIN/geo_em.d01.nc" \
  --start 2020-06-01T22:00:00Z --end 2020-06-02T02:00:00Z \
  --output "$CASE/forcing-ready"
```

`--input` 可传多个文件、带引号的文件匹配式（例如 `"$CASE/weather/*.nc"`）或带有集中元数据的本地 Zarr v2 目录。CDS ZIP 中的即时量和累计量 NetCDF 可一起读取，临时解包与输出使用同一磁盘。输入要覆盖整个 WPS 矩形域，边缘留至少一个源格点。若原件是 GRIB，先导出带有效时间和经纬度的逐小时 NetCDF。

`--start` 和 `--end` 是模拟起止时刻。示例输出第一份为 `2020060123.LDASIN_DOMAIN1`，其中降水代表 22:00–23:00 UTC。最后一份为 `2020060202.LDASIN_DOMAIN1`。在 `namelist.hrldas` 中使用 `FORC_TYP=1`、`FORCING_TIMESTEP=3600`，把 `INDIR` 指向输出目录。也可加 `--run-dir "$CASE/run"` 在已有运行目录创建 `FORCING` 链接，并设置 `INDIR="./FORCING"`。在不能创建符号链接的文件系统上使用绝对路径。

## 数据源和输入格式

| `--source` | 用途和官方先例 | 传给 `--input` 的文件 |
| --- | --- | --- |
| `era5-land` | 泾河等陆地流域的历史回算。ERA5 驱动的高分辨率陆面重算，CDS 网格 0.1°，原生约 9 km。NCAR HRLDAS 提供同类制备流程。[ECMWF 产品说明](https://confluence.ecmwf.int/pages/viewpage.action?pageId=505384848) · [NCAR HRLDAS ERA5-Land 指南](https://github.com/NCAR/hrldas/blob/master/hrldas/docs/README.ERA5) | CDS 小时 NetCDF 或 ZIP。原始产品默认按逐日累计解算。已解累计的格点资料用 `--accumulation hourly`。[CDS 小时产品](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land) · [ARCO 解累计说明](https://confluence.ecmwf.int/pages/viewpage.action?pageId=627854124) |
| `nldas2` | 北美 0.125° 小时产品，Easy VIC Build 论文的 Gasconade 案例使用同一产品。NCAR 提供 NLDAS-2 的 WRF-Hydro 重采样工具。[Easy VIC Build 论文](https://gmd.copernicus.org/articles/19/10503/2026/#section4) · [NCAR NLDAS-2 工具](https://github.com/NCAR/wrf_hydro_model_tools/tree/main/forcing/regrid/NLDAS) · [NASA FORA 文件说明](https://hydro1.gesdisc.eosdis.nasa.gov/data/NLDAS/NLDAS2_README.pdf) | NASA NLDAS-2 FORA NetCDF v2.0 文件，例如 `NLDAS_FORA0125_H.A20110826.0100.020.nc`。 |
| `aorc` | NOAA AORC v1.1，约 1 km 小时资料，适合 Gasconade 等美国流域的历史回算，也是美国国家水文模型历史回算的驱动。[NOAA AORC 数据说明](https://registry.opendata.aws/noaa-nws-aorc/) · [NOAA 国家水文模型手册](https://www.weather.gov/media/owp/operations/Public_Handbook_V2.4_%20NWC_Visualization_Services.pdf) | 原始或裁剪后的 AORC NetCDF，也可传本地年度 Zarr v2 目录。 |

ERA5-Land 需要 2 m 气温和露点、10 m 东西和南北风、地面气压、地表向下短波和长波辐射，以及总降水。风、湿度和温度的参考高度以源资料定义为准。NLDAS-2 和 AORC 直接提供比湿。

同一流域使用不同资料时，请给每次制备指定独立的输出目录。较细的源网格能提供更多空间细节，暴雨和洪峰效果仍需用观测验证。其他常见场景包括以 HRRR 或 GFS 做预报、用 MRMS 替换降水，以及直接读取同网格的 WRF 模式输出，各有对应的时效、格式和读入要求。[NCAR Forcing Engine](https://github.com/NCAR/WrfHydroForcing) · [WRF-Hydro 驱动类型](https://wrf-hydro.readthedocs.io/en/stable/model-inputs-preproc.html#meteorological-forcing-data)

## 单位与累计规则

| 模型字段 | 输出单位 | 处理 |
| --- | --- | --- |
| `RAINRATE` | mm/s | AORC 和 NLDAS-2 的 1 kg/m² 降水等效于 1 mm，按小时累计量除以 3600。ERA5-Land 取得小时累计水当量后从 m 换算成 mm，再除以 3600。 |
| `SWDOWN`、`LWDOWN` | W/m² | AORC 和 NLDAS-2 的 W/m² 直接使用。ERA5-Land 取得前一小时的 J/m² 后除以 3600。 |
| `T2D`、`PSFC` | K、Pa | 使用气温和地面气压。自定义资料中，摄氏温度加 273.15，hPa 乘 100。 |
| `Q2D` | kg/kg | NLDAS-2 和 AORC 使用源比湿。ERA5-Land 在源网格上以 2 m 露点和地面气压按 ECMWF IFS 公式计算，再重采样。[ECMWF 比湿公式](https://confluence.ecmwf.int/pages/viewpage.action?pageId=327674988) |
| `U2D`、`V2D` | m/s | 分别使用东西、南北风分量。 |

CDS **原始 ERA5-Land** 的 00 UTC 值是前一天 24 小时累计，用它减去前一天 23 UTC 的累计值。01 UTC 是新周期的第一小时，直接使用 01 UTC 的累计量。其他时刻用相邻累计量的差。请同时提供模拟起点时刻的数据，以便第一小时需要差分时可以读到前一时刻。已经解累计的 ERA5-Land 用 `--accumulation hourly` 按每小时独立处理。[ERA5-Land 累计规则](https://confluence.ecmwf.int/pages/viewpage.action?pageId=505384848)

ERA5-Land 的极小负值会在重采样前归零，阈值为每小时 0.01 mm 降水或小时平均 0.25 W/m² 辐射。清单记录受影响的源格点时次和原单位的最小值，超过阈值则报错。缺变量、缺小时、时次重复、未知单位或覆盖不全也会停止制备。[ECMWF 对累计量打包误差的说明](https://confluence.ecmwf.int/spaces/UDOC/pages/208501579/Why%2Bare%2Bthere%2Bsometimes%2Bsmall%2Bnegative%2Bprecipitation%2Baccumulations%2B-%2BecCodes%2BGRIB%2BFAQ)

默认对规则经纬度网格做双线性插值，重采样后流域总降水量可能改变。需要降水守恒重采样时，可用 NCAR ESMF 工具先重采样，再用 `custom` 导入与 WPS 经纬度匹配的结果。输出清单记录来源文件、变量名、单位、重采样方式、网格校验值和时段。[NCAR ESMF 重采样工具](https://ral.ucar.edu/dataset/earth-system-modeling-framework-esmf-regridding-scripts)

## 自定义驱动和可选下载

自定义 forcing 允许使用自己的格点气象资料，或将多个来源组合起来。例如用站点或雷达降水替换 ERA5-Land 降水，固定其他变量，检验不同降水驱动对洪峰的影响。先完成质控、空间插值和 UTC 时间对齐，再写配置文件。`source` 取 `custom`，在 `variables` 中逐一映射八个模型字段。例如 `"RAINRATE": {"name": "gauge_rain", "units": "mm"}` 表示输入是该时间段的毫米数。按来源选 `"time_label": "start"` 或默认的 `"end"`。

```json
{
  "source": "aorc",
  "geogrid": "DOMAIN/geo_em.d01.nc",
  "files": ["weather/*.nc"],
  "start": "2019-05-23T03:00:00Z",
  "end": "2019-05-23T06:00:00Z"
}
```

用 `ewhb prepare-forcing --config "$CASE/forcing.json" --output "$CASE/forcing-ready"` 读取配置，文件路径相对于 JSON 所在目录。只替换降水时，WRF-Hydro 另有在已有标准驱动之外读取单独降水文件的 `FORC_TYP=6`。[WRF-Hydro 驱动类型](https://wrf-hydro.readthedocs.io/en/stable/model-inputs-preproc.html#meteorological-forcing-data)

尚未准备原件时，`ewhb fetch-forcing` 可下载 AORC 区域子集、NASA NLDAS-2 原件或 CDS ERA5-Land 原件。NASA 和 CDS 的下载命令需要按各平台配置登录，已有文件的转换无需账号。[Earthdata 访问指南](https://earthaccess.readthedocs.io/en/stable/user/explanation/access/) · [CDS API 配置](https://cds.climate.copernicus.eu/how-to-api)
