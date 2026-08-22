# Contributing

[中文说明](CONTRIBUTING.zh-CN.md)

Contributions are welcome when they preserve the skill's narrow purpose: deciding whether a complete academic manuscript should stop general AI revision.

## Before opening a pull request

1. Use synthetic fixtures only. Never commit real manuscripts, reviewer reports, project evidence, local paths, credentials, or identifying metadata.
2. Preserve the read-only boundary. A closure decision must not authorize manuscript editing, literature search, citation repair, evidence admission, downstream skill execution, or submission.
3. Preserve evidence ceilings and the separation between substantive closure, evidence holds, and submission holds.
4. Add a regression test for any deterministic contract change.
5. Run the complete unit and adversarial suites.

```bash
python -B -m unittest discover -s tests -p "test_*.py"
python -B scripts/run_adversarial_probes_rc2_0.py
python -B scripts/run_adversarial_probes_rc2_1.py
```

## Documentation languages

Public explanatory documentation is maintained as separate English and Simplified Chinese files. Do not mix parallel translations into one page. Update both language files when a shared behavior or public contract changes.

## Pull requests

Keep changes focused. Describe the observed problem, the contract that should hold, the tests added or changed, and any compatibility impact. Do not delete a valid negative-path test merely to make a change pass.

By submitting a contribution, you agree that it is licensed under Apache License 2.0.
