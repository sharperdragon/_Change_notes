# pyright: reportMissingImports=false
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aqt.qt import QAction, QInputDialog, QMenu
from aqt.utils import showInfo, tooltip

from ..config_manager import ConfigManager
from .shared.defaults import ADD_MISSED_TAGS_DEFAULTS
from .shared.menu_styles import build_qmenu_stylesheet

# ! ----------------------------- CONFIG SECTIONS -----------------------------
CANONICAL_CONFIG_SECTION = "tag_missed_qid_notes"
LEGACY_CONFIG_SECTION = "add_missed_tags"
LEGACY_SELECTED_NOTES_SECTION = "tag_selected_notes_config"
LEGACY_MODULE_CONFIG_SECTION = "add_tags"
LEGACY_CONFIG_SECTIONS = [
    LEGACY_CONFIG_SECTION,
    LEGACY_SELECTED_NOTES_SECTION,
    LEGACY_MODULE_CONFIG_SECTION,
]
# ! -------------------------------------------------------------------------

# ! ----------------------------- ENUMS / KEYS -----------------------------
SCHEDULE_POLICY_UNKNOWN = "unknown"
SCHEDULE_POLICY_NEXT = "next"

PROMPT_BEHAVIOR_BASE_PLUS_ROTATION = "base_plus_rotation"
PROMPT_BEHAVIOR_BASE_ONLY = "base_only"
PROMPT_STYLE_ROTATION_THEN_NUMBER = "rotation_then_number"
PROMPT_STYLE_RANGE_THEN_NUMBER = "range_then_number"

# Canonical config key paths (change-prone schema keys kept in one place).
PATH_UI_MENU_LABEL = ("ui", "menu_label")

PATH_ROTATION_SCHEDULE = ("rotation", "schedule")
PATH_ROTATION_EXHAUSTED_POLICY = ("rotation", "exhausted_policy")
PATH_ROTATION_PARENT_TAG_SEGMENT = ("rotation", "parent_tag_segment")
PATH_ROTATION_WINTER_BREAK_LABEL = ("rotation", "winter_break_label")
PATH_ROTATION_POST_ROTATION_LABEL = ("rotation", "post_rotation_label")

PATH_ACTION_BASE_LABEL = ("actions", "base", "label")
PATH_ACTION_BASE_TAGS = ("actions", "base", "tags")

PATH_ACTION_UWORLD_LABEL = ("actions", "uworld", "label")
PATH_ACTION_UWORLD_BASE_TAGS = ("actions", "uworld", "base_tags")
PATH_ACTION_UWORLD_DEFAULT_TAG_PREFIX = ("actions", "uworld", "default_tag_prefix")
PATH_ACTION_UWORLD_TEST_RANGE_BLOCK_SIZE = ("actions", "uworld", "test_range_block_size")

PATH_ACTION_NBME_LABEL = ("actions", "nbme", "label")
PATH_ACTION_NBME_BASE_TAGS = ("actions", "nbme", "base_tags")
PATH_ACTION_NBME_DEFAULT_TAG_PREFIX = ("actions", "nbme", "default_tag_prefix")

PATH_ACTION_AMBOSS_LABEL = ("actions", "amboss", "label")
PATH_ACTION_AMBOSS_BASE_TAG = ("actions", "amboss", "base_tag")
PATH_ACTION_AMBOSS_BLANK_BEHAVIOR = ("actions", "amboss", "blank_behavior")
PATH_ACTION_AMBOSS_NUMBER_STYLE = ("actions", "amboss", "number_style")
PATH_ACTION_AMBOSS_REMOVE_FROM_OTHER_MENU = ("actions", "amboss", "remove_from_other_menu")

PATH_ACTION_MULTI_MISSED_LABEL = ("actions", "multi_missed", "label")
PATH_ACTION_MULTI_MISSED_TAG_SEGMENT = ("actions", "multi_missed", "tag_segment")

PATH_ACTION_KEY_INFO_LABEL = ("actions", "key_info", "label")
PATH_ACTION_KEY_INFO_TAG_BASE = ("actions", "key_info", "tag_base")

PATH_ACTION_CORRECT_GUESS_LABEL = ("actions", "correct_guess", "label")
PATH_ACTION_CORRECT_GUESS_TAGS = ("actions", "correct_guess", "tags")
PATH_ACTION_CORRECT_GUESS_INCLUDE_ROTATION = ("actions", "correct_guess", "include_rotation")
PATH_ACTION_CORRECT_GUESS_ROTATION_LOWERCASE = ("actions", "correct_guess", "rotation_lowercase")
PATH_ACTION_CORRECT_GUESS_UNKNOWN_SEGMENT = ("actions", "correct_guess", "unknown_segment")

PATH_ACTION_OTHER_RESOURCES = ("actions", "other", "resources")
PATH_ACTION_OTHER_TAG_SUFFIX = ("actions", "other", "tag_suffix")

USE_CUSTOM_SUBMENU_ARROW_ICON = True
SUBMENU_ARROW_ICON_ABS_PATH = str((Path(__file__).resolve().parent / "assets" / "submenu_arrow.svg"))
SUBMENU_ARROW_ICON_SIZE_PX = 12
MENU_ITEM_HOVER_BACKGROUND_COLOR = "rgba(120, 160, 255, 60)"
MENU_ITEM_PADDING_TOP_PX = 4.5
MENU_ITEM_PADDING_BOTTOM_PX = 4.5
MENU_ITEM_PADDING_LEFT_PX = 6
MENU_ITEM_PADDING_RIGHT_PX = 6

