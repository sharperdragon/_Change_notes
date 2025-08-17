# pyright: reportMissingImports=false
import  time, datetime, string
from pathlib import Path
from ...config_manager import ConfigManager
from PyQt6.QtWidgets import QInputDialog
from aqt import mw
from aqt.utils import showInfo
from datetime import datetime
import hashlib
from ..assets.scrub_match import (
    group_similar_notes_by_content,
)
from ...config_manager import ConfigManager

config_manager = ConfigManager("global_config", "tag_dupes_config")



config = config_manager.load()

DEBUG_MODE = False  # Set to True to enable verbose debug logging
now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
DEBUG_LOG_PATH = (Path(__file__).parent / (config.get("log_folder") or "logs") / "tag_dupes" / f"debug_log_{now_str}.txt")

def log_debug(msg: str, debug_mode=DEBUG_MODE):
    timestamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(timestamped + "\n")
    except Exception as e:
        print(f"[LOGGER ERROR] {e}")
    if debug_mode:
        print(timestamped)


def safe_cast_to_int(nid):
    if isinstance(nid, int):
        return nid
    try:
        return int(str(nid).strip())
    except Exception:
        log_debug(f"⚠️ Skipping invalid NID: {repr(nid)}")
        return None



BASE_TAG_LABEL = config.get("base_tag", "DUPE_Tagging")
def is_valid_tag(tag):
    return all(c in string.ascii_letters + string.digits + "_-" for c in tag)
FIELD_TO_COMPARE = config.get("comparison_field", "Text")
TAG_UNMATCHED = config.get("tag_unmatched", "false").lower() == "true"
MULTI_CHILD_LABEL = config.get("multi_tag_child", "multiple")
log_dir_path = (Path(__file__).parent / "logs" / "merge_tags").resolve()
log_dir_path.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
log_debug(f"Config: BASE_TAG_LABEL={BASE_TAG_LABEL}, FIELD_TO_COMPARE={FIELD_TO_COMPARE}, TAG_UNMATCHED={TAG_UNMATCHED}, MULTI_CHILD_LABEL={MULTI_CHILD_LABEL}, log_folder={(config.get('log_folder') or 'logs')}")
log_debug(f"Log directory: {log_dir_path}")


def prompt_fuzzy_threshold(default=98):
    val, ok = QInputDialog.getInt(
        mw,
        "Set Fuzzy Match Threshold",
        "Select fuzzy match threshold (0 = loose, 100 = strict):",
        default, 0, 100, 1
    )
    if ok:
        return val / 100
    return None


