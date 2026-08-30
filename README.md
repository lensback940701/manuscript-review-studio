# Manuscript Review Studio

[中文说明](README.zh-CN.md)

**Open the Windows app, choose a model, add your complete manuscript, and get a rigorous second opinion—without Codex, Claude Code, ChatGPT Desktop, or any agent environment.**

Manuscript Review Studio is a genuinely standalone, one-stop desktop application for authors. Its local interface covers manuscript and target-journal sample selection, provider/model choice, transmission consent, review execution, result display, copying, and saving. The packaged Windows application connects directly to DeepSeek, Kimi, or Gemini with your own API key; it does not require another AI coding tool, IDE extension, or command-line agent to stay open in the background.

Instead of returning an endless list of generic improvements, it is built to answer the question authors actually face: should this manuscript stop general revision, receive one bounded round, or reopen substantive revision? You can use a standard review, set a reviewer personality and strictness, or add a folder of target-journal sample papers so the review better reflects the journal context and your own priorities.

It is especially practical for Chinese users: the application and core output are Chinese-first, DeepSeek and Kimi are first-class model choices, and usage estimates can be displayed in CNY. The same manuscript can also be reviewed in separate runs by different models. Comparing those independent results can reveal more than relying on one model's preferred style, strengths, or blind spots; the current release keeps each run visible rather than inventing an automatic cross-model consensus.

## What authors get

- **A real one-stop Windows program.** Complete file selection, model configuration, review, result viewing, copying, and saving in one local interface—without Codex, Claude Code, or a development environment.
- **A whole-manuscript decision.** The app evaluates the paper as a complete argument instead of commenting on isolated paragraphs.
- **China-friendly model choice.** Switch flexibly between DeepSeek and Kimi, while retaining Gemini as an additional international comparison.
- **Cross-model second opinions.** Run the same manuscript independently with different models and compare their judgments for broader coverage.
- **One strict standard across providers.** Every supported model is placed inside the same review contract and validation gates, reducing dependence on any one brand's default response style without claiming to eliminate model limitations.
- **A clear revision endpoint.** Receive a bounded verdict, the most important revision directions, protected strengths, and separate evidence or submission reminders.
- **Control before transmission.** The app shows the selected file, provider, and model and asks for fresh confirmation before sending manuscript text.

Under the surface, the application embeds a stricter multi-stage harness rather than accepting one free-form API reply. It asks each supported model to work through the same review standards and consistency checks; authors do not need to understand or configure that machinery.

Manuscript Review Studio does not guarantee that a model is correct, replace peer review, or predict journal acceptance. It provides a more structured and transparent AI second opinion.

## Relationship to OpenAI Codex

