from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# pyright: reportMissingImports=false
from ..config_manager import ConfigManager
from .shared.parsing import parse_bool

from aqt.browser import Browser
from aqt.qt import QInputDialog
from aqt.utils import showInfo


# --------------------------- USER-TUNABLE CONSTANTS ---------------------------
DEFAULT_BATCH_SIZE = 200
DEFAULT_BACKUP_DIR = "~/Anki_Backups/NoteTypeChange"
BACKUP_FILENAME_PREFIX = "batch_note_change_backup_"
# -----------------------------------------------------------------------------

config_manager = ConfigManager("batch_note_change_config")
config = config_manager.load()


# Compatibility shim: Tries multiple import paths to ensure compatibility with
# different Anki versions' change note type dialogs.
try:
    from aqt.dialogs import changeNoteType as _change_note_type_fn

    def _run_change_note_type(browser, nids, mid):
        return _change_note_type_fn(browser, nids, mid)

except ImportError:
    try:
        from aqt.change import changeNoteType as _change_note_type_fn

        def _run_change_note_type(browser, nids, mid):
            return _change_note_type_fn(browser, nids, mid)

    except ImportError:
        from aqt.changenotetype import ChangeNotetypeDialog

        def _run_change_note_type(browser, nids, mid):
            return ChangeNotetypeDialog(browser, browser.mw, nids, mid).exec()


def _normalize_batch_size(raw_value, default: int = DEFAULT_BATCH_SIZE) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def _iter_chunks(items: list[int], chunk_size: int):
    for idx in range(0, len(items), chunk_size):
        yield items[idx: idx + chunk_size]


def _with_progress(browser: Browser, enabled: bool, total: int, label: str):
    if not enabled or total <= 0:
        return False
    try:
        browser.mw.progress.start(label=label, max=total, immediate=True)
        return True
    except Exception:
        return False


def _update_progress(browser: Browser, active: bool, done: int, total: int, label: str):
    if not active:
        return
    try:
        browser.mw.progress.update(value=done, max=total, label=label)
        browser.mw.app.processEvents()
    except Exception:
        pass


def _finish_progress(browser: Browser, active: bool):
    if not active:
        return
    try:
        browser.mw.progress.finish()
    except Exception:
        pass


def _selected_note_type_count(col, nids: list[int]) -> int:
    mids = set()
    for nid in nids:
        try:
            mids.add(col.get_note(nid).model()["id"])
        except Exception:
            continue
    return len(mids)


def _resolve_mapping_profile(
    browser: Browser,
    field_mappings: dict,
    last_map: str,
    auto_confirm: bool,
) -> str | None:
    mapping_keys = list(field_mappings.keys())
    if not mapping_keys:
        return None

    # Skip the profile picker when explicitly configured.
    if auto_confirm and last_map in mapping_keys:
        return last_map
    if auto_confirm and len(mapping_keys) == 1:
        return mapping_keys[0]

    mapping_names = ["None"] + mapping_keys
    map_index = mapping_keys.index(last_map) + 1 if last_map in mapping_keys else 0
    profile_name, ok = QInputDialog.getItem(
        browser,
        "Select Field-Mapping Profile",
        "Mapping Profile:",
        mapping_names,
        map_index,
        False,
    )
    if not ok or not profile_name or profile_name == "None":
        return None
    return profile_name


def _backup_selected_notes(
    browser: Browser,
    col,
    nids: list[int],
    target_name: str,
    batch_size: int,
    show_progress: bool,
    backup_directory: str,
) -> Path:
    backup_dir = Path(str(backup_directory or DEFAULT_BACKUP_DIR)).expanduser()
    if not backup_dir.is_absolute():
        backup_dir = (Path.home() / backup_dir).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{BACKUP_FILENAME_PREFIX}{timestamp}.json"
    snapshot = []

    progress_active = _with_progress(
        browser,
        show_progress,
        len(nids),
        "Creating note-type backup...",
    )
    processed = 0
    try:
        for chunk in _iter_chunks(nids, batch_size):
            for nid in chunk:
                note = col.get_note(nid)
                model = note.model()
                field_names = col.models.field_names(model)
                snapshot.append(
                    {
                        "nid": nid,
                        "model_id": model.get("id"),
                        "model_name": model.get("name", ""),
                        "tags": list(note.tags),
                        "fields": {
                            name: note.fields[idx] if idx < len(note.fields) else ""
                            for idx, name in enumerate(field_names)
                        },
                    }
                )
            processed += len(chunk)
            _update_progress(
                browser,
                progress_active,
                processed,
                len(nids),
                f"Creating note-type backup... {processed}/{len(nids)}",
            )
    finally:
        _finish_progress(browser, progress_active)

    payload = {
        "created_at": datetime.now().isoformat(),
        "target_note_type": target_name,
        "note_count": len(nids),
        "notes": snapshot,
    }
    backup_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return backup_path


