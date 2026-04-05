# pyright: reportMissingImports=false
from __future__ import annotations

from typing import Any

from aqt.qt import QAction, QMenu
from aqt.utils import showInfo, tooltip

from ..config_manager import ConfigManager

# ! ----------------------------- CONFIG SECTION -----------------------------
CONFIG_SECTION = "add_custom_tags"
# ! ------------------------------------------------------------------------

# ! --------------------------- USER-TUNABLE DEFAULTS ---------------------------
DEFAULT_SUBMENU_LABEL = "Custom Tags"
DEFAULT_MSG_NO_NOTES_SELECTED = "❌ No notes selected."
DEFAULT_MSG_APPLIED_TEMPLATE = "✅ Applied {tag_count} tag(s) to {note_count} notes."
# ! -----------------------------------------------------------------------------

# ! --------------------------- OPTIONAL CONFIG KEYS ---------------------------
CONFIG_KEY_SUBMENU_LABEL = "submenu_label"
CONFIG_KEY_PRESETS = "presets"
CONFIG_KEY_MSG_NO_NOTES_SELECTED = "message_no_notes_selected"
CONFIG_KEY_MSG_APPLIED_TEMPLATE = "message_applied_template"
# ! -----------------------------------------------------------------------------


def _to_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []

    if isinstance(value, list):
        out = [str(v).strip() for v in value if str(v).strip()]
        return out

    return []


def _normalize_presets(raw: Any) -> list[dict[str, list[str]]]:
    if not isinstance(raw, list):
        return []

    normalized: list[dict[str, list[str]]] = []
    for preset in raw:
        if not isinstance(preset, dict):
            continue

        label = str(preset.get("label", "")).strip()
        tags = _to_string_list(preset.get("tags", []))
        if not label or not tags:
            continue

        normalized.append({"label": label, "tags": tags})

    return normalized


def _load_runtime_config(
    menu_label_override: str | None = None,
) -> tuple[str, list[dict[str, list[str]]], str, str]:
    section_cfg = ConfigManager(CONFIG_SECTION).load()
    if not isinstance(section_cfg, dict):
        section_cfg = {}

    configured_submenu_label = str(section_cfg.get(CONFIG_KEY_SUBMENU_LABEL, "")).strip()
    if isinstance(menu_label_override, str) and menu_label_override.strip():
        submenu_label = menu_label_override.strip()
    elif configured_submenu_label:
        submenu_label = configured_submenu_label
    else:
        submenu_label = DEFAULT_SUBMENU_LABEL

    configured_no_notes = str(section_cfg.get(CONFIG_KEY_MSG_NO_NOTES_SELECTED, "")).strip()
    configured_applied_template = str(section_cfg.get(CONFIG_KEY_MSG_APPLIED_TEMPLATE, "")).strip()
    msg_no_notes_selected = configured_no_notes or DEFAULT_MSG_NO_NOTES_SELECTED
    msg_applied_template = configured_applied_template or DEFAULT_MSG_APPLIED_TEMPLATE

    # Presets come from config only; no hardcoded fallback presets.
    presets = _normalize_presets(section_cfg.get(CONFIG_KEY_PRESETS, []))

    return submenu_label, presets, msg_no_notes_selected, msg_applied_template


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
    if not presets:
        return

    custom_menu = QMenu(submenu_label, browser)

    for preset in presets:
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
        custom_menu.addAction(action)

    if custom_menu.actions():
        parent_menu.addSeparator()
        parent_menu.addMenu(custom_menu)
