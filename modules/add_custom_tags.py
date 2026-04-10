# pyright: reportMissingImports=false
from __future__ import annotations

from typing import Any

from aqt.qt import QAction, QMenu
from aqt.utils import showInfo, tooltip

from ..config_manager import ConfigManager
from .shared.defaults import ADD_CUSTOM_TAGS_DEFAULTS

# ! ----------------------------- CONFIG SECTION -----------------------------
CONFIG_SECTION = "add_custom_tags"
# ! ------------------------------------------------------------------------

# ! --------------------------- OPTIONAL CONFIG KEYS ---------------------------
CONFIG_KEY_SUBMENU_LABEL = "submenu_label"
CONFIG_KEY_PRESETS = "presets"
CONFIG_KEY_GROUP = "group"
# ! -----------------------------------------------------------------------------

# ! --------------------- USER-TUNABLE BUILT-IN CUSTOM ACTIONS -------------------
MANAGEMENT_TREATMENT_LABEL = "Management Tx"
MANAGEMENT_TREATMENT_TAG = "#Custom::#Management::#Treatment"
# ! -----------------------------------------------------------------------------

# ! ------------------------- USER-TUNABLE UI STYLING ----------------------------
CUSTOM_MENU_STYLESHEET = """
    QMenu::item {
        padding-top: 4.5px;
        padding-bottom: 4.5px;
        padding-left: 6px;
        padding-right: 6px;
    }
    QMenu::item:selected {
        background-color: rgba(120, 160, 255, 60);  /* subtle hover highlight */
    }
"""
# ! -----------------------------------------------------------------------------

# ! ----------------------- HARDCODED UI MESSAGES -----------------------
MSG_NO_NOTES_SELECTED = "❌ No notes selected."
MSG_APPLIED_TEMPLATE = "✅ Applied {tag_count} tag(s) to {note_count} notes."
# ! --------------------------------------------------------------------


def _to_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []

    if isinstance(value, list):
        out = [str(v).strip() for v in value if str(v).strip()]
        return out

    return []


def _normalize_group(value: Any) -> str | None:
    if value is None:
        return None
    group = str(value).strip()
    return group or None


def _normalize_presets(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []

    normalized: list[dict[str, Any]] = []
    for preset in raw:
        if not isinstance(preset, dict):
            continue

        label = str(preset.get("label", "")).strip()
        tags = _to_string_list(preset.get("tags", []))
        if not label or not tags:
            continue

        normalized_preset: dict[str, Any] = {"label": label, "tags": tags}
        group = _normalize_group(preset.get(CONFIG_KEY_GROUP))
        if group:
            normalized_preset["group"] = group
        normalized.append(normalized_preset)

    return normalized


def _preset_list_contains_tag(presets: list[dict[str, Any]], tag: str) -> bool:
    for preset in presets:
        tags = preset.get("tags", [])
        if any(str(existing).strip() == tag for existing in tags):
            return True
    return False


def _load_runtime_config(
    menu_label_override: str | None = None,
) -> tuple[str, list[dict[str, Any]], str, str]:
    section_cfg = ConfigManager(CONFIG_SECTION).load()
    if not isinstance(section_cfg, dict):
        section_cfg = {}

    configured_submenu_label = str(section_cfg.get(CONFIG_KEY_SUBMENU_LABEL, "")).strip()
    if isinstance(menu_label_override, str) and menu_label_override.strip():
        submenu_label = menu_label_override.strip()
    elif configured_submenu_label:
        submenu_label = configured_submenu_label
    else:
        submenu_label = ADD_CUSTOM_TAGS_DEFAULTS["submenu_label"]

    # Presets come from config only; no hardcoded fallback presets.
    presets = _normalize_presets(section_cfg.get(CONFIG_KEY_PRESETS, []))

    return submenu_label, presets, MSG_NO_NOTES_SELECTED, MSG_APPLIED_TEMPLATE


def _add_tag_safe(note, tag: str):
    if hasattr(note, "add_tag"):
        note.add_tag(tag)
    else:
        note.addTag(tag)


def _save_note_safe(col, note):
    try:
        col.update_note(note)
    except Exception:
        note.flush()


def _apply_tags_to_selected_notes(
    browser,
    tags: list[str],
    *,
    msg_no_notes_selected: str,
    msg_applied_template: str,
):
    nids = browser.selectedNotes()
    if not nids:
        showInfo(msg_no_notes_selected)
        return

    # Deduplicate while preserving order
    final_tags: list[str] = []
    seen = set()
    for tag in tags:
        if tag and tag not in seen:
            seen.add(tag)
            final_tags.append(tag)

    if not final_tags:
        return

    col = browser.mw.col
    for nid in nids:
        note = col.get_note(nid)
        current_tags = set(note.tags)
        for tag in final_tags:
            if tag not in current_tags:
                _add_tag_safe(note, tag)
        _save_note_safe(col, note)

    browser.model.reset()
    tooltip(msg_applied_template.format(tag_count=len(final_tags), note_count=len(nids)))


def add_custom_tag_menu_items(
    browser,
    parent_menu,
    *,
    menu_label: str | None = None,
):
    submenu_label, presets, msg_no_notes_selected, msg_applied_template = _load_runtime_config(
        menu_label_override=menu_label
    )

    custom_menu = QMenu(submenu_label, browser)
    custom_menu.setStyleSheet(CUSTOM_MENU_STYLESHEET)

    root_presets: list[dict[str, Any]] = []
    grouped_presets: dict[str, list[dict[str, Any]]] = {}
    for preset in presets:
        group_name = str(preset.get(CONFIG_KEY_GROUP, "")).strip()
        if not group_name:
            root_presets.append(preset)
            continue
        if group_name not in grouped_presets:
            grouped_presets[group_name] = []
        grouped_presets[group_name].append(preset)

    def _add_preset_action(target_menu: QMenu, preset: dict[str, Any]) -> None:
        label = preset["label"]
        tags = list(preset["tags"])

        action = QAction(label, browser)
        action.triggered.connect(
            lambda _=None, preset_tags=tags: _apply_tags_to_selected_notes(
                browser,
                preset_tags,
                msg_no_notes_selected=msg_no_notes_selected,
                msg_applied_template=msg_applied_template,
            )
        )
        target_menu.addAction(action)

    for preset in root_presets:
        _add_preset_action(custom_menu, preset)

    if not _preset_list_contains_tag(presets, MANAGEMENT_TREATMENT_TAG):
        management_action = QAction(MANAGEMENT_TREATMENT_LABEL, browser)
        management_action.triggered.connect(
            lambda _=None: _apply_tags_to_selected_notes(
                browser,
                [MANAGEMENT_TREATMENT_TAG],
                msg_no_notes_selected=msg_no_notes_selected,
                msg_applied_template=msg_applied_template,
            )
        )
        custom_menu.addAction(management_action)

    for group_name, group_items in grouped_presets.items():
        group_menu = QMenu(group_name, browser)
        group_menu.setStyleSheet(CUSTOM_MENU_STYLESHEET)
        for preset in group_items:
            _add_preset_action(group_menu, preset)
        if group_menu.actions():
            custom_menu.addMenu(group_menu)

    if custom_menu.actions():
        parent_menu.addSeparator()
        parent_menu.addMenu(custom_menu)
