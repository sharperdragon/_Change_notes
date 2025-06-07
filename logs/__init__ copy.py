# pyright: reportMissingImports=false
import json
import os
from aqt.browser import Browser
from aqt.qt import QAction, QInputDialog
from aqt import mw
from aqt.utils import showInfo
from .merge_tags import unify_tags_on_duplicates
from .utils import load_config, save_config
from collections import defaultdict

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
        _run_change_note_type = lambda browser, nids, mid: ChangeNotetypeDialog(browser, browser.mw, nids, mid).exec_()

config = load_config()

# Opens a dialog to batch-change note types of selected notes in the Anki browser.
# Also applies optional field-mapping profiles saved in the config.
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
            model = note.model()
            flds = col.models.field_names(model)
            for m in mappings:
                src, tgt = m.get("source"), m.get("target")
                if not src or not tgt or src not in flds or tgt not in flds:
                    continue
                note.fields[flds.index(tgt)] = note.fields[flds.index(src)]
            note.flush()




# Scans all note types and deletes those with zero associated cards from the collection.
def delete_empty_note_types():
    col = mw.col
    models = col.models.all()
    deleted = 0
    for model in models:
        cards = col.db.scalar("SELECT COUNT() FROM cards WHERE nid IN (SELECT id FROM notes WHERE mid=?)", model["id"])
        if cards == 0:
            col.models.rem(model)
            deleted += 1
    mw.reset()
    showInfo(f"Deleted {deleted} note types with zero cards.")


# Injects right-click browser menu options for:
# - Batch changing note types
# - Unifying tags between notes with duplicate first fields
# - Deleting empty note types
def on_browser_will_show_context_menu(browser: Browser, menu):
    selected = browser.selectedNotes()
    if not selected:
        return
    col = browser.mw.col
    note_types = {col.models.get(col.get_note(n).mid)["name"] for n in selected}
    action = QAction("Batch Change Note Type…", browser)
    action.triggered.connect(lambda: change_selected_notes(browser))
    menu.addAction(action)

    unify_tags_action = QAction("Unify Tags Between Twin Notes", browser)
    unify_tags_action.triggered.connect(lambda: unify_tags_on_duplicates(browser))
    menu.addAction(unify_tags_action)

    delete_empty_action = QAction("Delete Note Types With Zero Cards", browser)
    delete_empty_action.triggered.connect(delete_empty_note_types)
    menu.addAction(delete_empty_action)


from aqt import gui_hooks
# Ensures the browser context menu is only hooked once
if not getattr(mw, "_change_note_type_menu_injected", False):
    gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)
    mw._change_note_type_menu_injected = True

from aqt.qt import QMenu, QAction

# Adds a submenu under Tools > Add-ons for quick access to browser-based operations.
# Currently includes placeholders to focus the browser window.
def inject_tools_menu(menu):
    change_menu = QMenu("Change Note Types", menu)

    batch = QAction("Batch Change Note Type…", mw)
    batch.triggered.connect(lambda: mw.browser.activateWindow() or mw.browser.raise_())
    change_menu.addAction(batch)

    resolve = QAction("Resolve Duplicates in Browser", mw)
    resolve.triggered.connect(lambda: mw.browser.activateWindow() or mw.browser.raise_())
    change_menu.addAction(resolve)

    menu.addMenu(change_menu)

try:
    from aqt.gui_hooks import addon_menu_will_show
    if not getattr(mw, "_change_note_type_tools_menu_injected", False):
        addon_menu_will_show.append(inject_tools_menu)
        mw._change_note_type_tools_menu_injected = True
except ImportError:
    pass  # Older Anki versions don't support addon menu hook

from Main_Toolbar.assets.config_ui import ConfigDialog
from .config_manager import ConfigManager

# Opens the GUI config dialog for managing field-mapping profiles and other add-on settings.
def open_config_gui():
    dialog = ConfigDialog("Change_note-types", ConfigManager)
    dialog.exec_()