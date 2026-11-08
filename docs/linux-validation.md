# Linux 安装与验证

Linux、WSL2 和 Linux 虚拟机使用按处理器架构区分的同一安装包。当前有 `linux-aarch64` 和 `linux-x86_64` 预览包。x86_64 三版本已在 QEMU 用户态模拟中完成离线安装与 Croton 验证；Windows WSL2 实机仍未验证。Apple Silicon Mac 内的 ARM64 Linux 测试不能代替 x86_64 测试。

## 安装边界

安装器提供 `--check-only`、`--resume`、阶段日志和并发安装锁。先检查目标目录，再开始安装；详细步骤见[安装恢复指南](installation-recovery.md)。

- 当前验证系统为 Ubuntu 24.04 ARM64，运行于 macOS 的 Lima/VZ 虚拟机。
- 包内附带 GNU 编译器、MPI、NetCDF-C、NetCDF-Fortran、HDF5、Make、binutils、Perl 等依赖，精确版本和构建号见包内 `manifest.json`。
- Linux 包依赖基线锁定为 glibc 2.28，安装入口会检查架构和 glibc。此要求来自软件包依赖，低版本发行版的运行验证仍需另做。
- 主机还需要 Python 3.9+、Bash、tar、gzip、sed、awk、find、ldd。这些基础工具不随当前包重复分发。
- WSL2 和 Linux 虚拟机用户在来宾系统的终端解压、安装。构建目录使用 Linux 文件系统，例如用户主目录，不建议在 `/mnt/c` 或虚拟机共享目录内编译。
- Windows 原生终端和 WSL1 未验证。Windows 常见 x86_64 电脑不可使用 ARM64 包。

```bash
uname -m
python3 install.py /absolute/path/to/new-install --run-example --jobs 4
```

## 存储布局

开发机器的移动硬盘为 exFAT。虚拟机文件存放在移动硬盘上的 APFS 稀疏映像内，Linux 系统和编译目录则使用映像中的 ext4 虚拟磁盘。这样保留 Unix 权限、链接和编译性能所需的文件系统语义，不改动外置盘现有分区。

映像上限 48 GiB，Linux 系统盘虚拟容量 40 GiB，实际按需分配；虚拟机使用 4 核 CPU、4 GiB 内存。Linux 环境、依赖缓存、构建输出和安装包都在移动硬盘。完成验证后停止虚拟机以释放运行内存。

移动硬盘的 `linux-host/linux.sh` 提供 `start`、`shell`、`stop`、`eject`、`status` 操作。拔盘前使用 `eject` 停止虚拟机并卸载映像，然后从 macOS 弹出物理硬盘。

## 验证范围

每个版本先验证源码编译与匹配 Croton 算例，再从各自独立的离线包恢复环境并重新编译运行。验收检查成功结束标记、168 个逐小时观测站输出、最终时刻 2011-09-02 00:00，以及最终 NetCDF 文件中的 `streamflow`。这属于安装和运行验证，不能替代水文精度评价。

具体完成记录见[已验证构建](verified-builds.md)。同一套 Linux 包对 WSL2 和其他虚拟机的兼容性有共同基础，但发行版、架构和 MPI 进程通信仍需匹配；未实测的平台不标为已验证。

参考：[Lima 虚拟机后端](https://lima-vm.io/docs/config/vmtype/)、[Microsoft 对 WSL1/WSL2 的比较](https://learn.microsoft.com/en-us/windows/wsl/compare-versions)。
