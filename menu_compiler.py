"""Browser context-menu compiler for _Change_notes.

This module centralizes imports and menu wiring for actions inserted
into Anki's Browser right-click menu.
"""

# pyright: reportMissingImports=false

from typing import Optional

from aqt import mw
from aqt.qt import QAction, QMenu

from .config_manager import ConfigManager
from .modules.add_custom_tags import add_custom_tag_menu_items, discover_custom_tag_sections
from .modules.Add_img_class import main as add_img_class_main
from .modules.add_missed_tags import add_missed_tag_menu_items
from .modules.add_table_class.main import add_class_main
from .modules.change_note_types import change_selected_notes
from .modules.shared.parsing import parse_bool
from .modules.del_empty_notes import delete_empty_note_types
from .modules.export_nids import create_export_nids_action
from .modules.export_UW_qid_tags import run_export_for_selected_notes
from .modules.img_tags_merge import merge_imgs_and_tags
from .modules.merge_imgs import merge_images_main
from .modules.merge_schedule import run_merge_scheduling
from .modules.merge_tags import prompt_fuzzy_threshold, unify_tags_on_duplicates
from .modules.shared.menu_styles import (
    build_context_submenu_arrow_stylesheet,
    build_context_submenu_item_stylesheet,
)
from .modules.tag_dupes import run_tag_dupes

# ! --------------------------- USER-TUNABLE CONSTANTS ---------------------------
DEFAULT_CUSTOM_TAGS_MENU_LABEL = " 🎛️ Custom Tags"
DEFAULT_CUSTOM_TAGS_MENU_HIDE_WHEN_NO_PRESETS = False
GLOBAL_SECTION_KEY = "global_config"
GLOBAL_MAIN_MENU_SEPARATOR_BEFORE_KEY = "main_context_menu_separator_before"
GLOBAL_MAIN_MENU_SEPARATOR_AFTER_EDIT_KEY = "main_context_menu_separator_after_edit_menu"
MENU_ITEM_KEY_MISSED_TAGS = "missed_tags_menu"
MENU_ITEM_KEY_OTHER_ACTIONS = "other_actions_menu"
MENU_ITEM_KEY_ADD_IMG_CLASS = "add_img_class_action"
MENU_ITEM_KEY_MERGE_MENU = "merge_menu"
MENU_ITEM_KEY_EDIT_MENU = "edit_menu"
DEFAULT_MAIN_MENU_SEPARATOR_BEFORE: dict[str, bool] = {
    MENU_ITEM_KEY_MISSED_TAGS: True,
    "add_custom_tags_1": False,
    "add_custom_tags_2": False,
    "add_custom_tags_3": False,
    MENU_ITEM_KEY_OTHER_ACTIONS: True,
    MENU_ITEM_KEY_ADD_IMG_CLASS: False,
    MENU_ITEM_KEY_MERGE_MENU: True,
    MENU_ITEM_KEY_EDIT_MENU: False,
}
DEFAULT_MAIN_MENU_SEPARATOR_BEFORE_FALLBACK = False
DEFAULT_MAIN_MENU_SEPARATOR_AFTER_EDIT_MENU = True
MENU_LABEL_EXPORT_UW_QIDS = "Export UW QID tag(s) 🧿"
MENU_LABEL_ADD_IMG_CLASS = "Add IMG class 🏞️"
MENU_LABEL_ADD_TABLE_CLASS = "📊 Add Table class (col)"
MENU_LABEL_OTHER_ACTIONS = "Other actions"
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


def _apply_submenu_arrow_style(menu: QMenu) -> None:
    extra_stylesheet = build_context_submenu_arrow_stylesheet()
    if not extra_stylesheet:
        return

    current_stylesheet = menu.styleSheet() or ""
    if extra_stylesheet in current_stylesheet:
        return

    joined = f"{current_stylesheet}\n{extra_stylesheet}".strip()
    menu.setStyleSheet(joined)


