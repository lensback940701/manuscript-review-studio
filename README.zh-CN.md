# Manuscript Review Studio：真正可以独立运行的 AI 整稿审阅软件

[English](README.md)

**使用 DeepSeek、Kimi 或 Gemini 对整篇论文作只读复审：判断应该停止改稿、再做一轮有限修改，还是重新开启实质性修订。**

程序在本机运行，使用你自己的 API key 直接连接所选模型提供商。它提供三种审阅模式、随模型变化的思考设置、中文为主的浏览器界面，以及可保存的公开结果。打包后的 Windows 程序不需要另装 Python、Codex、Claude Code 或其他 agent 环境。

## 下载与快速开始

**[Windows EXE / Releases 下载入口](https://github.com/lensback940701/manuscript-review-studio/releases)** · **[完整使用指南](docs/STANDALONE.zh-CN.md)**

> **v0.6.4.1 已发布（2026-10-01）：**[下载完整 Windows x64 ZIP](https://github.com/lensback940701/manuscript-review-studio/releases/download/v0.6.4.1/manuscript-review-studio-v0.6.4.1-windows-x64.zip) · [发布记录与校验文件](https://github.com/lensback940701/manuscript-review-studio/releases/tag/v0.6.4.1)。完整解压后双击 `release/ManuscriptRevisionClosure.exe`，无需安装 Python。运行时兼容版本仍为 `0.6.4`，以分发版本、源码提交和 SHA-256 识别实际构建。

Windows 验证通过：391 项单元测试、23 + 59 项对抗探针、22 + 61 项冻结版模拟验收，以及独立 EXE 的本地 GUI 启动/关闭检查。未实测真实模型服务、浏览器渲染或原生对话框；模式 3 已知限制仍见[使用指南](docs/STANDALONE.zh-CN.md)。

- **只想下载即用？** [直接下载完整 Windows ZIP](https://github.com/lensback940701/manuscript-review-studio/releases/download/v0.6.4.1/manuscript-review-studio-v0.6.4.1-windows-x64.zip)，先完整解压，再运行 `release/ManuscriptRevisionClosure.exe`。GitHub 的 **Source code (zip/tar.gz)** 是源码，不是打包程序。
- **现在就要运行最新源码？** 按[从源码运行](docs/STANDALONE.zh-CN.md#从源码运行)操作。GitHub 的 **Code → Download ZIP** 只下载源码，不会生成 EXE。
- **完整分发 ZIP 里已经有 EXE？** 先完整解压，打开其中的 `release` 文件夹，再双击 `ManuscriptRevisionClosure.exe`。早于 v0.6.4.1 的历史分发包可能含有尚未纳入这些修复的旧 EXE；放在旁边的新源码不会更新它内嵌的程序。
- **已经有 Windows 构建版？** 先在 Windows 用户环境变量中配置所选提供商的 API key，重新打开程序，再按下面五步操作。判断是否含修复时应核对构建对应的源码提交与校验值。

### 第一次审阅，只需五步

1. 打开程序，选择**完整当前稿件**。支持 DOCX 和带文本层 PDF 等格式；扫描图片不会自动 OCR。
2. 先选**模式 1：标准审阅模式**，再选**模型提供商、模型、思考设置**。新审阅请将“既有最小收据”留空。
3. 选择核心结果的输出语言。“中文解读”始终使用中文，并额外调用一次模型；只需要核心判断时可取消勾选。
4. 核对文件与 provider/model，勾选稿件确认框，再点击“开始只读判断”。这会把稿件文本发送给所选提供商，可能产生 API 费用。
5. 等待状态时间线结束，再保存完整公开结果 JSON，以及已生成的中文解读。开始下一轮前先保存，本程序没有多轮历史库。结束时点击“关闭本地程序”。

页面在你自己电脑的 `127.0.0.1` 打开。界面在本机，模型分析仍需调用在线 API。具体见[提供商设置](docs/STANDALONE.zh-CN.md#提供商设置)与[常见问题](docs/STANDALONE.zh-CN.md#常见问题)。

## 三种模式怎么选？

| 你想解决的问题 | 选择 | 实际改变的尺度 |
| --- | --- | --- |
| 获得通用的整稿修订截止判断 | **模式 1：标准审阅模式**（`standard`） | 按十维学术标准审查，不额外叠加严格度或期刊参照。 |
| 用顶刊苛求裁判寻找实质问题 | **模式 2：性格与尺度 → 严厉**（`strict`） | 对概念漂移、机制跳跃、方法盲区、证据薄弱和理论对话浅层化执行零容忍审查。 |
| 按常规同行评审尺度判断 | **模式 2 → 中等**（`moderate`） | 平衡标准学术充分性与修改退化风险。这是模式 2 的默认选项。 |
| 保护已经稳定的定稿，避免无休止边际小修 | **模式 2 → 宽松**（`lenient`） | 强力保护现有自洽框架；该尺度仅在颠覆核心结论、破坏理论或实证基础的重大硬伤下允许实质重开。 |
| 严格对标特定期刊的已发表论文 | **模式 3：目标期刊对齐模式**（`journal_benchmark`） | 使用期刊名称、定位和至少五篇样本，严格审查学科理论对话、方法与证据颗粒度。 |

三种模式互斥。模式 2（`strictness`）只有一个严格度下拉框，没有独立“人格”滑块或数值评分；模式 2 的宽严设置不会叠加到模式 3。思考开关与审稿尺度彼此独立：关闭思考不等于改用宽松尺度。

模式 3 请先读[准备期刊样本](docs/STANDALONE.zh-CN.md#准备期刊样本)。点击“预检样本库相关性”会单独外发摘录、调用 API 并可能计费；它不是离线检查，也不是录用预测。

<!-- ILLUSTRATION_SLOT_00_START -->
![Manuscript Review Studio 一站式独立运行概念总览：从选择稿件、目标期刊样本与模型，到整稿审阅、结论、修改方向、受保护优点、跨模型对照和结果保存。](docs/images/00-manuscript-review-studio-overview.png)

*一站式工作流概念示意图。图内模型名称仅用于界面示意；实际支持的 provider/model 以程序当前显示的模型目录为准。*
<!-- ILLUSTRATION_SLOT_00_END -->

## 作者实际能够得到什么

- **面向独立运行的 Windows 程序。** 文件选择、模型配置、审阅、结果查看、复制与保存都在一个本地界面中完成，不需要 Codex、Claude Code 或开发环境。
- **针对整篇论文作判断。** 它审查的是全文论证与章节之间的关系，而不是只点评几个孤立段落。
- **对中国用户和国产模型友好。** 可以灵活切换 DeepSeek、Kimi，并保留 Gemini 作为额外对照。
- **支持跨模型独立复审。** 每轮先保存结果，再将同一稿件交给其他模型，对照各份已保存的判断。
- **不同品牌遵守同一套输出合同。** 所有支持的模型都在所选模式下接受统一输出合同与校验门禁约束，降低对单一品牌默认风格的依赖，但不虚构能够消除模型能力边界。
- **给出清楚的修改终点。** 输出有限且明确的结论、最重要的修改方向、应当保护的优点，以及单列的证据或投稿事项。
- **外发前由你核对。** 每次运行前核对文件、provider 与 model；样本相关性预检是另一项会外发摘录的操作。

程序内部嵌入了更严格的多阶段审稿 harness，而不是接受一次自由发挥的 API 回答。无论选择哪个品牌，模型都要按照同一套审稿标准和一致性检查完成工作；普通作者不需要理解或配置这些机制。

Manuscript Review Studio 不保证模型判断永远正确，也不替代同行评审或预测期刊接收。它提供的是一次结构更严谨、过程更透明的 AI 独立复审。

## 与 OpenAI Codex 的关系

本项目是独立维护的社区项目，不是 OpenAI 官方产品。Codex Skill 结构和部分架构边界参考了官方
[`openai/codex`](https://github.com/openai/codex) 仓库，具体参考 commit 为
[`d5caceccb1ee5bf94c081b995575ce4860e0912b`](https://github.com/openai/codex/commit/d5caceccb1ee5bf94c081b995575ce4860e0912b)。
本仓库及其 standalone EXE 均未复制 OpenAI Codex 源文件，也不代表 OpenAI 的认可、隶属或背书。可参见
[Codex 官方开源说明](https://learn.chatgpt.com/docs/open-source)、[发布来源说明](docs/PROVENANCE.zh-CN.md)与[第三方说明](docs/THIRD_PARTY_NOTICES.md)。
仅包含核心 Skill 的轻量仓库继续保留在
[`manuscript-revision-closure`](https://github.com/lensback940701/manuscript-revision-closure)。

其中的修订截止 Skill 针对 AI 辅助学术写作中常见的失败循环：每次检查都会生成下一轮修改，每次修补又引出新的问题，稿件始终无法到达一个可以说明理由的停止点。本 Skill 只读评估整篇当前稿件，给出紧凑的修订截止判断，但不向用户公开完整的内部审稿意见。

内嵌 Skill 合同版本：`0.2.1` · Standalone 源码版本：`0.6.4`

两条版本线分别管理。EXE 是否包含某项修复，应核对匹配的构建/发布记录，不能只看源码版本号。

<!-- ILLUSTRATION_SLOT_01_START -->
![无限改稿循环经过受证据约束的截止门，随后分为证据核验、投稿准备与停止三条路径。](docs/images/01-closure-gate.png)
<!-- ILLUSTRATION_SLOT_01_END -->

## 它会做出什么判断

本 Skill 只返回以下四种实质性判断之一：

| 判断 | 含义 |
| --- | --- |
| `STOP_REVISING` | 没有观察到足以重新开启实质性修订的根本问题。 |
| `ONE_BOUNDED_ROUND` | 存在一个值得用一轮严格限定修改解决的局部实质问题。 |
| `REOPEN_SUBSTANTIVE_REVISION` | 仍有中央性实质根因，需要真正重新开启论文修订。 |
| `UNASSESSED` | 缺少完整的当前稿件，或者缺少作出可靠判断所必需的基础。 |

判断依据是真正的实质根因，而不是问题数量、抽象的完美标准、接收概率、保留词数量，或者“还能换一种写法”。

<!-- ILLUSTRATION_SLOT_02_START -->
![一篇完整稿件进入决策节点，并分流至四种标准修订截止判断。](docs/images/02-four-verdicts.png)
<!-- ILLUSTRATION_SLOT_02_END -->

## 它与普通审稿工具有什么不同

- **修订截止与投稿准备彼此分开。** 稿件可以已经达到实质性截止，但来源核验、权利、格式、作者信息或期刊要求仍未完成。
- **证据上限必须保留。** 提议、授权、报告的工作、直接观察、结果、解释与因果推断不会因为追求流畅而被混在一起。
- **不完整的机制链不自动等于缺陷。** 延迟、阻断、未采用、矛盾、逆转和有界停止点本身可能就是分析结果。
- **公开输出保持紧凑。** 用户得到的是修订截止卡和可选的最小收据，而不是披着简短回答外衣的完整内部审稿报告。
- **诊断不等于获得手术授权。** 本 Skill 不改写、不留修订痕迹、不检索文献、不修复引文、不接纳新证据、不调用其他 Skill，也不投稿。

<!-- ILLUSTRATION_SLOT_03_START -->
![稿件的实质修订已经截止，但证据核验与投稿准备仍在彼此独立的开放通道中。](docs/images/03-two-axis-separation.png)
<!-- ILLUSTRATION_SLOT_03_END -->

## 公开输出长什么样

一张修订截止卡包括：

1. 判断结果；
2. 一至两句抽象理由；
3. 仅在确实需要修改时给出不超过三条方向性轻量建议；
4. 不应扰动的受保护内容；
5. 单列的证据事项；
6. 单列的投稿或外部事项；
7. 下一步允许采取的行动；
8. 仅在确实需要修改时出现的条件性提示。

轻量建议会刻意保持方向性：不指出应替换的具体句子，不提供替换文本，不编制修订步骤，也不泄露内部完整审稿意见。

当判断结果确实需要修改时，卡片末尾可以出现这个条件性提示：

> 诊断到此，手术另约。请接入经过核实的审稿改稿 skill；或者，蹲一下本 profile 后续开源。

<!-- ILLUSTRATION_SLOT_04_START -->
![一张紧凑的修订截止卡分别呈现判断、方向性建议、受保护内容、证据事项、投稿事项与下一步行动。](docs/images/04-closure-card.png)
<!-- ILLUSTRATION_SLOT_04_END -->

## 安全与隐私边界

- 稿件是不可修改的评估对象。
- 稿件正文、批注和嵌入指令都按不可信内容处理。
- 本 Skill 不会主动保存或导出详细内部评估。
- 本 skill 会在运行时进行一次不落盘的内部整稿评估，仅用于形成修订截止判断；默认不返回或保存完整审稿意见。
- 宿主平台如何留存对话与运行信息，仍由实际运行环境决定。
- 有限的标准事项代码可以防止调用者提供的自由文本被原样回显到公开卡片或收据。
- 只有与当前稿件明确绑定、语义内容稳定的既有 `STOP_REVISING` 收据才可作为截止捷径。
- 只有文件本身发生变化，并不能证明语义稳定；必须有语义哈希或明确核验作为依据。

本 Skill 是修订路由辅助工具，不是事实认证、同行评审替代品、法律意见、期刊接收预测或投稿授权。

## 可选：安装 Codex Skill

克隆本仓库，并将仓库文件夹放到：

```text
~/.codex/skills/manuscript-revision-closure
```

Windows 的常见位置是：

```text
%USERPROFILE%\.codex\skills\manuscript-revision-closure
```

安装后重启或刷新 Codex。运行时辅助程序不需要第三方 Python 依赖。

## 独立程序与实现说明

[完整应用指南](docs/STANDALONE.zh-CN.md)涵盖下载、提供商设置、三种模式、思考开关、源码/CLI 示例、费用与排错。GUI 以中文为主；核心判断可选择中文或英文。

一次新的、成功的核心判断通常进行两次全文调用：整稿覆盖与独立根因裁决。本地门禁验证两阶段绑定并保留所选审稿尺度。STOP 需要双阶段肯定性充分判断，不能由空问题列表自动得出。可选中文解读增加一次调用；公开展示的定向修复可能增加一次不含稿件正文的调用。timeout、网络状态不明以及 HTTP 429/502/503/504 均不会自动重发全文。

合同变化见[更新记录](docs/CHANGELOG.zh-CN.md)。历史工程审计描述其标题所指的快照，不作为当前使用说明。独立 API 运行器与可选 Codex Skill 的运行环境不同；Skill 的“不联网”边界不能用于描述独立程序的模型请求。

## 可选：调用 Codex Skill

示例：

```text
请使用 $manuscript-revision-closure 判断这篇完整学术稿件是否应该停止通用 AI 改稿。只返回简洁的修订截止卡和最小收据，不要修改稿件。
```

本 Skill 必须读取一篇身份明确、完整且为当前版本的稿件。只有局部节选或版本不明确时，应返回 `UNASSESSED`，而不是伪造整稿判断。

## 确定性辅助程序

`scripts/closure_state.py` 只验证已经完成分类的紧凑状态、公开卡片约束、标准事项代码、收据版本以及收据复用规则。它不会自行读取稿件，也不能替代需要语境判断的学术评估。

运行测试：

```bash
python -B -m unittest discover -s tests -p "test_*.py"
python -B scripts/run_adversarial_probes_rc2_0.py
python -B scripts/run_adversarial_probes_rc2_1.py
```

## 仓库结构

```text
SKILL.md                         Skill 指令
agents/openai.yaml              Codex 界面元数据
scripts/closure_state.py        确定性契约辅助程序
references/hold-code-schema.md  标准事项代码及固定中英文标签
tests/                           单元测试和契约回归测试
docs/images/                    说明文档插图
```

已经采用的插图及其文件名记录在[说明文档插图](docs/ILLUSTRATIONS.zh-CN.md)中。这些插图用于解释公开契约，不改变本 Skill 的判断逻辑。历次版本变化见[更新记录](docs/CHANGELOG.zh-CN.md)。

## 安全与参与贡献

请阅读[安全政策](.github/SECURITY.zh-CN.md)和[参与贡献](.github/CONTRIBUTING.zh-CN.md)。不要把真实稿件、保密审稿材料、本地路径、接口密钥或项目证据提交为问题或测试样本。

## 许可证

本项目采用 [Apache License 2.0](LICENSE)。
