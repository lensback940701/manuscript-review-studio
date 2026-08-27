# 多阶段 Harness 提取说明

## 冻结输入

- `manuscript-revision-closure` donor commit：`fd30bf0daf0e8557b315491c72479b1b2598c22f`
- OpenAI Codex 参考 commit：`d5caceccb1ee5bf94c081b995575ce4860e0912b`
- Skill 合同版本：`0.2.1`
- Standalone 版本：`0.6.1`

Codex 参考源码只用于识别公开 harness 模式。Standalone 没有复制或嵌入 Codex
Rust、Python SDK 或 App Server 源码，也不需要安装 Codex。实现采用本项目自己的
Python 标准库代码，并继续复用本 Skill 的 `scripts/closure_state.py` 确定性合同。

本文件描述与当前 Skill 直接相关的 bounded harness 能力，不构成对 Codex 通用 agent 能力的复制声明。
已实现门、验证边界与剩余局限见 [`HARNESS_EQUIVALENCE_AUDIT.zh-CN.md`](HARNESS_EQUIVALENCE_AUDIT.zh-CN.md)。

## 行为反推结果

| Codex harness 能力 | 本程序是否保留 | Standalone 实现 |
| --- | --- | --- |
| thread/turn 生命周期 | 是 | `standalone/events.py` 的有限状态机 |
| started/completed/failed 事件 | 是 | 隐私受限的内存或显式 JSONL 事件 |
| 结构化 agent 输出 | 是 | coverage 十维 exact-set + adjudication digest 绑定与有限裁决；Kimi/Gemini 严格 JSON Schema，DeepSeek JSON mode + 同一本地合同 |
| 整稿覆盖证明 | 是，领域限定 | deterministic intake + 十维 coverage + 只公开计数/hash 的 harness receipt |
| 独立根因裁决 | 是，同模型第二 pass | 重新读取全文，逐一消费 coverage candidate，不能静默丢 hold 或保护不变量 |
| 跨阶段 verifier | 是 | canonical coverage SHA-256 + candidate/hold/invariant contradiction gate |
| 公开中文解读 | 是，独立可选 | Kimi/Gemini 严格 JSON Schema + 唯一完整对象提取 + 十一键 exact-set 本地验证 + Markdown 渲染；失败 usage 仍计费 |
| 模型、思考与计价 | 是，provider-aware | 可见模型下拉框 + 每模型思考能力矩阵 + 原币官方价 + ECB 双币种换算 + usage token 确定性计算 |
| 审批边界 | 是，缩减 | CLI 显式调用或本地 GUI 按钮；完整稿件需主动确认 |
| 沙箱边界 | 是，缩减 | 只读一个输入；只在显式保存时写输出；网络仅访问所选 provider |
| 错误和停止状态 | 是 | 合同错误立即失败，不做语义自修复循环 |
| transient retry | 是，缩减 | 仅 408/409/425/429/5xx 和连接超时，最多两次 |
| 会话续接 | 仅领域等价项 | 稳定 prior STOP receipt 可免模型调用 |
| Shell / command execution | 否 | 无任意命令入口 |
| apply patch / 文件编辑 | 否 | 稿件永不修改 |
| Git / worktree | 否 | 不属于修订截止判断合同 |
| MCP、浏览器、网络搜索 | 否 | 合同禁止搜索和外部证据接纳 |
| 多代理、计划系统、长期记忆 | 否 | 单次整稿判断不需要 |

## 从 Codex 参考的公开模式

参考位置：

- `codex-rs/exec/src/exec_events.rs`：thread、turn、item 的有限事件类型；
- `codex-rs/exec/src/event_processor_with_jsonl_output.rs`：JSONL 生命周期输出；
- `codex-rs/app-server-protocol`：请求、通知、审批与终态分离；
- `sdk/python`：同步任务包装、显式 sandbox/approval 参数与事件流测试。

Standalone 只采用了这些架构原则：

1. 生命周期状态必须有限且转移合法；
2. 每个外部动作必须有 started/completed 或 failed；
3. 用户结果与运行事件分开；
4. 终态只有成功或明确失败，不把异常解释成判断结果；
5. 凭据、原稿和模型原始输出不得进入事件流；
6. 模型只生产受限分类，最终卡片和收据由确定性合同生成。

GUI 只是该确定性内核的本地输入/展示适配层：它监听 `127.0.0.1` 随机端口，
以一次性随机 token、Host/Origin 校验和严格 CSP 约束访问，不复制任何判断逻辑，
也不会让浏览器直接接触 provider API key。

可选中文解读层不读取私有分类对象，也不改变确定性 verdict。它重新以不可执行数据
方式读取同一稿件，并先验证稿件 artifact SHA 与核心裁决一致，再根据公开 Closure
Card 和 `standalone/AGENT.md` 生成精确十一个键中文 JSON，最后由本地代码渲染 Markdown。
计价层只读取提供商返回的公开 usage 计数和官方定价页，不读取稿件或 API key；价格
刷新失败时只能显示带日期的内置参考价，并明确标记为非实时回退。

## 有意没有实现的能力

本程序不是通用 agent，也不是 Codex 的替代品。它不会：

- 自行决定或发明工具；
- 执行 Shell、修改文件、调用其他 Skill；
- 搜索文献、验证来源、改写稿件；
- 保存详细内部审稿意见或模型原始分类；
- 在模型输出不合法时反复诱导模型“修好 JSON”。

这些缺省不是功能缺口，而是由原 Skill 合同推导出的最小权限面。