def _apply_submenu_item_style(menu: QMenu) -> None:
    extra_stylesheet = build_context_submenu_item_stylesheet()
    if not extra_stylesheet:
        return

    current_stylesheet = menu.styleSheet() or ""
    if extra_stylesheet in current_stylesheet:
        return

    joined = f"{current_stylesheet}\n{extra_stylesheet}".strip()
    menu.setStyleSheet(joined)


def _run_merge_tags_with_threshold(browser):
    threshold = prompt_fuzzy_threshold(parent=browser)
    if threshold is not None:
        unify_tags_on_duplicates(browser, threshold)


def _selected_note_type_count(browser, selected_nids: list[int]) -> int:
    mids = set()
    col = browser.mw.col
    for nid in selected_nids:
        try:
            mids.add(col.get_note(nid).model()["id"])
        except Exception:
            continue
    return len(mids)


def _should_show_batch_change_action(browser, selected_nids: list[int]) -> bool:
    cfg = ConfigManager("batch_note_change_config").load()
    hide_for_single = parse_bool(cfg.get("hide_menu_when_one_type_selected", False), default=False)
    allow_single_override = parse_bool(cfg.get("allow_single_type_override", True), default=True)
    if not hide_for_single:
        return True
    if allow_single_override:
        return True
    return _selected_note_type_count(browser, selected_nids) > 1


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _load_main_menu_separator_config(root_cfg: dict | None) -> tuple[dict[str, object], bool]:
    root_cfg_dict = _as_dict(root_cfg)
    global_cfg = _as_dict(root_cfg_dict.get(GLOBAL_SECTION_KEY))
    separator_before_cfg = _as_dict(global_cfg.get(GLOBAL_MAIN_MENU_SEPARATOR_BEFORE_KEY))
    separator_after_edit = parse_bool(
        global_cfg.get(
            GLOBAL_MAIN_MENU_SEPARATOR_AFTER_EDIT_KEY,
            DEFAULT_MAIN_MENU_SEPARATOR_AFTER_EDIT_MENU,
        ),
        default=DEFAULT_MAIN_MENU_SEPARATOR_AFTER_EDIT_MENU,
    )
    return separator_before_cfg, separator_after_edit


def _main_menu_separator_before_enabled(separator_before_cfg: dict[str, object], item_key: str) -> bool:
    default = DEFAULT_MAIN_MENU_SEPARATOR_BEFORE.get(
        item_key,
        DEFAULT_MAIN_MENU_SEPARATOR_BEFORE_FALLBACK,
    )
    return parse_bool(separator_before_cfg.get(item_key, default), default=default)


def _add_separator_if_needed(menu) -> QAction | None:
    actions = menu.actions()
    if actions and actions[-1].isSeparator():
        return None
    return menu.addSeparator()


def _add_separator_before_item_if_enabled(
    menu,
    separator_before_cfg: dict[str, object],
    item_key: str,
) -> QAction | None:
    if not _main_menu_separator_before_enabled(separator_before_cfg, item_key):
        return None
    return _add_separator_if_needed(menu)


def _rollback_separator_if_item_not_added(menu, separator_action: QAction | None, *, item_added: bool) -> None:
    if item_added or separator_action is None:
        return
    menu.removeAction(separator_action)


