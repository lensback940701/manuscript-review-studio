# 更新记录

[English](CHANGELOG.md)

## Standalone 0.6.3——Provider 合同与状态完整性修复

- coverage、adjudication、presentation repair 与 interpretation 的每个逻辑调用只允许一次物理 HTTP 请求，不再自动重发全文。
- 增加 bounded 物理请求收据、provider capability 元数据、canonical schema 哈希与未知潜在计费表达。
- 在模型可见 prompt 中嵌入 canonical coverage schema 和本轮动态 adjudication schema；支持 strict schema 的 provider 继续使用 API 级交付。
- 增加动态 candidate cardinality/enum 绑定、独立 exact-set verifier，以及 missing/extra/duplicate bounded 诊断。
- 在 runtime 与 GUI 中分离 machine HOLD 和 presentation HOLD，不改变 Skill `0.2.1` 的学术判断合同。

## 0.2.1——公开发布候选

- 为无版本、`0.1.x`、`0.2.0` 和 `0.2.1` 收据增加统一的版本族验证。
- 对不支持的收据版本直接拒绝，不再猜测其结构。
- 加强方向性轻量建议的边界检查，防止修改命令借助已声明的标点和包裹符号泄漏。
- 保留标准事项代码、固定标签、精确旧版迁移、非回显、四种实质判断、双哈希收据语义与只读路由。
- 将英文和简体中文公开说明拆分为独立页面。
- 在中英文首页中加入四张由作者提供的说明插图。
