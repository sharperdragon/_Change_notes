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
DEFAULT_SUBMENU_LABEL = " 🎛️ Custom Tags"
DEFAULT_PRESETS = [
    {
        "label": "Drug ADRs 😵",
        "tags": ["#Custom::Bugs+Drugs::Drugs::ADRs"],
    },
    {
        "label": "D.O. Med 🌬️",
        "tags": ["#Custom::DO_Med"],
    },
]

MSG_NO_NOTES_SELECTED = "❌ No notes selected."
MSG_APPLIED_TEMPLATE = "✅ Applied {tag_count} tag(s) to {note_count} notes."
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


def _load_runtime_config() -> tuple[str, list[dict[str, list[str]]]]:
    section_cfg = ConfigManager(CONFIG_SECTION).load()
    if not isinstance(section_cfg, dict):
        section_cfg = {}

    submenu_label = str(section_cfg.get("submenu_label", DEFAULT_SUBMENU_LABEL)).strip()
    if not submenu_label:
        submenu_label = DEFAULT_SUBMENU_LABEL

    presets = _normalize_presets(section_cfg.get("presets", DEFAULT_PRESETS))
    if not presets:
        presets = _normalize_presets(DEFAULT_PRESETS)

    return submenu_label, presets


def _add_tag_safe(note, tag: str):
    if hasattr(note, "add_tag"):
        note.add_tag(tag)
    else:
        note.addTag(tag)


def _apply_tags_to_selected_notes(browser, tags: list[str]):
    nids = browser.selectedNotes()
    if not nids:
        showInfo(MSG_NO_NOTES_SELECTED)
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
        note.flush()

    browser.model.reset()
    tooltip(MSG_APPLIED_TEMPLATE.format(tag_count=len(final_tags), note_count=len(nids)))


def add_custom_tag_menu_items(browser, parent_menu):
    submenu_label, presets = _load_runtime_config()
    if not presets:
        return

    custom_menu = QMenu(submenu_label, browser)

    for preset in presets:
        label = preset["label"]
        tags = list(preset["tags"])

        action = QAction(label, browser)
        action.triggered.connect(
            lambda _=None, preset_tags=tags: _apply_tags_to_selected_notes(browser, preset_tags)
        )
        custom_menu.addAction(action)

    if custom_menu.actions():
        parent_menu.addSeparator()
        parent_menu.addMenu(custom_menu)
