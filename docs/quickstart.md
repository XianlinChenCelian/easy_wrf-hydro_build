# 在 Ubuntu 上编译 WRF-Hydro

[文档目录](index.md) · [English build guide](bootstrap.md)

在 Ubuntu 24.04（包括 WSL2 和 Linux 虚拟机）上，用 GNU 编译器和系统 NetCDF 构建 WRF-Hydro 5.1.2。切换版本或在 macOS 上构建时，参照[三版本安装](versioned-install.md)。

## 1. 安装工具

```bash
sudo apt-get update
sudo apt-get install -y git python3-venv build-essential gfortran csh \
  openmpi-bin libopenmpi-dev libnetcdf-dev libnetcdff-dev netcdf-bin
git clone https://github.com/XianlinChenCelian/easy_wrf-hydro_build.git
cd easy_wrf-hydro_build
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
ewhb --help
```

工具需要 Python 3.9 或更新版本。首次安装时，pip 从 PyPI 获取构建依赖。有学校或单位提供的 PyPI 镜像时，可以给 pip 加 `--index-url https://你的镜像/simple`。

GitHub 连接不稳定时，可以用 `git clone --depth 1` 重试，或在项目页选择 **Code → Download ZIP**。解压后从 `python3 -m venv .venv` 继续。复测特定提交时，下载该提交对应的源码归档。[GitHub 源码归档说明](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives)

## 2. 下载源码并编译

```bash
ewhb fetch-sources --wrf-hydro-version 5.1.2 --output ~/wrf-hydro-packages
ewhb bootstrap --wrf-hydro-version 5.1.2 --compiler-family gnu \
  --shared-dir ~/wrf-hydro-packages --prefix ~/ewhb/5.1.2-gnu \
  --netcdf /usr --jobs 4
```

WSL2 中，把 `--prefix` 放在 Linux 家目录。下载的源码可存放在 Windows 盘，再用 `--shared-dir` 指向对应的 `/mnt/.../wrf-hydro-packages`。

需要固定 NetCDF 版本时，在下载和构建命令中都加 `--build-netcdf`，并从构建命令移除 `--netcdf /usr`。Intel 用户可按 [Intel Classic 安装](oneapi-install.md)选择编译器、MPI 和依赖。加 `--dry-run` 可查看构建计划和生成的脚本。

## 3. 检查可执行文件

```bash
source ~/ewhb/5.1.2-gnu/wrf_hydro_gnu_env.sh
test -x "$WRFHYDRO_RUN_DIR/wrf_hydro_NoahMP.exe"
ldd "$WRFHYDRO_RUN_DIR/wrf_hydro_NoahMP.exe"
```

`WRFHYDRO_RUN_DIR` 指向包含模型可执行文件和参数表的目录。构建日志保存在 `~/ewhb/5.1.2-gnu/logs/`。

## 4. 运行 Croton 示例

将 [Croton v5.1.1 数据归档](source-archives.md#croton-示例数据)放到 `~/wrf-hydro-packages`，再用相同命令追加 `--run-example --example-config NWM --example-np 1`。安装脚本会沿用已经完成的构建步骤。

在 `~/ewhb/5.1.2-gnu/runs/croton_NY_NWM/` 检查 168 个逐小时 `CHANOBS_DOMAIN1` 文件。末个文件为 `201109020000.CHANOBS_DOMAIN1`，用 `ncdump -v streamflow` 检查流量变量。测试机记录到了 `CHAN_DEPTH` 与浮点提示，算例仍完成了上述检查。

下次使用 `ewhb` 时，先激活仓库里的 `.venv`。运行模型时，加载第 3 步的环境脚本。
