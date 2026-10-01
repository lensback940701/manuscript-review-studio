# Manuscript Review Studio：独立程序使用指南

[English](STANDALONE.md) · [项目首页](../README.zh-CN.md)

本指南对应当前 Standalone 源码 `0.6.4`，内嵌 Skill 合同为 `0.2.1`。程序窗口与可执行文件沿用 **Manuscript Revision Closure** 名称。界面以中文为主，核心结果可选择中文或英文；程序不会改写稿件。

## 下载与打开

**[Windows 下载 / GitHub Releases](https://github.com/lensback940701/manuscript-review-studio/releases)**

**2026-10-01 核实的状态：**本仓库尚无已发布的 GitHub Release 或 EXE 附件；当前修复在源码中。原完整分发包内的旧 EXE 早于本次模式/响应处理修复；仅显示 `0.6.4` 不能证明它已更新。把新 `.py` 文件放在旧 EXE 旁边也不会更新它内嵌的程序。

| 你下载到的内容 | 从哪里开始 |
| --- | --- |
| 确实包含 `release/ManuscriptRevisionClosure.exe` 的完整分发 ZIP | **先完整解压，再打开解压目录下的 `release` 文件夹，双击 `ManuscriptRevisionClosure.exe`。** 不要在压缩包浏览窗口中直接运行。 |
| Release 的 **Assets（资源）** 中发布的 Windows EXE/压缩包 | 先看该版本的构建说明与校验值，下载并按需解压，再打开 EXE。只有实际发布此类附件后，这条下载路径才可用。 |
| GitHub **Code → Download ZIP** 或 **Source code (zip/tar.gz)** | 这是源码，不是已打包程序。请按[从源码运行](#从源码运行)或[在 Windows 构建](#在-windows-构建)操作。 |

Windows 单文件构建的设计是自带 Python 运行时和文档解析依赖。你仍需兼容的 Windows x64 电脑、浏览器、提供商网络访问及自己的 API key。发现 EXE 或旧构建收据，不代表它来自当前源码；请保留同一分发包的发布记录和校验值，不要把旧 EXE 与新源码混在一起当作同一版本。

启动后程序会在本机随机 `127.0.0.1` 端口监听，并打开默认浏览器。这个地址表示**你正在使用的这台电脑**，不依赖开发者电脑，也不是托管网站。退出时点击页面里的“关闭本地程序”；只关闭浏览器标签页不会结束后台程序。模型分析仍需联网。

## 提供商设置

1. 在所选提供商的官方 API 平台获取密钥：[DeepSeek](https://platform.deepseek.com/)、[Kimi](https://platform.kimi.com/) 或 [Google AI Studio](https://aistudio.google.com/apikey)。确认账户有对应模型权限和足够额度/余额。
2. 在 Windows 开始菜单搜索“编辑账户的环境变量”，在“用户变量”中新增下表对应的变量名，将密钥填入变量值。请私下完成，不要把密钥放进文档、issue、截图、源码或共享命令中。
3. 关闭并重新打开程序。若从终端启动，也应重新打开终端。程序读取进程继承的环境变量，仅刷新网页不会让进程重新读取用户环境。
4. 在界面中选择提供商，查看密钥状态，再点击“刷新列表”。状态提示只说明变量存在，不等于鉴权已经成功。

| 提供商 | 用户环境变量 | 本源码登记的默认模型标识 |
| --- | --- | --- |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-v4-pro` |
| Kimi | `MOONSHOT_API_KEY`，也兼容 `KIMI_API_KEY` | `kimi-k2.6` |
| Gemini | `GEMINI_API_KEY` | `gemini-3.7-flash` |

只需配置自己要用的提供商。不要把 key 填到稿件或路径框。程序没有密钥输入表单，不显示密钥值，也不将密钥保存到公开结果中。提供商当前可用模型可能与内置目录不同；显示回退目录不代表你的账户能调用其中所有模型。

高级用户可用 `DEEPSEEK_MODEL`、`KIMI_MODEL`、`GEMINI_MODEL` 及对应 `*_BASE_URL` 覆盖默认设置。除非明确选择并信任另一接收方，否则保持默认地址：修改 base URL 会改变密钥与稿件请求的接收方。

## 第一次审阅

1. 点击“选择文件…”或粘贴完整路径，选取身份明确的**完整当前稿件**，不要只选摘要或节选。程序只读原文件。
2. 初次可选**模式 1**，再选择 provider/model 和思考设置。“稳定稿件身份”可填 `paper-v12`；新审阅将“既有最小收据”留空。
3. 选择核心结果语言。“中文解读”默认勾选，需要额外一次模型调用；即使核心语言选 English，这份解读也仍是中文。
4. 每次运行前核对文件与接收方。只有允许将其文本发送给该提供商时，才勾选稿件确认框并点击“开始只读判断”。当前 GUI 也用这个确认框提供主任务外发确认。
5. 等待时间线结束，保存完整公开结果 JSON，以及已生成的中文解读 Markdown。下一轮前先保存：界面只显示当前结果，没有自动多轮历史库。结束后点击“关闭本地程序”。

**对比不同模式、严格度、模型提供商或思考设置时，不要加载旧收据。** 合法且稳定的 STOP 收据可能跳过两次核心调用，而不是重新审阅。独立对比请留空，并把本轮所选设置与结果一同记录。

## 模式与尺度

点击顶部三个标签之一。模式 2 的尺度选择只对模式 2 生效，不是其他模式的附加开关。

| 标签 / CLI 值 | 适用目的 | 实际标准 |
| --- | --- | --- |
| **模式 1：标准审阅模式** / `standard` | 获得通用整稿截止判断 | 按十维学术充分性与材料性根因标准审查，不额外附加宽严或期刊画像。 |
| **模式 2：性格与尺度模式** / `strictness` | 主动改变审稿裁判的尺度 | 从严厉、中等、宽松中选一项。只有一个下拉框，没有额外的人格控制或数值滑块。 |
| **模式 3：目标期刊对齐模式** / `journal_benchmark` | 检查相对于某一期刊已发表论文的实质差距 | 使用期刊信息与样本摘录，执行严格的期刊对齐审查。 |

### 模式 2：三档尺度

- **严厉（`strict`）**：顶刊苛求裁判。对概念界定模糊、机制跳跃、内生性疑点、三角验证不足、方法盲区和理论对话浅层化执行零容忍审查；竞争解释未得到实质回应时不得认定充分。适用于主动接受高压复审。
- **中等（`moderate`，默认）**：常规同行评审尺度，平衡实质性改进收益与修改退化风险，按标准学术充分性判断。
- **宽松（`lenient`）**：强力保护定稿框架；该尺度仅在颠覆核心结论、使理论或实证基础受到根本破坏的重大硬伤下记录实质根因。润色、可选表格和一般审稿偏好不应触发重开。适用于防止稳定稿件陷入边际小修。

三档确实改变判断尺度，但都遵守相同的结构化输出校验。本说明不会重新定义或削弱这些标准。

### 准备期刊样本

1. 填写**目标期刊名称**，可选填写 Scope / 领域定位。优先写实际定位文字；粘贴网址只会提供一段文本，程序不会访问它来抓取期刊要求。
2. 将**至少五篇相关的已发表样本论文**直接放在同一个文件夹。选择能够代表目标主题、方法和理论对话的论文。支持 `.pdf`、`.docx`、`.txt`、`.md`、`.html`、`.htm`；不递归扫描子文件夹，不对扫描 PDF 自动 OCR。
3. 选择该文件夹、待测稿件、provider/model 和思考设置。
4. 点击“**预检样本库相关性**”将**立即单独发送一次可能计费的 API 请求**：发送稿件前 4,000 字符、最多十篇样本的文件名与各前 3,000 字符摘录，以及期刊名称/定位。**这项预检不经过主任务的稿件确认框，其 usage/费用目前也不计入页面的主任务估算。** 只有允许向所选提供商披露这些内容时才点击。
5. 阅读相关性等级和解释。`HIGH`、`MODERATE`、`LOW` 表示样本匹配度，不是论文质量分或录用概率。样本不适合时先更换。LOW 时会出现知情确认框，但当前核心运行器并未将该框落实为强制运行门禁。
6. 再次核对材料，确认主任务并开始审阅。预检与正式审阅之间保持稿件和样本不变。

期刊标准刻意保持严格：学科核心理论应成为论证的构成性支柱，而非外围装饰；方法与证据细节需要对标样本；存在真实期刊尺度差距时，不能仅以“已有自洽”或“避免过度修改”为由放行 STOP。

**当前范围与限制：**样本文件在本地读取，但核心审阅只接收按文件名排序的前八篇、每篇最多 400 字符的摘录。程序不逐篇全文审阅全部样本，也不独立核验其发表状态。样本读取失败时，当前核心运行器可能退回不含期刊画像的审阅。先解决预检/文件错误再运行，不要把样本目录无效时的结果当作已经完成有效期刊对标；增加很多文件也不保证它们的内容全部被评估。

## 思考设置

思考强度控制模型执行方式，不决定审阅模式或宽严尺度。开启与关闭都使用相同模式和输出检查。多次输出仍可能不同，本地合同测试通过也不代表实时模型调用必然成功或裁决完全一致。

下表是本源码登记的能力，不是对提供商未来可用性的承诺：

| 提供商/模型 | 可选设置 |
| --- | --- |
| DeepSeek | 默认 high、关闭（`disabled`）、`low`、`high`、`max` |
| Kimi K2.5 / K2.6 | 默认开启、`enabled`、`disabled`；没有强度档位 |
| Kimi K3 | 默认 max、`low`、`high`、`max`；不能关闭 |
| Kimi K2.7 Code 系列 | 仅默认；固定开启 |
| Gemini 2.5 Flash / Flash-Lite | 默认、关闭（`none`）、`low`、`medium`、`high` |
| Gemini 3.7 Flash | 默认 medium、`low`、`medium`、`high`；不能关闭 |
| 其他已登记 Gemini 型号 | 仅界面显示的子集；部分有 `minimal`，部分不能关闭 |
| 未登记能力的 Kimi/Gemini 型号或别名 | 仅默认 |

先选 provider/model，再查看刷新后的选项。不支持的组合会在模型请求前停止。不要把 Kimi 的 `disabled` 用作 Gemini 的关闭参数，也不要把 `minimal` 当作关闭。更强思考可能改变等待时间和 token 用量，不保证判断更严厉或更准确。

## 结果、等待与费用

| 结果 | 含义与下一步 |
| --- | --- |
| `STOP_REVISING` | 没有材料性根因支持通用实质重修。保护稳定稿件，另行检查证据与投稿事项。 |
| `ONE_BOUNDED_ROUND` | 在一轮有限修改中解决所述局部实质问题，不代表允许全稿重写。 |
| `REOPEN_SUBSTANTIVE_REVISION` | 仍有中央性根因，需要实质修订。 |
| `UNASSESSED` | 没有形成可靠实质裁决。查看状态与失败阶段，原因可能是材料不足、未授权或技术失败。 |

新的成功核心审阅通常进行**两次全文 API 调用**：整稿覆盖，再独立根因裁决。整稿基础不足时在覆盖阶段停止。可选中文解读再调用一次，包含稿件内容。公开展示的定向修复最多再调用一次，不含稿件正文。合法稳定的 STOP 收据可能跳过核心判断。样本预检独立计费。

当前核心、公开展示修复与中文解读的默认等待上限为：**DeepSeek/Gemini 每阶段 600 秒，Kimi 每阶段 900 秒**。样本预检另设 **90 秒**。这是单阶段上限，不是承诺耗时；时间线显示真实阶段和等待时间，不提供保证准确的完成百分比。

timeout、网络状态不明、HTTP 429/502/503/504 或合同失败不会自动重发全文。手动启动新一轮可能再次计费。未收到 usage 的潜在计费请求以 `UNKNOWN_POTENTIAL_CHARGE` 表达，不按零费用处理。

GUI 按主任务记录的 usage、模型价格和参考汇率估算 CNY/USD。带日期的内置回退价标为 `bundled_snapshot_fallback`；缺价或缺 usage 不代表免费，最终以提供商账单为准。样本预检费用目前不在此估算中。直接 CLI 输出核心 runtime/usage 收据，不执行 GUI 额外的中文解读和费用汇总流程。

## 常见问题

| 现象 | 处理方法 |
| --- | --- |
| 下载 GitHub ZIP 后找不到 EXE | 下载到的是源码。按源码方式运行，或获取实际发布的 Windows 分发包。 |
| 未检测到密钥 / 鉴权失败 | 核对变量名，重新打开程序，在提供商官网核对 API 账户、密钥和余额。不要把 key 发到 issue。 |
| 模型目录显示 `bundled_fallback` | 实时目录读取失败。检查网络/密钥并刷新，只选 API 账户确实可用的模型。 |
| 思考选项不支持 | 重新选择模型，使用对应下拉框中的设置，不要假设所有模型都能关闭或使用所有强度。 |
| 空文本、文件不可读、PDF 错误 | 换用可提取文本的支持格式。必要时在外部 OCR，核对提取质量后选择完整结果。源码环境需安装 `pypdf` 才能读 PDF。 |
| 文件/上下文超限 | 不要只提交稿件前半部分。默认文件上限 50 MiB、提取文本上限 300,000 字符；模型另有上下文预算。选择合适模型，或明确了解限制后再调整 `MRC_MAX_FILE_BYTES` / `MRC_MAX_TEXT_CHARS`。 |
| 样本不足/读取失败 | 将至少五篇支持格式、可读的文件直接放进所选文件夹，先解决错误再运行期刊模式。 |
| `UNASSESSED` / 机器裁决 HOLD | 查看失败阶段。provider/schema/binding 错误不等于论文被否定。先保存公开诊断，再决定是否重新付费运行。 |
| 公开展示 HOLD / 中文解读失败 | 已完成的机器判断可能仍有效，应以明确的 machine/presentation 状态区分，不把可选解释失败当成新裁决。 |
| timeout、429、网络错误 | 检查提供商状态、额度和网络。程序不会自动重发；手动再试前先看 usage 和潜在费用。 |
| 浏览器没自动打开 | 用 `--gui-no-browser` 启动，在同一台电脑打开控制台打印的地址；不要公开其中随机访问 token。 |
| Windows 拦截 EXE | 核对来源和校验值，遵循单位的软件使用流程，不要为未知构建关闭安全防护。 |
| 旧 `--console` 向导未进行新判断 | 当前向导只传递完整性声明，未传递必要的外发同意参数，也未提供全部模式。请用 GUI 或下方直接 CLI。 |

报告问题时提供源码提交或包校验值、版本、provider/model、模式/尺度、思考选项和已脱敏的公开错误/状态。不要上传真实稿件、样本论文、key、私人路径、prompt 或原始模型回复。

## 从源码运行

使用仓库 CI 覆盖的 **Python 3.11 或 3.12**。下载并解压源码，在包含 `mrc_standalone.py` 的目录打开终端：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pypdf==6.16.2
.\.venv\Scripts\python.exe -B -m standalone
```

本地界面会在浏览器打开。如需不自动打开浏览器、检查版本或参数：

```powershell
.\.venv\Scripts\python.exe -B -m standalone --gui-no-browser
.\.venv\Scripts\python.exe -B -m standalone --version
.\.venv\Scripts\python.exe -B -m standalone --help
```

其他系统对应的解释器路径为 `.venv/bin/python`；Windows EXE 不能在这些系统原生运行，Windows 打包检查也不代表已保证跨平台 GUI 兼容性。

### 直接 CLI 示例

先配置环境变量密钥。下面的命令明确授权本次将稿件发送给所选提供商。若不授权外发，请勿添加同意参数；`--confirm-complete` 只是兼容旧收据的声明，**不能代替外发授权**。

```powershell
# 模式 1：标准，使用提供商在程序中登记的默认模型/思考设置
.\.venv\Scripts\python.exe -B -m standalone .\paper.docx --provider deepseek --mode standard --language zh --identity paper-v12 --consent-to-provider-transmission --output .\standard.json

# 模式 2：严厉；选择已登记支持关闭思考的模型
.\.venv\Scripts\python.exe -B -m standalone .\paper.docx --provider kimi --model kimi-k2.6 --mode strictness --strictness strict --reasoning disabled --consent-to-provider-transmission --output .\strict.json

# 模式 3：期刊对齐；CLI 没有单独的样本相关性预检入口
.\.venv\Scripts\python.exe -B -m standalone .\paper.docx --provider deepseek --mode journal_benchmark --target-journal-name "Target Journal" --target-journal-scope "Research field and methods" --sample-papers-dir .\samples --consent-to-provider-transmission --output .\journal.json
```

模式 2 可按需将 `strict` 改为 `moderate` 或 `lenient`。已有构建包时，可把 Python 启动部分替换为 `.\release\ManuscriptRevisionClosure.exe`。`--timeout` 以秒覆盖每阶段等待上限；`--transient-retries` 只接受 `0`。`--event-log .\events.jsonl` 会显式保存有隐私边界的事件日志。兼容参数 `--sample-relevance-override` 虽可解析，目前并无核心相关性门禁可被它强制启用或绕过。

## 在 Windows 构建

在 Windows 上使用 Python 3.11/3.12，从源码根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_exe.ps1
```

脚本的输出位置为 `release\ManuscriptRevisionClosure.exe`，并写入构建/校验记录。构建成功不等于已发布 Release 或通过冻结版验收。分发前应验证这一份 EXE，并标明源码提交与 SHA-256；不能用旧收据认证新生成的二进制。

仓库检查使用合成/mock 数据，不需要真实稿件或实时模型请求：

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
python -B scripts/run_adversarial_probes_rc2_0.py
python -B scripts/run_adversarial_probes_rc2_1.py
```

## 隐私与边界

本地界面只监听 loopback，使用随机 token 和 Host/Origin 检查，不加载远程脚本或图片。运行器不提供 shell 工具、稿件编辑、文献检索或投稿功能。公开保存结果不包含密钥、稿件全文、原始模型回复或私有推理；文件保存需显式操作，提供商的数据留存由其条款决定。

只发送自己有权向该提供商披露的稿件与样本摘录。本地界面不等于离线分析。这是没有独立来源核验的模型辅助判断，不是事实认证、同行评审替代品或投稿授权。

实现历史见[更新记录](CHANGELOG.zh-CN.md)、[发布来源](PROVENANCE.zh-CN.md)与[解读合同](../standalone/AGENT.md)。历史工程审计是快照，不作为当前启动说明。
