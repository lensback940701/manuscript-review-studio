# Manuscript Review Studio: application guide

[中文说明](STANDALONE.zh-CN.md) · [Project home](../README.md)

This guide describes the current standalone source (`0.6.4`, with Skill contract `0.2.1`). The app's window and executable retain the name **Manuscript Revision Closure**. The interface is Chinese-first; the core result language can be English or Chinese. No manuscript is rewritten.

## Download and open

**[Windows downloads / GitHub Releases](https://github.com/lensback940701/manuscript-review-studio/releases)**

**Availability checked 2026-10-01:** no published GitHub Release or EXE asset is available in this repository. Current fixes are in the source. The original full-bundle EXE predates the current mode/response-handling fixes. The version string `0.6.4` alone does not prove it is updated, and placing new `.py` files beside the old EXE does not replace its embedded program.

| What you have | Where to start |
| --- | --- |
| A complete distribution ZIP that actually includes `release/ManuscriptRevisionClosure.exe` | Extract the entire ZIP, open the extracted `release` folder, then double-click `ManuscriptRevisionClosure.exe`. Do not run it from inside the ZIP viewer. |
| A published Windows EXE/package in a Release's **Assets** | Read that release's build notes and checksum, download it, extract if needed, and open the included EXE. This route becomes available only when such an asset is published. |
| GitHub **Code → Download ZIP** or **Source code (zip/tar.gz)** | This is source, not a packaged application. Follow [Run from source](#run-from-source) or [Build on Windows](#build-on-windows). |

A Windows one-file build is intended to carry its Python runtime and document-reading dependencies. You still need a compatible Windows x64 machine, a browser, provider network access, and your own API key. The presence of an EXE or an old build receipt is not proof that it was built from current source. Keep release notes and checksums with the distribution; do not mix an old EXE with newer source and assume they match.

The app starts a local server on a random `127.0.0.1` port and opens your default browser. That address means **this computer**. It is not a hosted website or a page on the developer's computer. Use the page's **Close local program** button to stop it; closing a browser tab alone does not stop the process. Model requests still go online.

## Provider setup

1. Obtain an API key from your chosen provider's own API platform: [DeepSeek](https://platform.deepseek.com/), [Kimi](https://platform.kimi.com/), or [Google AI Studio](https://aistudio.google.com/apikey). Check that your account has access to the model and sufficient quota/balance.
2. In Windows, search Start for **Edit environment variables for your account**. In **User variables**, add the variable below, with your key as its value. Do this privately; do not put the key in a document, issue, screenshot, source file, or shared command.
3. Close the running app and reopen it. If launching from a terminal, open a new terminal too. The application reads inherited environment variables; refreshing the browser does not refresh the process environment.
4. Select that provider in the UI. Check the key-presence indicator and click **Refresh list** to request its model catalog. The indicator confirms presence, not successful authentication.

| Provider | Required user variable | Default identifier registered in this source |
| --- | --- | --- |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-v4-pro` |
| Kimi | `MOONSHOT_API_KEY` (also accepts `KIMI_API_KEY`) | `kimi-k2.6` |
| Gemini | `GEMINI_API_KEY` | `gemini-3.7-flash` |

You need only the key for the provider you use. Do not enter keys into the manuscript/path fields. The program has no key-entry form, does not display key values, and does not save them in public results. A provider's current model availability may differ from the bundled list; a fallback list is not proof that your account can use every model.

Advanced users can override `DEEPSEEK_MODEL`, `KIMI_MODEL`, or `GEMINI_MODEL`, and the matching `*_BASE_URL`. Leave endpoints at their defaults unless you deliberately trust another recipient: changing a base URL changes where the credential and manuscript requests go.

## First review

1. Select the complete current manuscript using the file button or paste its full path. Use one identifiable version, not an abstract or selected excerpts. The manuscript is read without modification.
2. Start with **Mode 1**. Select provider, model, and thinking setting. Give the manuscript a recognizable identity, such as `paper-v12`; leave the prior-receipt field empty for a new assessment.
3. Select the core output language. The optional Chinese interpretation is enabled by default; it is a separate model call and stays Chinese even when the core language is English.
4. Verify the selected file and destination before every run. Check the manuscript confirmation box and start the review only if you authorize sending its text to that provider. In the current GUI, this checkbox also supplies the main-run transmission confirmation.
5. Wait for the stage timeline. Save the public JSON and, when available, the Chinese interpretation Markdown. Save before another run: the UI shows one current result and has no automatic multi-run archive. Close the local program when finished.

Do not use a prior receipt when comparing modes, strictness levels, providers, or thinking settings: a valid stable STOP receipt can skip the two core calls instead of conducting a new review. Leave it empty for independent comparisons and record the chosen settings with each saved result.

## Modes and scales

Choose one of the three tabs. Mode 2's selector is active only in Mode 2; it is not an extra setting for the other modes.

| Tab / CLI value | When to use it | Applied standard |
| --- | --- | --- |
| **1: Standard** / `standard` | A baseline whole-manuscript closure review | Ten-dimensional academic sufficiency and material-root-cause review, without an additional strictness or journal profile. |
| **2: Personality and scale** / `strictness` | Deliberately change the referee's calibration | Select Strict, Moderate, or Lenient below. There is one selector, not a separate personality control or numeric scale. |
| **3: Target journal benchmark** / `journal_benchmark` | Test substantive gaps against a particular journal and its published papers | A demanding journal-specific standard using your journal context and sample excerpts. |

### Mode 2: choose the referee's strictness

- **Strict (`strict`)**: top-tier referee scrutiny, with zero tolerance for unclear concepts, mechanism leaps, endogeneity concerns, weak triangulation, likely methodological blind spots, and shallow theoretical dialogue. Unanswered substantive rival explanations cannot count as sufficient. Use it for a deliberately demanding review.
- **Moderate (`moderate`, default)**: standard academic sufficiency, balancing substantive gains against the risk of making an established paper worse. Use it for a conventional balanced review.
- **Lenient (`lenient`)**: strong final-draft regression protection. This profile reserves substantive root causes for major flaws that overturn the core conclusion or undermine the theoretical/empirical basis; polish, optional tables, and ordinary reviewer preferences should not reopen revision. Use it when protecting a stable final draft is the purpose.

These are actual judgment calibrations. They do not change the structured-output validation rules. The documentation does not redefine or soften their standards.

### Mode 3: prepare journal samples

<a id="prepare-journal-samples"></a>

1. Enter the **target journal name** and, optionally, its scope/field. Write useful scope text; a pasted URL is only text, and the app does not visit it to fetch journal rules.
2. Put **at least five relevant, published sample papers** directly in one folder. Prefer samples that genuinely represent the intended subject, methods, and theoretical conversation. Use `.pdf`, `.docx`, `.txt`, `.md`, `.html`, or `.htm`; nested subfolders are not scanned. Scanned PDFs are not OCR'd.
3. Choose that folder and the manuscript, provider/model, and thinking setting.
4. If you click **Check sample relevance**, expect an immediate, separate, potentially billable API request. It sends the manuscript's first 4,000 characters, filenames and excerpts from up to ten samples (up to 3,000 characters each), plus journal name/scope. **This precheck does not use the main-run confirmation checkbox, and its usage/cost is not included in the displayed main-task estimate.** Only click if you may share that material with the selected provider.
5. Read the relevance rating and explanation. `HIGH`, `MODERATE`, and `LOW` describe sample fit, not manuscript quality or acceptance probability. Replace unsuitable samples before reviewing. A LOW result exposes an acknowledgement checkbox, but the current core runner does not enforce it as an eligibility gate.
6. Recheck the inputs, confirm the main run, and start the review. Keep the manuscript and samples unchanged between precheck and review.

The journal standard is intentionally demanding: disciplinary theory must be a substantive pillar rather than decorative framing; methodological and empirical detail is compared with the supplied samples; an internally coherent paper must not receive STOP merely to avoid further revision when substantive journal-level gaps remain.

**Current scope and limitation:** sample files are read locally, but the core review receives only excerpts from the first eight filename-sorted papers, up to 400 characters each. It does not perform full-text review of every sample or independently verify publication status. A failed sample ingestion can currently fall back to review without the benchmark profile. Resolve any precheck/file error before proceeding; do not interpret a run with an invalid sample folder as a verified journal comparison. Adding many papers does not guarantee all their contents are assessed.

## Thinking settings

Thinking effort controls model execution; it does not select the review mode or strictness. The same mode and output checks apply with thinking on or off. Responses can still differ between runs, and passing local contract tests does not guarantee live-provider success or identical judgments.

The dropdown follows this source's registered model contracts:

| Provider/model | Available controls |
| --- | --- |
| DeepSeek | Default (high), off (`disabled`), `low`, `high`, `max` |
| Kimi K2.5 / K2.6 | Default (on), `enabled`, `disabled`; no effort levels |
| Kimi K3 | Default (max), `low`, `high`, `max`; cannot turn off |
| Kimi K2.7 Code family | Default only; thinking fixed on |
| Gemini 2.5 Flash / Flash-Lite | Default, off (`none`), `low`, `medium`, `high` |
| Gemini 3.7 Flash | Default (medium), `low`, `medium`, `high`; cannot turn off |
| Other registered Gemini models | Only their displayed subset; some include `minimal`, some cannot turn off |
| Unregistered Kimi/Gemini models or aliases | Default only |

Select the provider/model first and inspect the refreshed options. Unsupported combinations stop before a model request. Do not use Kimi's `disabled` value for Gemini or assume `minimal` means off. Stronger thinking may change latency and token usage; it is not a guarantee of a stricter or better verdict.

## Results, waiting, and charges

| Result | Meaning / next step |
| --- | --- |
| `STOP_REVISING` | No material root cause justifies general substantive revision. Preserve the stable paper; check evidence and submission holds separately. |
| `ONE_BOUNDED_ROUND` | Address the stated local material issue within a bounded round. This is not permission for a full rewrite. |
| `REOPEN_SUBSTANTIVE_REVISION` | A central material root cause warrants substantive revision. |
| `UNASSESSED` | No reliable substantive judgment was formed. Read the status and failed stage; this can reflect insufficient material, missing consent, or a technical failure. |

A fresh successful core assessment normally uses **two full-manuscript API calls**, coverage then independent adjudication. Insufficient whole-manuscript basis stops after coverage. Optional Chinese interpretation adds one request with manuscript content. A presentation-only repair can add one request without manuscript text. A stable prior STOP receipt can skip core review. Sample precheck is separate.

Current core, presentation-repair, and interpretation timeout limits are **600 seconds per stage for DeepSeek/Gemini and 900 seconds for Kimi**. The sample precheck has a separate **90-second** timeout. These are limits, not promised completion times. The timeline shows stages and elapsed waiting, not a guaranteed percentage.

No full request is automatically resent after a timeout, network ambiguity, HTTP 429/502/503/504, or contract failure. A manual new run may incur another charge. A timeout with unknown usage is recorded as `UNKNOWN_POTENTIAL_CHARGE`, not zero cost.

The GUI estimates recorded main-run usage in CNY/USD using model pricing and reference exchange rates. A dated fallback price is labelled `bundled_snapshot_fallback`; missing prices or usage are not a free-run guarantee. The provider's bill is authoritative. Remember that sample-precheck charges are currently outside this estimate. Direct CLI output contains core runtime/usage receipts, not the GUI's extra interpretation and pricing workflow.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| No EXE after downloading GitHub ZIP | You downloaded source. Use the source instructions or obtain an actual Windows distribution from a published release. |
| Missing key / authentication error | Check the exact variable name, reopen the app, and verify the API account/key and balance on the provider's site. Do not post the key in a bug report. |
| Model list says `bundled_fallback` | Live catalog retrieval failed. Check connectivity/key, refresh, and choose a model your API account actually supports. |
| Thinking option rejected | Re-select the model and use an option shown for it. Do not assume all models support off or all effort levels. |
| No text, unreadable file, PDF problem | Use a supported file with extractable text. Perform OCR separately if needed, check extraction quality, then select the complete result. The source environment needs `pypdf` for PDFs. |
| File/context limit exceeded | Do not submit only the first part of the paper. Default file limit is 50 MiB and extracted-text limit 300,000 characters; context budgets also depend on the model. Choose a suitable model or deliberately review limits before changing `MRC_MAX_FILE_BYTES` / `MRC_MAX_TEXT_CHARS`. |
| Sample count/read error | Put at least five readable supported files directly in the chosen folder. Fix the error before starting journal mode. |
| `UNASSESSED` / machine HOLD | Read the failed stage. A provider/schema/binding failure is not a rejection of the paper. Save the public diagnostics before a deliberate new run. |
| Presentation HOLD / Chinese interpretation failed | A completed machine judgment may remain valid; use the explicit machine/presentation status. Do not confuse optional explanation failure with a new substantive verdict. |
| Timeout, 429, or network error | Check the provider's status/quota and your network. No automatic resend occurs; inspect usage and possible charges before retrying manually. |
| Browser did not open | Launch with `--gui-no-browser` and open the printed local URL on the same computer. Keep its random access token private. |
| Windows blocks the executable | Verify its source and checksum and follow your organization's approved software process. Do not disable protection merely to run an unknown build. |
| Legacy `--console` returns without a fresh assessment | The current wizard forwards completeness but not the required transmission flag and does not expose all modes. Use the GUI or direct CLI below. |

When reporting an error, include source commit or package checksum, version, provider/model, mode/scale, thinking option, and sanitized public error/status. Do not upload real manuscripts, sample papers, keys, private paths, prompts, or raw provider responses.

## Run from source

Use Python **3.11 or 3.12**, the versions in repository CI. Download and extract the source, open a terminal in the folder containing `mrc_standalone.py`, and run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pypdf==6.16.2
.\.venv\Scripts\python.exe -B -m standalone
```

The main interface opens in your local browser. For terminal diagnostics without automatic browser launch:

```powershell
.\.venv\Scripts\python.exe -B -m standalone --gui-no-browser
.\.venv\Scripts\python.exe -B -m standalone --version
.\.venv\Scripts\python.exe -B -m standalone --help
```

On other systems, the equivalent interpreter is `.venv/bin/python`; the Windows EXE cannot run there natively, and Windows packaging checks do not establish cross-platform GUI support.

### Direct CLI examples

Configure the environment key first. These commands deliberately authorize sending this invocation's manuscript to the provider. Omit the consent flag if you do not authorize transmission; `--confirm-complete` alone is a legacy statement and **does not authorize API transmission**.

```powershell
# Mode 1: standard, provider's registered default model/thinking
.\.venv\Scripts\python.exe -B -m standalone .\paper.docx --provider deepseek --mode standard --language en --identity paper-v12 --consent-to-provider-transmission --output .\standard.json

# Mode 2: strict referee, thinking off on a registered OFF-capable model
.\.venv\Scripts\python.exe -B -m standalone .\paper.docx --provider kimi --model kimi-k2.6 --mode strictness --strictness strict --reasoning disabled --consent-to-provider-transmission --output .\strict.json

# Mode 3: journal benchmark; no separate relevance precheck in CLI
.\.venv\Scripts\python.exe -B -m standalone .\paper.docx --provider deepseek --mode journal_benchmark --target-journal-name "Target Journal" --target-journal-scope "Research field and methods" --sample-papers-dir .\samples --consent-to-provider-transmission --output .\journal.json
```

For Mode 2, replace `strict` with `moderate` or `lenient` as needed. For a built distribution, replace the Python invocation with `.\release\ManuscriptRevisionClosure.exe`. `--timeout` overrides each stage's wait in seconds; `--transient-retries` accepts only `0`. `--event-log .\events.jsonl` explicitly saves privacy-bounded lifecycle events. The compatibility flag `--sample-relevance-override` is accepted but currently does not enforce or bypass a core relevance gate.

## Build on Windows

From the source root, using Windows and Python 3.11/3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_exe.ps1
```

The configured output is `release\ManuscriptRevisionClosure.exe`. The script also writes build/checksum records. Building is not the same as publishing a release or passing frozen acceptance. Validate the exact EXE before distributing it, and identify its source revision and SHA-256. Never use an earlier receipt to certify a rebuilt executable.

Repository checks (synthetic/mocked, no real manuscripts or live API calls):

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
python -B scripts/run_adversarial_probes_rc2_0.py
python -B scripts/run_adversarial_probes_rc2_1.py
```

## Privacy and boundaries

The local interface binds only to loopback, uses a random access token and Host/Origin checks, and loads no remote scripts or images. The runtime does not provide shell tools, manuscript editing, literature search, or submission. Public saved results omit API keys, full manuscript text, raw model replies, and private reasoning. Save operations are explicit; provider retention is governed by the provider's terms.

Only send manuscripts and sample excerpts you are permitted to disclose to that provider. A local GUI does not make analysis offline. The assessment is a model-assisted judgment, without independent source verification; it does not certify facts, replace peer review, or authorize submission.

For implementation history see the [Changelog](CHANGELOG.md), [provenance](PROVENANCE.md), and [interpretation contract](../standalone/AGENT.md). Historical engineering audits are snapshots, not current startup instructions.
