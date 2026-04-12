"""Browser context-menu compiler for _Change_notes.

This module centralizes imports and menu wiring for actions inserted
into Anki's Browser right-click menu.
"""

# pyright: reportMissingImports=false

from aqt import mw
from aqt.qt import QAction, QMenu

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

# ! --------------------------- USER-TUNABLE CONSTANTS ---------------------------
DEFAULT_CUSTOM_TAGS_MENU_LABEL = " 🎛️ Custom Tags"
MENU_LABEL_EXPORT_UW_QIDS = "Export UW QID tag(s) 🧿"
MENU_LABEL_ADD_IMG_CLASS = "Add IMG class 🏞️"
MENU_LABEL_ADD_TABLE_CLASS = "📊 Add Table class (col)"
MENU_LABEL_EDIT_MENU = "Edit Menu 📝"
MENU_LABEL_MERGE_MENU = "Merge Menu 🚧"
MENU_LABEL_MERGE_IMGS_TAGS = "🍃Merge Imgs+Tags"
MENU_LABEL_MERGE_IMAGES = "🧬 Merge Images"
MENU_LABEL_MERGE_TAGS = "🔀 Merge Tags⊹"
MENU_LABEL_MERGE_SCHEDULE = "🛻 Merge Schedule"
MENU_LABEL_TAG_DUPES = "Tag Dupes 🔖"
MENU_LABEL_DELETE_EMPTY = "❌ Empty Note Types࿏"
MENU_LABEL_BATCH_CHANGE = "Batch Change Note Types"
# ! -----------------------------------------------------------------------------


def _run_merge_tags_with_threshold(browser):
    threshold = prompt_fuzzy_threshold()
    if threshold is not None:
        unify_tags_on_duplicates(browser, threshold)


def compile_browser_context_menu(
    browser,
    menu,
    *,
    custom_tags_menu_label: str = DEFAULT_CUSTOM_TAGS_MENU_LABEL,
):
    selected = browser.selectedNotes()
    if not selected:
        return

    menu.addSeparator()

    # Tag-related root menu entries.
    add_missed_tag_menu_items(browser, menu)
    add_custom_tag_menu_items(browser, menu, menu_label=custom_tags_menu_label)

    menu.addSeparator()

    # Export NIDs (adds two Desktop files + copies query to clipboard)
    export_action = create_export_nids_action(parent=browser, mw=mw, browser=browser)
    menu.addAction(export_action)

    # Export UWorld Step QID tags (deduped + sorted + clipboard + Desktop file)
    export_uw_qids_action = QAction(MENU_LABEL_EXPORT_UW_QIDS, browser)
    export_uw_qids_action.triggered.connect(lambda: run_export_for_selected_notes(browser))
    menu.addAction(export_uw_qids_action)

    # Context menu image/table classifiers.
    classify_imgs_action = QAction(MENU_LABEL_ADD_IMG_CLASS, browser)
    classify_imgs_action.triggered.connect(lambda: add_img_class_main(browser))
    menu.addAction(classify_imgs_action)

    classify_tables_action = QAction(MENU_LABEL_ADD_TABLE_CLASS, browser)
    classify_tables_action.triggered.connect(lambda: add_class_main(browser))
    menu.addAction(classify_tables_action)

    # Create submenus for grouped actions.
    edit_menu = QMenu(MENU_LABEL_EDIT_MENU, menu)
    edit_menu.setObjectName("editMenu")
    added_edit = False

    merge_menu = QMenu(MENU_LABEL_MERGE_MENU, menu)
    merge_menu.setObjectName("mergeMenu")
    added_merge = False

    unify_img_and_tags_action = QAction(MENU_LABEL_MERGE_IMGS_TAGS, browser)
    unify_img_and_tags_action.triggered.connect(lambda _=None: merge_imgs_and_tags(browser=browser))
    merge_menu.addAction(unify_img_and_tags_action)
    added_merge = True

    merge_imgs_action = QAction(MENU_LABEL_MERGE_IMAGES, browser)
    merge_imgs_action.triggered.connect(lambda: merge_images_main(selected, browser))
    merge_menu.addAction(merge_imgs_action)
    added_merge = True

    unify_tags_action = QAction(MENU_LABEL_MERGE_TAGS, browser)
    unify_tags_action.triggered.connect(lambda: _run_merge_tags_with_threshold(browser))
    merge_menu.addAction(unify_tags_action)
    added_merge = True

    merge_sched_action = QAction(MENU_LABEL_MERGE_SCHEDULE, browser)
    merge_sched_action.triggered.connect(lambda: run_merge_scheduling(browser))
    merge_menu.addAction(merge_sched_action)
    added_merge = True

    tag_dupes_action = QAction(MENU_LABEL_TAG_DUPES, browser)
    tag_dupes_action.triggered.connect(lambda: run_tag_dupes(browser, debug=True))
    edit_menu.addAction(tag_dupes_action)
    added_edit = True

    delete_empty_action = QAction(MENU_LABEL_DELETE_EMPTY, browser)
    delete_empty_action.triggered.connect(delete_empty_note_types)
    edit_menu.addAction(delete_empty_action)
    added_edit = True

    batch_change_action = QAction(MENU_LABEL_BATCH_CHANGE, browser)
    batch_change_action.triggered.connect(lambda: change_selected_notes(browser))
    edit_menu.addAction(batch_change_action)
    added_edit = True

    if added_merge:
        menu.addSeparator()
        menu.addMenu(merge_menu)

    if added_edit:
        menu.addMenu(edit_menu)
        menu.addSeparator()
