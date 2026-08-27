"""Launch the local GUI by default, while preserving console and CLI routes."""

from __future__ import annotations

import sys

from .cli import run_cli
from .interactive import run_interactive
from .native_dialogs import show_error_box
from .web_gui import run_web_gui


def main() -> int:
    if len(sys.argv) == 1:
        try:
            return run_web_gui()
        except Exception as exc:
            show_error_box(str(exc))
            return 2
    if sys.argv[1:] == ["--gui"]:
        return run_web_gui()
    if sys.argv[1:] == ["--gui-no-browser"]:
        return run_web_gui(open_browser=False, hide_console=False)
    if sys.argv[1:] == ["--console"]:
        return run_interactive()
    return run_cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
