
from .utils import save_config
from ..config_manager import ConfigManager

from aqt import mw
from aqt.qt import QAction, QInputDialog, QMenu
from aqt.browser import Browser
from aqt.utils import showInfo
from aqt import gui_hooks


config_manager = ConfigManager("batch_note_change_config", "global_config")

# Load merged config from config_manager
config = config_manager.load()
# Compatibility shim: Tries multiple import paths to ensure compatibility with different Anki versions' change note type dialogs
try:
    from aqt.dialogs import changeNoteType as _change_note_type_fn
    _run_change_note_type = lambda browser, nids, mid: _change_note_type_fn(browser, nids, mid)
except ImportError:
    try:
        from aqt.change import changeNoteType as _change_note_type_fn
        _run_change_note_type = lambda browser, nids, mid: _change_note_type_fn(browser, nids, mid)
    except ImportError:
        from aqt.changenotetype import ChangeNotetypeDialog
        _run_change_note_type = lambda browser, nids, mid: ChangeNotetypeDialog(browser, browser.mw, nids, mid).exec()




# Opens a dialog to batch-change note types of selected notes in the Anki browser.
# Also applies optional field-mapping profiles saved in the config.
def change_selected_notes(browser: Browser):
    # Get selected note IDs from browser
    nids = browser.selectedNotes()
    if not nids:
        showInfo("No notes selected.")
        return

    col = browser.mw.col
    # Retrieve all note types
    models = col.models.all()
    names = [m["name"] for m in models]

    last_target = config.get("last_target_model", "")
    default_index = names.index(last_target) if last_target in names else 0

    # Prompt user to select target note type
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

    # Retrieve saved field-mapping profiles
    mapping_keys = list(config.get("field_mappings", {}).keys())
    mapping_names = ["None"] + mapping_keys
    last_map = config.get("last_mapping_profile", "")
    map_index = mapping_keys.index(last_map) + 1 if last_map in mapping_keys else 0
    # Prompt user to select field-mapping profile (optional)
    profile_name, ok2 = QInputDialog.getItem(
        browser,
        "Select Field-Mapping Profile",
        "Mapping Profile:",
        mapping_names,
        map_index,
        False
    )
    mapping_profile = profile_name if ok2 and profile_name and profile_name != "None" else None
    # If a mapping profile is chosen, store selection
    if mapping_profile:
        config["last_mapping_profile"] = mapping_profile
        save_config(config)

    # Get model ID of selected note type
    mid = col.models.by_name(target_name)["id"]
    _run_change_note_type(browser, nids, mid)

    # Apply field mappings from selected profile
    if mapping_profile:
        mappings = config.get("field_mappings", {}).get(mapping_profile, [])
        for nid in nids:
            note = col.get_note(nid)
            model = note.model()
            flds = col.models.field_names(model)
            for m in mappings:
                src, tgt = m.get("source"), m.get("target")
                if not src or not tgt or src not in flds or tgt not in flds:
                    continue
                note.fields[flds.index(tgt)] = note.fields[flds.index(src)]
            note.flush()

