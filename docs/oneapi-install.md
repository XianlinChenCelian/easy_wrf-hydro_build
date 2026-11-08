# 在自己的电脑上安装 Intel oneAPI

超算用户按站点文档加载管理员提供的 Intel 工具链，然后使用 `bash install.sh /absolute/new-prefix --site-toolchain ifort`。在自己的 x86_64 Linux 或 Windows WSL2 上，可把 Intel 的 Linux 版 oneAPI 安装到个人目录，再从源码配方构建 WRF-Hydro。WSL2 的安装与编译应在 Linux 终端和 Linux 文件系统内完成。[Intel 的 WSL2 支持说明](https://www.intel.com/content/www/us/en/developer/articles/release-notes/oneapi-toolkit/2026.html)

1. 在 Linux 中确认 `uname -m` 为 `x86_64`，并按 Intel 的系统要求准备 GNU 链接工具、Bash 等系统依赖。模型配方还需要 Python 3.9+、make 和标准 Linux 工具，5.4.0 需要 CMake 3.12+。[Intel 系统要求](https://www.intel.com/content/www/us/en/developer/articles/release-notes/fortran-compiler/2026.html)
2. 从 Intel 下载与发行版匹配的 Linux x86_64 离线安装器。选择包含 Intel C/C++、Intel Fortran 和 Intel MPI 开发组件的 oneAPI Toolkit。当前工具链对应 `icx`、`ifx`、`mpiifx`。[Intel 官方下载](https://www.intel.com/content/www/us/en/developer/tools/oneapi/oneapi-toolkit-download.html?distributions=webdownload&operatingsystem=linux&options=offline)
3. 阅读 Intel 许可后，以普通用户运行配方内的 `install-oneapi.sh`。使用官方提供的 SHA256（如有）。也可在下载后记录本地 SHA256，用来核验随后复制到离线机器的文件。自行计算的值只核对复制完整性。

```bash
bash install-oneapi.sh /path/to/intel-offline.sh SHA256 "$HOME/ewhb-toolchains/oneapi" --accept-eula ifx
```

安装脚本用 Intel 官方安装器在指定目录创建独立实例，并检查 `ifx`、`icx` 和 `mpiifx`。安装成功后会打印应传给模型安装器的 `INTEL_HOME`。这个路径包含 `setvars.sh` 或 `oneapi-vars.sh`。如果希望只安装部分组件，可先执行 `sh intel-offline.sh -a --list-components`，再以 `EWHB_ONEAPI_COMPONENTS` 提供冒号分隔的组件 ID。[Intel 安装器参数](https://www.intel.com/content/www/us/en/docs/oneapi-toolkit/installation-guide-linux/latest/command-line-options.html)

```bash
bash install.sh "$HOME/ewhb/linux-x86_64/intel/5.4.0" /path/printed/by/installer ifx
```

三个版本均提供 `ifx` 预览选项。5.1.2 和 5.2.0 使用上游的 Intel Make 配置，实际编译由 `mpiifx` 驱动。已有经典 Intel 工具链可显式选择 `ifort`，并提供配套 `icc` 与 `mpiifort`。新版 oneAPI 使用 `ifx`，旧版 `ifort` 的官方获取受版本和账号条件限制。[Intel 旧版本获取说明](https://www.intel.com/content/www/us/en/developer/articles/troubleshooting/older-version-product.html)

Apple Silicon macOS 与 Linux ARM64 使用 GNU 包，Intel 路线可在远程 x86_64 Linux 上执行。Intel 已从 oneAPI 2024.0 移除经典 Fortran 的 macOS 支持。Windows 上选择 WSL2 或 x86_64 Linux 虚拟机，在来宾系统内安装 Linux 版工具链。[Intel macOS 支持变更](https://www.intel.com/content/www/us/en/developer/articles/release-notes/fortran-compiler/2024.html)
