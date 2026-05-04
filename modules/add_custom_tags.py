# pyright: reportMissingImports=false
from __future__ import annotations

from typing import Any

from aqt.qt import QAction, QMenu
from aqt.utils import showInfo, tooltip

from ..config_manager import ConfigManager
from .shared.defaults import ADD_CUSTOM_TAGS_DEFAULTS
from .shared.menu_styles import build_custom_tags_menu_stylesheet

# ! ----------------------------- CONFIG SECTION -----------------------------
DEFAULT_PARENT_CONFIG_SECTION = "custom_tags_config"
DEFAULT_CONFIG_SECTION = "add_custom_tags_1"
DEFAULT_HIDE_WHEN_NO_PRESETS = False
LEGACY_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "add_custom_tags_1": ("add_custom_tags",),
    "add_custom_tags_2": (),
}
# ! ------------------------------------------------------------------------

# ! --------------------------- OPTIONAL CONFIG KEYS ---------------------------
CONFIG_KEY_SUBMENU_LABEL = "submenu_label"
CONFIG_KEY_GROUP_LABELS = "group_labels"
CONFIG_KEY_PRESETS = "presets"
CONFIG_KEY_GROUP = "group"
CONFIG_KEY_REVIEW_SHORTCUT = "review_shortcut"
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


def _normalize_shortcut(value: Any) -> str | None:
    if value is None:
        return None
    shortcut = str(value).strip()
    return shortcut or None


