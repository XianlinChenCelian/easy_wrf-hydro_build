# 在自己的电脑上安装 Intel oneAPI

在 x86_64 Linux、WSL2 或 Linux 虚拟机中，使用 Intel 的 Linux 工具链。使用 WSL2 时，在 Ubuntu 终端安装，把构建目录放在 Linux 家目录。超算用户加载站点提供的编译器与 MPI，然后运行 `bash install.sh /absolute/new-prefix --site-toolchain ifort`。

## Intel Classic

WSL2 实测组合为 oneAPI 2023.2.4（`ifort`、`icc` 和 `icpc` 2021.10.0）与 Intel MPI 2021.10.0（`mpiifort`）。安装时选择 Fortran Classic、C/C++ Classic 和 MPI 开发组件。[Intel 旧版本获取说明](https://www.intel.com/content/www/us/en/developer/articles/troubleshooting/older-version-product.html)

使用 Intel APT 源时，先用 `apt-cache madison` 查询 `intel-oneapi-compiler-fortran`、`intel-oneapi-compiler-dpcpp-cpp-and-cpp-classic`、`intel-oneapi-mpi-devel` 的可用版本，再指定仓库返回的完整版本号安装。WSL2 实测的 MPI 包版本为 `2021.10.0-49371`。使用独立的 WSL 发行版可以保留电脑上其他 oneAPI 版本的安装。

有 Classic 离线安装器时，在对应的源码配方目录运行以下命令。将 `SHA256` 换成对应安装器的校验值。

```bash
bash install-oneapi.sh /path/to/intel-offline.sh SHA256 "$HOME/ewhb-toolchains/oneapi" --accept-eula ifort
bash install.sh "$HOME/ewhb/linux-x86_64/intel/5.4.0" /path/printed/by/installer ifort
```

载入工具链后，用 `command -v ifort icc mpiifort` 检查命令。使用 Intel APT 安装时，通常从 `/opt/intel/oneapi/setvars.sh` 加载环境。

## ifx 预览

使用 `ifx`、`icx` 和 `mpiifx`，并准备由同一套工具链编译的 NetCDF-C 和 NetCDF-Fortran。源码配方中的 HDF5 1.12.0 依赖栈使用 Intel Classic。已有 ifx 库时，可通过 `ewhb bootstrap --compiler-option ifx --netcdf /path/to/ifx-netcdf …` 选择它们，或给源码配方设置 `EWHB_NETCDF`。WSL2 实测记录见[验证记录](verified-builds.md)。

```bash
EWHB_NETCDF=/path/to/ifx-netcdf \
  bash install.sh "$HOME/ewhb/linux-x86_64/intel/5.4.0-ifx" /path/to/oneapi ifx
```

Apple Silicon macOS 和 Linux ARM64 使用 GNU 工具链。需要 Intel 构建时，使用 x86_64 Linux 或超算。
