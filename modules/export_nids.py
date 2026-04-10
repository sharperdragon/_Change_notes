# pyright: reportMissingImports=false
from __future__ import annotations


import os
import re
from datetime import datetime
from typing import Any, List, Sequence, Tuple


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
- Saves a comma-separated NID list to your Desktop.
- Splits the Anki query into safe chunks to avoid SQLite expression depth limits; writes them into ONE file separated by two blank lines.
"""



# Anki / Qt imports (use Anki shims to stay version-tolerant)
try:
    from aqt import mw
    from aqt.qt import QAction, QApplication, QFileDialog, QWidget, QInputDialog
    from aqt.utils import tooltip, showText
except Exception:
    # Fallbacks if static checking; at runtime Anki provides these.
    mw = None  # type: ignore
    QApplication = None  # type: ignore
    QWidget = object  # type: ignore

    class QAction:  # type: ignore
        def __init__(self, *a, **k): ...
    class QFileDialog:  # type: ignore
        AnyFile = 0
        @staticmethod
        def getSaveFileName(*a, **k): return ("", "")




_FNAME_SAFE = re.compile(r'[^\w\-. ]+', re.UNICODE)
CHUNK_SIZE = 850  # keep chunk size configurable at the top of the script


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
    export_dir = os.path.join(desktop, "NID export")
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


# New helper: write error log to Desktop/NID export
def _write_error_log(details: str) -> str:
    """Write an error report to ~/Desktop/NID export and return the path.

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
    - Writes two files to your Desktop:
        1) Comma-separated NIDs (e.g., "121451, 441451, ...")
        2) Anki query string (e.g., "NID:121451 OR NID:441451 ...")
    - Copies the first query chunk to the clipboard
    - Shows a short tooltip summary
    """
    action = QAction(title, parent)

    def _run() -> None:
        # 1) Collect selection
        nids = _get_selected_nids(browser)
        if not nids:
            tooltip("No notes selected.")
            return

        # 2) Ask user for a base name (run-time, not import-time)
        try:
            base_text, ok = QInputDialog.getText(parent, "Export name", "Base name for files:")
        except Exception:
            ok = False
            base_text = ""
        if not ok:
            tooltip("Export cancelled.")
            return
        base = _sanitize_filename(base_text) or "selected_nids"

        # 3) Build content strings (unchanged logic)
        comma_str = ", ".join(str(n) for n in nids)

        def _chunks(seq, size):
            for i in range(0, len(seq), size):
                yield seq[i:i+size]

        query_chunks = [
            " OR ".join(f"NID:{n}" for n in chunk)
            for chunk in _chunks(nids, CHUNK_SIZE)
        ]
        # Two empty lines between chunks -> join with 3 newlines
        query_text = ("\n\n\n").join(query_chunks)

        # 4) Paths with user base name + timestamp (ensure export dir exists)
        export_dir = _ensure_export_dir()
        ts = datetime.now().strftime("%H-%M_%m-%d")
        simple_path = os.path.join(export_dir, f"{base}_{ts}_simple.txt")
        query_path  = os.path.join(export_dir, f"{base}_{ts}_query.txt")

        # 5) Write files
        ok1, msg1 = _write_text_to_path(comma_str, simple_path)
        ok2, msg2 = _write_text_to_path(query_text, query_path)

        # 6) Copy first chunk to clipboard for convenience
        if query_chunks:
            _copy_nids_to_clipboard(query_chunks[0])

        # 7) Report
        if ok1 and ok2:
            tooltip(
                f"Saved {len(nids)} NIDs.\n"
                f"- {simple_path}\n"
                f"- {query_path}\n"
                f"(Copied CHUNK 1 to clipboard.)"
            )
        else:
            details = "\n".join([msg1, msg2])
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

    # Connect on creation
    action.triggered.connect(_run)  # type: ignore[attr-defined]
    return action
