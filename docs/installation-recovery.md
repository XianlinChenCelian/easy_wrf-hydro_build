# 安装前检查与失败后继续

请用普通 Linux 用户执行安装器。每个版本使用独立目录，优先选择 `~/ewhb/版本`。在 Windows 中先进入 WSL2 的 Linux 终端，再解压并安装所选架构的包。

## 先检查

```bash
python3 install.py ~/ewhb/5.4.0 --check-only
```

检查会验证架构、系统库、基础命令、文件完整性、目标目录写入/执行/符号链接能力和剩余空间，不安装依赖或模型。磁盘至少需有 4 GiB 可用空间，建议每套预留 6 GiB。

```bash
python3 install.py ~/ewhb/5.4.0 --run-example --jobs 4
```

运行中会显示当前阶段、日志位置，并在长时间编译时持续提示。`install.log` 保存详细记录，模型各阶段的日志在 `model/logs/`。

## 常见问题

| 提示 | 原因与下一步 |
| --- | --- |
| `E_ARCH` | 在 Linux 内执行 `uname -m`，重新选择 x86_64 或 aarch64 包。Windows 主机和 Linux 来宾可能不是同一架构。 |
| `E_ROOT` | 当前是 root 或使用了 sudo。切回普通用户，并安装在自己的主目录。WSL 默认进入 root 时先选择已有的普通 Linux 用户。 |
| `E_FILESYSTEM` | 目标是 Windows 共享盘、exFAT、网络共享或虚拟机共享目录。下载包可保存在那里，但安装目标应改为 Linux 主目录或 ext4 磁盘。 |
| `E_MOUNT` | 磁盘只读或禁止执行。换到可写且允许执行的 Linux 文件系统，或联系管理员调整此磁盘的策略。 |
| `E_PERMISSION` / `E_OWNER` | 目录不属于当前用户，或无法创建文件/符号链接。选一个自己拥有的新目录，不要用 sudo 安装或 chmod 777。 |
| `E_SPACE` | 可用空间不足。释放空间，或扩大 WSL/虚拟机的 Linux 磁盘。Windows 外层磁盘有空间不一定代表来宾磁盘有空间。 |
| `E_GLIBC` | 发行版系统库不满足要求。使用兼容发行版，不手工替换系统 glibc。 |
| `E_TOOL` | 缺少基础工具。根据提示安装该工具；没有管理员权限时联系管理员。模型工具链本身由离线包提供。 |
| `E_CHECKSUM` | 文件缺失、损坏或被改写。重新下载并在 Linux 中解压，不要修改校验清单。 |
| `E_BUSY` | 同一目录已有安装进程。等待其结束，或使用另一个目录。 |
| `E_EXISTING` / `E_BUNDLE` | 目录不是这个安装包创建的，或包的内容已改变。选择新目录，或使用原包继续原安装。 |
| `E_STAGE` | 安装、编译或算例失败。先读显示的日志；修复原因后使用安装器打印的续装命令。 |

WSL 的 Windows 文件权限仍受 Windows ACL 约束，`chmod 777` 不能保证解决问题。WSL2 的 `/mnt/c` 适合交换文件，默认安装目录应位于 Linux 主目录。安装包位于可读取但禁止执行的共享盘时，安装器会把已校验的环境安装器复制到目标目录后执行，不修改原包权限。

## 中断或失败后继续

```bash
python3 install.py ~/ewhb/5.4.0 --resume --run-example --jobs 4
```

也可以直接复制失败时打印的命令，其中会保留实际路径和选项。安装器用状态文件核对原包身份，恢复/补齐离线依赖，并利用构建阶段记录继续执行。不会自动删除整个目录或覆盖其他安装。同一目录仅允许一个安装进程。

先前没有状态文件的旧版安装器不支持此续装方式，应使用新目录。`--dry-run` 会恢复依赖并生成编译脚本；之后用 `--resume` 去掉 `--dry-run` 即可真正构建。

MPI 失败请查看 `model/logs/run_croton_NWM.log`。先以普通用户、单进程算例验证；如日志显示进程通信被限制，请检查本机防火墙、WSL/虚拟机网络策略或联系管理员。安装器不会关闭防火墙、修改系统权限或启用 root MPI。

参考：[Microsoft WSL 文件权限](https://learn.microsoft.com/en-us/windows/wsl/file-permissions)、[WSL 文件系统建议](https://learn.microsoft.com/en-us/windows/wsl/filesystems)。

## WSL 用户与诊断命令

在 Windows PowerShell 中查看发行版名称和 WSL 版本，再用已有普通 Linux 用户进入（以下 `Ubuntu` 和 `your_linux_user` 替换为实际名称）：

```powershell
wsl --list --verbose
wsl -d Ubuntu -u your_linux_user
```

如果没有普通账户，需先由该 Linux 环境的管理员创建账户。安装器不会自动创建用户或改变系统账户权限。

在 Linux 中查看安装日志：

```bash
tail -n 60 ~/ewhb/5.4.0/install.log
df -h ~/ewhb
```

若日志明确显示编译进程因内存不足被终止，释放内存或增加 WSL/虚拟机内存后，可以使用 `--resume --jobs 2` 降低编译并行度。续装命令仍使用原来的安装包与目录。
