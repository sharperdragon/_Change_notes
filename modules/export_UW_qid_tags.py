# -*- coding: utf-8 -*-
"""
Export UW QID tags from selected notes in the Browser.

Exports:
- Matches UW tags using configurable segment/prefix rules
- Dedupe + sorted
- Writes to Desktop with timestamp
- Copies OR-joined tags to clipboard
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

# Match tags that contain any of these full path segments.
MATCH_SEGMENTS = (
    "*UW_Tests",
)

# Match explicit tag branches (kept for backward compatibility).
MATCH_PREFIXES = (
    "#Zank::#Step2_v12::#UWorld::Step",
)

# Exclude tag branches from export even if they match include rules.
# This removes Missed-Q branches such as:
#   ##Missed-Qs::*UW_Tests::051-100::96-100::96
EXCLUDE_PREFIXES = (
    "##Missed-Qs::*UW_Tests",
)

OUTPUT_DIR = Path.home() / "Desktop"
TS_FORMAT = "%H-%M_%m-%d"  # your preferred timestamp format
OUTPUT_BASENAME = "anki_export_uw_qid_tags"
CLIPBOARD_JOINER = " OR "


@dataclass(frozen=True)
class ExportResult:
    tags: List[str]
    output_path: Path


def _now_stamp() -> str:
    return datetime.now().strftime(TS_FORMAT)


def _get_selected_note_ids(browser) -> List[int]:
    """Read selected note ids across Anki versions."""
    if hasattr(browser, "selected_notes") and callable(getattr(browser, "selected_notes")):
        return list(getattr(browser, "selected_notes")())
    if hasattr(browser, "selectedNotes") and callable(getattr(browser, "selectedNotes")):
        return list(getattr(browser, "selectedNotes")())
    return []


def _get_note_tags(note_id: int) -> List[str]:
    """Return tags for a note, as full tag strings."""
    note = mw.col.get_note(note_id)
    return list(note.tags)


def _tag_matches_uw_rules(tag: str) -> bool:
    if not tag:
        return False

    if any(tag.startswith(prefix) for prefix in EXCLUDE_PREFIXES if prefix):
        return False

    if any(tag.startswith(prefix) for prefix in MATCH_PREFIXES if prefix):
        return True

    parts = tag.split("::")
    part_set = set(parts)
    return any(seg in part_set for seg in MATCH_SEGMENTS if seg)


def _filter_matching_tags(tags: Iterable[str]) -> List[str]:
    return [t for t in tags if _tag_matches_uw_rules(t)]


def collect_matching_tags(note_ids: Iterable[int]) -> List[str]:
    """
    Collect unique UW tags across notes using configured match rules.
    Returns sorted list.
    """
    found: Set[str] = set()

    for nid in note_ids:
        note_tags = _get_note_tags(nid)
        matches = _filter_matching_tags(note_tags)
        found.update(matches)

    return sorted(found)


def export_tags_to_desktop(tags: List[str]) -> Path:
    """
    Write tags to a timestamped text file on Desktop.
    One tag per line.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{OUTPUT_BASENAME}_{_now_stamp()}.txt"
    out_path = OUTPUT_DIR / filename

    text = "\n".join(tags).strip() + ("\n" if tags else "")
    out_path.write_text(text, encoding="utf-8")

    return out_path


def copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard."""
    QApplication.clipboard().setText(text)


def run_export_for_selected_notes(browser) -> ExportResult | None:
    """
    Browser action handler: export matching UW tags for selected notes.
    """
    note_ids = _get_selected_note_ids(browser)

    if not note_ids:
        tooltip("No notes selected.")
        return None

    tags = collect_matching_tags(note_ids)
    if not tags:
        showInfo(
            "No UW QID tags matched the current rules.\n\n"
            f"Checked segments: {', '.join(MATCH_SEGMENTS) or '(none)'}\n"
            f"Checked prefixes: {', '.join(MATCH_PREFIXES) or '(none)'}\n\n"
            f"Excluded prefixes: {', '.join(EXCLUDE_PREFIXES) or '(none)'}"
        )
        return None

    out_path = export_tags_to_desktop(tags)
    copy_to_clipboard(CLIPBOARD_JOINER.join(tags))

    showInfo(
        f"Exported {len(tags)} UW QID tag(s).\n\n"
        f"Saved to:\n{out_path}\n\n"
        "Copied to clipboard."
    )

    return ExportResult(tags=tags, output_path=out_path)


def add_browser_menu_action(browser) -> None:
    """
    Add action to Browser menu.
    Call this from your add-on's browser setup hook.
    """
    action = QAction("Export UW QID tag(s)", browser)
    action.triggered.connect(lambda _checked=False: run_export_for_selected_notes(browser))

    browser.form.menuEdit.addAction(action)