def _post_process_changed_notes(
    browser: Browser,
    col,
    changed_nids: list[int],
    mappings: list[dict],
    tag_on_change: str,
    batch_size: int,
    show_progress: bool,
) -> tuple[int, int, int]:
    if not changed_nids:
        return 0, 0, 0

    changed_notes = 0
    mapped_notes = 0
    tagged_notes = 0
    clean_tag = (tag_on_change or "").strip()
    safe_mappings = mappings if isinstance(mappings, list) else []

    progress_active = _with_progress(
        browser,
        show_progress,
        len(changed_nids),
        "Applying mapping/tag post-processing...",
    )
    processed = 0
    try:
        for chunk in _iter_chunks(changed_nids, batch_size):
            for nid in chunk:
                note = col.get_note(nid)
                model = note.model()
                field_names = col.models.field_names(model)
                field_idx = {name: idx for idx, name in enumerate(field_names)}

                did_map = False
                did_tag = False

                for mapping in safe_mappings:
                    src = mapping.get("source") if isinstance(mapping, dict) else None
                    tgt = mapping.get("target") if isinstance(mapping, dict) else None
                    if not src or not tgt:
                        continue
                    src_idx = field_idx.get(src)
                    tgt_idx = field_idx.get(tgt)
                    if src_idx is None or tgt_idx is None:
                        continue
                    src_val = note.fields[src_idx]
                    if note.fields[tgt_idx] != src_val:
                        note.fields[tgt_idx] = src_val
                        did_map = True

                if clean_tag and clean_tag not in note.tags:
                    try:
                        note.add_tag(clean_tag)
                    except Exception:
                        note.tags = sorted(set(note.tags) | {clean_tag})
                    did_tag = True

                if did_map or did_tag:
                    note.flush()
                    changed_notes += 1
                if did_map:
                    mapped_notes += 1
                if did_tag:
                    tagged_notes += 1

            processed += len(chunk)
            _update_progress(
                browser,
                progress_active,
                processed,
                len(changed_nids),
                f"Applying mapping/tag post-processing... {processed}/{len(changed_nids)}",
            )
    finally:
        _finish_progress(browser, progress_active)

    return changed_notes, mapped_notes, tagged_notes


# Opens a dialog to batch-change note types of selected notes in the Anki
# browser, then applies optional mapping/tag post-processing to changed notes.
def change_selected_notes(browser: Browser):
    global config
    config = config_manager.reload()

    nids = browser.selectedNotes()
    if not nids:
        showInfo("No notes selected.")
        return

    col = browser.mw.col
    allow_single_override = parse_bool(config.get("allow_single_type_override", True), default=True)
    if not allow_single_override and _selected_note_type_count(col, nids) <= 1:
        showInfo("Batch note-type change is disabled when only one source note type is selected.")
        return

    models = col.models.all()
    names = [m["name"] for m in models]
    if not names:
        showInfo("No note types found.")
        return

    last_target = config.get("last_target_model", "")
    default_index = names.index(last_target) if last_target in names else 0
    target_name, ok = QInputDialog.getItem(
        browser,
        "Select Target Note Type",
        "Note Type:",
        names,
        default_index,
        False,
    )
    if not ok or not target_name:
        return

    field_mappings = config.get("field_mappings", {})
    if not isinstance(field_mappings, dict):
        field_mappings = {}

    auto_confirm = parse_bool(config.get("auto_confirm_mappings", False), default=False)
    last_map = str(config.get("last_mapping_profile", "") or "")
    mapping_profile = _resolve_mapping_profile(browser, field_mappings, last_map, auto_confirm)
    mappings = field_mappings.get(mapping_profile, []) if mapping_profile else []

    config["last_target_model"] = target_name
    if mapping_profile:
        config["last_mapping_profile"] = mapping_profile
    config_manager.save_config(config)

    batch_size = _normalize_batch_size(config.get("batch_size", DEFAULT_BATCH_SIZE))
    show_progress = parse_bool(config.get("show_progress", True), default=True)
    enable_backup = parse_bool(config.get("enable_backup", True), default=True)
    backup_dir = str(config.get("backup_directory", DEFAULT_BACKUP_DIR) or DEFAULT_BACKUP_DIR)
    tag_on_change = str(config.get("tag_on_change", "") or "").strip()

    backup_path = None
    if enable_backup:
        try:
            backup_path = _backup_selected_notes(
                browser=browser,
                col=col,
                nids=nids,
                target_name=target_name,
                batch_size=batch_size,
                show_progress=show_progress,
                backup_directory=backup_dir,
            )
        except Exception as exc:
            showInfo(f"Backup failed. No note types were changed.\n\n{exc}")
            return

    before_mid_by_nid = {}
    for nid in nids:
        try:
            before_mid_by_nid[nid] = col.get_note(nid).model()["id"]
        except Exception:
            continue

    model = col.models.by_name(target_name)
    if not model:
        showInfo(f"Target note type '{target_name}' no longer exists.")
        return
    target_mid = model["id"]
    _run_change_note_type(browser, nids, target_mid)

    changed_nids = []
    for nid in nids:
        before_mid = before_mid_by_nid.get(nid)
        if before_mid is None:
            continue
        try:
            after_mid = col.get_note(nid).model()["id"]
        except Exception:
            continue
        if after_mid != before_mid:
            changed_nids.append(nid)

    _changed_notes, mapped_notes, tagged_notes = _post_process_changed_notes(
        browser=browser,
        col=col,
        changed_nids=changed_nids,
        mappings=mappings,
        tag_on_change=tag_on_change,
        batch_size=batch_size,
        show_progress=show_progress,
    )

    browser.mw.reset()

    summary = [
        f"Changed note type on {len(changed_nids)} note(s).",
        f"Mapping profile: {mapping_profile or 'None'}",
    ]
    if not changed_nids:
        summary.append("No note types were changed (conversion likely canceled).")
    if mappings:
        summary.append(f"Mapped fields on {mapped_notes} changed note(s).")
    if tag_on_change:
        summary.append(f"Tagged {tagged_notes} changed note(s) with '{tag_on_change}'.")
    if changed_nids and not mappings and not tag_on_change:
        summary.append("No post-change mapping or tagging was configured.")
    if backup_path:
        summary.append(f"Backup saved: {backup_path}")

    showInfo("\n".join(summary))