def run_tag_dupes(browser=None, debug=None):
    if debug is None:
        debug = DEBUG_MODE
    if DEBUG_LOG_PATH.exists():
        try:
            DEBUG_LOG_PATH.unlink()
        except Exception as e:
            log_debug(f"⚠️ Could not clear previous debug log: {e}", debug_mode=debug)

    def try_get_note(nid):
        try:
            return mw.col.get_note(nid)
        except Exception as e:
            log_debug(f"⚠️ Could not load note {nid}: {e}", debug_mode=debug)
            return None

    if not browser or not hasattr(browser, "selectedNotes"):
        log_debug("❌ This function must be run from the Anki browser.", debug_mode=debug)
        showInfo("Tag Dupes Error: must run from the Anki browser.")
        return
    fuzzy_threshold = prompt_fuzzy_threshold()
    if fuzzy_threshold is None:
        log_debug("🚫 Cancelled by user.", debug_mode=debug)
        showInfo("Tag Dupes cancelled by user.")
        return

    if not is_valid_tag(BASE_TAG_LABEL):
        log_debug(f"❌ Invalid base tag label: {BASE_TAG_LABEL}", debug_mode=debug)
        showInfo("Invalid tag label in config. Please use alphanumeric or _/- characters.")
        return

    match_tag_label = f"{BASE_TAG_LABEL}_matchf{int(fuzzy_threshold * 100)}"
    multi_tag_label = f"{BASE_TAG_LABEL}_GT2_Match_f{int(fuzzy_threshold * 100)}"
    unmatched_tag_label = f"{BASE_TAG_LABEL}_No-Matchf{int(fuzzy_threshold * 100)}"

    # === MAIN EXECUTION ===

    selected_nids = browser.selectedNotes()
    selected_nids = set(selected_nids)  # ensure it's a set for fast lookup
    log_debug(f"✅ Firing tag_dupes on {len(selected_nids)} selected notes", debug_mode=debug)
    log_debug(f"📋 Selected NIDs: {selected_nids}", debug_mode=debug)
    if not selected_nids:
        log_debug("⚠️ No notes selected in the browser.", debug_mode=debug)
        showInfo("Tag Dupes: no notes selected.")
        return
    selected_notes = [try_get_note(nid) for nid in selected_nids]
    log_debug(f"🧠 Retrieved note objects: {[note.id for note in selected_notes if note]}", debug_mode=debug)
    missing = sum(1 for note in selected_notes if note is None)
    if missing:
        log_debug(f"⚠️ {missing} selected notes could not be loaded and will be skipped.", debug_mode=debug)

    # Defensive check: ensure selected_notes contains only valid note objects
    if not all(note and hasattr(note, "fields") for note in selected_notes):
        log_debug("❌ One or more selected notes could not be retrieved properly.", debug_mode=debug)
        return

    # Clean up log files older than 24 hours

    now = time.time()
    cutoff_seconds = 24 * 60 * 60  # 24 hours

    tag_dupes_log_dir = log_dir_path / "tag_dupes"
    tag_dupes_log_dir.mkdir(parents=True, exist_ok=True)

    deleted_count = 0
    for file in tag_dupes_log_dir.glob("*.txt"):
        if file.is_file() and now - file.stat().st_mtime > cutoff_seconds:
            try:
                file.unlink()
                deleted_count += 1
            except Exception as e:
                log_debug(f"⚠️ Failed to delete old log file {file}: {e}", debug_mode=debug)
    log_debug(f"🗑️ Cleaned up {deleted_count} old log files (>24h)", debug_mode=debug)

    # Group notes by content similarity
    grouped = group_similar_notes_by_content(
        selected_notes,
        threshold=fuzzy_threshold,
        field_name=FIELD_TO_COMPARE
    )

    for norm_key, notes in grouped.items():
        log_debug(f"🔎 Group '{norm_key}' contains {len(notes)} notes: {[note.id for note in notes]}", debug_mode=debug)

    # Compute unmatched note IDs (notes not in any group)
    all_grouped_ids = {note.id for notes in grouped.values() for note in notes}
    unmatched_nids = [nid for nid in selected_nids if nid not in all_grouped_ids]

    log_debug(f"📊 Result - Groups: {len(grouped)}, Unmatched: {len(unmatched_nids)}", debug_mode=debug)
    log_debug(f"Unmatched NIDs: {unmatched_nids}", debug_mode=debug)

    # Tag each group of similar notes
    tagged = 0
    triple_match_nids = []

    for notes in grouped.values():
        if len(notes) < 2:
            continue  # Skip groups with only one note
        log_debug(f"🔁 Tagging {len(notes)} notes with {match_tag_label}...", debug_mode=debug)
        for note in notes:
            try:
                note.add_tag(match_tag_label)
                mw.col.update_note(note)
            except Exception as e:
                log_debug(f"⚠️ Failed to tag/update note {note.id}: {e}", debug_mode=debug)
        tagged += len(notes)

        if len(notes) >= 3:
            for note in notes:
                try:
                    note.add_tag(f"{BASE_TAG_LABEL}_{MULTI_CHILD_LABEL}::{len(notes)}-Notes_f{int(fuzzy_threshold * 100)}")
                    note.add_tag(multi_tag_label)
                    mw.col.update_note(note)
                except Exception as e:
                    log_debug(f"⚠️ Failed to tag/update note {note.id}: {e}", debug_mode=debug)
                triple_match_nids.append(note.id)

    unmatched_nids = [nid for nid in unmatched_nids if nid in selected_nids]
    # Tag unmatched notes (optional)
    if TAG_UNMATCHED and unmatched_nids:
        log_debug(f"🔹 Tagging {len(unmatched_nids)} unmatched notes with '{unmatched_tag_label}'", debug_mode=debug)
        for nid in unmatched_nids:
            nid = safe_cast_to_int(nid)
            if nid is None:
                continue
            note = try_get_note(nid)
            if note is None:
                continue
            try:
                note.add_tag(unmatched_tag_label)
                mw.col.update_note(note)
            except Exception as e:
                log_debug(f"⚠️ Failed to tag/update note {nid}: {e}", debug_mode=debug)

    # Export log to file

    export_log = [
        f"Fuzzy threshold: {int(fuzzy_threshold * 100)}%",
        f"Tagged {tagged} notes as {match_tag_label}",
    ]
    if TAG_UNMATCHED and unmatched_nids:
        export_log.append(f"Tagged {len(unmatched_nids)} unmatched notes as {unmatched_tag_label}")

    hash_suffix = hashlib.md5("".join(map(str, sorted(selected_nids))).encode()).hexdigest()[:4]
    log_filename = f"log_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash_suffix}.txt"
    log_debug("Export log content:", debug_mode=debug)
    for line in export_log:
        log_debug(f"  • {line}", debug_mode=debug)
    try:
        (log_dir_path / log_filename).write_text("\n\n".join(export_log), encoding="utf-8")
        log_debug(f"✅ Export log written to: {log_dir_path / log_filename}", debug_mode=debug)
    except Exception as e:
        log_debug(f"⚠️ Could not write export log file: {e}", debug_mode=debug)
    log_debug("🔍 Searching for near-duplicate notes...", debug_mode=debug)
    log_debug(f"🔎 Found {len(grouped) + len(unmatched_nids)} unique normalized groups from {len(selected_notes)} notes.", debug_mode=debug)
    log_debug(f"🧪 Fuzzy match threshold set to: {fuzzy_threshold}", debug_mode=debug)
    log_debug("🏷️ Tagging notes now...", debug_mode=debug)
    log_debug(f"✅ Tagged {tagged} near-duplicate notes. Log written to: {log_dir_path}", debug_mode=debug)

    # Write NID summary log to tag_dupes log folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    desktop_log_filename = f"grouped_{timestamp}_{len(selected_nids)}notes_f{int(fuzzy_threshold * 100)}.txt"
    with open(tag_dupes_log_dir / desktop_log_filename, "w", encoding="utf-8") as f:
        f.write("TRIPLE MATCH:\n")
        # Group triple matches by lines of 3
        for i in range(0, len(triple_match_nids), 3):
            group = triple_match_nids[i:i+3]
            f.write(", ".join(str(nid) for nid in map(safe_cast_to_int, group) if nid is not None) + ",\n")
        f.write("\nUNMATCH:\n")
        if unmatched_nids:
            f.write(", ".join(str(nid) for nid in map(safe_cast_to_int, unmatched_nids) if nid is not None) + ",\n")

    log_debug(f"🧾 Summary:", debug_mode=debug)
    log_debug(f"• Triple-matched note count: {len(triple_match_nids)}", debug_mode=debug)
    log_debug(f"• Unmatched note count: {len(unmatched_nids)}", debug_mode=debug)
    log_debug(f"📄 Full details in: {tag_dupes_log_dir / desktop_log_filename}", debug_mode=debug)
    log_debug("✅ run_tag_dupes completed successfully.", debug_mode=debug)
    showInfo(f"Tag Dupes completed: tagged {tagged} notes"
             + (f", {len(unmatched_nids)} unmatched notes." if unmatched_nids else "."))