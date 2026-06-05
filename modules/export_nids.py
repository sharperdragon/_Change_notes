# pyright: reportMissingImports=false
from __future__ import annotations


import os
import re
from datetime import datetime
from typing import Any, List, Tuple

from .utils import prompt_checkbox_option


"""
Export Selected NIDs – helper module (Anki 2.1.60+ / 25.x, Qt6)

Usage from your __init__.py:
    from .export_selected_nids import create_export_nids_action

    # inside your Browser menu wiring:
    action = create_export_nids_action(parent=browser, mw=mw, browser=browser)
    some_menu.addAction(action)

Design:
- No auto-injection. You control where/when to add the action.
- Compatible with browser.selected_notes() (new) and selectedNotes() (old).
- Copies a comma-separated NID list and can optionally save it to your Desktop.
"""



# Anki / Qt imports (use Anki shims to stay version-tolerant)
try:
    from aqt import mw
    from aqt.qt import QAction, QApplication, QWidget
    from aqt.utils import tooltip, showText
except Exception:
    # Fallbacks if static checking; at runtime Anki provides these.
    mw = None  # type: ignore
    QApplication = None  # type: ignore
    QWidget = object  # type: ignore

    class QAction:  # type: ignore
        def __init__(self, *a, **k): ...


_FNAME_SAFE = re.compile(r'[^\w\-. ]+', re.UNICODE)
EXPORT_BASENAME = "selected_nids"  # user-tunable
EXPORT_FOLDER_NAME = "NID export"  # user-tunable
WRITE_TXT_TO_DESKTOP_DEFAULT = True  # user-tunable
WRITE_TXT_TO_DESKTOP_LABEL = "Write .txt file to Desktop"  # user-tunable
EXPORT_OPTIONS_TITLE = "Export Selected NIDs"  # user-tunable
WRITE_TXT_TO_DESKTOP_MEMORY_SECTION = "global_config"  # user-tunable
WRITE_TXT_TO_DESKTOP_MEMORY_KEY = "export_nids_write_txt_to_desktop"  # user-tunable


def _sanitize_filename(name: str) -> str:
    s = name.strip()
    s = _FNAME_SAFE.sub('_', s)           # remove illegal chars
    s = re.sub(r'__+', '_', s)            # collapse repeats
    s = s.strip('._ ')                    # trim noisy ends
    return s or "selected_nids"

# ---------- Core helpers ----------

def _get_selected_nids(browser: Any) -> List[int]:
    """
    Return the selected Note IDs (NIDs) from the Browser.

    Supports both:
      - browser.selected_notes()  (newer Anki)
      - browser.selectedNotes()   (older Anki)
    """
    # NOTE: Try new snake_case first.
    if hasattr(browser, "selected_notes") and callable(getattr(browser, "selected_notes")):
        return list(getattr(browser, "selected_notes")())
    # Fallback for older Anki
    if hasattr(browser, "selectedNotes") and callable(getattr(browser, "selectedNotes")):
        return list(getattr(browser, "selectedNotes")())
    return []


def _copy_nids_to_clipboard(nids_or_text) -> None:
    """
    Copy to the system clipboard. Accepts either:
      - Sequence[int] of NIDs (newline-separated), or
      - A single string (copied as-is)
    """
    app = QApplication.instance()
    if not app:
        return
    cb = app.clipboard()
    if isinstance(nids_or_text, str):
        cb.setText(nids_or_text)
    else:
        cb.setText("\n".join(str(n) for n in nids_or_text))


# New helper to ensure Desktop export directory exists
def _ensure_export_dir() -> str:
    """Ensure the Desktop export directory exists and return its path."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    export_dir = os.path.join(desktop, EXPORT_FOLDER_NAME)
    os.makedirs(export_dir, exist_ok=True)
    return export_dir


# New helper: write arbitrary text

def _write_text_to_path(text: str, path: str) -> Tuple[bool, str]:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return True, f"Saved to: {path}"
    except Exception as e:
        return False, f"Failed to save to {path}: {e!r}"


# New helper: write error log to Desktop export folder
def _write_error_log(details: str) -> str:
    """Write an error report to the Desktop export folder and return the path.

    If writing fails, returns an empty string.
    """
    try:
        export_dir = _ensure_export_dir()
        ts = datetime.now().strftime("%H-%M_%m-%d")
        log_path = os.path.join(export_dir, f"export_nids_error_{ts}.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(details)
        return log_path
    except Exception:
        return ""


def _prompt_write_txt_to_desktop(parent: Any) -> bool | None:
    """Ask whether to write a Desktop .txt file. Returns None if canceled."""
    return prompt_checkbox_option(
        title=EXPORT_OPTIONS_TITLE,
        checkbox_label=WRITE_TXT_TO_DESKTOP_LABEL,
        checked=WRITE_TXT_TO_DESKTOP_DEFAULT,
        remember_section=WRITE_TXT_TO_DESKTOP_MEMORY_SECTION,
        remember_key=WRITE_TXT_TO_DESKTOP_MEMORY_KEY,
        parent=parent,
    )


# ---------- Public entry point you call from __init__ ----------

def create_export_nids_action(
    parent: Any,
    mw,  # aqt.mw – kept untyped to avoid mypy/pyright noise in mixed envs
    browser: Any,
    *,
    title: str = "Export Selected NIDs…",
):
    """
    Create a QAction that:
    - Collects selected note IDs from the Browser
    - Optionally writes one file to your Desktop:
        1) Comma-separated NIDs (e.g., "121451,441451,...")
        2) Uses an automatic filename (no prompt)
    - Copies the simple list to the clipboard
    - Shows a short tooltip summary
    """
    action = QAction(title, parent)

    def _run() -> None:
        # 1) Collect selection
        nids = _get_selected_nids(browser)
        if not nids:
            tooltip("No notes selected.")
            return

        write_txt = _prompt_write_txt_to_desktop(browser)
        if write_txt is None:
            tooltip("Export canceled.")
            return

        # 2) Use automatic base name (no prompt)
        base = _sanitize_filename(EXPORT_BASENAME)

        # 3) Build content string
        comma_str = ",".join(str(n) for n in nids)
        _copy_nids_to_clipboard(comma_str)

        # 4) Optionally write file
        if write_txt:
            export_dir = _ensure_export_dir()
            ts = datetime.now().strftime("%H-%M_%m-%d")
            simple_path = os.path.join(export_dir, f"{base}_{ts}_simple.txt")
            ok1, msg1 = _write_text_to_path(comma_str, simple_path)

            if ok1:
                tooltip(
                    f"Saved {len(nids)} NIDs.\n"
                    f"Saved to Desktop/{EXPORT_FOLDER_NAME}\n"
                    f"(Copied simple NID list to clipboard.)"
                )
                return

            details = msg1
            log_path = _write_error_log(details)

            extra = f"\n\nError log: {log_path}" if log_path else ""
            try:
                showText(
                    details + extra,
                    title="Export NIDs Error",
                    plain_text=True,
                )
            except Exception:
                if log_path:
                    tooltip(f"Export completed with errors.\nError log: {log_path}")
                else:
                    tooltip("Export completed with errors (failed to write error log).")
            return

        # 5) Report (no file write)
        tooltip(
            f"Saved {len(nids)} NIDs.\n"
            "Desktop .txt save skipped.\n"
            "(Copied simple NID list to clipboard.)"
        )
        return

    # Connect on creation
    action.triggered.connect(_run)  # type: ignore[attr-defined]
    return action
