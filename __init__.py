"""
_Change_notes Add-on for Anki

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
# pyright: reportMissingImports=false
# mypy: disable_error_code=import
import os, sys
from collections import defaultdict
from datetime import datetime
from PyQt6.QtWidgets import QWidgetAction, QLabel
from PyQt6.QtGui import QFont
from fnmatch import fnmatch
from pathlib import Path
import json

from aqt import mw
from aqt.qt import QAction, QInputDialog, QMenu
from aqt.browser import Browser
from aqt.utils import showInfo, showText
from aqt import gui_hooks


from .modules.utils import load_config, save_config
from .config_manager import ConfigManager
from .config_ui import ConfigDialog

from .modules.merge_tags import prompt_fuzzy_threshold, unify_tags_on_duplicates
from .modules.tag_dupes import run_tag_dupes
from .modules.merge_schedule import run_merge_scheduling
from .modules.del_empty_notes import delete_empty_note_types
from .modules.change_note_types import change_selected_notes
from .modules.add_tags import add_tag_menu_items
from .modules.Add_img_class import main as add_img_class_main
from .modules.export_nids import create_export_nids_action
from .modules.merge_imgs import run_merge_images

from .modules.add_table_class import main as add_table_class_main  # supports module-level access


# Calls the module-level add_table_class.main.add_class_main(browser). 
def _run_classify_tables(browser: Browser):
    if add_table_class_main is None:
        showText("[_Change_notes] add_table_class module not available.", title="_Change_notes import error", plain_text=True)
        return
    fn = getattr(add_table_class_main, "add_class_main", None)
    if not callable(fn):
        showText("[_Change_notes] Entry point 'add_class_main(browser)' not found in add_table_class module.", title="_Change_notes entry error", plain_text=True)
        return
    return fn(browser)

config_manager = ConfigManager("_Change_notes")

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
    menu.addSeparator()

    # Add tag menu items after existing menu actions (directly to root menu)
    add_tag_menu_items(browser, menu, config)
    
    #gui_hooks.browser_menus_did_init.append(_add_img_class_menu_action)
    menu.addSeparator()

    # Export NIDs (adds two Desktop files + copies query to clipboard)
    export_action = create_export_nids_action(parent=browser, mw=mw, browser=browser)
    menu.addAction(export_action)  # <-- add to the context menu
    
    # Context menu → runs add_table_class on currently selected notes.
    classify_imgs_action = QAction("Add IMG class 🏞️", browser)
    classify_imgs_action.triggered.connect(lambda: add_img_class_main(browser))
    menu.addAction(classify_imgs_action)
    
    # Context menu → runs add_table_class on currently selected notes.
    classify_tables_action = QAction("📊 Add Table class (columns)", browser)
    classify_tables_action.triggered.connect(lambda: _run_classify_tables(browser))
    menu.addAction(classify_tables_action)

    # Create a submenu for all merge-related actions
    merge_menu = QMenu("Edit Menu", menu)
    merge_menu.setObjectName("changeNotesMenu")
    added_merge = False

    if run_merge_images:
        merge_imgs_action = QAction("🧬 Merge Images", browser)
        merge_imgs_action.triggered.connect(lambda: run_merge_images(selected, browser))
        merge_menu.addAction(merge_imgs_action)
        added_merge = True

    unify_tags_action = QAction("Merge Twin Note Tags⊹", browser)
    unify_tags_action.triggered.connect(lambda: run_merge_tags_with_threshold(browser))
    merge_menu.addAction(unify_tags_action)
    added_merge = True

    merge_sched_action = QAction("Merge Scheduling (Similarity)", browser)

    merge_sched_action.triggered.connect(lambda: run_merge_scheduling(browser))
    merge_menu.addAction(merge_sched_action)
    added_merge = True

    tag_dupes_action = QAction("Tag Dupes 🔖", browser)
    tag_dupes_action.triggered.connect(lambda: run_tag_dupes(browser, debug=True))
    merge_menu.addAction(tag_dupes_action)
    added_merge = True
    
    delete_empty_action = QAction("❌ Empty Note Types࿏", browser)
    delete_empty_action.triggered.connect(delete_empty_note_types)
    merge_menu.addAction(delete_empty_action)
    added_merge = True
        
    action = QAction("Batch Change Note Types", browser)
    action.triggered.connect(lambda: change_selected_notes(browser))
    merge_menu.addAction(action)
    added_merge = True
    
    # Only add the merge submenu if at least one merge action was added
    if added_merge:
        menu.addMenu(merge_menu)
        menu.addSeparator()

    # Get names of note types for selected notes
    note_types = {col.models.get(col.get_note(n).mid)["name"] for n in selected}



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

    classify_tables = QAction("Classify Tables on Selected Notes…", mw)
    classify_tables.triggered.connect(
        lambda: _run_classify_tables(mw.browser) if getattr(mw, "browser", None) else showInfo("Open the Browser and select notes first.")
    )
    change_menu.addAction(classify_tables)

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


def custom_styled_action(text, parent, triggered_fn):
    action = QWidgetAction(parent)
    label = QLabel(text)
    f = QFont()
    f.setPointSize(15)       # bigger font just for this item
    label.setFont(f)
    return action


