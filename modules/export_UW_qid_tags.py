# -*- coding: utf-8 -*-
"""
Export tags matching a prefix from selected notes in the Browser.

Exports:
- Only tags beginning with TAG_PREFIX
- Dedupe + sorted
- Writes to Desktop with timestamp
- Copies to clipboard
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Set

from aqt import mw
from aqt.qt import QAction, QApplication
from aqt.utils import showInfo, tooltip

# ----------------------------
# User-configurable constants
# ----------------------------

TAG_PREFIX = "#Zank::#Step2_v12::#UWorld::Step"
OUTPUT_DIR = Path("/Users/claytongoddard/Desktop")
TS_FORMAT = "%H-%M_%m-%d"  # your preferred timestamp format


@dataclass(frozen=True)
class ExportResult:
    tags: List[str]
    output_path: Path


def _now_stamp() -> str:
    return datetime.now().strftime(TS_FORMAT)


def _get_note_tags(note_id: int) -> List[str]:
    """Return tags for a note, as full tag strings."""
    note = mw.col.get_note(note_id)
    # note.tags is List[str]
    return list(note.tags)


def _filter_tags_by_prefix(tags: Iterable[str], prefix: str) -> List[str]:
    """Keep only tags that begin with prefix."""
    return [t for t in tags if t.startswith(prefix)]


def collect_matching_tags(note_ids: Iterable[int], prefix: str) -> List[str]:
    """
    Collect unique tags across notes that begin with prefix.
    Returns sorted list.
    """
    found: Set[str] = set()

    for nid in note_ids:
        note_tags = _get_note_tags(nid)
        matches = _filter_tags_by_prefix(note_tags, prefix)
        found.update(matches)

    return sorted(found)


def export_tags_to_desktop(tags: List[str]) -> Path:
    """
    Write tags to a timestamped text file on Desktop.
    One tag per line.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"anki_export_tags_{_now_stamp()}.txt"
    out_path = OUTPUT_DIR / filename

    text = "\n".join(tags).strip() + ("\n" if tags else "")
    out_path.write_text(text, encoding="utf-8")

    return out_path


def copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard."""
    QApplication.clipboard().setText(text)


def run_export_for_selected_notes(browser) -> ExportResult | None:
    """
    Browser action handler: export matching tags for selected notes.
    """
    # Browser selectedNotes() returns note ids
    note_ids = browser.selectedNotes()

    if not note_ids:
        tooltip("No notes selected.")
        return None

    tags = collect_matching_tags(note_ids, TAG_PREFIX)

    # Write file + clipboard
    out_path = export_tags_to_desktop(tags)
    copy_to_clipboard("\n".join(tags))

    # Minimal feedback
    showInfo(
        f"Exported {len(tags)} tag(s).\n\n"
        f"Prefix:\n{TAG_PREFIX}\n\n"
        f"Saved to:\n{out_path}\n\n"
        f"Copied to clipboard."
    )

    return ExportResult(tags=tags, output_path=out_path)


def add_browser_menu_action(browser) -> None:
    """
    Add action to Browser menu.
    Call this from your add-on's browser setup hook.
    """
    action = QAction(
        "Export UWorld Step tags (#Zank::#Step2_v12::#UWorld::Step…)", browser
    )
    action.triggered.connect(lambda: run_export_for_selected_notes(browser))

    # Add under Edit menu by default (common pattern)
    browser.form.menuEdit.addAction(action)
