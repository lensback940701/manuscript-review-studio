# Security Policy

[中文说明](SECURITY.zh-CN.md)

## Supported version

Security fixes are currently applied to the latest `0.2.x` release candidate.

## Reporting a vulnerability

Do not publish manuscript data, confidential review material, local file paths, credentials, API keys, or exploit details in a public issue.

Use GitHub Private Vulnerability Reporting or a private Security Advisory when the repository enables it. If neither channel is available, contact the repository owner through the [GitHub profile](https://github.com/lensback940701) and request a private reporting channel before sharing details.

Include the affected version, a minimal synthetic reproduction, expected and observed behavior, and the security impact. Real manuscripts and project evidence are never required for a report.

## Scope

Relevant reports include unauthorized file writes, leakage of detailed internal review content, caller-controlled hold-text echo, receipt reuse across changed semantic content, unsafe path handling, or unexpected network activity.

The skill does not provide a secure execution sandbox by itself. Host-platform retention, tool permissions, and filesystem or network controls remain properties of the environment in which it runs.
