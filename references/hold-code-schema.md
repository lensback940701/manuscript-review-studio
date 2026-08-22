# Canonical Hold-Code Schema

RC2.0 treats hold codes as the only machine-state and receipt representation.
The helper renders fixed labels from these maps; it never echoes caller text as
a public hold label.

## Evidence codes

| Code | English label | Chinese label |
|---|---|---|
| `SOURCE_VERIFICATION_REQUIRED` | Source verification required | 来源核验待完成 |
| `SOURCE_PACKAGE_MISSING` | Source package missing | 来源材料包缺失 |
| `EVIDENCE_CONFLICT_REQUIRES_QUERY` | Evidence conflict requires author query | 证据冲突待作者确认 |
| `CLAIM_STATUS_UNRESOLVED` | Claim status unresolved | 主张状态待确认 |
| `SECOND_VERIFIER_REQUIRED` | Second verifier required | 第二核验者待完成 |
| `BOUNDED_MECHANISM_STOPPING_POINT` | Bounded mechanism stopping point requires verification | 有界机制停止点待核验 |
| `OTHER_EVIDENCE_HOLD` | Other evidence hold requires human clarification | 其他证据事项待人工澄清 |

## Submission/external codes

| Code | English label | Chinese label |
|---|---|---|
| `QUOTE_PERMISSION_UNRESOLVED` | Quote permission unresolved | 引文许可未解决 |
| `IMAGE_RIGHTS_UNRESOLVED` | Image rights unresolved | 图像权利未解决 |
| `FORMAT_QA_PENDING` | Format QA pending | 格式核查待完成 |
| `COMMENTS_OR_TRACKING_REMAIN` | Comments or tracking remain | 批注或修订痕迹仍存在 |
| `JOURNAL_CONTRACT_UNCHECKED` | Journal contract unchecked | 期刊合同待核查 |
| `ANONYMIZATION_PENDING` | Anonymization pending | 匿名化待完成 |
| `AUTHOR_METADATA_MISSING` | Author metadata missing | 作者信息缺失 |
| `DECLARATIONS_OR_CONTRACT_PENDING` | Declarations or contract pending | 声明或合同待完成 |
| `LICENSING_UNRESOLVED` | Licensing unresolved | 许可事项未解决 |
| `REVISION_AUTHORIZATION_PENDING` | Revision authorization pending | 修订授权待确认 |
| `OTHER_SUBMISSION_HOLD` | Other submission hold requires human clarification | 其他投稿事项待人工澄清 |

## Legacy exact-map boundary

Legacy free-text fields are normalized only by trim, repeated-whitespace
collapse, and Unicode-safe case folding. The complete normalized item must be
an exact key in the adapter map. There is no substring, fuzzy, regex-near,
semantic, or LLM inference.

Known mappings include:

- `source verification required` → `SOURCE_VERIFICATION_REQUIRED`
- `image rights unresolved` → `IMAGE_RIGHTS_UNRESOLVED`
- `quote permission unresolved` → `QUOTE_PERMISSION_UNRESOLVED`
- `format QA pending` → `FORMAT_QA_PENDING`
- `comments or tracking remain` → `COMMENTS_OR_TRACKING_REMAIN`
- `comments or formatting` → `COMMENTS_OR_TRACKING_REMAIN`, `FORMAT_QA_PENDING`
- `journal contract unchecked` → `JOURNAL_CONTRACT_UNCHECKED`
- `anonymization pending` → `ANONYMIZATION_PENDING`
- `author metadata missing` → `AUTHOR_METADATA_MISSING`
- `licensing unresolved` → `LICENSING_UNRESOLVED`
- `revision authorization pending` → `REVISION_AUTHORIZATION_PENDING`
- `mechanism ends at documented blockage` → `BOUNDED_MECHANISM_STOPPING_POINT`
- `来源核验待完成` → `SOURCE_VERIFICATION_REQUIRED`
- `图像权利未解决` → `IMAGE_RIGHTS_UNRESOLVED`
- `格式核查待完成` → `FORMAT_QA_PENDING`
- `作者信息缺失` → `AUTHOR_METADATA_MISSING`

Both old and new fields are ambiguous and therefore rejected when supplied
together. Unknown or mixed-clause text is rejected as a whole; it is never
trimmed to a safe prefix or downgraded to `OTHER`.
