# MRC Standalone 0.6.3 Provider 合同与状态完整性修复

本版本是从 `0.6.2` 精确基线实施的一次 bounded 技术修复。Skill 学术判断合同继续使用 `0.2.1`；四种业务 verdict、十个考察维度、STOP/REOPEN、证据 hold 与投稿 hold 语义均未改变。

## 修复范围

- coverage、adjudication、presentation repair 与 interpretation 的逻辑调用均固定为一次物理 HTTP attempt；CLI 兼容参数只接受 `0`。
- 每次物理 attempt 形成不含 key、请求体、稿件或原始 response 的 bounded receipt。timeout、网络不明与 5xx 使用 `UNKNOWN`，usage 不可得时标记 `UNKNOWN_POTENTIAL_CHARGE`。
- provider capability registry 区分 strict JSON schema、JSON object mode 与 schema delivery mode。
- coverage 与 adjudication 使用同一 canonical schema 源完成 prompt、API payload、本地 validation 与 receipt hash 绑定。DeepSeek 在 JSON object mode 外，同时收到完整、确定性的 schema 文本与 SHA-256。
- adjudication schema 按本轮 coverage candidates 动态设置 cardinality 和 dimension enum；独立 verifier 记录 required、observed、missing、extra、duplicate 五组集合。
- contradiction 或合同失败不提交 machine state，不发布 candidate 自然语言，也不建立 authoritative presentation source。
- GUI 按 machine-first 真值表区分 `completed`、`completed_with_presentation_hold`、`completed_with_machine_hold` 与 configuration failure。

## 隐私与验收边界

所有自动测试与冻结 EXE 验收只使用 loopback mock、合成有限状态和临时假稿件。未调用真实 provider API，未读取真实稿件，未保存 secret、全文 prompt 或原始 provider response。冻结 mock acceptance 不等同于用户后续 live replay。