CANONICAL_ALIAS_PATHS: tuple[tuple[tuple[str, ...], tuple[tuple[str, ...], ...]], ...] = (
    (PATH_UI_MENU_LABEL, (PATH_UI_MENU_LABEL, ("menu_label",))),
    (
        PATH_ROTATION_SCHEDULE,
        (PATH_ROTATION_SCHEDULE, ("rotation_schedule",)),
    ),
    (
        PATH_ROTATION_EXHAUSTED_POLICY,
        (PATH_ROTATION_EXHAUSTED_POLICY, ("schedule_exhausted_policy",)),
    ),
    (
        PATH_ROTATION_PARENT_TAG_SEGMENT,
        (PATH_ROTATION_PARENT_TAG_SEGMENT, ("tags", "rotation_parent_segment")),
    ),
    (
        PATH_ROTATION_WINTER_BREAK_LABEL,
        (PATH_ROTATION_WINTER_BREAK_LABEL, ("tags", "winter_break_label")),
    ),
    (
        PATH_ROTATION_POST_ROTATION_LABEL,
        (PATH_ROTATION_POST_ROTATION_LABEL, ("tags", "post_rotation_label")),
    ),
    (
        PATH_ACTION_BASE_LABEL,
        (PATH_ACTION_BASE_LABEL, ("ui", "action_label_base"), ("action_label_base",)),
    ),
    (
        PATH_ACTION_BASE_TAGS,
        (PATH_ACTION_BASE_TAGS, ("base_missed_tag",), ("missed_base_tag",)),
    ),
    (
        PATH_ACTION_UWORLD_LABEL,
        (PATH_ACTION_UWORLD_LABEL, ("subset_1_name",)),
    ),
    (
        PATH_ACTION_UWORLD_BASE_TAGS,
        (PATH_ACTION_UWORLD_BASE_TAGS, ("subset_tag_1",), ("subset_1_tag",)),
    ),
    (
        PATH_ACTION_UWORLD_DEFAULT_TAG_PREFIX,
        (PATH_ACTION_UWORLD_DEFAULT_TAG_PREFIX, ("tags", "default_test_tag_prefix")),
    ),
    (
        PATH_ACTION_UWORLD_TEST_RANGE_BLOCK_SIZE,
        (PATH_ACTION_UWORLD_TEST_RANGE_BLOCK_SIZE, ("test_range_block_size",)),
    ),
    (
        PATH_ACTION_NBME_LABEL,
        (PATH_ACTION_NBME_LABEL, ("subset_2_name",)),
    ),
    (
        PATH_ACTION_NBME_BASE_TAGS,
        (PATH_ACTION_NBME_BASE_TAGS, ("subset_tag_2",), ("subset_2_tag",)),
    ),
    (
        PATH_ACTION_NBME_DEFAULT_TAG_PREFIX,
        (
            PATH_ACTION_NBME_DEFAULT_TAG_PREFIX,
            ("tags", "default_nbme_tag_prefix"),
            ("tags", "default_comquest_tag_prefix"),
        ),
    ),
    (
        PATH_ACTION_AMBOSS_LABEL,
        (PATH_ACTION_AMBOSS_LABEL, ("amboss", "top_level_name")),
    ),
    (
        PATH_ACTION_AMBOSS_BASE_TAG,
        (PATH_ACTION_AMBOSS_BASE_TAG, ("amboss", "base_tag")),
    ),
    (
        PATH_ACTION_AMBOSS_BLANK_BEHAVIOR,
        (PATH_ACTION_AMBOSS_BLANK_BEHAVIOR, ("amboss", "blank_behavior")),
    ),
    (
        PATH_ACTION_AMBOSS_NUMBER_STYLE,
        (PATH_ACTION_AMBOSS_NUMBER_STYLE, ("amboss", "number_style")),
    ),
    (
        PATH_ACTION_AMBOSS_REMOVE_FROM_OTHER_MENU,
        (
            PATH_ACTION_AMBOSS_REMOVE_FROM_OTHER_MENU,
            ("amboss", "remove_from_other_menu"),
        ),
    ),
    (
        PATH_ACTION_MULTI_MISSED_LABEL,
        (
            PATH_ACTION_MULTI_MISSED_LABEL,
            ("ui", "action_label_multi_missed"),
            ("action_label_multi_missed",),
        ),
    ),
    (
        PATH_ACTION_MULTI_MISSED_TAG_SEGMENT,
        (PATH_ACTION_MULTI_MISSED_TAG_SEGMENT, ("tags", "multi_miss_tag")),
    ),
    (
        PATH_ACTION_KEY_INFO_LABEL,
        (
            PATH_ACTION_KEY_INFO_LABEL,
            ("ui", "action_label_key_info"),
            ("action_label_key_info",),
        ),
    ),
    (
        PATH_ACTION_KEY_INFO_TAG_BASE,
        (PATH_ACTION_KEY_INFO_TAG_BASE, ("tags", "key_tag_base")),
    ),
    (
        PATH_ACTION_CORRECT_GUESS_LABEL,
        (
            PATH_ACTION_CORRECT_GUESS_LABEL,
            ("ui", "action_label_correct_guess"),
            ("action_label_correct_guess",),
        ),
    ),
    (
        PATH_ACTION_CORRECT_GUESS_TAGS,
        (PATH_ACTION_CORRECT_GUESS_TAGS, ("correct_guess", "tags")),
    ),
    (
        PATH_ACTION_CORRECT_GUESS_INCLUDE_ROTATION,
        (
            PATH_ACTION_CORRECT_GUESS_INCLUDE_ROTATION,
            ("correct_guess", "include_rotation"),
        ),
    ),
    (
        PATH_ACTION_CORRECT_GUESS_ROTATION_LOWERCASE,
        (
            PATH_ACTION_CORRECT_GUESS_ROTATION_LOWERCASE,
            ("correct_guess", "rotation_lowercase"),
        ),
    ),
    (
        PATH_ACTION_CORRECT_GUESS_UNKNOWN_SEGMENT,
        (
            PATH_ACTION_CORRECT_GUESS_UNKNOWN_SEGMENT,
            ("correct_guess", "unknown_segment"),
        ),
    ),
    (
        PATH_ACTION_OTHER_RESOURCES,
        (PATH_ACTION_OTHER_RESOURCES, ("other_menu", "resources"), ("other_resources",)),
    ),
    (
        PATH_ACTION_OTHER_TAG_SUFFIX,
        (PATH_ACTION_OTHER_TAG_SUFFIX, ("tags", "other_suffix")),
    ),
)
# ! -------------------------------------------------------------------------

