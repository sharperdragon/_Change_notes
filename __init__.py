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

from .modules.utils import load_config, save_config
from .config_manager import ConfigManager
from .config_ui import ConfigDialog

from .modules.merge_tags import prompt_fuzzy_threshold, unify_tags_on_duplicates
from .modules.tag_dupes import run_tag_dupes
from .modules.small_modules import delete_empty_note_types
from .modules.change_note_types import change_selected_notes
from .modules.add_tags import add_tag_menu_items


config_manager = ConfigManager("Change_notes")

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
    # Get names of note types for selected notes
    note_types = {col.models.get(col.get_note(n).mid)["name"] for n in selected}
    action = QAction("Batch Change Note Types", browser)
    action.triggered.connect(lambda: change_selected_notes(browser))
    menu.addAction(action)

    unify_tags_action = QAction("Merge Twin Note Tags⊹", browser)
    unify_tags_action.triggered.connect(lambda: run_merge_tags_with_threshold(browser))
    menu.addAction(unify_tags_action)

    tag_dupes_action = QAction("Tag Dupes 🔖", browser)
    tag_dupes_action.triggered.connect(lambda: run_tag_dupes(browser, debug=True))
    menu.addAction(tag_dupes_action)

    delete_empty_action = QAction("❌ Empty Note Types࿏", browser)
    delete_empty_action.triggered.connect(delete_empty_note_types)
    menu.addAction(delete_empty_action)

    # Add tag menu items after existing menu actions
    add_tag_menu_items(browser, menu, config)

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