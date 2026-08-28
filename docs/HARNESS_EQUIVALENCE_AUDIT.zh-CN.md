# Standalone 0.6.1 多阶段 Harness 实现与边界审计

## 裁决

0.6.1 已实现上一轮建议的领域专用多阶段架构：确定性 intake、模型上下文预算、十维整稿
coverage、重新读取全文的 root-cause adjudication、coverage SHA-256 绑定、跨阶段矛盾门和
既有确定性 reducer。它不再是“一次模型调用 + JSON 合法性检查”的薄运行器。

它仍不是 Codex 通用 agent harness 的复刻：没有 Shell、文件编辑、浏览器、搜索、子代理或
长期记忆。这些能力被原 Skill 明确排除，不属于当前功能的缺失。

## 当前执行链

1. **Immutable document read**：读取 TXT/Markdown/HTML/DOCX/文本层 PDF，计算文件与
   语义文本 SHA-256，拒绝静默截断；
2. **Deterministic intake gate**：在用户确认之外，识别标题、摘要、结论和参考文献，确认
   结论位于参考文献之前；结构不完整即 `UNASSESSED`，不调用模型；
3. **Model-specific context budget**：根据所选提供商/模型登记的上下文窗口，保守估算完整
   prompt、Skill 合同和输出余量；不足时不截断全文；
4. **Coverage pass**：模型读取完整全文，对以下十个维度各评估一次：
   contribution、whole-paper argument、theory/concepts、methods/design、evidence/analysis、
   rivals/negative findings/limitations、section roles/coherence、claim ceiling/scope、
   evidence status/provenance、revision/submission boundary；
5. **Coverage validator**：本地检查维度集合精确匹配、无重复、assessed/status 合法、候选列表
   与 `POTENTIAL_MATERIAL_ROOT_CAUSE` 行完全一致、hold codes 和保护不变量有限合法；
6. **Canonical binding**：对验证后的 coverage 使用 UTF-8 canonical JSON 计算 SHA-256；
7. **Adjudication pass**：同一模型在独立第二次调用中重新读取全文，同时接收有限 coverage；
   每个候选维度必须且只能由一个 root-cause row 消费，包括最终因 style-only、hold-only、
   verification-only 或收益不超过回归风险而被驳回的候选；
8. **Contradiction gate**：本地独立重算 digest，拒绝 stale hash、漏候选、重复认领、未知维度、
   coverage hold 被丢弃或保护不变量失败却没有候选维度；
9. **Deterministic reducer**：只有上述门全部通过，才把有限裁决交给既有
   `scripts/closure_state.py` 生成 Closure Card 和最小收据；
10. **Optional interpretation**：核心裁决冻结后才进行第三次可选调用，生成中文公开解读，
    不参与重判。

## 请求等待与不可重发合同

Kimi 的 coverage 默认单次等待 300 秒，adjudication 与 interpretation 默认 900 秒；其他
已登记组合默认 180 秒。CLI 的显式 `--timeout` 可覆盖这些默认值。coverage、adjudication、
presentation repair 与 interpretation 均只允许一次物理 HTTP attempt；429、502、503、504、
socket/read timeout 与网络状态不明均不得自动重发全文。这一合同不改变输出 token 余量，
也不通过截短全文或压缩裁决来换取更短运行时间。

## 私有状态与公开收据

完整 coverage rows 仅存在于单次进程内，并只作为第二 pass 的有限输入；不会写入事件、公开
JSON、最小收据或解读文件。公开 runtime 只保留：

- intake 布尔门和 heading count；
- 每个阶段的估算输入、上下文上限和输出余量；
- coverage 合同版本、维度计数和 canonical digest；
- adjudication digest binding 与 contradiction gate 的 PASS/HOLD；
- 各次 API 的 token usage、模型和尝试次数。

因此，用户能验证流程确实走过各门，但不会获得详细私有审稿记录。

## 已闭合的旧缺口

- 不再只依赖“用户勾选完整 + 最小字符数”；
- 不再把完整稿件直接交给一次不可验证的 STOP/REOPEN 输出；
- 不再缺少模型级上下文预算；
- 不再允许空 root-cause 输出在 coverage 已发现候选时静默 STOP；
- 不再允许第二 pass 丢弃第一 pass 的 evidence/submission holds；
- 不再把可选中文解读误当作核心 verifier；
- 不再用输出 token 数或运行时间充当审阅充分性的代理指标。

## 仍然存在的诚实边界

1. **同模型独立 pass，而非异构双模型复核。** 第二 pass 使用同一用户选择的提供商与模型，
   以隔离 prompt、重新读取全文和 hash binding 获得过程独立性，但不是不同模型间的共识；
2. **token 预算是保守估算。** 未引入三家专有 tokenizer；估算不足会 fail-closed，但不是账单级
   精确 token 预测；
3. **结构识别是领域规则。** 标题、摘要、结论、参考文献使用中英文常见 heading typology；
   极不常见的标题写法可能被诚实判为 `UNASSESSED`；
4. **semantic truth 仍由 LLM 判断。** 本地 verifier 能验证完整性、绑定和矛盾，不能像事实核验
   Skill 那样证明论文事实为真；
5. **不替代同行评审或投稿授权。** 本程序只判断是否应停止通用 AI 改稿。

这些限制与当前功能边界一致，不需要通过加入搜索、改稿、第三方工具或自动投稿来“补齐”。
