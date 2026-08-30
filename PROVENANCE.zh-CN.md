# 发布来源说明

[English](PROVENANCE.md)

Manuscript Review Studio 是经过本地审计的 Manuscript Revision Closure `0.2.1` Skill 与 standalone `0.6.4` 运行层的公开多模式封装版。更小的纯 Skill 版本单独维护在 [`manuscript-revision-closure`](https://github.com/lensback940701/manuscript-revision-closure)。

面向 Codex 的 Skill 封装结构和部分架构边界参考了官方
[`openai/codex`](https://github.com/openai/codex) 仓库的 commit
[`d5caceccb1ee5bf94c081b995575ce4860e0912b`](https://github.com/openai/codex/commit/d5caceccb1ee5bf94c081b995575ce4860e0912b)。
本项目由社区独立维护，不代表 OpenAI 官方产品或背书；源码树及 EXE 均未复制 Codex 仓库中的源文件。

公开仓库包含 Skill 指令、界面元数据、standalone 运行层、契约辅助程序、标准事项代码说明、合成测试材料、回归测试和四张由作者提供的说明插图。它不包含真实稿件、项目专用示例、证据包、内部 failure-first/build 回执、本地绝对路径、凭据、本地画图提示词或未采用的图片版本。

源码仓库不提交第三方数据集、稿件内容、外部模型输出或本地构建的 EXE；standalone 构建可能捆绑的依赖见[第三方说明](THIRD_PARTY_NOTICES.md)。软件与文档按照 Apache License 2.0 发布；仓库中的四张说明插图已在公开前单独核验。
