# Windows 发布验证

[English](WINDOWS_RELEASE.md) · [应用使用指南](STANDALONE.zh-CN.md)

## 下载与识别构建

在 [GitHub Releases](https://github.com/lensback940701/manuscript-review-studio/releases)
发布资源中下载 `manuscript-review-studio-v0.6.4.1-windows-x64.zip`，完整解压后打开
`release/ManuscriptRevisionClosure.exe`，无需安装 Python。完整 ZIP 同时包含源码、
测试、双语指南、许可声明与这一份 EXE 的构建/验收收据；单独提供的 EXE 也可独立运行。

应用兼容版本仍为 **0.6.4**。分发版本 **v0.6.4.1**、源码提交与二进制 SHA-256
共同标识本次修复后的重建。`BUILD_RECEIPT.json` 记录实际安装的 Python/依赖版本
和源码提交；`VALIDATION_RECEIPT.json` 将测试绑定到准确的 EXE。`SHA256SUMS`
覆盖下载附件；ZIP 内的 `DISTRIBUTION_MANIFEST.json` 覆盖除清单自身外的每个文件。
GitHub 自动生成的 **Source code (zip/tar.gz)** 不含 EXE。

## Windows 流程实际检查什么

- Windows x64 源码单元测试（至少保留的 391 项）及 23 + 59 项对抗性探针
- 按固定依赖生成全新的 PyInstaller 单文件 EXE，核对 PE/x64 文件头、源码提交和实际依赖版本
- 仅把 EXE 复制到另一个空临时目录，清除环境中的 Python/源码路径并运行冻结版版本命令
- 从该 EXE 启动本地 GUI 服务，检查页面与三种模式控件、带 token 的就绪状态、
  未授权请求拒绝、安全关闭、退出码与端口释放
- 既有冻结版 CLI/GUI 验收与多模式合成接口验收，包括思考开关、有限修改/重开/停止裁决、
  非法合同拒绝和上下文预算边界
- 生成全新收据与白名单分发 ZIP，核对逐文件哈希及 ZIP 完整性；不沿用旧 EXE 或旧收据，
  不打包构建目录、虚拟环境与真实稿件

全部模型返回均来自本机模拟服务。这些验证不能证明真实提供商可用性、模型质量或科学正确性。
无头 CI 未实测浏览器渲染、原生文件对话框或截图。EXE 未签名；若 Windows SmartScreen
提示风险，请遵循组织认可的软件信任流程，不要关闭系统防护。使用指南中列明的模式 3
样本/相关性限制仍然适用。

## 维护者构建与发布

工作流位于 `.github/workflows/windows-release.yml`，使用 `windows-2022` 与
Python 3.12 x64；官方 Action 固定到已核验的提交。构建任务只有 `contents: read`，
checkout 不保存凭据。只有隔离的发布任务有 `contents: write`；它不会执行源码或下载
的 EXE，只使用 GitHub 临时内置令牌，不需要 PAT 或新增仓库 secret。

仅向明确的 `release/windows-v0.6.4.1` 分支推送，或在 `main`/该发布分支手动启动并
勾选 **publish**，才会发布。手动运行默认只构建和测试；普通推送和 PR 不会发布。
固定标签为 `v0.6.4.1`，指向测试对应的准确提交，不覆盖已有 Release 或附件。
发布新版本需要显式审查并更新工作流。

通过连接器启动时，先从旧源码提交创建该专用分支，再把它推进到已审查的工作流提交，
由这次分支推送触发。只把工作流放到 `main` 不会自动发布。必须确认发布任务成功且
实际附件存在后，才能宣布可下载。

本地检查需从 Windows 的干净 Git 克隆目录开始：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -B scripts/windows_release.py source-tests
.\build_exe.ps1
.\.venv\Scripts\python.exe -B scripts/windows_release.py validate-package
```

待发布文件位于 `.build/publish`。测试、构建与打包必须针对同一干净提交。
重建时使用新的克隆目录，不能让历史产物认证另一份 EXE。
