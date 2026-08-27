"""Windows common file dialogs without Tk or third-party GUI packages."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path


OFN_OVERWRITEPROMPT = 0x00000002
OFN_NOCHANGEDIR = 0x00000008
OFN_PATHMUSTEXIST = 0x00000800
OFN_FILEMUSTEXIST = 0x00001000
OFN_EXPLORER = 0x00080000


class NativeDialogError(RuntimeError):
    """Raised when a native dialog fails for a reason other than cancellation."""


if os.name == "nt":
    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD),
            ("hwndOwner", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR),
            ("lpstrCustomFilter", wintypes.LPWSTR),
            ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", wintypes.LPWSTR),
            ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR),
            ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD),
            ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR),
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD),
        ]


def _dialog(*, save: bool, title: str, filters: str, default_extension: str | None = None) -> Path | None:
    if os.name != "nt":
        raise NativeDialogError("native file dialogs are available only on Windows")
    buffer = ctypes.create_unicode_buffer(32_768)
    dialog = OPENFILENAMEW()
    dialog.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    dialog.lpstrFilter = filters
    dialog.nFilterIndex = 1
    dialog.lpstrFile = ctypes.cast(buffer, wintypes.LPWSTR)
    dialog.nMaxFile = len(buffer)
    dialog.lpstrTitle = title
    dialog.lpstrDefExt = default_extension
    dialog.Flags = OFN_EXPLORER | OFN_NOCHANGEDIR | OFN_PATHMUSTEXIST
    dialog.Flags |= OFN_OVERWRITEPROMPT if save else OFN_FILEMUSTEXIST
    comdlg32 = ctypes.windll.comdlg32
    function = comdlg32.GetSaveFileNameW if save else comdlg32.GetOpenFileNameW
    if function(ctypes.byref(dialog)):
        return Path(buffer.value).resolve()
    error_code = comdlg32.CommDlgExtendedError()
    if error_code:
        raise NativeDialogError(f"Windows common dialog failed with code {error_code}")
    return None


def pick_manuscript() -> Path | None:
    return _dialog(
        save=False,
        title="选择完整当前稿件 / Select complete current manuscript",
        filters=(
            "Supported manuscripts\0*.txt;*.md;*.markdown;*.rst;*.html;*.htm;*.docx;*.pdf\0"
            "Word documents\0*.docx\0PDF documents\0*.pdf\0"
            "Text and Markdown\0*.txt;*.md;*.markdown;*.rst\0All files\0*.*\0\0"
        ),
    )


def pick_prior_receipt() -> Path | None:
    return _dialog(
        save=False,
        title="选择既有最小收据 / Select prior minimal receipt",
        filters="JSON files\0*.json\0All files\0*.*\0\0",
    )


def pick_result_destination() -> Path | None:
    return _dialog(
        save=True,
        title="保存公开 Closure Card 与最小收据 / Save public result",
        filters="JSON files\0*.json\0All files\0*.*\0\0",
        default_extension="json",
    )


def pick_interpretation_destination() -> Path | None:
    return _dialog(
        save=True,
        title="保存中文解读文档 / Save Chinese interpretation",
        filters="Markdown files\0*.md\0Text files\0*.txt\0All files\0*.*\0\0",
        default_extension="md",
    )


def hide_console_window() -> None:
    """Hide the console only for the double-click GUI route."""

    if os.name != "nt":
        return
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    window = kernel32.GetConsoleWindow()
    if window:
        user32.ShowWindow(window, 0)


def show_error_box(message: str) -> None:
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, "Manuscript Revision Closure", 0x10)