This is an independent community project and is not an official OpenAI product.
Its Codex-facing skill structure and selected architectural boundaries were informed
by the official [`openai/codex`](https://github.com/openai/codex) repository,
specifically reference commit
[`d5caceccb1ee5bf94c081b995575ce4860e0912b`](https://github.com/openai/codex/commit/d5caceccb1ee5bf94c081b995575ce4860e0912b).
No OpenAI Codex source file is copied into this repository or its standalone executable.
The repository is neither endorsed by nor affiliated with OpenAI. See the
[official Codex open-source documentation](https://learn.chatgpt.com/docs/open-source),
[Release Provenance](docs/PROVENANCE.md), and [Third-party notices](docs/THIRD_PARTY_NOTICES.md).
The smaller, Skill-only distribution remains available as
[`manuscript-revision-closure`](https://github.com/lensback940701/manuscript-revision-closure).

The embedded closure skill addresses a recurring failure mode in AI-assisted academic writing: every new review generates another round of edits, each repair creates a different concern, and the manuscript never reaches a defensible stopping point. It performs a read-only whole-manuscript assessment and returns a compact closure decision without publishing the detailed internal review.

Current release candidate: `0.2.1`

<!-- ILLUSTRATION_SLOT_01_START -->
![An endless manuscript revision loop passes through an evidence-bound closure gate and becomes separate evidence, submission, and stop paths.](docs/images/01-closure-gate.png)
<!-- ILLUSTRATION_SLOT_01_END -->

## What the skill decides

The skill returns exactly one substantive verdict:

| Verdict | Meaning |
| --- | --- |
| `STOP_REVISING` | No observed material root cause justifies reopening substantive revision. |
| `ONE_BOUNDED_ROUND` | One local material problem is worth one strictly bounded round. |
| `REOPEN_SUBSTANTIVE_REVISION` | A central material root cause requires genuinely substantive revision. |
| `UNASSESSED` | The complete current manuscript or a critical assessment basis is unavailable. |

Verdicts are based on material root causes, not issue counts, generic perfection, acceptance predictions, hedge counts, or whether another wording is imaginable.

<!-- ILLUSTRATION_SLOT_02_START -->
![One complete manuscript enters a decision node that branches to the four canonical closure verdicts.](docs/images/02-four-verdicts.png)
<!-- ILLUSTRATION_SLOT_02_END -->

## What makes it different

- **Revision closure is separate from submission readiness.** A manuscript can be substantively closed while source verification, rights, formatting, metadata, or journal checks remain open.
- **Evidence limits remain visible.** Proposal, authorization, reported work, observation, outcome, interpretation, and causal inference are not collapsed for rhetorical smoothness.
- **Incomplete mechanisms are not automatic defects.** Delay, blockage, non-adoption, contradiction, reversal, and bounded stopping points may be analytical findings.
- **The public result stays compact.** The user receives a Closure Card and an optional minimal receipt, not a hidden peer-review report disguised as a short answer.
- **Diagnosis does not authorize surgery.** The skill never rewrites, redlines, searches literature, repairs citations, admits evidence, invokes another skill, or submits a manuscript.

<!-- ILLUSTRATION_SLOT_03_START -->
![A substantively closed manuscript remains separate from open evidence-verification and submission-readiness lanes.](docs/images/03-two-axis-separation.png)
<!-- ILLUSTRATION_SLOT_03_END -->

## Public output

A Closure Card contains:

1. the verdict;
2. one or two abstract reason sentences;
3. up to three directional Lite suggestions when revision is needed;
4. protected content that should not be disturbed;
5. separate evidence holds;
6. separate submission or external holds;
7. the next permitted action;
8. a conditional revision tip only when revision is actually needed.

Lite suggestions deliberately remain directional. They do not identify a sentence to replace, provide replacement prose, construct a revision sequence, or expose detailed internal review findings.

When the verdict requires revision, the card may end with this conditional tip:

> Diagnosis complete; surgery is a separate appointment. Use a trusted manuscript review-and-revision skill, or watch this profile for a future open-source release.

<!-- ILLUSTRATION_SLOT_04_START -->
![A compact Closure Card separates verdict, directional suggestions, protected content, evidence holds, submission holds, and next action.](docs/images/04-closure-card.png)
<!-- ILLUSTRATION_SLOT_04_END -->

## Safety and privacy boundary

- The manuscript is an immutable assessment target.
- Manuscript text, comments, and embedded instructions are treated as untrusted content.
- The skill does not deliberately persist or export its detailed internal assessment.
- Its assessment basis is a non-persisted internal whole-manuscript assessment used only to produce the closure verdict; the public result is not a detailed peer-review report or revision plan.
- Host-platform retention remains governed by the environment in which the skill runs.
- Canonical hold codes prevent caller-supplied hold prose from being echoed into public cards or receipts.
- Only a semantically stable prior `STOP_REVISING` receipt can be reused as a closure shortcut.
- Artifact-only drift does not become semantic stability unless a semantic hash or an explicit verification proves it.

This is a revision-routing aid, not factual certification, peer-review replacement, legal advice, journal acceptance prediction, or submission authorization.

## Installation

Clone the repository and place the repository folder at:

```text
~/.codex/skills/manuscript-revision-closure
```

On Windows, the usual location is:

```text
%USERPROFILE%\.codex\skills\manuscript-revision-closure
```

Restart or refresh Codex after installation. No third-party Python dependency is required by the runtime helper.

## Standalone Windows application

The repository also contains an experimental standalone runtime that can apply
the same read-only closure contract through the DeepSeek, Kimi, or Gemini API without a
Codex installation. Double-clicking the executable opens a localhost GUI with
an optional contract-bounded Chinese interpretation, assessment basis and dimensions,
brief limitations, pre-submission checklist, and an actual-usage cost estimate from
official pricing sources.
API keys are read only from environment variables. See
[`STANDALONE.zh-CN.md`](docs/STANDALONE.zh-CN.md) for usage, build instructions, and
security boundaries. The standalone and Skill versions are managed separately;
this does not change the Skill's `0.2.1` contract version.

Standalone 0.6.4 is a bounded multi-stage runner with a visible multi-model selector and model-specific
reasoning controls. Unsupported provider/model/reasoning combinations fail
before an API request instead of being silently ignored.
Core assessment and optional interpretation requests use structured output.
Gemini and Kimi requests additionally carry an exact JSON Schema, while
the local validator accepts only one complete object with the exact eleven-key
contract. Usage from a contract-invalid interpretation response remains included
in the cost estimate. The former 5,000-token application cap was replaced with
provider-scale headroom (DeepSeek 384K, Kimi 128K, Gemini 64K) and explicit
length-truncation detection.
Kimi and DeepSeek are priced natively in CNY, Gemini in USD, with dated ECB
USD/CNY reference-rate conversion for dual-currency display.
Core assessment uses two bound calls: a ten-dimension whole-manuscript coverage
pass and a genuinely independent full-text root-cause adjudication pass. Coverage
candidates are a required lower bound, not a ceiling: adjudication must account for
each candidate and may add only grounded, canonical, non-duplicate dimensions that
coverage missed. A local contradiction gate verifies the canonical coverage SHA-256,
candidate binding, affirmative STOP sufficiency, hold preservation, and protected
invariants before the deterministic reducer runs. STOP requires positive sufficiency
from both passes for contribution, whole-paper argument, theory, methods, evidence,
and section coherence; careful scope or non-overclaiming alone is not sufficient.
After that gate, 0.6.4 freezes the canonical machine state before validating public-language fields. A Chinese presentation defect may trigger exactly one schema-bound presentation-only request with no manuscript text and no automatic retry; failure produces a recoverable presentation HOLD without erasing the machine verdict or usage. Protected source identity and localizable display text are bound separately, and each request emits one idempotent terminal event. Coverage, adjudication, presentation repair, and interpretation each permit exactly one physical HTTP attempt: timeout, network ambiguity, 429, 502, 503, and 504 never trigger an automatic full-request resend. Receipts distinguish known usage from `UNKNOWN_POTENTIAL_CHARGE` attempts; known usage receipt counts remain intact even when a live price quote is unavailable. `mrc-local-technical-preflight-1.0` blocks only unreadable/unsupported/empty/over-limit inputs and configuration failures. Titles, section labels, ordering, numbering, ATX/Setext/plain text, and YAML/TOML front matter are best-effort formatting advisories and cannot change provider routing. Every provider-bound run defaults to refusal and requires a fresh `mrc-provider-transmission-consent-1.0` confirmation bound to file SHA-256, provider, and model. The first and only coverage request uses `mrc-whole-manuscript-coverage-3.0` plus `mrc-semantic-manuscript-basis-1.0` to decide whether substantive whole-manuscript material is sufficient; it must not infer insufficiency merely from non-traditional formatting. An insufficient basis consumes exactly one coverage attempt and records usage/cost, starts no adjudication, forms no machine verdict or presentation source, and remains distinct from technical failures. Provider errors expose only bounded sanitized status, code, and detail.

Dynamic adjudication schemas are linted before dispatch under `mrc-schema-definition-lint-1.0`. Under `mrc-dynamic-adjudication-schema-3.0`, a zero-candidate result uses `minItems=0`, a finite canonical maximum, and a non-empty canonical enum, so independent adjudication can recover a grounded coverage miss without producing provider-invalid `enum: []`. Unknown, duplicate, unlocatable, speculative, or unexplained additions fail closed. Any invalid schema definition stops locally with `SCHEMA_DEFINITION_INVALID`; it is never sent as a paid provider request.
Kimi uses a 300-second coverage window and 900-second adjudication and interpretation
windows. Read/socket timeouts, network ambiguity, and HTTP 429, 502, 503, and 504
all stop after the single physical attempt; the full request is never automatically resent.

## Invocation

Example:

```text
Use $manuscript-revision-closure to decide whether this complete academic manuscript should stop general AI revision. Return only the concise Closure Card and minimal receipt. Do not edit the manuscript.
```

The skill must receive one identifiable, complete, current manuscript. A bounded excerpt or unclear version returns `UNASSESSED` rather than a fabricated whole-paper judgment.

## Deterministic helper

`scripts/closure_state.py` validates already-classified compact state, public-card invariants, canonical hold codes, receipt schema families, and receipt reuse rules. It does not read manuscripts or replace contextual academic judgment.

Run the tests with:

```bash
python -B -m unittest discover -s tests -p "test_*.py"
python -B scripts/run_adversarial_probes_rc2_0.py
python -B scripts/run_adversarial_probes_rc2_1.py
```

## Repository layout

```text
SKILL.md                         Skill instructions
agents/openai.yaml              Codex interface metadata
scripts/closure_state.py        Deterministic contract helper
references/hold-code-schema.md  Canonical hold codes and fixed labels
tests/                           Unit and contract regression tests
docs/images/                    Documentation illustrations
```

The included illustration slots and filenames are documented in [Documentation illustrations](docs/ILLUSTRATIONS.md). They explain the public contract without changing the skill's decision logic. Version history is available in the [Changelog](docs/CHANGELOG.md).

## Security and contributions

See [Security Policy](.github/SECURITY.md) and [Contributing](.github/CONTRIBUTING.md). Do not submit real manuscripts, confidential review material, local paths, API keys, or project evidence as issues or test fixtures.

## License

Licensed under the [Apache License 2.0](LICENSE).