# ? Exclude list for auto-added rotation/month context tags.
EXCLUDE_AUTO_MISS = {
    "add_key_info_action",
    "base_plain",
    "correct_guess",
}


@dataclass(frozen=True)
class MissedTagsConfig:
    base_missed_tag: list[str]
    subset_1_name: str
    subset_1_tag: list[str]
    subset_2_name: str
    subset_2_tag: list[str]
    other_resources: list[str]
    rotation_schedule: list[tuple[str, str, str]]
    schedule_exhausted_policy: str
    missed_tags_menu_label: str
    action_label_base: str
    action_label_multi_missed: str
    action_label_key_info: str
    action_label_correct_guess: str
    rotation_parent_tag_segment: str
    winter_break_tag_label: str
    post_rotation_tag_label: str
    multi_miss_tag: str
    default_test_tag_prefix: str
    default_nbme_tag_prefix: str
    other_suffix: str
    key_tag_base: str
    amboss_top_level_name: str
    amboss_base_tag: str
    amboss_blank_behavior: str
    amboss_number_style: str
    amboss_remove_from_other_menu: bool
    correct_guess_tags: list[str]
    correct_guess_include_rotation: bool
    correct_guess_rotation_lowercase: bool
    correct_guess_unknown_segment: str
    test_range_block_size: int


def scrub_resource_label_to_tag(label: str) -> str:
    missed_base = str(label).strip()
    missed_base = re.sub(r"[^A-Za-z0-9\- ]+", "", missed_base)
    missed_base = re.sub(r"\s+", " ", missed_base).strip()
    return missed_base


def _to_text(value: Any, fallback: str) -> str:
    text = str(value).strip()
    return text or fallback


def _to_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return fallback


def _to_positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(str(value).strip())
        return parsed if parsed > 0 else fallback
    except Exception:
        return fallback


def _to_string_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        out = [str(v).strip() for v in value if str(v).strip()]
        return out or list(fallback)
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return list(fallback)


_MISSING = object()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _get_path_value(data: Any, path: tuple[str, ...]) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return _MISSING
        current = current[key]
    return current


