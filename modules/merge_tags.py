# pyright: reportMissingImports=false
import os, re, html, json, re, unicodedata
from aqt import mw
from collections import defaultdict
from aqt.utils import showInfo
from aqt.browser import Browser
from pathlib import Path
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from PyQt6.QtWidgets import QInputDialog
from ..config_manager import ConfigManager
from datetime import datetime

from .assets.scrub_match import (
    normalize,
    group_similar_notes_by_content,
)

DEBUG_MODE = False


config = ConfigManager("global_config", "merge_tags_config").load()

LOG_DIR = Path(mw.addonManager.addonsFolder()) / "Change_notes" / "logs" / "merge_tags"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}_merge_tags.log"

def log_debug(msg):
    timestamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}"
    if DEBUG_MODE:
        print(timestamped)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(timestamped + "\n")

base_tag = config.get("base_tag", "TAGS_MERGED")
date_suffix = datetime.now().strftime("%B_%d")
merged_tag = f"{base_tag}::{date_suffix}"

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

def unify_tags_on_duplicates(browser: Browser, threshold=None):
    if threshold is None:
        threshold = prompt_fuzzy_threshold()
        if threshold is None:
            return

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
        for note in notes:
            all_tags.update(note.tags)
        for note in notes:
            if set(note.tags) != all_tags:
                note.tags = sorted(all_tags.union({merged_tag}))
                note.flush()
                updated += 1
                log_debug(f"Updated tags for note {note.id} -> Tags: {note.tags}")

    mw.reset()
    log_debug(f"Completed tag merge. Updated {updated} notes.")
    showInfo(f"Updated tags on {updated} duplicate notes.")