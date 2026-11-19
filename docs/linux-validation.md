# Linux 安装与验证

Linux、WSL2 和 Linux 虚拟机按来宾系统的 CPU 架构选择构建路线。Ubuntu 24.04 ARM64 虚拟机与 QEMU 中的 x86_64 用户态均完成三个版本的离线安装和 Croton 运行。Windows WSL2 完成三个 GNU 版本的源码构建，其中 GNU 和 Intel Classic 的 5.1.2 完成 Croton 运行。[验证记录](verified-builds.md)

可以按[版本安装指南](versioned-install.md)从源码构建，或先[组装 GNU 离线包](release-bundles.md#gnu-离线包)再使用下文的安装器。

## GNU 离线包安装

安装器提供 `--check-only`、`--resume`、阶段日志和并发安装锁。先检查目标目录，再开始安装；详细步骤见[安装恢复指南](installation-recovery.md)。

- 包内附带 GNU 编译器、MPI、NetCDF-C、NetCDF-Fortran、HDF5、Make、binutils、Perl 等依赖，精确版本和构建号见包内 `manifest.json`。
- Linux 包依赖基线锁定为 glibc 2.28，安装入口会检查架构和 glibc。此要求来自软件包依赖，低版本发行版的运行验证仍需另做。
- 主机还需要 Python 3.9+、Bash、tar、gzip、sed、awk、find、ldd。这些基础工具不随当前包重复分发。
- WSL2 和 Linux 虚拟机用户在来宾系统的终端解压、安装。构建目录使用 Linux 文件系统，例如用户主目录，不建议在 `/mnt/c` 或虚拟机共享目录内编译。
- Windows x86_64 用户在 WSL2 内选择 Linux x86_64 包。先用 `uname -m` 查看来宾系统架构。

```bash
uname -m
python3 install.py /absolute/path/to/new-install --run-example --jobs 4
```

## 存储布局

虚拟机的系统和构建目录可保存在外置磁盘上的虚拟磁盘内。来宾系统使用 ext4 等支持 Unix 权限和符号链接的文件系统。Windows 用户可从共享盘读取归档，把构建输出放在 WSL2 的 Linux 家目录中。

## 验证范围

每个版本先验证源码编译与匹配 Croton 算例，再从各自独立的离线包恢复环境并重新编译运行。验收检查成功结束标记、168 个逐小时观测站输出、最终时刻 2011-09-02 00:00，以及最终 NetCDF 文件中的 `streamflow`。这些指标用来核对环境安装、模型启动、模拟时段与输出可读性。

具体完成记录见[已验证构建](verified-builds.md)。该记录按发行版、处理器架构和 MPI 环境标注实测范围。

参考：[Lima 虚拟机后端](https://lima-vm.io/docs/config/vmtype/)、[Microsoft 对 WSL1/WSL2 的比较](https://learn.microsoft.com/en-us/windows/wsl/compare-versions)。
