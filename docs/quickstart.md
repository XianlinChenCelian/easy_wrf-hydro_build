# 快速开始

[文档目录](index.md) · [English build guide](bootstrap.md)

本页从已有 Linux、WSL2 Ubuntu 或 Linux 虚拟机开始，目标是完成 WRF-Hydro 5.1.2 离线模型的编译。
先阅读 [验证记录](verified-builds.md) 选择路线。GNU 完整闭环仍待验证；oneAPI/ifx 不能等同于已验证的 Intel 2018。

## 1. 安装工具

Ubuntu 中安装共同需要的工具：

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git \
  build-essential m4 perl csh tcsh
git clone https://github.com/XianlinChenCelian/easy_wrf-hydro_build.git
cd easy_wrf-hydro_build
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
ewhb --help
```

Python 最低版本为 3.9。`venv` 只安装本工具，不包含 Fortran 编译器、MPI 或模型依赖。
依赖库由下一步的 `bootstrap` 从源码构建。其他 Linux 发行版请用相应包管理器安装等效工具。

GNU 路线再安装：

```bash
sudo apt-get install -y gfortran openmpi-bin libopenmpi-dev
command -v gcc g++ gfortran mpif90 mpirun
mpif90 --showme:command
```

Intel 路线需要已有 Intel Fortran、C/C++ 编译器和 Intel MPI。
`--intel-home` 指向包含 `setvars.sh` 或 `bin/compilervars.sh` 的安装目录。
兼容范围见 [Intel 编译器矩阵](intel-compiler-matrix.md)。

## 2. 准备源码

按 [源码清单](source-archives.md) 将五个必需压缩包放到 `~/wrf-hydro-packages`。
WSL 用户可以把压缩包放在 `/mnt/d/...`，建议让编译目录 `--prefix` 位于 Linux 家目录。
每种组件只放一个目标版本；自动发现不会替你选择最兼容的版本。

## 3. 编译

Intel classic 示例：

```bash
ewhb bootstrap --compiler-family intel \
  --shared-dir ~/wrf-hydro-packages \
  --prefix ~/wrfhydro-intel \
  --intel-home ~/intel/parallel_studio_xe_2018 \
  --jobs 4
```

GNU 示例：

```bash
ewhb bootstrap --compiler-family gnu \
  --shared-dir ~/wrf-hydro-packages \
  --prefix ~/wrfhydro-gnu \
  --jobs 4
```

选择一条路线执行。`--jobs` 控制依赖库的并行编译任务数，内存不足时可改为 `2`。
要先检查生成内容，在命令后加 `--dry-run`，再查看 `<prefix>/bootstrap_easy_wrf_hydro.sh`。
它会创建目录和脚本，但不会编译。完整参数见 [命令参考](cli.md)。

新编译器、依赖版本或路线应使用新的 `--prefix`。脚本用 `.done` 标记跳过已完成步骤，不能用相同目录直接切换版本。

## 4. 检查模型

以下以 Intel 为例；GNU 用户将前两行改为对应前缀和 `wrf_hydro_gnu_env.sh`：

```bash
EWHB_PREFIX="$HOME/wrfhydro-intel"
source "$EWHB_PREFIX/wrf_hydro_intel_env.sh"
test -x "$WRFHYDRO_ROOT/Run/wrf_hydro_NoahMP.exe"
ldd "$WRFHYDRO_ROOT/Run/wrf_hydro_NoahMP.exe"
nc-config --version
nf-config --version
```

`ldd` 中不应出现 `not found`。逐步日志在 `<prefix>/logs/`，源码位置会写入 `<prefix>/wrf_hydro_root.txt`。
命令退出成功及可执行文件存在只说明构建完成，真实运行还需要配套输入数据。

## 5. 可选运行官方示例

准备好匹配的 Croton NY 数据后，在第 3 步原命令后追加 `--run-example --example-config NWM --example-np 1`。

运行目录为 `<prefix>/runs/croton_NY_NWM`，日志为 `<prefix>/logs/run_croton_NWM.log`。
检查进程正常结束、日志无模型报错，以及运行目录中的预期输出文件。
当前记录只包含单进程示例；运行成功不等于已完成科学精度评估。

## 下次打开终端

运行模型前加载对应环境：

```bash
source ~/wrfhydro-intel/wrf_hydro_intel_env.sh
```

使用 `ewhb` 时，还需要激活安装它的 Python 环境：

```bash
source ~/easy_wrf-hydro_build/.venv/bin/activate
```

将路径替换为实际克隆位置。工具不修改 `~/.bashrc`；同一个终端只加载一条模型编译路线。
