# Documentation

[项目首页](../README.md) · [English overview](../README_EN.md)

## 开始使用 / Get Started

先选择 [系统架构、编译器和模型版本](release-bundles.md)。个人 Intel 工具链的安装步骤见 [oneAPI 安装指南](oneapi-install.md)。

第一次使用建议按以下顺序阅读：

1. [快速开始](quickstart.md)：Python 环境、系统工具、编译和运行检查。
2. [源码清单 / Source archives](source-archives.md)：版本、官方来源和示例数据。
3. [完整构建流程 / Bootstrap](bootstrap.md)：英文构建说明、产物和重建行为。
4. [可运行示例 / Examples](../examples/README.md)：Intel 和 GNU 命令脚本。

- [WRF/WPS 扩展与课程路线](wrf-wps.md)：三组版本依据、可选编译与分阶段验收。
- [离线流域制备](domain-preparation.md)：共享静态数据、网格、河网、土壤和初始场。
- [离线气象驱动](forcing.md)：资料下载、单位转换、时间和格网检查及运行目录。

## 兼容性和排查 / Compatibility

- [验证记录](verified-builds.md)：已实际运行和仅完成静态检查的组合。
- [Intel 编译器矩阵](intel-compiler-matrix.md)：classic、oneAPI 和 ifx 的边界。
- [故障排查](troubleshooting.md)：MPI、NetCDF 和环境路径问题。
- [命令参考](cli.md)：`bootstrap`、`compile`、`doctor`、`write-env`、`init-case`。

## 参与维护 / Development

- [仓库结构](repository-layout.md)：代码、文档、示例和图片的职责。
- [贡献指南](../CONTRIBUTING.md) 与 [隔离完整测试](isolated-testing.md)。
- [路线图](roadmap.md)、[变更记录](../CHANGELOG.md) 和 [发布说明](github-publishing.md)。
- [图片源文件与设计说明](assets/README.md)。

## 附录 / Appendix

- [空白 Windows 配置](blank-windows.md)：辅助资料；主流程从已有 Linux 环境开始。
