# 从模板生成参数试验

`ewhb prepare-parameters` 从一个已有的离线算例创建一套新输入。新目录里的 `DOMAIN/` 是独立副本，`FORCING` 链接到模板或另行指定的离线气象驱动。同一份模板可以生成多组试验，每组都从原始值开始计算。

也可以在[本机图形工作台](workbench.md)读取模板参数、填入本次改动，再选择新运行目录。

Easy VIC Build 把待率定参数和空间参数生成过程分别管理。这里沿用集中定义试验参数的思路，在 WRF-Hydro 已生成的 NetCDF 上应用改动。参数字段和文件位置按 WRF-Hydro 文档及 NCAR 率定工具核对。[Easy VIC Build 参数化方法](https://gmd.copernicus.org/articles/19/10503/2026/#section3) · [NCAR 参数调整脚本](https://github.com/NCAR/PyWrfHydroCalib/blob/master/core/adjust_parameters.py) · [WRF-Hydro 参数文件](https://wrf-hydro.readthedocs.io/en/stable/appendices.html#a9-spatially-distributed-soil-and-vegetation-parameters)

## 查看模板参数

用已有的流域制备环境，或执行 `python -m pip install '.[parameters]'`。模板可以是已有算例，也可以用 [流域制备](domain-preparation.md) 生成 `DOMAIN/` 后，再在同一目录放入 [离线气象驱动](forcing.md)。模板中的目录名 `domain`、`forcing` 也能识别。

```bash
ewhb prepare-parameters --template "$BASE_CASE" --list
```

清单显示每个可调参数在模板里的实际最小值、最大值和有效值数量。可用项取决于模板中有哪些文件和变量。

## 创建一组试验

把[示例配置](../examples/parameters.json)存为 `trial.json`，只填需要修改的参数。以下配置把每个格点原有的 `refkdt` 乘以 0.8，把细网格坡面糙率乘数放大 15%，并把每个地下水分区的指数设为 3.5。这些数值用于演示操作。

```json
{
  "refkdt": {"scale": 0.8},
  "ovroughrtfac": {"scale": 1.15},
  "gw_exponent": {"set": 3.5}
}
```

`scale` 乘以指定系数，用正系数可保留原有的空间差异。`set` 把该字段的有效格点或河段统一为一个值。缺测和填充值保留原样。配置写成 `{}` 可生成同一模板的基准试验。

```bash
ewhb prepare-parameters --template "$BASE_CASE" \
  --config "$PWD/trial.json" --output "$EXPERIMENTS/trial-01"
```

```text
trial-01/
├── DOMAIN/                 独立副本，配置指定的 NetCDF 字段已修改
├── FORCING -> ...          链接到本组试验选定的驱动目录
├── parameters.json         本组试验的配置
├── parameter-manifest.json  参数修改前后范围、数据位置和校验值
└── *.TBL                   如果模板提供，则复制到试验目录
```

另选驱动时，在创建命令后加 `--forcing-dir /path/to/prepared-forcing`。这时模板只需有 `DOMAIN/`。指定的是已经完成单位转换和网格处理、可供模型读取的驱动目录。命令只建立目录链接，清单会记录实际目标路径。

输出需为新目录。试验目录可放在移动硬盘上的 APFS 卷或 Linux 文件系统，Windows 的 WSL 用户可放在 Linux 家目录。exFAT 等无法创建目录链接时，模板和气象文件可继续放在原盘，给 `--output` 选一个支持链接的位置。移动试验目录时要保留与驱动目录的相对位置，或重新创建 `FORCING` 链接。

运行时沿用对应版本的可执行文件及 namelist。在新目录运行时，将 `INDIR` 指向 `./FORCING`，各水文和陆面文件指向 `./DOMAIN/`，把输出位置设到本试验内。初始场从 `DOMAIN` 复制，运行用的 namelist 和重启文件由用户按试验时段准备。对比时可为基准和变体使用相同的驱动与初始条件，记录预热方式。

## 可调参数

| 配置键 | NetCDF 文件和字段 | 作用 |
| --- | --- | --- |
| `refkdt` | `soil_properties.nc` · `refkdt` | Noah-MP 地表径流参数化中的入渗系数 |
| `dksat` | `soil_properties.nc` · `dksat` | 分层垂向饱和导水率，m/s |
| `lksat` | `hydro2dtbl.nc` · `LKSAT` | 坡面侧向饱和导水率，m/s |
| `ov_rough2d` | `hydro2dtbl.nc` · `OV_ROUGH2D` | 陆面格点的坡面 Manning 糙率 |
| `lksatfac` | `Fulldom_hires.nc` · `LKSATFAC` | 细网格侧向饱和导水率乘数 |
| `ovroughrtfac` | `Fulldom_hires.nc` · `OVROUGHRTFAC` | 细网格坡面 Manning 糙率乘数 |
| `retdeprtfac` | `Fulldom_hires.nc` · `RETDEPRTFAC` | 发生坡面径流前的滞蓄深度乘数 |
| `channel_manning_n`、`channel_manning_n_compound` | `Route_Link.nc` · `n`、`nCC` | 河段主槽和复合河道的 Manning 糙率 |
| `gw_coefficient`、`gw_exponent`、`gw_max_depth` | `GWBUCKPARM.nc` · `Coeff`、`Expon`、`Zmax` | 地下水桶出流系数、指数和最大储水深度，深度单位为 mm |

参数要与运行选项匹配。土壤参数需要 Noah-MP 空间参数输入指向本试验的 `soil_properties.nc`，侧向和坡面参数需要启用对应汇流方式。河段糙率用于读取 `Route_Link.nc` 的河段汇流，`nCC` 还需要模板含该字段且开启复合河道。地下水参数需要运行配置选用 `GWBUCKPARM.nc`。一次同时改变基础值与乘数时，两者都会参与计算。工具会拒绝未知字段、越界值，以及低于原 `Zinit` 的 `Zmax`。[WRF-Hydro 模型物理说明](https://wrf-hydro.readthedocs.io/en/stable/model-physics.html) · [WRF-Hydro 参数与运行选项](https://wrf-hydro.readthedocs.io/en/stable/appendices.html)
