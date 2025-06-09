# pyright: reportMissingImports=false
import json, os, html, json
from pathlib import Path
from aqt import mw
from aqt.browser import Browser
from aqt.utils import showInfo
from aqt.qt import QInputDialog

# Compatibility for changeNoteType across Anki versions
try:
    from aqt.dialogs import changeNoteType as _change_note_type_fn
    _run_change_note_type = lambda browser, nids, mid: _change_note_type_fn(browser, nids, mid)
except ImportError:
    try:
        from aqt.change import changeNoteType as _change_note_type_fn
        _run_change_note_type = lambda browser, nids, mid: _change_note_type_fn(browser, nids, mid)
    except ImportError:
        from aqt.changenotetype import ChangeNotetypeDialog
        _run_change_note_type = lambda browser, nids, mid: ChangeNotetypeDialog(browser, browser.mw, nids, mid).exec_()

# Config file location
config_path = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

config = load_config()

def change_selected_notes(browser: Browser):
    nids = browser.selectedNotes()
    if not nids:
        showInfo("No notes selected.")
        return

    col = browser.mw.col
    models = col.models.all()
    names = [m["name"] for m in models]

    last_target = config.get("last_target_model", "")
    default_index = names.index(last_target) if last_target in names else 0

    target_name, ok = QInputDialog.getItem(
        browser,
        "Select Target Note Type",
        "Note Type:",
        names,
        default_index,
        False
    )
    if not ok or not target_name:
        return

    config["last_target_model"] = target_name
    save_config(config)

    # Optional field-mapping profile
    mapping_keys = list(config.get("field_mappings", {}).keys())
    mapping_names = ["None"] + mapping_keys
    last_map = config.get("last_mapping_profile", "")
    map_index = mapping_keys.index(last_map) + 1 if last_map in mapping_keys else 0
    profile_name, ok2 = QInputDialog.getItem(
        browser,
        "Select Field-Mapping Profile",
        "Mapping Profile:",
        mapping_names,
        map_index,
        False
    )
    mapping_profile = profile_name if ok2 and profile_name and profile_name != "None" else None
    if mapping_profile:
        config["last_mapping_profile"] = mapping_profile
        save_config(config)

    mid = col.models.by_name(target_name)["id"]
    _run_change_note_type(browser, nids, mid)

    # Apply field mappings
    if mapping_profile:
        mappings = config.get("field_mappings", {}).get(mapping_profile, [])
        for nid in nids:
            note = col.get_note(nid)
            for m in mappings:
                src, tgt = m.get("source"), m.get("target")
                if src in note and tgt in note:
                    note[tgt] = note[src]
            note.flush()