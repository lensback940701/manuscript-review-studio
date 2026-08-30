# Release Provenance

[中文说明](PROVENANCE.zh-CN.md)

This repository is a copy-first public derivative of the locally audited `0.2.1` release candidate.

The Codex-facing package structure and selected architectural boundaries were
informed by the official [`openai/codex`](https://github.com/openai/codex)
repository at commit
[`d5caceccb1ee5bf94c081b995575ce4860e0912b`](https://github.com/openai/codex/commit/d5caceccb1ee5bf94c081b995575ce4860e0912b).
This project is independently maintained, is not endorsed by OpenAI, and copies
no source file from the Codex repository into either the source tree or executable.

The public derivative includes the skill instructions, interface metadata, a standard-library Python contract helper, canonical hold-code reference, synthetic fixtures, regression tests, and four author-supplied documentation illustrations. It excludes real manuscripts, project-specific examples, evidence packages, internal development reports, absolute local paths, credentials, API integrations, local illustration prompts, and unselected image variants.

No third-party dataset, manuscript content, binary dependency, or external model output is bundled as a runtime asset. The software and documentation are released under Apache License 2.0. The final illustrations are intentionally absent from this release candidate and will receive their own provenance review before upload.