def _normalize_presets(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []

    normalized: list[dict[str, Any]] = []
    for preset in raw:
        if not isinstance(preset, dict):
            continue

        raw_label = preset.get("label", preset.get("menu_label", ""))
        label = str(raw_label).strip() if raw_label is not None else ""
        tags = _to_string_list(preset.get("tags", []))
        if not label or not tags:
            continue

        normalized_preset: dict[str, Any] = {"label": label, "tags": tags}
        group = _normalize_group(preset.get(CONFIG_KEY_GROUP))
        if group:
            normalized_preset["group"] = group
        review_shortcut = _normalize_shortcut(preset.get(CONFIG_KEY_REVIEW_SHORTCUT))
        if review_shortcut:
            normalized_preset[CONFIG_KEY_REVIEW_SHORTCUT] = review_shortcut
        normalized.append(normalized_preset)

    return normalized


def _normalize_group_labels(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}

    normalized: dict[str, str] = {}
    for group_key, group_label in raw.items():
        key = str(group_key).strip()
        label = str(group_label).strip()
        if key and label:
            normalized[key] = label
    return normalized


def _load_runtime_config(
    menu_label_override: str | None = None,
    config_section: str = DEFAULT_CONFIG_SECTION,
    parent_config_section: str = DEFAULT_PARENT_CONFIG_SECTION,
) -> tuple[str, dict[str, str], list[dict[str, Any]], str, str]:
    root_cfg = ConfigManager(ConfigManager.ROOT_ADDON_NAME).load()
    if not isinstance(root_cfg, dict):
        root_cfg = {}

    section_cfg: dict[str, Any] = {}

    parent_cfg = root_cfg.get(parent_config_section, {})
    if isinstance(parent_cfg, dict):
        nested_cfg = parent_cfg.get(config_section)
        if isinstance(nested_cfg, dict):
            section_cfg = nested_cfg
        else:
            for alias in LEGACY_SECTION_ALIASES.get(config_section, ()):
                alias_cfg = parent_cfg.get(alias)
                if isinstance(alias_cfg, dict):
                    section_cfg = alias_cfg
                    break

    if not section_cfg:
        top_level_cfg = root_cfg.get(config_section)
        if isinstance(top_level_cfg, dict):
            section_cfg = top_level_cfg
        else:
            for alias in LEGACY_SECTION_ALIASES.get(config_section, ()):
                alias_cfg = root_cfg.get(alias)
                if isinstance(alias_cfg, dict):
                    section_cfg = alias_cfg
                    break

    if not isinstance(section_cfg, dict):
        section_cfg = {}

    configured_submenu_label = str(section_cfg.get(CONFIG_KEY_SUBMENU_LABEL, "")).strip()
    if isinstance(menu_label_override, str) and menu_label_override.strip():
        submenu_label = menu_label_override.strip()
    elif configured_submenu_label:
        submenu_label = configured_submenu_label
    else:
        submenu_label = ADD_CUSTOM_TAGS_DEFAULTS["submenu_label"]

    group_labels = _normalize_group_labels(section_cfg.get(CONFIG_KEY_GROUP_LABELS, {}))

    # Presets come from config only; no hardcoded fallback presets.
    presets = _normalize_presets(section_cfg.get(CONFIG_KEY_PRESETS, []))

    return submenu_label, group_labels, presets, MSG_NO_NOTES_SELECTED, MSG_APPLIED_TEMPLATE


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


def _dedupe_tags(tags: list[str]) -> list[str]:
    final_tags: list[str] = []
    seen = set()
    for tag in tags:
        if tag and tag not in seen:
            seen.add(tag)
            final_tags.append(tag)
    return final_tags


def apply_tags_to_note(col, note, tags: list[str]) -> int:
    """Apply unique tags to one note and return number of newly added tags."""
    final_tags = _dedupe_tags(tags)
    if not final_tags:
        return 0

    current_tags = set(note.tags)
    added_count = 0
    for tag in final_tags:
        if tag not in current_tags:
            _add_tag_safe(note, tag)
            current_tags.add(tag)
            added_count += 1

    _save_note_safe(col, note)
    return added_count


def iter_reviewer_shortcut_actions(
    *,
    config_section: str = DEFAULT_CONFIG_SECTION,
) -> list[tuple[str, str, list[str]]]:
    """Return (shortcut, preset_label, tags) entries for reviewer shortcuts."""
    _, _, presets, _, _ = _load_runtime_config(config_section=config_section)

    actions: list[tuple[str, str, list[str]]] = []
    seen_shortcuts: set[str] = set()
    for preset in presets:
        shortcut = _normalize_shortcut(preset.get(CONFIG_KEY_REVIEW_SHORTCUT))
        if not shortcut:
            continue

        shortcut_key = shortcut.lower()
        if shortcut_key in seen_shortcuts:
            continue

        seen_shortcuts.add(shortcut_key)
        actions.append((shortcut, preset["label"], list(preset["tags"])))

    return actions


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

    final_tags = _dedupe_tags(tags)

    if not final_tags:
        return

    col = browser.mw.col
    for nid in nids:
        note = col.get_note(nid)
        apply_tags_to_note(col, note, final_tags)

    browser.model.reset()
    tooltip(msg_applied_template.format(tag_count=len(final_tags), note_count=len(nids)))


def _apply_menu_style(menu: QMenu) -> None:
    stylesheet = build_custom_tags_menu_stylesheet()
    if stylesheet:
        menu.setStyleSheet(stylesheet)
        return

    # Empty stylesheet keeps native Qt/platform menu visuals.
    menu.setStyleSheet("")


def _display_group_label(group_key: str, group_labels: dict[str, str]) -> str:
    configured = group_labels.get(group_key, "")
    normalized = str(configured).strip()
    return normalized or group_key


def add_custom_tag_menu_items(
    browser,
    parent_menu,
    *,
    menu_label: str | None = None,
    config_section: str = DEFAULT_CONFIG_SECTION,
    hide_when_no_presets: bool = DEFAULT_HIDE_WHEN_NO_PRESETS,
    add_separator_before: bool = False,
) -> bool:
    (
        submenu_label,
        group_labels,
        presets,
        msg_no_notes_selected,
        msg_applied_template,
    ) = _load_runtime_config(
        menu_label_override=menu_label,
        config_section=config_section,
    )

    if hide_when_no_presets and not presets:
        return False

    custom_menu = QMenu(submenu_label, browser)
    _apply_menu_style(custom_menu)

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

    for group_name, group_items in grouped_presets.items():
        group_menu_label = _display_group_label(group_name, group_labels)
        group_menu = QMenu(group_menu_label, browser)
        _apply_menu_style(group_menu)
        for preset in group_items:
            _add_preset_action(group_menu, preset)
        if group_menu.actions():
            custom_menu.addMenu(group_menu)

    if custom_menu.actions():
        if add_separator_before:
            parent_menu.addSeparator()
        parent_menu.addMenu(custom_menu)
        return True

    return False
