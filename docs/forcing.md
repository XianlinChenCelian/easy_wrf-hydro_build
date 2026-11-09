# 离线气象驱动制备

`ewhb prepare-forcing` 将已下载的气象资料重采样到 `geo_em.d01.nc` 的陆面格点，并生成 WRF-Hydro Noah-MP 离线模式需要的 `YYYYMMDDHH.LDASIN_DOMAIN1`。输入原件、输出和运行目录可分别放在移动硬盘上。格式和时间以 WRF-Hydro 的官方读入程序为准。[WRF-Hydro 驱动手册](https://wrf-hydro.readthedocs.io/en/stable/model-inputs-preproc.html#meteorological-forcing-data) · [NCAR WRF-Hydro Forcing Engine](https://github.com/NCAR/WrfHydroForcing) · [NCAR ESMF 重采样工具](https://ral.ucar.edu/dataset/earth-system-modeling-framework-esmf-regridding-scripts)

| 来源 | 适用场景 | 下载与制备 |
| --- | --- | --- |
| NOAA AORC v1.1 | Gasconade 等北美历史模拟，小时资料，约 1 km | `fetch-forcing --source aorc` 按计算域和时间从公开存储取子集。制备时使用 `source: aorc`。[产品变量与时段](https://registry.opendata.aws/noaa-nws-aorc/) |
| NASA NLDAS-2 FORA NetCDF v2.0 | Gasconade 论文同类的 0.125° 小时资料 | 可用 GES DISC 网页按区裁剪，或用 `fetch-forcing --source nldas2` 下载 NASA 小时原始文件，后者要配置 Earthdata Login 与 GES DISC 授权。长时段宜在 NASA 端裁剪。制备时使用 `source: nldas2`。[NASA FORA 说明](https://ldas.gsfc.nasa.gov/nldas/v2/forcing) · [NASA NetCDF 文件和变量说明](https://hydro1.gesdisc.eosdis.nasa.gov/data/NLDAS/NLDAS2_README.pdf) |
| ECMWF ERA5-Land | 泾河等全球陆地区域的小时模拟 | 从 CDS 下载原始小时 NetCDF，或配置 CDS API 后用 `fetch-forcing --source era5-land` 按区域和月份请求。制备时使用 `source: era5-land`。[CDS 数据页](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land) · [累计量定义](https://confluence.ecmwf.int/pages/viewpage.action?pageId=239346540) |
| 中国地面气象要素驱动数据集 CMFD | 泾河论文同类数据，0.1°、3 小时 | 从数据中心下载对应版本和时段，补齐风的两个分量后可走 `custom`。此预览未提供 CMFD 专用下载器或自动风向推断。[CMFD 数据说明](https://data.casearth.cn/dataset/5feae826819aec33049b7c8d) |
| GFS、HRRR、RAP、WRF、MRMS | 预报、区域模式输出或雷达降水替换 | 可先用 NCAR 的数据源工具生成或重采样。GRIB 预报时效重叠、WRF 逐时输出和 MRMS 单独降水属于不同入口，当前预览提供标准小时文件生成，不直接处理这些原始格式。[NCAR 重采样资料](https://ral.ucar.edu/dataset/earth-system-modeling-framework-esmf-regridding-scripts) |

## 从下载到运行目录

在流域制备的环境中可直接运行转换。若单独安装，执行 `python -m pip install '.[forcing]'`。下载 AORC 另装 `'.[aorc]'`，下载 NLDAS 装 `earthaccess` 并配置 Earthdata 登录，下载 ERA5-Land 装 `cdsapi`，按 CDS 官方指南配置 API 访问并接受数据条款。[Earthdata 下载说明](https://earthaccess.readthedocs.io/en/stable/user/explanation/access/) · [CDS API 配置](https://cds.climate.copernicus.eu/how-to-api)

```bash
ewhb fetch-forcing --source aorc \
  --geogrid "$CASE/DOMAIN/geo_em.d01.nc" \
  --start 2011-08-26T00:00:00Z --end 2011-08-26T03:00:00Z \
  --output "$CASE/weather"
```

在案例下保存 `forcing.json`。路径以 JSON 所在目录为基准。已有本地 NetCDF 时，可以直接跳到这一步。若 CDS 将即时值与累计值分到两个 NetCDF，两个文件都放进 `files` 匹配范围。

```json
{
  "source": "aorc",
  "geogrid": "DOMAIN/geo_em.d01.nc",
  "files": ["weather/*.nc"],
  "start": "2011-08-26T00:00:00Z",
  "end": "2011-08-26T03:00:00Z",
  "interval_seconds": 3600
}
```

```bash
ewhb prepare-forcing --config "$CASE/forcing.json" \
  --output "$CASE/forcing-ready" --run-dir "$CASE/run"
```

输出清单给出实际 `FORC_TYP`、`FORCING_TIMESTEP` 和 `INDIR`。使用 `--run-dir` 时在已有运行目录创建 `FORCING` 链接，原有目录不会被覆盖。移动硬盘或 Windows 盘不允许创建链接时，可以省略 `--run-dir`，在 `namelist.hrldas` 中把 `INDIR` 指向生成目录的绝对路径。模拟从 00:00 UTC 开始时，第一份小时降水文件是 01:00，代表 00:00–01:00；结束时间对应最后一份文件。修改运行时间和时间步时，以清单和实际编译版本读入方式为准。

## 单位与时间规则

| 模型字段 | 输出单位 | 关键处理 |
| --- | --- | --- |
| `RAINRATE` | mm/s | AORC 和 NLDAS FORA 的前一小时降水以 kg/m² 给出。1 kg/m² 液态水等效于 1 mm，用每小时累积量除以 3600。ERA5-Land 原始累计量先作相邻差，再把 m 转成 mm 后除以 3600。 |
| `SWDOWN`、`LWDOWN` | W/m² | 已是 W/m² 的数据直接使用。ERA5-Land 的 J/m² 先解累计，再除以区间秒数。 |
| `T2D`、`PSFC` | K、Pa | 摄氏温度加 273.15，hPa 乘 100。只转换有明确定义的单位。 |
| `Q2D` | kg/kg | 比湿直接按质量比例换算。ERA5-Land 采用 ECMWF IFS 公式，根据 2 m 露点和地面气压计算，再重采样。 |
| `U2D`、`V2D` | m/s | 分别使用东西、南北风分量。仅有风速时要提供可追溯的风向或分量来源。 |

CDS 原始 ERA5-Land 的 00 UTC 累计值对应前一天的 24 小时累计，需减去前一天 23 UTC 的值。01 UTC 是新一轮累计的首小时，直接取当时累计量。下载入口会包含差分所需的前一时刻。已经解累计的 ERA5-Land 产品可显式用 `custom` 入口，防止差分两次。时间或变量缺失、单位不明、覆盖不全或出现非法值时，转换会停止。[ERA5-Land 累计规则](https://confluence.ecmwf.int/pages/viewpage.action?pageId=239346540) · [ECMWF 比湿计算](https://confluence.ecmwf.int/pages/viewpage.action?pageId=327674988)

本预览对规则经纬度网格使用双线性插值。双线性不保证降水的**空间**总量守恒。对流域总降水敏感的论文实验，可先用 NCAR ESMF 等工具生成守恒重采样的结果，再用 `custom` 传入与 WPS 网格经纬度一致的 NetCDF。转换会保留原先的网格和气象变量值。清单记录实际输入单位、输出单位、网格校验值与时段。

## 自定义 forcing 是什么

自定义 forcing 是用自己的气象资料或组合来驱动模型。例如用站点或雷达降水替换再分析降水，其余要素沿用 ERA5-Land，可以检验洪峰差异有多少来自降雨输入。也可用同一套气温、湿度等背景资料，比较不同降雨产品，或构造设计暴雨做敏感性实验。

先把站点资料插值成网格，或准备已经格网化的 NetCDF。把各变量对齐到相同 UTC 时段和网格，明确降水是该时段的累计量还是速率，再在 JSON 中选 `"source": "custom"`，用 `variables` 映射八个模型字段。例如 `"RAINRATE": {"name": "gauge_rain", "units": "mm"}` 表示这个变量是每个输入时间段的毫米数。只有确认源数据元数据缺失或错误时才手动指定单位。支持时段开头或结尾标记，通过 `time_label` 明确选择，默认 `end`。站点 CSV 本身仍需先完成空间插值和质控。

如果只替换降水，另一种官方做法是 `FORC_TYP=6`，在已有标准气象驱动外提供单独的降水文件。本预览的 `custom` 入口生成八要素小时文件，模式用 `FORC_TYP=1` 读取。[WRF-Hydro 驱动类型说明](https://wrf-hydro.readthedocs.io/en/stable/model-inputs-preproc.html#meteorological-forcing-data)
