# 本机图形工作台

工作台有两个页面。**流域制备**从已有 WPS 网格生成水文域。**参数率定**读取模板参数并生成独立的离线试验目录。两页都能浏览本机文件，也能直接输入路径。计算在启动命令的环境中执行。

## 启动

流域制备需先按[环境与数据准备](domain-preparation.md)安装 NCAR GIS、WhiteboxTools 和配套 Python 依赖。只用参数率定时，可在独立 Python 环境中安装：

```bash
python -m pip install '.[parameters]'
ewhb ui
```

在流域制备环境已经激活时，安装项目后直接运行 `ewhb ui`。终端会显示默认地址 `http://127.0.0.1:8765/`，并尝试打开浏览器。端口占用时可用 `ewhb ui --port 8766`。

- macOS 在已激活的环境中启动，选择 Mac 路径。运行目录需要链接时，输出应放在 APFS 等支持符号链接的卷。
- Windows 用户在 WSL2 终端运行 `ewhb ui --no-browser`，在 Windows 浏览器打开终端显示的地址。路径以 WSL 为准，例如 `/home/用户名/cases` 或 `/mnt/d/data`。建议把试验输出放在 Linux 家目录。[微软 WSL 网络说明](https://learn.microsoft.com/en-us/windows/wsl/networking#accessing-linux-networking-apps-from-windows-localhost)
- Linux 虚拟机在来宾系统中启动，用来宾浏览器打开。超算或无桌面的服务器可直接使用 [命令行](cli.md) 和调度脚本。

工作台监听本机回环地址。关闭浏览器后，只要终端还在运行，正在执行的任务就会继续。等任务结束后，可按 Ctrl+C 关闭工作台。

## 流域制备

1. 选择 `geo_em.d01.nc` 和覆盖整个网格的 DEM GeoTIFF。可选站点 CSV 需要 `FID,LAT,LON` 字段。当前支持一个等间距 Lambert 网格。
2. 填写陆面间距除以水文间距的整数，默认 **10**。起河阈值默认 **200 格**。工作台会显示水文间距和对应的名义汇流面积。河段路由默认勾选，生成 `Route_Link.nc`。
3. 需要湖库时勾选「启用湖库」，再选择多边形 `.shp`。同目录保留同名 `.shx`、`.dbf`、`.prj`。如果多边形未与有效河网相交，检查坐标系、DEM 和起河阈值。
4. 选择模型版本、对应的 Noah-MP 参数表目录、NCAR GIS 脚本目录、初始场月份，以及一个新的输出路径。点击「生成水文域」。输出包含 `DOMAIN/`、`routing-stack.zip`、`domain-config.json` 和各阶段日志。可以将保存的配置交给 `ewhb prepare-domain --config`，指定另一个新目录重跑。

## 参数率定

选择含 `DOMAIN/` 的初始案例，点击「读取模板参数」。常量显示单个值，变化的栅格或河段参数显示有效值范围和单位。每项可选择「乘系数」或「统一设值」。留空沿用模板，全部留空则创建基准试验。

选择离线驱动来源。默认沿用模板的 `FORCING`。若已单独完成单位转换和网格处理，可选择该目录，此时模板无需自带驱动。

选择任意可写的新目录，点击「创建试验目录」。其中的 `DOMAIN/` 是独立副本，`FORCING` 自动链接到选定的驱动目录。参数改动写入 `parameters.json`，链接目标记入 `parameter-manifest.json`。模型运行所需的 namelist 仍按各试验的路径和时段准备。见[参数文件和运行方式](parameters.md)。
