# Changelog

[中文说明](CHANGELOG.zh-CN.md)

## Standalone 0.6.3 — Provider contract and state integrity repair

- Disabled automatic full-request retries for coverage, adjudication, presentation repair, and interpretation; every logical call now has one physical HTTP attempt.
- Added bounded physical-request receipts, provider capability metadata, canonical schema hashes, and explicit unknown-potential-charge accounting.
- Embedded the canonical coverage and dynamic adjudication schemas in model-visible prompts while preserving strict API schema delivery where supported.
- Added dynamic candidate cardinality/enum binding, an independent exact-set verifier, and bounded missing/extra/duplicate diagnostics.
- Separated machine HOLD from presentation HOLD in the runtime and GUI without changing the Skill `0.2.1` academic decision contract.

## 0.2.1 — Public release candidate

- Added normalized receipt schema-family validation for absent, `0.1.x`, `0.2.0`, and `0.2.1` receipts.
- Rejected unsupported receipt versions instead of guessing their schema.
- Hardened directional Lite suggestions against command leakage across declared punctuation and wrapper boundaries.
- Preserved canonical hold codes, fixed labels, exact legacy migration, non-echo behavior, four substantive verdicts, dual-hash receipt semantics, and read-only routing.
- Added separate English and Simplified Chinese public documentation.
- Added four author-supplied documentation illustrations to the paired landing pages.
