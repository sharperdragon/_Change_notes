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

# Import from the merge_images addon
merge_images_path = os.path.expanduser("~/Library/Application Support/Anki2/addons21/merge_images")
import sys
if merge_images_path not in sys.path:
    sys.path.append(merge_images_path)

try:
    from merge_images import run_merge_images
except ImportError:
    run_merge_images = None

from aqt import mw
from aqt.qt import QAction, QInputDialog, QMenu
from aqt.browser import Browser
from aqt.utils import showInfo
from aqt import gui_hooks

from .modules.utils import load_config, save_config
from .config_manager import ConfigManager
from .config_ui import ConfigDialog

from .modules.merge.merge_tags import prompt_fuzzy_threshold, unify_tags_on_duplicates
from .modules.merge.tag_dupes import run_tag_dupes
from .modules.small_modules import delete_empty_note_types
from .modules.change_note_types import change_selected_notes
from .modules.add_tags import add_tag_menu_items
from .modules.merge.merge_schedule import run_merge_scheduling
try:
    from .modules.add_table_class import main as add_table_class_main  # supports module-level access
except Exception:
    add_table_class_main = None

# Wrapper to run table classification safely
from aqt.utils import showText

def _run_classify_tables(browser: Browser):
    if add_table_class_main is None:
        showText("[Change_notes] Could not import add_table_class module.", title="Change_notes import error", plain_text=True)
        return
    fn = getattr(add_table_class_main, "add_class_main", None)
    if callable(fn):
        return fn(browser)
    # Fallback: if only initialize_addon exists, initialize menus and inform user
    init_fn = getattr(add_table_class_main, "initialize_addon", None)
    if callable(init_fn):
        try:
            init_fn()
            showInfo("Table classifier initialized. Use the Browser context menu to run it.")
        except Exception as e:
            showText(f"[Change_notes] Failed to initialize table classifier:\n{e}", title="Change_notes init error", plain_text=True)
        return
    showText("[Change_notes] Entry point 'add_class_main' not found in add_table_class module.", title="Change_notes entry error", plain_text=True)



#from .modules.merge_images.main  import merge_images_main

#from .modules.Add_img_class.main import initialize_addon

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

    # Create a submenu for all merge-related actions
    merge_menu = QMenu("Edit Menu", menu)
    added_merge = False

    if run_merge_images:
        merge_imgs_action = QAction("🖼 Merge Images", browser)
        merge_imgs_action.triggered.connect(lambda: run_merge_images(selected, browser))
        merge_menu.addAction(merge_imgs_action)
        added_merge = True

    unify_tags_action = QAction("Merge Twin Note Tags⊹", browser)
    unify_tags_action.triggered.connect(lambda: run_merge_tags_with_threshold(browser))
    merge_menu.addAction(unify_tags_action)
    added_merge = True

    merge_sched_action = QAction("Merge Sched via Similarity", browser)
    merge_sched_action.triggered.connect(lambda: run_merge_scheduling(browser))
    merge_menu.addAction(merge_sched_action)
    added_merge = True

    tag_dupes_action = QAction("Tag Dupes 🔖", browser)
    tag_dupes_action.triggered.connect(lambda: run_tag_dupes(browser, debug=True))
    merge_menu.addAction(tag_dupes_action)
    added_merge = True

    # Only add the merge submenu if at least one merge action was added
    if added_merge:
        menu.addMenu(merge_menu)
        menu.addSeparator()

    # Get names of note types for selected notes
    note_types = {col.models.get(col.get_note(n).mid)["name"] for n in selected}
    
    # Add tag menu items after existing menu actions (directly to root menu)
    add_tag_menu_items(browser, menu, config)

    action = QAction("Batch Change Note Types", browser)
    action.triggered.connect(lambda: change_selected_notes(browser))
    menu.addAction(action)


    # Add classify tables action
    classify_tables_action = QAction("📊 Add Table class (columns)", browser)
    classify_tables_action.triggered.connect(lambda: _run_classify_tables(browser))
    menu.addAction(classify_tables_action)

    delete_empty_action = QAction("❌ Empty Note Types࿏", browser)
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

    classify = QAction("Classify Tables on Selected Notes…", mw)
    classify.triggered.connect(
        lambda: _run_classify_tables(mw.browser) if getattr(mw, "browser", None) else showInfo("Open the Browser and select notes first.")
    )
    change_menu.addAction(classify)

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