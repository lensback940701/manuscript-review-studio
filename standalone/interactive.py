"""Dependency-free interactive console fallback."""

from __future__ import annotations

from pathlib import Path

from . import __version__
from .cli import run_cli
from .providers import PROVIDERS, reasoning_profile


def _ask_choice(prompt: str, choices: tuple[str, ...], default: str) -> str:
    while True:
        value = input(f"{prompt} [{'/'.join(choices)}] (default {default}): ").strip().casefold()
        if not value:
            return default
        if value in choices:
            return value
        print("Invalid choice / 选项无效。")


def _ask_yes_no(prompt: str) -> bool:
    while True:
        value = input(prompt + " [y/N]: ").strip().casefold()
        if value in {"y", "yes", "是"}:
            return True
        if value in {"", "n", "no", "否"}:
            return False
        print("Please enter y or n / 请输入 y 或 n。")


def run_interactive() -> int:
    print(f"Manuscript Revision Closure Standalone {__version__}")
    print("Read-only closure; API keys are read from environment variables only.")
    print("只读修订截止判断；API key 仅从环境变量读取。\n")
    manuscript = input("Manuscript path / 稿件路径: ").strip().strip('"')
    if not manuscript:
        print("No manuscript supplied / 未提供稿件。")
        return 2
    provider = _ask_choice("Provider / 模型提供商", ("deepseek", "kimi", "gemini"), "deepseek")
    spec = PROVIDERS[provider]
    model = input(f"Model / 模型 (Enter for {spec.default_model}): ").strip()
    selected_model = model or spec.default_model
    profile = reasoning_profile(provider, selected_model)
    reasoning_values = tuple(item["value"] for item in profile["options"])
    reasoning = _ask_choice("Reasoning / 思考设置", reasoning_values, profile["default"])
    print(profile["note"])
    language = _ask_choice("Output language / 输出语言", ("zh", "en"), "zh")
    identity = input(f"Stable identity / 稳定稿件身份 (Enter for {Path(manuscript).name}): ").strip()
    confirmed = _ask_yes_no("Confirm this is the complete identifiable current manuscript? / 确认这是身份明确的完整当前稿件？")
    output = input("Optional result JSON path / 可选结果 JSON 保存路径 (Enter to display only): ").strip().strip('"')
    args = [manuscript, "--provider", provider, "--language", language]
    if model:
        args.extend(["--model", model])
    args.extend(["--reasoning", reasoning])
    if identity:
        args.extend(["--identity", identity])
    if confirmed:
        args.append("--confirm-complete")
    if output:
        args.extend(["--output", output])
    code = run_cli(args)
    input("\nPress Enter to close / 按 Enter 关闭…")
    return code
