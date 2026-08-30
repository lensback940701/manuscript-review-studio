# Release Provenance

[中文说明](PROVENANCE.zh-CN.md)

Manuscript Review Harness is the public, multimode packaging of the locally audited Manuscript Revision Closure `0.2.1` skill and standalone `0.6.4` runtime. The smaller Skill-only distribution is maintained separately at [`manuscript-revision-closure`](https://github.com/lensback940701/manuscript-revision-closure).

The Codex-facing package structure and selected architectural boundaries were
informed by the official [`openai/codex`](https://github.com/openai/codex)
repository at commit
[`d5caceccb1ee5bf94c081b995575ce4860e0912b`](https://github.com/openai/codex/commit/d5caceccb1ee5bf94c081b995575ce4860e0912b).
This project is independently maintained, is not endorsed by OpenAI, and copies
no source file from the Codex repository into either the source tree or executable.

The public repository includes the skill instructions, interface metadata, standalone runtime, contract helpers, canonical hold-code reference, synthetic fixtures, regression tests, and four author-supplied documentation illustrations. It excludes real manuscripts, project-specific examples, evidence packages, internal failure-first/build receipts, absolute local paths, credentials, local illustration prompts, and unselected image variants.

No third-party dataset, manuscript content, external model output, or locally built executable is committed to the source repository. The standalone build may bundle dependencies identified in [Third-party notices](THIRD_PARTY_NOTICES.md). The software and documentation are released under Apache License 2.0; the four committed illustrations were separately reviewed before publication.
