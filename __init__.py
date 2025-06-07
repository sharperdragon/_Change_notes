# pyright: reportMissingImports=false
"""
Change_notes Add-on for Anki

Features:
- Batch change note types from the browser context menu
- Optionally apply field-mapping profiles for note type migration
- Delete unused note types from the collection
- Unify tags between notes with identical first fields
- GUI dialog for editing field-mapping profiles

Compatibility:
- Supports multiple Anki versions through dynamic import fallbacks
- GUI and context menu integrations ensure minimal user disruption

"""
import os
from collections import defaultdict
from datetime import datetime

from aqt import mw
from aqt.qt import QAction, QInputDialog, QMenu
from aqt.browser import Browser
from aqt.utils import showInfo
from aqt import gui_hooks

from .merge_tags import prompt_fuzzy_threshold, unify_tags_on_duplicates
from .tag_dupes import run_tag_dupes  # supports debug flag
from .utils import load_config, save_config
from .config_manager import ConfigManager
from .config_ui import ConfigDialog

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
        _run_change_note_type = lambda browser, nids, mid: ChangeNotetypeDialog(browser, browser.mw, nids, mid).exec_()

# Prompt for threshold and run tag unification if threshold is set
def run_merge_tags_with_threshold(browser: Browser):
    threshold = prompt_fuzzy_threshold()
    if threshold is not None:
        unify_tags_on_duplicates(browser, threshold)

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




# Scans all note types and deletes those with zero associated cards from the collection.
def delete_empty_note_types():
    col = mw.col
    # Iterate through all note types to check usage
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
    # Only show context menu options if notes are selected
    selected = browser.selectedNotes()
    if not selected:
        return
    col = browser.mw.col
    # Get names of note types for selected notes
    note_types = {col.models.get(col.get_note(n).mid)["name"] for n in selected}
    action = QAction("Batch Change Note Types", browser)
    action.triggered.connect(lambda: change_selected_notes(browser))
    menu.addSeparator()
    menu.addAction(action)

    unify_tags_action = QAction("Twin Notes – Merge Tags", browser)
    unify_tags_action.triggered.connect(lambda: run_merge_tags_with_threshold(browser))
    menu.addAction(unify_tags_action)

    tag_dupes_action = QAction("Tag Dupe Notes", browser)
    tag_dupes_action.triggered.connect(lambda: run_tag_dupes(browser, debug=True))
    menu.addAction(tag_dupes_action)

    delete_empty_action = QAction("Delete Empty Note Types ␡", browser)
    delete_empty_action.triggered.connect(delete_empty_note_types)
    menu.addAction(delete_empty_action)


# Ensures the browser context menu is only hooked once
if not getattr(mw, "_change_note_type_menu_injected", False):
    gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)
    mw._change_note_type_menu_injected = True


# Adds a submenu under Tools > Add-ons for quick access to browser-based operations.
# Currently includes placeholders to focus the browser window.
def inject_tools_menu(menu):
    # Create "Change Note Types" submenu in Tools > Add-ons
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


# Opens the GUI config dialog for managing field-mapping profiles and other add-on settings.
def open_config_gui():
    # Launch GUI config dialog for field-mapping setup
    dialog = ConfigDialog("Change_note-types", ConfigManager)
    dialog.exec_()