def _set_path_value(data: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = data
    for key in path[:-1]:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    current[path[-1]] = value


def _first_present_value(data: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> Any:
    for path in paths:
        value = _get_path_value(data, path)
        if value is not _MISSING:
            return value
    return _MISSING


def _default_value(path: tuple[str, ...]) -> Any:
    value = _get_path_value(ADD_MISSED_TAGS_DEFAULTS, path)
    if value is _MISSING:
        raise KeyError(f"Missing default at path: {'.'.join(path)}")
    return value


def _normalize_rotation_schedule(raw: Any) -> list[tuple[str, str, str]]:
    normalized: list[tuple[str, str, str]] = []
    if not isinstance(raw, list):
        return normalized

    for item in raw:
        label = start = end = ""
        if isinstance(item, dict):
            label = str(item.get("label", "")).strip()
            start = str(item.get("start", "")).strip()
            end = str(item.get("end", "")).strip()
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            label = str(item[0]).strip()
            start = str(item[1]).strip()
            end = str(item[2]).strip()

        if not label or not start or not end:
            continue
        try:
            datetime.strptime(start, "%Y-%m-%d")
            datetime.strptime(end, "%Y-%m-%d")
        except Exception:
            continue

        normalized.append((label, start, end))
    return normalized


def _migrate_override_sections_to_canonical() -> bool:
    """One-time migration: move legacy missed-tag overrides into canonical key."""
    overrides = ConfigManager.load_user_overrides()
    if not isinstance(overrides, dict):
        return False

    has_legacy_override = any(section in overrides for section in LEGACY_CONFIG_SECTIONS)
    if not has_legacy_override:
        return False

    merged_legacy: dict[str, Any] = {}
    for section_name in LEGACY_CONFIG_SECTIONS:
        section_data = overrides.get(section_name)
        if isinstance(section_data, dict):
            merged_legacy = ConfigManager.deep_merge_dicts(merged_legacy, section_data)

    canonical_override = overrides.get(CANONICAL_CONFIG_SECTION)
    if isinstance(canonical_override, dict):
        merged_canonical = ConfigManager.deep_merge_dicts(merged_legacy, canonical_override)
    else:
        merged_canonical = merged_legacy

    migrated_overrides = ConfigManager.deep_merge_dicts({}, overrides)
    migrated_overrides[CANONICAL_CONFIG_SECTION] = merged_canonical
    for section_name in LEGACY_CONFIG_SECTIONS:
        migrated_overrides.pop(section_name, None)

    if migrated_overrides == overrides:
        return False

    ConfigManager(ConfigManager.ROOT_ADDON_NAME).save_config(migrated_overrides)
    return True


def _load_merged_missed_tags_config() -> dict[str, Any]:
    _migrate_override_sections_to_canonical()

    legacy_cfg: dict[str, Any] = {}
    for section_name in LEGACY_CONFIG_SECTIONS:
        section_data = ConfigManager(section_name).load()
        if isinstance(section_data, dict):
            legacy_cfg = ConfigManager.deep_merge_dicts(legacy_cfg, section_data)

    section_cfg = ConfigManager(CANONICAL_CONFIG_SECTION).load()
    if not isinstance(section_cfg, dict):
        section_cfg = {}
    return ConfigManager.deep_merge_dicts(legacy_cfg, section_cfg)


def _normalize_missed_tags_config(raw_cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = ConfigManager.deep_merge_dicts({}, ADD_MISSED_TAGS_DEFAULTS)
    if not isinstance(raw_cfg, dict):
        return normalized

    for canonical_path, alias_paths in CANONICAL_ALIAS_PATHS:
        value = _first_present_value(raw_cfg, alias_paths)
        if value is _MISSING:
            continue
        _set_path_value(normalized, canonical_path, value)
    return normalized


def load_runtime_config() -> MissedTagsConfig:
    merged_cfg = _load_merged_missed_tags_config()
    canonical_cfg = _normalize_missed_tags_config(merged_cfg)

    ui_cfg = _as_dict(canonical_cfg.get("ui"))
    rotation_cfg = _as_dict(canonical_cfg.get("rotation"))
    actions_cfg = _as_dict(canonical_cfg.get("actions"))

    base_cfg = _as_dict(actions_cfg.get("base"))
    uworld_cfg = _as_dict(actions_cfg.get("uworld"))
    nbme_cfg = _as_dict(actions_cfg.get("nbme"))
    amboss_cfg = _as_dict(actions_cfg.get("amboss"))
    multi_missed_cfg = _as_dict(actions_cfg.get("multi_missed"))
    key_info_cfg = _as_dict(actions_cfg.get("key_info"))
    correct_guess_cfg = _as_dict(actions_cfg.get("correct_guess"))
    other_cfg = _as_dict(actions_cfg.get("other"))

    default_menu_label = _to_text(_default_value(PATH_UI_MENU_LABEL), "Missed Tags")

    default_base_missed_tag = _to_string_list(_default_value(PATH_ACTION_BASE_TAGS), fallback=["##Missed-Qs"])
    default_action_label_base = _to_text(_default_value(PATH_ACTION_BASE_LABEL), "Base")

    default_subset_1_name = _to_text(_default_value(PATH_ACTION_UWORLD_LABEL), "UWorld")
    default_subset_1_tag = _to_string_list(
        _default_value(PATH_ACTION_UWORLD_BASE_TAGS), fallback=[f"{default_base_missed_tag[0]}::UW_Tests"]
    )
    default_test_tag_prefix = _to_text(_default_value(PATH_ACTION_UWORLD_DEFAULT_TAG_PREFIX), "UW_Tests")
    default_test_range_block_size = _to_positive_int(_default_value(PATH_ACTION_UWORLD_TEST_RANGE_BLOCK_SIZE), 25)

    default_subset_2_name = _to_text(_default_value(PATH_ACTION_NBME_LABEL), "NBME")
    default_subset_2_tag = _to_string_list(
        _default_value(PATH_ACTION_NBME_BASE_TAGS), fallback=[f"{default_base_missed_tag[0]}::NBME"]
    )
    default_nbme_tag_prefix = _to_text(_default_value(PATH_ACTION_NBME_DEFAULT_TAG_PREFIX), "NBME")

    default_amboss_label = _to_text(_default_value(PATH_ACTION_AMBOSS_LABEL), "Amboss")
    default_amboss_base_tag = _to_text(_default_value(PATH_ACTION_AMBOSS_BASE_TAG), f"{default_base_missed_tag[0]}::Amboss")
    default_amboss_blank_behavior = _to_text(
        _default_value(PATH_ACTION_AMBOSS_BLANK_BEHAVIOR),
        PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    )
    default_amboss_number_style = _to_text(
        _default_value(PATH_ACTION_AMBOSS_NUMBER_STYLE),
        PROMPT_STYLE_ROTATION_THEN_NUMBER,
    )
    default_amboss_remove_from_other_menu = _to_bool(
        _default_value(PATH_ACTION_AMBOSS_REMOVE_FROM_OTHER_MENU),
        True,
    )

    default_action_label_multi_missed = _to_text(_default_value(PATH_ACTION_MULTI_MISSED_LABEL), "2x Missed")
    default_multi_miss_tag = _to_text(_default_value(PATH_ACTION_MULTI_MISSED_TAG_SEGMENT), "2x")

    default_action_label_key_info = _to_text(_default_value(PATH_ACTION_KEY_INFO_LABEL), "Key Info")
    default_key_tag_base = _to_text(_default_value(PATH_ACTION_KEY_INFO_TAG_BASE), "#Custom::#KEY")

    default_action_label_correct_guess = _to_text(
        _default_value(PATH_ACTION_CORRECT_GUESS_LABEL),
        "Guessed Correct",
    )
    default_correct_guess_tags = _to_string_list(
        _default_value(PATH_ACTION_CORRECT_GUESS_TAGS),
        fallback=["#Custom::correct_marked"],
    )
    default_correct_guess_include_rotation = _to_bool(
        _default_value(PATH_ACTION_CORRECT_GUESS_INCLUDE_ROTATION),
        True,
    )
    default_correct_guess_rotation_lowercase = _to_bool(
        _default_value(PATH_ACTION_CORRECT_GUESS_ROTATION_LOWERCASE),
        True,
    )
    default_correct_guess_unknown_segment = _to_text(
        _default_value(PATH_ACTION_CORRECT_GUESS_UNKNOWN_SEGMENT),
        "unknown",
    )

    default_other_resources = _to_string_list(_default_value(PATH_ACTION_OTHER_RESOURCES), fallback=[])
    default_other_suffix = _to_text(_default_value(PATH_ACTION_OTHER_TAG_SUFFIX), "Other")

    default_rotation_schedule_raw = _default_value(PATH_ROTATION_SCHEDULE)
    schedule_raw = rotation_cfg.get("schedule", default_rotation_schedule_raw)
    rotation_schedule = _normalize_rotation_schedule(schedule_raw)
    if not rotation_schedule:
        rotation_schedule = _normalize_rotation_schedule(default_rotation_schedule_raw)

    default_schedule_exhausted_policy = _to_text(
        _default_value(PATH_ROTATION_EXHAUSTED_POLICY),
        SCHEDULE_POLICY_UNKNOWN,
    ).lower()
    if default_schedule_exhausted_policy not in {SCHEDULE_POLICY_UNKNOWN, SCHEDULE_POLICY_NEXT}:
        default_schedule_exhausted_policy = SCHEDULE_POLICY_UNKNOWN

    schedule_exhausted_policy = _to_text(
        rotation_cfg.get("exhausted_policy", default_schedule_exhausted_policy),
        default_schedule_exhausted_policy,
    ).lower()
    if schedule_exhausted_policy not in {SCHEDULE_POLICY_UNKNOWN, SCHEDULE_POLICY_NEXT}:
        schedule_exhausted_policy = SCHEDULE_POLICY_UNKNOWN

    default_rotation_parent_tag_segment = _to_text(_default_value(PATH_ROTATION_PARENT_TAG_SEGMENT), "Rotation")
    default_winter_break_label = _to_text(_default_value(PATH_ROTATION_WINTER_BREAK_LABEL), "Winter-break")
    default_post_rotation_label = _to_text(_default_value(PATH_ROTATION_POST_ROTATION_LABEL), "Dedicated")

    return MissedTagsConfig(
        base_missed_tag=_to_string_list(
            base_cfg.get("tags", default_base_missed_tag),
            fallback=default_base_missed_tag,
        ),
        subset_1_name=_to_text(uworld_cfg.get("label", default_subset_1_name), default_subset_1_name),
        subset_1_tag=_to_string_list(
            uworld_cfg.get("base_tags", default_subset_1_tag),
            fallback=default_subset_1_tag,
        ),
        subset_2_name=_to_text(nbme_cfg.get("label", default_subset_2_name), default_subset_2_name),
        subset_2_tag=_to_string_list(
            nbme_cfg.get("base_tags", default_subset_2_tag),
            fallback=default_subset_2_tag,
        ),
        other_resources=_to_string_list(
            other_cfg.get("resources", default_other_resources),
            fallback=default_other_resources,
        ),
        rotation_schedule=rotation_schedule,
        schedule_exhausted_policy=schedule_exhausted_policy,
        missed_tags_menu_label=_to_text(ui_cfg.get("menu_label", default_menu_label), default_menu_label),
        action_label_base=_to_text(
            base_cfg.get("label", default_action_label_base),
            default_action_label_base,
        ),
        action_label_multi_missed=_to_text(
            multi_missed_cfg.get("label", default_action_label_multi_missed),
            default_action_label_multi_missed,
        ),
        action_label_key_info=_to_text(
            key_info_cfg.get("label", default_action_label_key_info),
            default_action_label_key_info,
        ),
        action_label_correct_guess=_to_text(
            correct_guess_cfg.get("label", default_action_label_correct_guess),
            default_action_label_correct_guess,
        ),
        rotation_parent_tag_segment=_to_text(
            rotation_cfg.get("parent_tag_segment", default_rotation_parent_tag_segment),
            default_rotation_parent_tag_segment,
        ),
        winter_break_tag_label=_to_text(
            rotation_cfg.get("winter_break_label", default_winter_break_label),
            default_winter_break_label,
        ),
        post_rotation_tag_label=_to_text(
            rotation_cfg.get("post_rotation_label", default_post_rotation_label),
            default_post_rotation_label,
        ),
        multi_miss_tag=_to_text(
            multi_missed_cfg.get("tag_segment", default_multi_miss_tag),
            default_multi_miss_tag,
        ),
        default_test_tag_prefix=_to_text(
            uworld_cfg.get("default_tag_prefix", default_test_tag_prefix),
            default_test_tag_prefix,
        ),
        default_nbme_tag_prefix=_to_text(
            nbme_cfg.get("default_tag_prefix", default_nbme_tag_prefix),
            default_nbme_tag_prefix,
        ),
        other_suffix=_to_text(
            other_cfg.get("tag_suffix", default_other_suffix),
            default_other_suffix,
        ),
        key_tag_base=_to_text(
            key_info_cfg.get("tag_base", default_key_tag_base),
            default_key_tag_base,
        ),
        amboss_top_level_name=_to_text(
            amboss_cfg.get("label", default_amboss_label),
            default_amboss_label,
        ),
        amboss_base_tag=_to_text(
            amboss_cfg.get("base_tag", default_amboss_base_tag),
            default_amboss_base_tag,
        ),
        amboss_blank_behavior=_to_text(
            amboss_cfg.get("blank_behavior", default_amboss_blank_behavior),
            default_amboss_blank_behavior,
        ),
        amboss_number_style=_to_text(
            amboss_cfg.get("number_style", default_amboss_number_style),
            default_amboss_number_style,
        ),
        amboss_remove_from_other_menu=_to_bool(
            amboss_cfg.get("remove_from_other_menu", default_amboss_remove_from_other_menu),
            default_amboss_remove_from_other_menu,
        ),
        correct_guess_tags=_to_string_list(
            correct_guess_cfg.get("tags", default_correct_guess_tags),
            fallback=default_correct_guess_tags,
        ),
        correct_guess_include_rotation=_to_bool(
            correct_guess_cfg.get("include_rotation", default_correct_guess_include_rotation),
            default_correct_guess_include_rotation,
        ),
        correct_guess_rotation_lowercase=_to_bool(
            correct_guess_cfg.get("rotation_lowercase", default_correct_guess_rotation_lowercase),
            default_correct_guess_rotation_lowercase,
        ),
        correct_guess_unknown_segment=_to_text(
            correct_guess_cfg.get("unknown_segment", default_correct_guess_unknown_segment),
            default_correct_guess_unknown_segment,
        ),
        test_range_block_size=_to_positive_int(
            uworld_cfg.get("test_range_block_size", default_test_range_block_size),
            default_test_range_block_size,
        ),
    )


def base_tag_path(cfg: MissedTagsConfig, *parts: str) -> str:
    default_base_missed_tag = _to_string_list(_default_value(PATH_ACTION_BASE_TAGS), fallback=["##Missed-Qs"])
    base = cfg.base_missed_tag[0] if cfg.base_missed_tag else default_base_missed_tag[0]
    return "::".join([base, *[p for p in parts if p]])


def _uw_base_tag(cfg: MissedTagsConfig) -> str:
    for cand in cfg.subset_1_tag + cfg.subset_2_tag:
        if "UW_Base" in cand or "::UW" in cand:
            return cand
    return base_tag_path(cfg, cfg.default_test_tag_prefix)


def _nbme_base_tag(cfg: MissedTagsConfig) -> str:
    for cand in cfg.subset_2_tag + cfg.subset_1_tag:
        upper_cand = cand.upper()
        if "::NBME" in upper_cand or "NBME_BASE" in upper_cand:
            return cand
        # Backward compatibility for older COMQUEST-only config overrides.
        if "::COMQUEST" in upper_cand or "COMQUEST_BASE" in upper_cand:
            return cand
    return base_tag_path(cfg, cfg.default_nbme_tag_prefix)


def _rotation_label_matches(actual: str, expected: str) -> bool:
    return str(actual or "").strip().lower() == str(expected or "").strip().lower()


def get_current_or_next_rotation_meta(cfg: MissedTagsConfig) -> tuple[str, str, str]:
    today = datetime.today().date()
    if not cfg.rotation_schedule:
        return "00", "Unknown", "Rotation schedule is empty; using Unknown."

    parsed = []
    for idx, (rotation, start_str, end_str) in enumerate(cfg.rotation_schedule, start=1):
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        parsed.append((idx, rotation, start, end))
        if start <= today <= end:
            return f"{idx:02d}", rotation, ""

    if cfg.schedule_exhausted_policy == SCHEDULE_POLICY_NEXT:
        for idx, rotation, start, _ in parsed:
            if today < start:
                warning = (
                    f"No active rotation for {today.isoformat()}; using next window "
                    f"{rotation} ({start.isoformat()})."
                )
                return f"{idx:02d}", rotation, warning

    last_end = parsed[-1][3]
    if today > last_end:
        post_label = str(cfg.post_rotation_tag_label).strip()
        if post_label:
            return "00", post_label, ""
        return "00", "Unknown", f"No rotation configured after {last_end.isoformat()}; using Unknown."
    return "00", "Unknown", f"No rotation configured for {today.isoformat()}; using Unknown."


def get_formatted_rotation_segment(cfg: MissedTagsConfig, rot_num_2d: str, rot_label: str) -> str:
    label = str(rot_label or "").strip()
    if not label:
        return "00_Unknown"

    if _rotation_label_matches(label, cfg.winter_break_tag_label):
        return cfg.winter_break_tag_label

    if _rotation_label_matches(label, cfg.post_rotation_tag_label):
        return cfg.post_rotation_tag_label

    if label == "Unknown":
        return "00_Unknown"

    rot_num = str(rot_num_2d or "00").strip() or "00"
    return f"{rot_num}_{label}"


def get_rotation_segment(cfg: MissedTagsConfig) -> str:
    rot_num_2d, rot_label, _ = get_current_or_next_rotation_meta(cfg)
    return get_formatted_rotation_segment(cfg, rot_num_2d, rot_label)


def get_rotation_key_info_tag(cfg: MissedTagsConfig) -> str:
    rot_segment = get_rotation_segment(cfg)
    return f"{cfg.key_tag_base}::{rot_segment}"


def get_correct_guess_rotation_segment(cfg: MissedTagsConfig) -> str:
    _, rot_label, _ = get_current_or_next_rotation_meta(cfg)
    raw = str(rot_label or cfg.correct_guess_unknown_segment).strip()
    raw = raw if raw else cfg.correct_guess_unknown_segment
    slug = re.sub(r"\s+", "-", raw)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "", slug)
    if not slug:
        slug = cfg.correct_guess_unknown_segment
    return slug.lower() if cfg.correct_guess_rotation_lowercase else slug


def get_correct_guess_tags(cfg: MissedTagsConfig) -> list[str]:
    if not cfg.correct_guess_include_rotation:
        return list(cfg.correct_guess_tags)

    rotation_segment = get_correct_guess_rotation_segment(cfg)
    return [f"{base_tag}::{rotation_segment}" for base_tag in cfg.correct_guess_tags]


def get_missed_month_tag(cfg: MissedTagsConfig) -> str:
    now = datetime.now()
    default_base_missed_tag = _to_string_list(_default_value(PATH_ACTION_BASE_TAGS), fallback=["##Missed-Qs"])
    base = cfg.base_missed_tag[0] if cfg.base_missed_tag else default_base_missed_tag[0]
    return f"{base}::{now.year}::{now.strftime('%m')}_{now.strftime('%B')}"


def get_missed_tag_for_rotation(cfg: MissedTagsConfig) -> tuple[str, str]:
    rot_num_2d, rot_label, warning = get_current_or_next_rotation_meta(cfg)
    segment = get_formatted_rotation_segment(cfg, rot_num_2d, rot_label)
    return base_tag_path(cfg, cfg.rotation_parent_tag_segment, segment), warning


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


def apply_tags_to_selected_notes(
    browser,
    tag_list: list[str],
    action_key: str,
    cfg: MissedTagsConfig | None = None,
):
    runtime_cfg = cfg or load_runtime_config()

    col = browser.mw.col
    nids = browser.selectedNotes()
    if not nids:
        return

    final = list(tag_list or [])
    rotation_warning = ""
    if action_key not in EXCLUDE_AUTO_MISS:
        rotation_tag, rotation_warning = get_missed_tag_for_rotation(runtime_cfg)
        final.append(rotation_tag)
        final.append(get_missed_month_tag(runtime_cfg))

    seen = set()
    final_tags = []
    for tag in final:
        if tag and tag not in seen:
            seen.add(tag)
            final_tags.append(tag)

    for nid in nids:
        note = col.get_note(nid)
        current = set(note.tags)
        for tag in final_tags:
            if tag not in current:
                _add_tag_safe(note, tag)
        _save_note_safe(col, note)

    browser.model.reset()
    msg = f"✅ Applied {len(final_tags)} tags to {len(nids)} notes."
    if rotation_warning:
        msg += f"\n⚠️ {rotation_warning}"
    tooltip(msg)


def add_base_plain_action(browser, menu, cfg: MissedTagsConfig):
    action = QAction(cfg.action_label_base, browser)
    action.triggered.connect(
        lambda _: apply_tags_to_selected_notes(browser, cfg.base_missed_tag, action_key="base_plain", cfg=cfg)
    )
    menu.addAction(action)


def _build_tag_menu_stylesheet() -> str:
    return build_qmenu_stylesheet(
        item_padding_top_px=MENU_ITEM_PADDING_TOP_PX,
        item_padding_bottom_px=MENU_ITEM_PADDING_BOTTOM_PX,
        item_padding_left_px=MENU_ITEM_PADDING_LEFT_PX,
        item_padding_right_px=MENU_ITEM_PADDING_RIGHT_PX,
        hover_background_color=MENU_ITEM_HOVER_BACKGROUND_COLOR,
        use_custom_submenu_arrow_icon=USE_CUSTOM_SUBMENU_ARROW_ICON,
        submenu_arrow_icon_abs_path=SUBMENU_ARROW_ICON_ABS_PATH,
        submenu_arrow_icon_size_px=SUBMENU_ARROW_ICON_SIZE_PX,
        submenu_arrow_horizontal_padding_px=None,
    )


def add_missed_tag_menu_items(browser, menu):
    cfg = load_runtime_config()

    tag_menu = QMenu(cfg.missed_tags_menu_label, browser)
    tag_menu.setStyleSheet(_build_tag_menu_stylesheet())

    add_uworld_tags(browser, tag_menu, cfg)
    add_nbme_tag(browser, tag_menu, cfg)
    add_amboss_tag(browser, tag_menu, cfg)
    add_base_plain_action(browser, tag_menu, cfg)
    tag_menu.addSeparator()

    add_multi_tag(browser, tag_menu, cfg)
    tag_menu.addSeparator()

    add_correct_guess_action(browser, tag_menu, cfg)
    tag_menu.addSeparator()

    add_other_resources_actions(browser, tag_menu, cfg)

    if tag_menu.actions():
        menu.addSeparator()
        menu.addMenu(tag_menu)


def add_nbme_tag(browser, menu, cfg: MissedTagsConfig):
    base_tag = _nbme_base_tag(cfg)
    action = QAction(f"{cfg.subset_2_name:<24}", browser)

    def on_trigger():
        prompt_title = "Enter NBME Form"
        prompt_label = "Form #:"
        form_value, ok = QInputDialog.getText(browser, prompt_title, prompt_label)
        if not ok:
            return

        try:
            form_number = int((form_value or "").strip())
        except ValueError:
            showInfo("❌ Please enter a valid integer test number.")
            return

        if form_number <= 0:
            showInfo("❌ Please enter a valid integer test number.")
            return

        if not browser.selectedNotes():
            showInfo("❌ No notes selected.")
            return

        formatted_tag = f"{base_tag}::Form_{form_number}"
        apply_tags_to_selected_notes(browser, [formatted_tag], action_key="nbme_form_prompt", cfg=cfg)

    action.triggered.connect(on_trigger)
    menu.addAction(action)


def add_amboss_tag(browser, menu, cfg: MissedTagsConfig):
    action = QAction(f"{cfg.amboss_top_level_name:<24}", browser)
    action.triggered.connect(
        make_test_prompt_handler(
            browser,
            cfg,
            cfg.amboss_base_tag,
            action_key="amboss_test_prompt",
            title="Enter Amboss Test Number",
            label="Test #:",
            blank_behavior=cfg.amboss_blank_behavior,
            number_style=cfg.amboss_number_style,
        )
    )
    menu.addAction(action)


def add_multi_tag(browser, menu, cfg: MissedTagsConfig):
    multi_tag = base_tag_path(cfg, cfg.multi_miss_tag)
    add_static_action(
        browser,
        menu,
        f"{cfg.action_label_multi_missed:<24}",
        [multi_tag],
        action_key="multi_missed",
        cfg=cfg,
    )


def add_uworld_tags(browser, menu, cfg: MissedTagsConfig):
    set_name = cfg.subset_1_name
    base = _uw_base_tag(cfg)
    if set_name and base:
        action = QAction(f"{set_name:<24}", browser)
        action.triggered.connect(
            make_test_prompt_handler(
                browser,
                cfg,
                base,
                action_key="uw_test_prompt",
                title="Enter UWorld Test Number",
                label="Test #:",
                blank_behavior=PROMPT_BEHAVIOR_BASE_ONLY,
                number_style=PROMPT_STYLE_RANGE_THEN_NUMBER,
            )
        )
        menu.addAction(action)


def add_other_resources_actions(
    browser,
    menu,
    cfg: MissedTagsConfig,
    resources_override: list[str] | None = None,
):
    resources = resources_override if resources_override is not None else cfg.other_resources
    for resource_name in resources:
        label = str(resource_name).strip()
        canonical = scrub_resource_label_to_tag(resource_name)
        if not canonical:
            continue

        if cfg.amboss_remove_from_other_menu and canonical.lower() == "amboss":
            continue

        if canonical == "True-Learn":
            base_tag = base_tag_path(cfg, cfg.other_suffix, canonical)
            action = QAction(label, browser)
            handler = make_test_prompt_handler(
                browser,
                cfg,
                base_tag,
                action_key="true_learn_test_prompt",
                title="Enter True-Learn Test Number",
                label="Test #:",
                blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,
            )
            action.triggered.connect(handler)
            menu.addAction(action)
            continue

        resource_tag = base_tag_path(cfg, cfg.other_suffix, canonical)
        action = QAction(label, browser)

        def on_click(_, rtag=resource_tag):
            if not browser.selectedNotes():
                showInfo("❌ No notes selected.")
                return
            tags_to_apply = list(cfg.base_missed_tag) + [rtag]
            apply_tags_to_selected_notes(
                browser,
                tags_to_apply,
                action_key="other_resource",
                cfg=cfg,
            )

        action.triggered.connect(on_click)
        menu.addAction(action)


def make_test_prompt_handler(
    browser,
    cfg: MissedTagsConfig,
    base_tag: str,
    action_key: str,
    title: str | None = None,
    label: str | None = None,
    blank_behavior: str = PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    number_style: str = PROMPT_STYLE_RANGE_THEN_NUMBER,
):
    def on_trigger():
        prompt_title = (title or "Enter Test Number").strip() or "Enter Test Number"
        prompt_label = (label or "Test #:").strip() or "Test #:"
        test_num, ok = QInputDialog.getText(browser, prompt_title, prompt_label)
        if not ok:
            return
        test_num = (test_num or "").strip()
        rot_num_2d, rot_label, _ = get_current_or_next_rotation_meta(cfg)
        rotation_segment = get_formatted_rotation_segment(cfg, rot_num_2d, rot_label)

        if test_num == "":
            if blank_behavior == PROMPT_BEHAVIOR_BASE_ONLY:
                formatted_tag = f"{base_tag}"
            else:
                formatted_tag = f"{base_tag}::{rotation_segment}"
        else:
            try:
                tn = int(test_num)
            except ValueError:
                if blank_behavior == PROMPT_BEHAVIOR_BASE_ONLY:
                    formatted_tag = f"{base_tag}"
                else:
                    formatted_tag = f"{base_tag}::{rotation_segment}"
            else:
                if number_style == PROMPT_STYLE_ROTATION_THEN_NUMBER:
                    formatted_tag = f"{base_tag}::{rotation_segment}::{tn:02d}"
                else:
                    lower = ((tn - 1) // cfg.test_range_block_size) * cfg.test_range_block_size + 1
                    upper = lower + cfg.test_range_block_size - 1
                    range_tag = f"{lower}-{upper}"
                    formatted_tag = f"{base_tag}::{range_tag}::{tn:02d}"

        if not browser.selectedNotes():
            showInfo("❌ No notes selected.")
            return
        apply_tags_to_selected_notes(browser, [formatted_tag], action_key=action_key, cfg=cfg)

    return on_trigger


def add_static_action(browser, menu, set_name: str, tags: list[str], action_key: str, cfg: MissedTagsConfig):
    action = QAction(set_name, browser)
    action.triggered.connect(
        lambda _, tags=tags, k=action_key: apply_tags_to_selected_notes(browser, tags, action_key=k, cfg=cfg)
    )
    menu.addAction(action)


def add_key_info_action(browser, menu, cfg: MissedTagsConfig):
    action = QAction(cfg.action_label_key_info, browser)

    def on_click():
        if not browser.selectedNotes():
            showInfo("❌ No notes selected.")
            return
        key_tag = get_rotation_key_info_tag(cfg)
        apply_tags_to_selected_notes(browser, [key_tag], action_key="add_key_info_action", cfg=cfg)

    action.triggered.connect(on_click)
    menu.addAction(action)


def add_correct_guess_action(browser, menu, cfg: MissedTagsConfig):
    action = QAction(cfg.action_label_correct_guess, browser)
    action.triggered.connect(
        lambda _: apply_tags_to_selected_notes(
            browser, get_correct_guess_tags(cfg), action_key="correct_guess", cfg=cfg
        )
    )
    menu.addAction(action)
