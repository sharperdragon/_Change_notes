import re, sys
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from PyQt6.QtWidgets import QInputDialog
from collections import defaultdict

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw
from aqt.utils import showInfo
from aqt.browser import Browser

# Dynamically add the modules directory to sys.path
from ..config_manager import ConfigManager 
from .assets.scrub_match import (
    normalize
)
from .utils import prompt_similarity_threshold

config_manager = ConfigManager("_Change_notes")
config = ConfigManager("global_config", "merge_tags_config").load()
config = config_manager.load()
base_tag = config.get("base_tag", "TAGS_MERGED")
date_suffix = datetime.now().strftime("%B_%d")
merged_tag = f"{base_tag}::{date_suffix}"

DEBUG_MODE = False

# Read parents from the new key; fallback to deprecated key if needed
_parents_new = config.get("merge_only_parents")
_parents_old = config.get("merge_only_from_parents", [])
ALLOWED_PARENTS = [p for p in (_parents_new if _parents_new is not None else _parents_old) or [] if p]
ALLOWED_PARENTS_LOWER = [p.lower() for p in ALLOWED_PARENTS]


LOG_DIR = Path(mw.addonManager.addonsFolder()) / "_Change_notes" / "logs" / "merge_tags"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m')}_merge_tags.log"


# --- Config parsing helpers ---
def _parse_bool(val, default=False):
    """
    Normalize truthy strings like 'true'/'False' or integers 0/1 to a real bool.
    Falls back to default if value is None.
    """
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in {"true", "t", "yes", "y", "1"}:
            return True
        if v in {"false", "f", "no", "n", "0"}:
            return False
    return default



# Read new key; default is False, meaning "ignore parent filter"
MERGE_SELECT_ONLY = _parse_bool(config.get("merge_select_only"), default=False)

# Helper: case-insensitive parent check
def _is_tag_in_parents(tag: str) -> bool:
    """
    Returns True if tag equals a parent or starts with 'parent::'
    Comparison is case-insensitive.
    """
    t = tag.lower()
    for pl in ALLOWED_PARENTS_LOWER:
        if t == pl or t.startswith(pl + "::"):
            return True
    return False

# Gate: if MERGE_SELECT_ONLY is False, allow all tags (parents list ignored per spec)
def tag_is_allowed(tag: str) -> bool:
    if not MERGE_SELECT_ONLY:
        return True
    return _is_tag_in_parents(tag)





def log_debug(msg):
    timestamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}"
    if DEBUG_MODE:
        print(timestamped)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(timestamped + "\n")

# Log effective config (once per module import)
log_debug(f"Config — MERGE_SELECT_ONLY={MERGE_SELECT_ONLY}, ALLOWED_PARENTS={ALLOWED_PARENTS if MERGE_SELECT_ONLY else '(ignored)'}")

# --- Fuzzy matching helper ---

def prompt_fuzzy_threshold(default=None):
    """Prompt user for fuzzy threshold (0–100) using a popup input dialog."""
    if default is None:
        default = int(float(config.get("default_fuzzy", 0.98)) * 100)
    val, ok = QInputDialog.getInt(
        mw, "Set Fuzzy Match Threshold",
        "Select fuzzy match threshold (0 = loose, 100 = strict):",
        default, 85, 100, 1
    )
    if ok:
        return val / 100  # Normalize to 0.0–1.0 range
    return None

def unify_tags_on_duplicates(browser: Browser, threshold: float | None = None):
    skipped_by_parent_filter = 0
    log_debug(f"Run start — threshold={threshold}, MERGE_SELECT_ONLY={MERGE_SELECT_ONLY}, parents={ALLOWED_PARENTS if MERGE_SELECT_ONLY else '(ignored)'}")

    from anki.notes import Note
    col = browser.mw.col
    selected_nids = browser.selectedNotes()
    log_debug(f"Selected NIDs: {selected_nids}")
    field_name = config.get("comparison_field", "Text")
    norm_to_nids = {}

    # Build map of normalized text -> NIDs
    nid_to_norm = {}
    for nid in selected_nids:
        note = col.get_note(nid)
        flds = col.models.field_names(note.model())
        if field_name in flds:
            raw = note.fields[flds.index(field_name)]
            norm = normalize(raw)
            if norm:
                nid_to_norm[nid] = norm
    log_debug(f"Normalized NID Map: {nid_to_norm}")

    clustered = []
    visited = set()

    # Group NIDs by fuzzy-similar normalized values
    for nid1, norm1 in nid_to_norm.items():
        if nid1 in visited:
            continue
        group = [nid1]
        visited.add(nid1)
        for nid2, norm2 in nid_to_norm.items():
            if nid2 in visited:
                continue
            if SequenceMatcher(None, norm1, norm2).ratio() >= threshold:
                group.append(nid2)
                visited.add(nid2)
        clustered.append(group)
    log_debug(f"Formed {len(clustered)} clusters with threshold {threshold}")

    updated = 0
    for group in clustered:
        if len(group) < 2:
            continue
        all_tags = set()
        notes = [col.get_note(nid) for nid in group]
        # $ only collect allowed tags for merging when gated on
        for note in notes:
            for tag in note.tags:
                if tag_is_allowed(tag):
                    all_tags.add(tag)
                else:
                    skipped_by_parent_filter += 1
        for note in notes:
            existing_allowed_tags = {tag for tag in note.tags if tag_is_allowed(tag)}
            if existing_allowed_tags != all_tags:
                note.tags = sorted(all_tags.union({merged_tag}))
                note.flush()
                updated += 1
                log_debug(f"Updated tags for note {note.id} -> Tags: {note.tags}")

    mw.reset()
    log_debug(f"Completed tag merge. Updated {updated} notes. Skipped tags by parent filter: {skipped_by_parent_filter}")
    info_msg = f"Updated tags on {updated} duplicate notes."
    if MERGE_SELECT_ONLY:
        info_msg += f"\n(Parent filter active; skipped tags: {skipped_by_parent_filter})"
    showInfo(info_msg)


def unify_tags_main(browser: Browser | None = None):
    if browser is None:
        browser = mw.form.browser

    selected_nids = browser.selectedNotes()
    if not selected_nids:
        showInfo("No notes selected.")
        return

    # ? UI config fetch
    default_fuzzy = float(config.get("default_fuzzy", 0.97))
    min_fuzzy = float(config.get("min_fuzzy", 0.80))
    max_fuzzy = float(config.get("max_fuzzy", 1.0))
    ask_each = _parse_bool(config.get("ask_fuzzy_each_time"), default=True)

    # Decide threshold (prompt or silent clamp)
    if ask_each:
        default_pct = max(min(int(default_fuzzy * 100), 100), 0)
        t = prompt_similarity_threshold(default=default_pct)
        if t is None:
            return  # user canceled
        threshold = max(min(t, max_fuzzy), min_fuzzy)
    else:
        threshold = max(min(default_fuzzy, max_fuzzy), min_fuzzy)

    unify_tags_on_duplicates(browser, threshold=threshold)