def compile_browser_context_menu(
    browser,
    menu,
    *,
    custom_tags_menu_label: Optional[str] = DEFAULT_CUSTOM_TAGS_MENU_LABEL,
    custom_tags_menu_hide_when_no_presets: bool = DEFAULT_CUSTOM_TAGS_MENU_HIDE_WHEN_NO_PRESETS,
):
    _apply_submenu_arrow_style(menu)

    selected = browser.selectedNotes()
    if not selected:
        return

    root_cfg = ConfigManager(ConfigManager.ROOT_ADDON_NAME).load()
    separator_before_cfg, separator_after_edit_menu = _load_main_menu_separator_config(root_cfg)

    # Tag-related root menu entries.
    missed_separator = _add_separator_before_item_if_enabled(
        menu,
        separator_before_cfg,
        MENU_ITEM_KEY_MISSED_TAGS,
    )
    menu_actions_before_missed = len(menu.actions())
    add_missed_tag_menu_items(browser, menu)
    missed_menu_added = len(menu.actions()) > menu_actions_before_missed
    _rollback_separator_if_item_not_added(
        menu,
        missed_separator,
        item_added=missed_menu_added,
    )

    custom_tag_sections = discover_custom_tag_sections(root_cfg=root_cfg)
    for section_index, section_key in enumerate(custom_tag_sections):
        section_label_override = custom_tags_menu_label if section_index == 0 else None
        custom_separator = _add_separator_before_item_if_enabled(
            menu,
            separator_before_cfg,
            section_key,
        )
        custom_menu_added = add_custom_tag_menu_items(
            browser,
            menu,
            menu_label=section_label_override,
            config_section=section_key,
            hide_when_no_presets=custom_tags_menu_hide_when_no_presets,
            add_separator_before=False,
            root_cfg=root_cfg,
        )
        _rollback_separator_if_item_not_added(
            menu,
            custom_separator,
            item_added=custom_menu_added,
        )

    other_actions_menu = QMenu(MENU_LABEL_OTHER_ACTIONS, menu)
    other_actions_menu.setObjectName("otherActionsMenu")
    _apply_submenu_item_style(other_actions_menu)
    _apply_submenu_arrow_style(other_actions_menu)
    added_other_actions = False

    # Export NIDs (adds one simple Desktop file + copies list to clipboard)
    export_action = create_export_nids_action(parent=browser, mw=mw, browser=browser)
    other_actions_menu.addAction(export_action)
    added_other_actions = True

    # Export UWorld Step QID tags (deduped + sorted + clipboard + Desktop file)
    export_uw_qids_action = QAction(MENU_LABEL_EXPORT_UW_QIDS, browser)
    export_uw_qids_action.triggered.connect(lambda: run_export_for_selected_notes(browser))
    other_actions_menu.addAction(export_uw_qids_action)
    added_other_actions = True

    classify_tables_action = QAction(MENU_LABEL_ADD_TABLE_CLASS, browser)
    classify_tables_action.triggered.connect(lambda: add_class_main(browser))
    other_actions_menu.addAction(classify_tables_action)
    added_other_actions = True

    if added_other_actions:
        _add_separator_before_item_if_enabled(
            menu,
            separator_before_cfg,
            MENU_ITEM_KEY_OTHER_ACTIONS,
        )
        menu.addMenu(other_actions_menu)

    # Context menu image/table classifiers.
    classify_imgs_action = QAction(MENU_LABEL_ADD_IMG_CLASS, browser)
    classify_imgs_action.triggered.connect(lambda: add_img_class_main(browser))
    _add_separator_before_item_if_enabled(
        menu,
        separator_before_cfg,
        MENU_ITEM_KEY_ADD_IMG_CLASS,
    )
    menu.addAction(classify_imgs_action)

    # Create submenus for grouped actions.
    edit_menu = QMenu(MENU_LABEL_EDIT_MENU, menu)
    edit_menu.setObjectName("editMenu")
    _apply_submenu_item_style(edit_menu)
    _apply_submenu_arrow_style(edit_menu)
    added_edit = False

    merge_menu = QMenu(MENU_LABEL_MERGE_MENU, menu)
    merge_menu.setObjectName("mergeMenu")
    _apply_submenu_item_style(merge_menu)
    _apply_submenu_arrow_style(merge_menu)
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

    if _should_show_batch_change_action(browser, selected):
        batch_change_action = QAction(MENU_LABEL_BATCH_CHANGE, browser)
        batch_change_action.triggered.connect(lambda: change_selected_notes(browser))
        edit_menu.addAction(batch_change_action)
        added_edit = True

    if added_merge:
        _add_separator_before_item_if_enabled(
            menu,
            separator_before_cfg,
            MENU_ITEM_KEY_MERGE_MENU,
        )
        menu.addMenu(merge_menu)

    if added_edit:
        _add_separator_before_item_if_enabled(
            menu,
            separator_before_cfg,
            MENU_ITEM_KEY_EDIT_MENU,
        )
        menu.addMenu(edit_menu)
        if separator_after_edit_menu:
            _add_separator_if_needed(menu)
