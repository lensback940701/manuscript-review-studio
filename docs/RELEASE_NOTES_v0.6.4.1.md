# Windows x64 release v0.6.4.1

[Download the complete Windows x64 ZIP](https://github.com/lensback940701/manuscript-review-studio/releases/download/v0.6.4.1/manuscript-review-studio-v0.6.4.1-windows-x64.zip).
Extract all files and double-click `release/ManuscriptRevisionClosure.exe`. No Python installation is required. The standalone EXE asset can also run by itself.

Source commit: `afb85398ac0647d5b21cfc1a2626b5f5c54cd3ef`. Runtime compatibility version: `0.6.4`. Distribution revision: `v0.6.4.1`.

Windows validation passed: 391 unit tests, 23 + 59 adversarial probes, 22 retained frozen acceptance cases and 61 multimode frozen cases. The copied EXE also passed standalone startup, redirected Chinese JSON output, authenticated GUI ready status, all three mode controls, unauthorized-request rejection, safe shutdown and port-release checks. See `VALIDATION_RECEIPT.json` for details.

EXE SHA-256: `ef178f896755e6a8fa7bacb63423a348620c851d0a031a85f7ab810340da9f39`.

Full ZIP SHA-256: `1a7b2d9badd4ac98832ca07b7e79f228ae2ce454550239d5d6e51fac50215690`.

All provider responses were synthetic loopback mocks. No live providers or real manuscripts were used. Headless CI did not validate interactive browser rendering or native file dialogs. This executable is unsigned; follow your organization's software-trust policy. GitHub's automatically generated **Source code (zip/tar.gz)** does not contain the EXE.

## Release-note correction

The original downloadable `RELEASE_NOTES.md` contains an incorrect Chinese phrase claiming a journal sample-gate fix. That gate was **not** fixed by this release. This release includes the Mode 2 contract repairs and the frozen Windows UTF-8 output fix, with all three implemented modes tested. Mode 3's known sample-ingestion fallback, relevance-gate and rubric limitations still apply; consult the [current application guide](https://github.com/lensback940701/manuscript-review-studio/blob/main/docs/STANDALONE.md#prepare-journal-samples).

This correction changes only this release page's description. The original EXE, ZIP, receipts, checksum files and downloadable notes remain unchanged so their identities stay verifiable. The bundled application guides describe the limitations correctly. The bundled source copy of the release-note generator retains the original wording; the current repository generator has been corrected.

## 中文下载与验证说明

下载上方完整 Windows ZIP，全部解压后双击 `release/ManuscriptRevisionClosure.exe`，无需安装 Python。双语指南位于 `docs/STANDALONE.md` 与 `docs/STANDALONE.zh-CN.md`。

本次通过了 Windows 上的 391 项单元测试、23 + 59 项对抗性探针、22 项既有冻结版验收、61 项多模式冻结版验收，以及独立 EXE 启动、中文重定向输出、本地 GUI 状态和安全关闭检查。模型测试使用本机模拟接口，不代表真实提供商或模型质量实测；无头 CI 未检查浏览器渲染与原生文件对话框。程序未签名，可能触发 Windows SmartScreen 提示。

**勘误：**下载附件 `RELEASE_NOTES.md` 中声称已修复期刊样本门槛的中文表述不准确。本版本修复的是模式 2 合同及冻结版 Windows UTF-8 输出问题，**没有修复模式 3 的样本门槛/相关性/独立 rubric 提取限制**。请以[当前中文使用指南](https://github.com/lensback940701/manuscript-review-studio/blob/main/docs/STANDALONE.zh-CN.md)为准。此次仅更正发布页说明，所有原始二进制、ZIP、收据、校验文件及原下载说明附件均保持不变；ZIP 内的使用指南本身已准确列出限制。
