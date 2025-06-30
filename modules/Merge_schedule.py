import re
from aqt import mw
from aqt.utils import tooltip
from anki.notes import Note
from difflib import SequenceMatcher
import os
# Use normalized and scrubbed text from scrub_match for fuzzy matching
from .assets.scrub_match import normalize_and_scrub

# ---------------- CONFIG ---------------- #
CONFIG = mw.addonManager.getConfig(__name__)
MERGE_CONF = CONFIG.get("merge_scheduling", {})
THRESHOLD = int(MERGE_CONF.get("merge_similarity_threshold", 85))
FIELD_IDX = int(MERGE_CONF.get("merge_field_index", 0))
LOG_PATH = MERGE_CONF.get("scheduling_merge_log_path", "merged_scheduling.log")
LOG_DIR = mw.addonManager.addonFolder(__name__)
LOG_FILE = os.path.join(LOG_DIR, LOG_PATH)
TAG_ON_MERGE = MERGE_CONF.get("tag_on_merge", "")
# --------------------------------------- #

def similarity(a: str, b: str) -> float:
    """Use normalized and scrubbed text from scrub_match for fuzzy matching."""
    return SequenceMatcher(None, normalize_and_scrub(a), normalize_and_scrub(b)).ratio() * 100

def get_selected_notes() -> list[Note]:
    return [mw.col.get_note(nid) for nid in mw.selected_notes()]

def merge_scheduling(source_note: Note, target_note: Note) -> bool:
    """Copy scheduling from source to target if source has higher interval and tag both."""
    source_card = source_note.cards()[0]
    target_card = target_note.cards()[0]

    if source_card.ivl > target_card.ivl:
        target_card.ivl = source_card.ivl
        target_card.due = source_card.due
        target_card.ease = source_card.ease
        target_card.reps = source_card.reps
        target_card.lapses = source_card.lapses
        target_card.flush()

        # Apply tags if specified
        if TAG_ON_MERGE:
            for note in (source_note, target_note):
                if TAG_ON_MERGE not in note.tags:
                    note.add_tag(TAG_ON_MERGE)
                    note.flush()

        log_merge(source_note.id, target_note.id)
        return True
    return False

def log_merge(source_id: int, target_id: int):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"Merged scheduling: {source_id} → {target_id}\n")

def run_merge_scheduling():
    notes = get_selected_notes()
    matched_pairs = []
    similarity_map = {}

    # Build similarity map: note.id -> [matching note objects]
    for i, note1 in enumerate(notes):
        for j, note2 in enumerate(notes[i+1:], i+1):
            field1 = note1.fields[FIELD_IDX]
            field2 = note2.fields[FIELD_IDX]
            if similarity(field1, field2) >= THRESHOLD:
                similarity_map.setdefault(note1.id, []).append(note2)
                similarity_map.setdefault(note2.id, []).append(note1)

    # Filter for unique 1-to-1 matches only
    for note_id, matches in similarity_map.items():
        if len(matches) == 1:
            other = matches[0]
            if similarity_map.get(other.id, []) == [mw.col.get_note(note_id)]:
                matched_pairs.append((mw.col.get_note(note_id), other))

    total = 0
    seen_ids = set()
    for note1, note2 in matched_pairs:
        if note1.id in seen_ids or note2.id in seen_ids:
            continue  # avoid double-processing
        seen_ids.update([note1.id, note2.id])

        card1, card2 = note1.cards()[0], note2.cards()[0]
        # Pick source by highest reps
        source, target = (note1, note2) if card1.reps > card2.reps else (note2, note1)
        if merge_scheduling(source, target):
            total += 1

    tooltip(f"{total} note pairs had scheduling merged.")