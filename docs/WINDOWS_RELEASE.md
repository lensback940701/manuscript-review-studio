# Windows release verification

[中文说明](WINDOWS_RELEASE.zh-CN.md) · [Application guide](STANDALONE.md)

## Download and identify the build

Use the asset `manuscript-review-studio-v0.6.4.1-windows-x64.zip` from
[GitHub Releases](https://github.com/lensback940701/manuscript-review-studio/releases)
when it is published. Extract the full archive, then start
`release/ManuscriptRevisionClosure.exe`. No Python installation is needed.
The ZIP also contains source, tests, bilingual guides, license notices and the
exact build/validation receipts. The separately attached EXE works on its own.

The application compatibility version remains **0.6.4**. The distribution version
**v0.6.4.1**, source commit and binary SHA-256 identify this repaired rebuild.
`BUILD_RECEIPT.json` records the actual installed Python/build dependencies and
source commit. `VALIDATION_RECEIPT.json` binds the tests to that exact EXE.
`SHA256SUMS` covers the download assets. Inside the full ZIP,
`DISTRIBUTION_MANIFEST.json` records every included file except the manifest itself.
GitHub's automatically generated **Source code (zip/tar.gz)** omits the EXE.

## What the Windows pipeline checks

- Windows x64 source unit tests (at least the retained 391), and 23 + 59
  adversarial probes
- A fresh one-file PyInstaller build with pinned requirements, executable PE/x64
  header inspection, source-commit checks, and actual dependency versions
- Copying only the EXE into an otherwise empty temporary directory, removing
  Python/source paths from its environment, and running the frozen version command
- The copied EXE's local GUI server: page content and all three mode controls,
  authenticated ready status, unauthenticated request rejection, explicit safe
  shutdown, exit code and closed port
- The existing frozen CLI/GUI acceptance plus synthetic multimode provider
  contract checks, including thinking on/off, bounded/reopen/stop outcomes,
  invalid-contract rejection and context-budget handling
- Fresh receipts, an allowlisted clean ZIP, per-file hashes and ZIP integrity;
  old EXEs, old receipts, build folders, virtual environments and real manuscripts
  are never copied into the release

All model responses are synthetic loopback mocks. These checks do not certify
live provider availability, model quality or scientific correctness. Browser
rendering, native file dialogs and screenshots are not tested by headless CI.
The program is unsigned; follow your organization's trusted-software process
if Windows SmartScreen displays a warning. Do not disable system protection.
The known Mode 3 sample/relevance limitations in the application guide still apply.

## Maintainer build and publishing

The workflow is `.github/workflows/windows-release.yml`. It builds on
`windows-2022` with Python 3.12 x64; official actions are pinned to reviewed commits.
The build job has `contents: read`, and checkout does not persist credentials.
Only the isolated publishing job has `contents: write`; it does not execute source
or downloaded binaries and uses the ephemeral built-in GitHub token. No PAT or
additional repository secret is needed.

Publishing is deliberately limited to a push on the exact branch
`release/windows-v0.6.4.1`, or an explicit manual run with **publish** checked from
`main` or that release branch. Manual runs default to build/test only. Ordinary
pushes and pull requests cannot publish this workflow. The release tag is fixed
at `v0.6.4.1`, targets the exact tested commit, and existing releases/assets are
never overwritten. A new version requires an explicit reviewed workflow update.

For connector-based invocation, create the dedicated branch at the earlier
source commit, then move it to the reviewed workflow commit. That branch push
runs the workflow. Publishing the workflow on `main` by itself does not release.
Check the workflow's successful publishing job and actual Release assets before
announcing download availability.

For a local reproducible check, start from a clean Git checkout on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -B scripts/windows_release.py source-tests
.\build_exe.ps1
.\.venv\Scripts\python.exe -B scripts/windows_release.py validate-package
```

The publish-ready files are generated under `.build/publish`. Keep the tests,
build and packaging on the same clean commit. Run in a fresh checkout when
rebuilding; generated artifacts must never certify a different executable.
