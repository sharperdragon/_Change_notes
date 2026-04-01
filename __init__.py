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

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import QAction, QMenu
from aqt.utils import showInfo
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QWidgetAction

from .config_manager import ConfigManager
from .config_ui import ConfigDialog
from .modules.add_custom_tags import add_custom_tag_menu_items
from .modules.Add_img_class import main as add_img_class_main
from .modules.add_missed_tags import add_missed_tag_menu_items
from .modules.add_table_class.main import add_class_main
from .modules.change_note_types import change_selected_notes
from .modules.del_empty_notes import delete_empty_note_types
from .modules.export_nids import create_export_nids_action
from .modules.export_UW_qid_tags import run_export_for_selected_notes
from .modules.img_tags_merge import merge_imgs_and_tags
from .modules.merge_imgs import merge_images_main
from .modules.merge_schedule import run_merge_scheduling
from .modules.merge_tags import prompt_fuzzy_threshold, unify_tags_on_duplicates
from .modules.tag_dupes import run_tag_dupes


# Prompt for threshold and run tag unification if threshold is set
def run_merge_tags_with_threshold(browser: Browser):
    threshold = prompt_fuzzy_threshold()
    if threshold is not None:
        unify_tags_on_duplicates(browser, threshold)


# Injects right-click browser menu options
def on_browser_will_show_context_menu(browser: Browser, menu):
    selected = browser.selectedNotes()
    if not selected:
        return
    menu.addSeparator()

    # Add tag menu items after existing menu actions (directly to root menu)
    add_missed_tag_menu_items(browser, menu)
    add_custom_tag_menu_items(browser, menu)

    # gui_hooks.browser_menus_did_init.append(_add_img_class_menu_action)
    menu.addSeparator()

    # Export NIDs (adds two Desktop files + copies query to clipboard)
    export_action = create_export_nids_action(parent=browser, mw=mw, browser=browser)
    menu.addAction(export_action)

    # Export UWorld Step QID tags (deduped + sorted + clipboard + Desktop file)
    export_uw_qids_action = QAction("Export UW QID tag(s) 🧿", browser)
    export_uw_qids_action.triggered.connect(lambda: run_export_for_selected_notes(browser))
    menu.addAction(export_uw_qids_action)

    # Context menu → runs add_table_class on currently selected notes.
    classify_imgs_action = QAction("Add IMG class 🏞️", browser)
    classify_imgs_action.triggered.connect(lambda: add_img_class_main(browser))
    menu.addAction(classify_imgs_action)

    # Context menu → runs add_table_class on currently selected notes.
    classify_tables_action = QAction("📊 Add Table class (columns)", browser)
    classify_tables_action.triggered.connect(lambda: add_class_main(browser))
    menu.addAction(classify_tables_action)

    # Create a submenu for all edit-related actions
    edit_menu = QMenu("Edit Menu 📝", menu)
    edit_menu.setObjectName("editMenu")
    added_edit = False

    # Create a submenu for all merge-related actions
    merge_menu = QMenu("Merge Menu 🚧", menu)
    merge_menu.setObjectName("mergeMenu")
    added_merge = False

    unify_Img_and_tags_action = QAction("🍃Merge Imgs+Tags", browser)
    unify_Img_and_tags_action.triggered.connect(lambda _=None: merge_imgs_and_tags(browser=browser))
    merge_menu.addAction(unify_Img_and_tags_action)
    added_merge = True

    merge_imgs_action = QAction("🧬 Merge Images", browser)
    merge_imgs_action.triggered.connect(lambda: merge_images_main(selected, browser))
    merge_menu.addAction(merge_imgs_action)
    added_merge = True

    unify_tags_action = QAction("🔀 Merge Tags⊹", browser)
    unify_tags_action.triggered.connect(lambda: run_merge_tags_with_threshold(browser))
    merge_menu.addAction(unify_tags_action)
    added_merge = True

    merge_sched_action = QAction("🛻 Merge Schedule", browser)
    merge_sched_action.triggered.connect(lambda: run_merge_scheduling(browser))
    merge_menu.addAction(merge_sched_action)
    added_merge = True

    tag_dupes_action = QAction("Tag Dupes 🔖", browser)
    tag_dupes_action.triggered.connect(lambda: run_tag_dupes(browser, debug=True))
    edit_menu.addAction(tag_dupes_action)
    added_edit = True

    delete_empty_action = QAction("❌ Empty Note Types࿏", browser)
    delete_empty_action.triggered.connect(delete_empty_note_types)
    edit_menu.addAction(delete_empty_action)
    added_edit = True

    action = QAction("Batch Change Note Types", browser)
    action.triggered.connect(lambda: change_selected_notes(browser))
    edit_menu.addAction(action)
    added_edit = True

    # Only add the merge submenu if at least one merge action was added
    if added_merge:
        menu.addSeparator()
        menu.addMenu(merge_menu)

    # Add the edit submenu if at least one edit action was added
    if added_edit:
        menu.addMenu(edit_menu)
        menu.addSeparator()


# Ensures the browser context menu is only hooked once
if not getattr(mw, "_change_note_type_menu_injected", False):
    gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)
    mw._change_note_type_menu_injected = True


# Adds a submenu under Tools > Add-ons for quick access to browser-based operations.
# Currently includes placeholders to focus the browser window.
def inject_tools_menu(menu):
    # Create "Change Note Types" submenu in Tools > Add-ons
    change_menu = QMenu("Change Note Types", menu)

    def focus_browser_or_prompt():
        browser = getattr(mw, "browser", None)
        if browser:
            browser.activateWindow()
            browser.raise_()
        else:
            showInfo("Open the Browser and select notes first.")

    batch = QAction("Batch Change Note Type…", mw)
    batch.triggered.connect(focus_browser_or_prompt)
    change_menu.addAction(batch)

    resolve = QAction("Resolve Duplicates in Browser", mw)
    resolve.triggered.connect(focus_browser_or_prompt)
    change_menu.addAction(resolve)

    classify_tables = QAction("Classify Tables on Selected Notes…", mw)
    classify_tables.triggered.connect(
        lambda: (
            add_class_main(mw.browser)
            if getattr(mw, "browser", None)
            else showInfo("Open the Browser and select notes first.")
        )
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
    dialog = ConfigDialog("_Change_notes", ConfigManager)
    dialog.exec()


def custom_styled_action(text, parent, triggered_fn):
    action = QWidgetAction(parent)
    label = QLabel(text)
    f = QFont()
    f.setPointSize(15)  # bigger font just for this item
    label.setFont(f)
    return action
    label.setFont(f)
    return action
    return action
