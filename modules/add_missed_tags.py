# pyright: reportMissingImports=false
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aqt.qt import (
    QAction,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
)
from aqt.utils import showInfo, tooltip

from ..config_manager import ConfigManager
from .shared.defaults import ADD_MISSED_TAGS_DEFAULTS
from .shared.menu_styles import build_missed_tags_menu_stylesheet

# ! ----------------------------- CONFIG SECTIONS -----------------------------
CANONICAL_CONFIG_SECTION = "tag_missed_notes"
# ! -------------------------------------------------------------------------
# Prompt offset in pixels from screen center.
# 0,0 centers the prompt in the active screen.
PROMPT_DIALOG_OFFSET_CENTER_X = 200
PROMPT_DIALOG_OFFSET_CENTER_Y = -50
# Prompt sizing (tunable): increase these if dialog captions/labels appear clipped.
PROMPT_DIALOG_MIN_WIDTH = 250
PROMPT_DIALOG_MIN_HEIGHT = 0

# Keep a small margin so prompt windows never hug screen edges.
PROMPT_DIALOG_SAFE_MARGIN = 16
CORRECT_MISSED_DIALOG_MIN_WIDTH = 180
CORRECT_MISSED_DIALOG_MIN_HEIGHT = 0
# Show or hide the "Base" action in the Missed Tags menu.
# Canonical config key: actions.base.menu_display
SHOW_BASE_ACTION_IN_MISSED_TAGS_MENU = True

# ! --------------------------- CHANGE-PRONE VALUES ---------------------------
SCHEDULE_POLICY = {
    "unknown": "unknown",
    "next": "next",
}
DEFAULT_OPEN_ENDED_ROTATION_END = "2099-12-31"

# UWorld grouping for numeric test tags:
#   parent range (for example, 001-050) -> child range (for example, 01-05).
DEFAULT_UWORLD_PARENT_RANGE_BLOCK_SIZE = 50
DEFAULT_UWORLD_CHILD_RANGE_BLOCK_SIZE = 5
DEFAULT_PARENT_RANGE_PAD_WIDTH = 3
# Keep True to include child range like:
#   ##Missed-Qs::*UW_Tests::051-100::96-100::96
# Set False only if you intentionally want:
#   ##Missed-Qs::*UW_Tests::051-100::96
INCLUDE_UWORLD_CHILD_RANGE_SEGMENT = True
CANONICAL_UWORLD_TAG_SEGMENT = "*UW_Tests"
ACTION_KEY_CORRECT_TAG_MISSED_PROMPT = "correct_tag_missed_prompt"
CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY = "correct_tag_missed"
LEGACY_CORRECT_TAG_MISSED_ACTION_KEY = "uw_correct_missed"
DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL = "UW Correct + Missed Tag"
CORRECT_MARKED_TAG_SEGMENT = "correct_marked"
UWORLD_CORRECT_MISSED_SOURCE_KEY = "uw_correct_missed_source"
UWORLD_CORRECT_MISSED_SOURCE_OPTIONS = ("UWorld", "NBME", "Amboss", "Other")

PROMPT_BEHAVIOR_BASE_PLUS_ROTATION = "base_plus_rotation"
PROMPT_BEHAVIOR_BASE_ONLY = "base_only"

PROMPT_STYLE_ROTATION_THEN_NUMBER = "rotation_then_number"
PROMPT_STYLE_RANGE_THEN_NUMBER = "range_then_number"
PROMPT_STYLE_NUMBER_ONLY = "number_only"
PROMPT_KIND_NONE = "none"
PROMPT_KIND_NUMBER = "number"
PROMPT_KIND_FORM = "form"
VALID_PROMPT_KINDS = {
    PROMPT_KIND_NONE,
    PROMPT_KIND_NUMBER,
    PROMPT_KIND_FORM,
}
VALID_PROMPT_NUMBER_STYLES = {
    PROMPT_STYLE_ROTATION_THEN_NUMBER,
    PROMPT_STYLE_RANGE_THEN_NUMBER,
    PROMPT_STYLE_NUMBER_ONLY,
}
VALID_PROMPT_BLANK_BEHAVIORS = {
    PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    PROMPT_BEHAVIOR_BASE_ONLY,
}

# Amboss prompt behavior: when enabled, any non-empty prompt text is converted
# into child tag segments under Amboss::<rotation>.
AMBOSS_ALLOW_FREEFORM_CHILD_SEGMENTS = True
AMBOSS_FREEFORM_INCLUDE_ROTATION_SEGMENT = False

MSG_NO_NOTES_SELECTED = "❌ No notes selected."
MSG_INVALID_INTEGER_TEST_NUMBER = "❌ Please enter a valid integer test number."
MSG_INVALID_NBME_INPUT = "❌ Please enter a positive form number or a tag path."
MSG_INVALID_CORRECT_GUESS_SUBTAG = "❌ Subtag cannot include spaces."
MSG_INVALID_CORRECT_MARKED_SOURCE_INPUT = "❌ Please enter a value."
PROMPT_DEFAULT_TITLE = "Enter Test Number"
PROMPT_DEFAULT_LABEL = "Test #:"
PROMPT_NBME_TITLE = "Enter NBME Form or Path"
PROMPT_NBME_LABEL = "Form # or path:"
PROMPT_AMBOSS_TITLE = "Enter Amboss Subtag"
PROMPT_AMBOSS_LABEL = "Subtags:"
PROMPT_AMBOSS_APPEND_CORRECT_MARKED_LABEL = "correct_marked"
AMBOSS_CORRECT_MARKED_TAG_SEGMENT = "correct_marked"
AMBOSS_APPEND_CORRECT_MARKED_STATE_KEY = "amboss_append_correct_marked"
AMBOSS_APPEND_CORRECT_MARKED_DEFAULT = False
PROMPT_SHOW_CORRECT_MARKED_CHECKBOX_DEFAULT = False
PROMPT_UWORLD_TITLE = "Enter UWorld Test Number"
PROMPT_TRUE_LEARN_TITLE = "Enter True-Learn Test Number"
PROMPT_CORRECT_GUESS_SUBTAG_TITLE = "Guessed Correct Subtag"
PROMPT_CORRECT_GUESS_SUBTAG_LABEL = "Optional subtag (no spaces):"

# ! -------------------------------------------------------------------------

# ? Exclude list for auto-added rotation/month context tags.
EXCLUDE_AUTO_MISS = {
    "add_key_info_action",
    "base_plain",
    "correct_guess",
}

DEFAULT_ACTION_ADD_MISSED_DATE_CONTEXT = {
    "add_key_info_action": False,
    "base_plain": False,
    "correct_guess": False,
    "uw_test_prompt": True,
    ACTION_KEY_CORRECT_TAG_MISSED_PROMPT: True,
    "nbme_form_prompt": True,
    "amboss_test_prompt": True,
    "multi_missed": True,
    "other_resource": True,
    "true_learn_test_prompt": True,
}

STANDARD_ACTION_SCHEMA_KEYS = (
    "menu_label",
    "child_of_primary_missed",
    "absolute_tags",
    "tag_segment",
)
STANDARD_ACTION_SCHEMA_KEYS_WITH_PROMPT = (*STANDARD_ACTION_SCHEMA_KEYS, "prompt")
STANDARDIZED_ACTION_SCHEMA_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("base", STANDARD_ACTION_SCHEMA_KEYS),
    ("uworld", STANDARD_ACTION_SCHEMA_KEYS_WITH_PROMPT),
    ("nbme", STANDARD_ACTION_SCHEMA_KEYS_WITH_PROMPT),
    ("amboss", STANDARD_ACTION_SCHEMA_KEYS_WITH_PROMPT),
    ("multi_missed", STANDARD_ACTION_SCHEMA_KEYS),
    ("key_info", STANDARD_ACTION_SCHEMA_KEYS),
    ("correct_guess", STANDARD_ACTION_SCHEMA_KEYS),
    (CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY, STANDARD_ACTION_SCHEMA_KEYS),
)
ACTION_DATE_CONTEXT_RESOLUTION_SPECS: tuple[tuple[str, str, str], ...] = (
    ("base_plain", "base", "base_plain"),
    ("uw_test_prompt", "uworld", "uw_test_prompt"),
    ("nbme_form_prompt", "nbme", "nbme_form_prompt"),
    ("amboss_test_prompt", "amboss", "amboss_test_prompt"),
    ("multi_missed", "multi_missed", "multi_missed"),
    ("add_key_info_action", "key_info", "add_key_info_action"),
    ("correct_guess", "correct_guess", "correct_guess"),
    (
        ACTION_KEY_CORRECT_TAG_MISSED_PROMPT,
        CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY,
        ACTION_KEY_CORRECT_TAG_MISSED_PROMPT,
    ),
)


@dataclass(frozen=True)
class PromptActionConfig:
    kind: str
    number_style: str
    blank_behavior: str
    title: str
    label: str
    allow_freeform_child_segments: bool
    include_rotation_for_freeform: bool
    show_correct_marked_checkbox: bool = False


@dataclass(frozen=True)
class OtherResourceActionConfig:
    action_key: str
    label: str
    tags: list[str]
    prompt: PromptActionConfig
    include_base_tag: bool


@dataclass(frozen=True)
class MissedTagsConfig:
    base_missed_tag: list[str]
    subset_1_name: str
    subset_1_tag: list[str]
    subset_2_name: str
    subset_2_tag: list[str]
    other_resources: list[str]
    other_submenu_enabled: bool
    other_submenu_label: str
    rotation_schedule: list[tuple[str, str, str]]
    schedule_exhausted_policy: str
    missed_tags_menu_label: str
    include_day_segment: bool
    split_weeks: bool
    action_add_missed_date_context: dict[str, bool]
    show_base_plain_action: bool
    action_label_base: str
    action_label_multi_missed: str
    action_label_key_info: str
    action_label_correct_guess: str
    action_label_uw_correct_missed: str
    uw_correct_missed_tag_segment: str
    uw_correct_missed_tags: list[str]
    rotation_parent_tag_segment: str
    multi_miss_tag: str
    multi_miss_tags: list[str]
    default_test_tag_prefix: str
    default_nbme_tag_prefix: str
    other_suffix: str
    key_tag_base: str
    uworld_prompt: PromptActionConfig
    nbme_prompt: PromptActionConfig
    amboss_prompt: PromptActionConfig
    other_resource_actions: list[OtherResourceActionConfig]
    amboss_top_level_name: str
    amboss_base_tag: str
    amboss_blank_behavior: str
    amboss_number_style: str
    amboss_remove_from_other_menu: bool
    correct_guess_tags: list[str]
    correct_guess_include_rotation: bool
    correct_guess_rotation_lowercase: bool
    correct_guess_unknown_segment: str
    test_parent_range_block_size: int
    test_range_block_size: int


def scrub_resource_label_to_tag(label: str) -> str:
    missed_base = str(label).strip()
    missed_base = re.sub(r"[^A-Za-z0-9\- ]+", "", missed_base)
    missed_base = re.sub(r"\s+", " ", missed_base).strip()
    return missed_base


def _normalize_freeform_tag_path(raw: str) -> str:
    """Normalize user text to safe Anki tag path segments."""
    parts = str(raw or "").split("::")
    normalized: list[str] = []
    for part in parts:
        seg = str(part).strip()
        if not seg:
            continue
        seg = re.sub(r"\s+", "_", seg)
        seg = re.sub(r"[^A-Za-z0-9_+\-.]+", "-", seg)
        seg = re.sub(r"_+", "_", seg).strip("_-")
        if seg:
            normalized.append(seg)
    return "::".join(normalized)


def _normalize_nbme_child_path(raw: str) -> str:
    """Accept either a positive form number or a freeform NBME child path."""
    value = str(raw or "").strip()
    if not value:
        return ""

    try:
        form_number = int(value)
    except ValueError:
        return _normalize_freeform_tag_path(value)

    if form_number <= 0:
        return ""
    return f"Form_{form_number}"


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


def _default_value(path: tuple[str, ...]) -> Any:
    value = _get_path_value(ADD_MISSED_TAGS_DEFAULTS, path)
    if value is _MISSING:
        raise KeyError(f"Missing default at path: {'.'.join(path)}")
    return value


def _default_text(path: tuple[str, ...], fallback: str) -> str:
    return _to_text(_default_value(path), fallback)


def _default_bool(path: tuple[str, ...], fallback: bool) -> bool:
    return _to_bool(_default_value(path), fallback)


def _default_positive_int(path: tuple[str, ...], fallback: int) -> int:
    return _to_positive_int(_default_value(path), fallback)


def _default_string_list(path: tuple[str, ...], fallback: list[str]) -> list[str]:
    return _to_string_list(_default_value(path), fallback=fallback)


def _read_text(data: dict[str, Any], key: str, fallback: str) -> str:
    return _to_text(data.get(key, fallback), fallback)


def _read_bool(data: dict[str, Any], key: str, fallback: bool) -> bool:
    return _to_bool(data.get(key, fallback), fallback)


def _read_positive_int(data: dict[str, Any], key: str, fallback: int) -> int:
    return _to_positive_int(data.get(key, fallback), fallback)


def _read_string_list(data: dict[str, Any], key: str, fallback: list[str]) -> list[str]:
    return _to_string_list(data.get(key, fallback), fallback=fallback)


def _read_action_add_missed_date_context(action_cfg: dict[str, Any], fallback: bool) -> bool:
    return _read_bool(action_cfg, "add_missed_date_context", fallback)


def _normalize_prompt_kind(value: Any, fallback: str) -> str:
    normalized = _to_text(value, fallback).lower()
    return normalized if normalized in VALID_PROMPT_KINDS else fallback


def _normalize_prompt_number_style(value: Any, fallback: str) -> str:
    normalized = _to_text(value, fallback).lower()
    return normalized if normalized in VALID_PROMPT_NUMBER_STYLES else fallback


def _normalize_prompt_blank_behavior(value: Any, fallback: str) -> str:
    normalized = _to_text(value, fallback).lower()
    return normalized if normalized in VALID_PROMPT_BLANK_BEHAVIORS else fallback


def _normalize_prompt_settings(
    prompt_cfg: dict[str, Any],
    *,
    default_kind: str,
    default_number_style: str,
    default_blank_behavior: str,
) -> dict[str, Any]:
    normalized_prompt = _as_dict(prompt_cfg)
    normalized_prompt["kind"] = _normalize_prompt_kind(normalized_prompt.get("kind"), default_kind)
    normalized_prompt["number_style"] = _normalize_prompt_number_style(
        normalized_prompt.get("number_style"),
        default_number_style,
    )
    normalized_prompt["blank_behavior"] = _normalize_prompt_blank_behavior(
        normalized_prompt.get("blank_behavior"),
        default_blank_behavior,
    )
    return normalized_prompt


def _build_prompt_action_config(
    action_cfg: dict[str, Any],
    *,
    default_kind: str,
    default_number_style: str,
    default_blank_behavior: str,
    default_title: str,
    default_label: str,
    default_allow_freeform_child_segments: bool,
    default_include_rotation_for_freeform: bool,
    default_show_correct_marked_checkbox: bool,
) -> PromptActionConfig:
    prompt_cfg = _as_dict(action_cfg.get("prompt"))
    prompt_kind = _normalize_prompt_kind(prompt_cfg.get("kind"), default_kind)
    number_style = _normalize_prompt_number_style(prompt_cfg.get("number_style"), default_number_style)
    blank_behavior = _normalize_prompt_blank_behavior(
        prompt_cfg.get("blank_behavior", action_cfg.get("blank_behavior")),
        default_blank_behavior,
    )
    prompt_title = _read_text(prompt_cfg, "title", default_title)
    prompt_label = _read_text(prompt_cfg, "label", default_label)
    allow_freeform = _read_bool(
        prompt_cfg,
        "allow_freeform_child_segments",
        default_allow_freeform_child_segments,
    )
    include_rotation_for_freeform = _read_bool(
        prompt_cfg,
        "include_rotation_for_freeform",
        default_include_rotation_for_freeform,
    )
    show_correct_marked_checkbox = _read_bool(
        prompt_cfg,
        "show_correct_marked_checkbox",
        default_show_correct_marked_checkbox,
    )
    return PromptActionConfig(
        kind=prompt_kind,
        number_style=number_style,
        blank_behavior=blank_behavior,
        title=prompt_title,
        label=prompt_label,
        allow_freeform_child_segments=allow_freeform,
        include_rotation_for_freeform=include_rotation_for_freeform,
        show_correct_marked_checkbox=show_correct_marked_checkbox,
    )


def _normalize_rotation_schedule(raw: Any) -> list[tuple[str, str, str]]:
    normalized: list[tuple[str, str, str]] = []
    if not isinstance(raw, list):
        return normalized

    for item in raw:
        segment_label = start = end = ""
        if isinstance(item, dict):
            segment_label = str(item.get("segment_label", "")).strip()
            if not segment_label:
                # Backward compatibility for legacy schedule entries.
                segment_label = str(item.get("label", "")).strip()
            start = str(item.get("start", "")).strip()
            end = str(item.get("end", "")).strip() or DEFAULT_OPEN_ENDED_ROTATION_END
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            segment_label = str(item[0]).strip()
            start = str(item[1]).strip()
            end = str(item[2]).strip() if len(item) >= 3 else DEFAULT_OPEN_ENDED_ROTATION_END
            if not end:
                end = DEFAULT_OPEN_ENDED_ROTATION_END

        if not segment_label or not start:
            continue
        try:
            datetime.strptime(start, "%Y-%m-%d")
            datetime.strptime(end, "%Y-%m-%d")
        except Exception:
            continue

        normalized.append((segment_label, start, end))
    return normalized


def _build_child_tag(primary_tag: str, segment: str) -> str:
    normalized_primary = _to_text(primary_tag, "##Missed-Qs")
    normalized_segment = _to_text(segment, "")
    if not normalized_segment:
        return normalized_primary
    if normalized_segment == normalized_primary or normalized_segment.startswith(f"{normalized_primary}::"):
        return normalized_segment
    return f"{normalized_primary}::{normalized_segment}"


def _extract_tag_suffix(tag: Any, fallback: str) -> str:
    parts = [part.strip() for part in str(tag or "").split("::") if part.strip()]
    return parts[-1] if parts else fallback


def _resolve_standardized_action_tags(
    action_cfg: dict[str, Any],
    *,
    primary_tag: str,
    default_child_of_primary: bool,
    default_segments: list[str],
    default_absolute_tags: list[str],
) -> list[str]:
    child_of_primary = _to_bool(
        action_cfg.get("child_of_primary_missed"),
        default_child_of_primary,
    )
    if child_of_primary:
        segment_source = action_cfg.get("tag_segment")
        if segment_source is None:
            segment_source = action_cfg.get("tag_segments")
        segments = _to_string_list(segment_source, default_segments)
        return [_build_child_tag(primary_tag, seg) for seg in segments]

    return _to_string_list(action_cfg.get("absolute_tags"), default_absolute_tags)


def _apply_standardized_action_schema(cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = ConfigManager.deep_merge_dicts({}, cfg)
    actions_cfg = _as_dict(normalized.get("actions"))
    if not actions_cfg:
        return normalized

    action_defaults = _as_dict(normalized.get("action_defaults"))
    action_defaults_prompt = _as_dict(action_defaults.get("prompt"))
    default_child_of_primary = _to_bool(action_defaults.get("child_of_primary_missed"), True)

    base_cfg = _as_dict(actions_cfg.get("base"))
    base_tags_existing = _to_string_list(base_cfg.get("tags"), fallback=["##Missed-Qs"])
    primary_tag = _to_text(base_tags_existing[0] if base_tags_existing else "##Missed-Qs", "##Missed-Qs")

    def _copy_menu_label(action_cfg: dict[str, Any], target_cfg: dict[str, Any]) -> None:
        menu_label = _to_text(action_cfg.get("menu_label"), "")
        if menu_label:
            target_cfg["label"] = menu_label

    def _apply_add_date_context(action_cfg: dict[str, Any], target_cfg: dict[str, Any]) -> None:
        if "add_missed_date_context" in action_cfg:
            target_cfg["add_missed_date_context"] = _to_bool(
                action_cfg.get("add_missed_date_context"),
                True,
            )
            return
        if "add_missed_date_context" in action_defaults:
            target_cfg["add_missed_date_context"] = _to_bool(
                action_defaults.get("add_missed_date_context"),
                True,
            )

    def _has_standard_action_keys(action_cfg: dict[str, Any], keys: tuple[str, ...]) -> bool:
        return any(key in action_cfg for key in keys)

    def _resolve_action_cfg(action_key: str) -> dict[str, Any]:
        action_cfg = _as_dict(actions_cfg.get(action_key))
        if action_key == CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY and not action_cfg:
            action_cfg = _as_dict(actions_cfg.get(LEGACY_CORRECT_TAG_MISSED_ACTION_KEY))
            if action_cfg:
                actions_cfg[CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY] = action_cfg
        return action_cfg

    base_cfg = _as_dict(actions_cfg.get("base"))
    if base_cfg and "menu_display" not in base_cfg and "show_in_menu" in base_cfg:
        base_cfg["menu_display"] = _to_bool(base_cfg.get("show_in_menu"), True)

    for action_key, schema_keys in STANDARDIZED_ACTION_SCHEMA_SPECS:
        action_cfg = _resolve_action_cfg(action_key)
        if not action_cfg or not _has_standard_action_keys(action_cfg, schema_keys):
            continue

        _copy_menu_label(action_cfg, action_cfg)

        if action_key == "base":
            resolved_tags = _resolve_standardized_action_tags(
                action_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=False,
                default_segments=[""],
                default_absolute_tags=[primary_tag],
            )
            action_cfg["tags"] = resolved_tags
            if resolved_tags:
                primary_tag = _to_text(resolved_tags[0], primary_tag)
            _apply_add_date_context(action_cfg, action_cfg)
            continue

        if action_key == "uworld":
            resolved_tags = _resolve_standardized_action_tags(
                action_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=default_child_of_primary,
                default_segments=["*UW_Tests"],
                default_absolute_tags=[f"{primary_tag}::*UW_Tests"],
            )
            action_cfg["base_tags"] = [_canonicalize_uworld_base_tag_path(tag) for tag in resolved_tags]

            configured_default_prefix = _to_text(action_cfg.get("default_tag_prefix"), "")
            if configured_default_prefix:
                action_cfg["default_tag_prefix"] = _canonicalize_uworld_tag_segment(configured_default_prefix)
            else:
                extracted_suffix = _extract_tag_suffix(action_cfg["base_tags"][0], "*UW_Tests")
                action_cfg["default_tag_prefix"] = _canonicalize_uworld_tag_segment(extracted_suffix)

            action_prompt = _as_dict(action_cfg.get("prompt"))
            parent_range_block_size = _to_positive_int(
                action_prompt.get(
                    "parent_range_block_size",
                    action_cfg.get("test_parent_range_block_size"),
                ),
                0,
            )
            if parent_range_block_size > 0:
                action_cfg["test_parent_range_block_size"] = parent_range_block_size

            range_block_size = _to_positive_int(
                action_prompt.get(
                    "range_block_size",
                    action_cfg.get(
                        "test_range_block_size",
                        action_defaults_prompt.get("range_block_size"),
                    ),
                ),
                0,
            )
            if range_block_size > 0:
                action_cfg["test_range_block_size"] = range_block_size
                if "test_parent_range_block_size" not in action_cfg:
                    action_cfg["test_parent_range_block_size"] = range_block_size

            action_cfg["prompt"] = _normalize_prompt_settings(
                _as_dict(action_cfg.get("prompt")),
                default_kind=PROMPT_KIND_NUMBER,
                default_number_style=PROMPT_STYLE_RANGE_THEN_NUMBER,
                default_blank_behavior=PROMPT_BEHAVIOR_BASE_ONLY,
            )
            _apply_add_date_context(action_cfg, action_cfg)
            continue

        if action_key == "nbme":
            resolved_tags = _resolve_standardized_action_tags(
                action_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=default_child_of_primary,
                default_segments=["NBME"],
                default_absolute_tags=[f"{primary_tag}::NBME"],
            )
            action_cfg["base_tags"] = resolved_tags
            action_cfg["default_tag_prefix"] = _to_text(
                action_cfg.get("default_tag_prefix"),
                _extract_tag_suffix(resolved_tags[0], "NBME"),
            )
            action_cfg["prompt"] = _normalize_prompt_settings(
                _as_dict(action_cfg.get("prompt")),
                default_kind=PROMPT_KIND_FORM,
                default_number_style=PROMPT_STYLE_NUMBER_ONLY,
                default_blank_behavior=PROMPT_BEHAVIOR_BASE_ONLY,
            )
            _apply_add_date_context(action_cfg, action_cfg)
            continue

        if action_key == "amboss":
            resolved_tags = _resolve_standardized_action_tags(
                action_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=default_child_of_primary,
                default_segments=["Amboss"],
                default_absolute_tags=[f"{primary_tag}::Amboss"],
            )
            if resolved_tags:
                action_cfg["base_tag"] = resolved_tags[0]

            action_prompt = _as_dict(action_cfg.get("prompt"))
            number_style = _to_text(
                action_prompt.get("number_style", action_cfg.get("number_style")),
                "",
            )
            if number_style in VALID_PROMPT_NUMBER_STYLES:
                action_cfg["number_style"] = number_style

            if "blank_behavior" in action_cfg:
                action_cfg["blank_behavior"] = _to_text(
                    action_cfg.get("blank_behavior"),
                    PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                )
            elif "kind" in action_prompt:
                # Friend-style prompt config treats blank/non-numeric as base-only.
                action_cfg["blank_behavior"] = PROMPT_BEHAVIOR_BASE_ONLY

            if "remove_from_other_menu" in action_cfg:
                action_cfg["remove_from_other_menu"] = _to_bool(
                    action_cfg.get("remove_from_other_menu"),
                    True,
                )

            action_cfg["prompt"] = _normalize_prompt_settings(
                _as_dict(action_cfg.get("prompt")),
                default_kind=PROMPT_KIND_NUMBER,
                default_number_style=_to_text(
                    action_cfg.get("number_style"),
                    PROMPT_STYLE_ROTATION_THEN_NUMBER,
                ),
                default_blank_behavior=_to_text(
                    action_cfg.get("blank_behavior"),
                    PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                ),
            )
            _apply_add_date_context(action_cfg, action_cfg)
            continue

        if action_key == "multi_missed":
            resolved_tags = _resolve_standardized_action_tags(
                action_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=default_child_of_primary,
                default_segments=["2x"],
                default_absolute_tags=[f"{primary_tag}::2x"],
            )
            action_cfg["tags"] = resolved_tags
            if "tag_segment" not in action_cfg:
                resolved_segment = _to_text(resolved_tags[0], "2x") if resolved_tags else "2x"
                primary_prefix = f"{primary_tag}::"
                if resolved_segment.startswith(primary_prefix):
                    resolved_segment = resolved_segment[len(primary_prefix) :]
                elif resolved_segment == primary_tag:
                    resolved_segment = ""
                action_cfg["tag_segment"] = resolved_segment or "2x"
            _apply_add_date_context(action_cfg, action_cfg)
            continue

        if action_key == "key_info":
            resolved_tags = _resolve_standardized_action_tags(
                action_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=False,
                default_segments=["#KEY"],
                default_absolute_tags=[_to_text(action_cfg.get("tag_base"), "#Custom::#KEY")],
            )
            action_cfg["tag_base"] = _to_text(resolved_tags[0], "#Custom::#KEY") if resolved_tags else "#Custom::#KEY"
            _apply_add_date_context(action_cfg, action_cfg)
            continue

        if action_key == "correct_guess":
            action_cfg["tags"] = _resolve_standardized_action_tags(
                action_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=False,
                default_segments=["correct_marked"],
                default_absolute_tags=["#Custom::correct_marked"],
            )
            _apply_add_date_context(action_cfg, action_cfg)
            continue

        if action_key == CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY:
            resolved_tags = _resolve_standardized_action_tags(
                action_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=True,
                default_segments=[CORRECT_MARKED_TAG_SEGMENT],
                default_absolute_tags=[f"{primary_tag}::{CORRECT_MARKED_TAG_SEGMENT}"],
            )
            resolved_tag = _to_text(
                resolved_tags[0] if resolved_tags else f"{primary_tag}::{CORRECT_MARKED_TAG_SEGMENT}",
                f"{primary_tag}::{CORRECT_MARKED_TAG_SEGMENT}",
            )
            primary_prefix = f"{primary_tag}::"
            if resolved_tag.startswith(primary_prefix):
                action_cfg["tag_segment"] = resolved_tag[len(primary_prefix) :] or CORRECT_MARKED_TAG_SEGMENT
            else:
                action_cfg["tag_segment"] = _extract_tag_suffix(
                    resolved_tag,
                    CORRECT_MARKED_TAG_SEGMENT,
                )
            action_cfg["tags"] = resolved_tags
            _apply_add_date_context(action_cfg, action_cfg)

    other_cfg = _as_dict(actions_cfg.get("other"))
    if other_cfg:
        has_standard_other_keys = any(
            key in other_cfg for key in ("tagging", "actions", "submenu_label", "submenu_bool")
        )
        if has_standard_other_keys:
            other_tagging = _as_dict(other_cfg.get("tagging"))
            legacy_other_actions = other_cfg.get("actions")

            resources: list[str] = []
            if isinstance(legacy_other_actions, list):
                for item in legacy_other_actions:
                    if not isinstance(item, dict):
                        continue
                    tag_segment = _to_text(item.get("tag_segment"), "")
                    if tag_segment:
                        resources.append(tag_segment)
            if resources:
                other_cfg["resources"] = resources

            tag_suffix = _to_text(other_cfg.get("tag_suffix"), "Other")
            if _to_bool(other_tagging.get("tag_segment_group"), True):
                tag_suffix = _to_text(other_tagging.get("group_segment"), "Other")
                other_cfg["tag_suffix"] = tag_suffix

            if "add_missed_date_context" in other_tagging:
                other_cfg["add_missed_date_context"] = _to_bool(
                    other_tagging.get("add_missed_date_context"),
                    True,
                )
            elif "add_missed_date_context" in action_defaults:
                other_cfg["add_missed_date_context"] = _to_bool(
                    action_defaults.get("add_missed_date_context"),
                    True,
                )

            if isinstance(legacy_other_actions, list):
                normalized_other_actions: list[dict[str, Any]] = []
                default_child = _to_bool(other_tagging.get("child_of_primary_missed"), True)
                default_add_context = _to_bool(
                    other_cfg.get("add_missed_date_context"),
                    _to_bool(action_defaults.get("add_missed_date_context"), True),
                )
                for idx, raw_action in enumerate(legacy_other_actions):
                    action_cfg = _as_dict(raw_action)
                    if not action_cfg:
                        continue
                    normalized_action = ConfigManager.deep_merge_dicts({}, action_cfg)
                    _copy_menu_label(normalized_action, normalized_action)
                    label = _to_text(
                        normalized_action.get("label"),
                        _to_text(normalized_action.get("menu_label"), ""),
                    )
                    tag_segment = _to_text(
                        normalized_action.get("tag_segment"),
                        scrub_resource_label_to_tag(label) or f"Resource_{idx + 1:02d}",
                    )
                    default_segment = f"{tag_suffix}::{tag_segment}" if tag_suffix else tag_segment
                    default_absolute_tag = (
                        _build_child_tag(primary_tag, default_segment) if default_child else default_segment
                    )
                    resolved_tags = _resolve_standardized_action_tags(
                        normalized_action,
                        primary_tag=primary_tag,
                        default_child_of_primary=default_child,
                        default_segments=[default_segment],
                        default_absolute_tags=[default_absolute_tag],
                    )
                    normalized_action["tags"] = resolved_tags
                    if label:
                        normalized_action["label"] = label
                    normalized_action["add_missed_date_context"] = _to_bool(
                        normalized_action.get("add_missed_date_context"),
                        default_add_context,
                    )
                    normalized_action["prompt"] = _normalize_prompt_settings(
                        _as_dict(normalized_action.get("prompt")),
                        default_kind=PROMPT_KIND_NONE,
                        default_number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,
                        default_blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                    )
                    normalized_other_actions.append(normalized_action)
                other_cfg["actions"] = normalized_other_actions

    normalized["actions"] = actions_cfg
    return normalized


def _load_merged_missed_tags_config() -> dict[str, Any]:
    # Centralized migration lives in the root ConfigManager.
    ConfigManager.migrate_overrides_once()
    section_cfg = ConfigManager(CANONICAL_CONFIG_SECTION).load()
    return section_cfg if isinstance(section_cfg, dict) else {}


def _canonicalize_rotation_syntax(cfg: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(cfg, dict):
        return {}

    normalized = ConfigManager.deep_merge_dicts({}, cfg)
    rotation_cfg = _as_dict(normalized.get("rotation"))
    legacy_block_cfg = _as_dict(normalized.get("block"))
    if legacy_block_cfg:
        if rotation_cfg:
            # Prefer block syntax when both keys are present.
            normalized["rotation"] = ConfigManager.deep_merge_dicts(rotation_cfg, legacy_block_cfg)
        else:
            normalized["rotation"] = legacy_block_cfg
        normalized.pop("block", None)

    return normalized


def _normalize_missed_tags_config(raw_cfg: dict[str, Any]) -> dict[str, Any]:
    defaults = _canonicalize_rotation_syntax(ConfigManager.deep_merge_dicts({}, ADD_MISSED_TAGS_DEFAULTS))
    if not isinstance(raw_cfg, dict):
        return defaults
    canonical_raw_cfg = _canonicalize_rotation_syntax(raw_cfg)
    canonical = ConfigManager.deep_merge_dicts(defaults, canonical_raw_cfg)
    return _apply_standardized_action_schema(canonical)


def _load_missed_tags_override_section() -> dict[str, Any]:
    section_override = ConfigManager.get_override_section(CANONICAL_CONFIG_SECTION)
    return section_override if isinstance(section_override, dict) else {}


def _get_saved_prompt_input(prompt_key: str) -> str:
    if not prompt_key:
        return ""
    section_override = _load_missed_tags_override_section()
    runtime_cfg = _as_dict(section_override.get("runtime"))
    last_inputs = _as_dict(runtime_cfg.get("last_prompt_inputs"))
    value = last_inputs.get(prompt_key, "")
    return value if isinstance(value, str) else ""


def _save_prompt_inputs(prompt_values: dict[str, str]) -> None:
    if not isinstance(prompt_values, dict):
        return
    normalized_updates: dict[str, str] = {}
    for raw_key, raw_value in prompt_values.items():
        key = str(raw_key or "").strip()
        if not key:
            continue
        normalized_updates[key] = str(raw_value)
    if not normalized_updates:
        return

    try:
        section_override = _load_missed_tags_override_section()
        runtime_cfg = _as_dict(section_override.get("runtime"))
        last_inputs = _as_dict(runtime_cfg.get("last_prompt_inputs"))

        has_change = False
        for key, value in normalized_updates.items():
            current_value = last_inputs.get(key)
            if not isinstance(current_value, str) or current_value != value:
                has_change = True
                break
        if not has_change:
            return

        updated_override = ConfigManager.deep_merge_dicts({}, section_override)
        updated_runtime_cfg = _as_dict(updated_override.get("runtime"))
        updated_last_inputs = _as_dict(updated_runtime_cfg.get("last_prompt_inputs"))
        updated_last_inputs.update(normalized_updates)
        updated_runtime_cfg["last_prompt_inputs"] = updated_last_inputs
        updated_override["runtime"] = updated_runtime_cfg
        ConfigManager.save_section_override(CANONICAL_CONFIG_SECTION, updated_override)
    except Exception:
        # Prompt memory should never block tagging behavior.
        return


def _save_prompt_input(prompt_key: str, prompt_value: str) -> None:
    _save_prompt_inputs({prompt_key: prompt_value})


def _apply_prompt_dialog_size(dialog, min_width: int, min_height: int) -> None:
    """Apply a stable minimum size so title/labels are not clipped."""
    width = max(int(min_width), int(dialog.sizeHint().width()))
    height = max(int(min_height), int(dialog.sizeHint().height()))
    dialog.setMinimumSize(width, height)
    dialog.resize(width, height)


def _positioned_text_prompt(parent, title: str, label: str, default_text: str = "") -> tuple[str, bool]:
    dialog = QInputDialog(parent)
    dialog.setInputMode(QInputDialog.InputMode.TextInput)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(default_text)
    _apply_prompt_dialog_size(
        dialog,
        min_width=PROMPT_DIALOG_MIN_WIDTH,
        min_height=PROMPT_DIALOG_MIN_HEIGHT,
    )
    _position_dialog_near_center(dialog, parent)

    accepted = bool(dialog.exec())
    return dialog.textValue(), accepted


def _positioned_text_prompt_with_checkbox(
    parent,
    *,
    title: str,
    label: str,
    default_text: str,
    checkbox_label: str,
    checkbox_checked: bool,
) -> tuple[str, bool, bool]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)

    root = QVBoxLayout(dialog)
    prompt_label = QLabel(label, dialog)
    root.addWidget(prompt_label)

    input_line = QLineEdit(dialog)
    input_line.setText(default_text)
    root.addWidget(input_line)

    checkbox = QCheckBox(checkbox_label, dialog)
    checkbox.setChecked(bool(checkbox_checked))
    root.addWidget(checkbox)

    button_box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    root.addWidget(button_box)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    _apply_prompt_dialog_size(
        dialog,
        min_width=PROMPT_DIALOG_MIN_WIDTH,
        min_height=PROMPT_DIALOG_MIN_HEIGHT,
    )
    _position_dialog_near_center(dialog, parent)

    accepted = bool(dialog.exec())
    return input_line.text(), bool(checkbox.isChecked()), accepted


def _append_tag_segment(tag: str, segment: str) -> str:
    base = str(tag or "").strip()
    suffix = str(segment or "").strip()
    if not base or not suffix:
        return base
    parts = [part.strip() for part in base.split("::") if part.strip()]
    if parts and parts[-1] == suffix:
        return base
    return f"{base}::{suffix}"


def _correct_marked_checkbox_state_key(action_key: str) -> str:
    normalized_action = str(action_key or "").strip()
    if normalized_action == "amboss_test_prompt":
        return AMBOSS_APPEND_CORRECT_MARKED_STATE_KEY
    slug = re.sub(r"[^a-z0-9]+", "_", normalized_action.lower()).strip("_")
    return f"append_correct_marked_{slug or 'default'}"


def load_runtime_config() -> MissedTagsConfig:
    merged_cfg = _load_merged_missed_tags_config()
    canonical_cfg = _normalize_missed_tags_config(merged_cfg)

    ui_cfg = _as_dict(canonical_cfg.get("ui"))
    date_cfg = _as_dict(canonical_cfg.get("date"))
    rotation_cfg = _as_dict(canonical_cfg.get("rotation"))
    actions_cfg = _as_dict(canonical_cfg.get("actions"))

    base_cfg = _as_dict(actions_cfg.get("base"))
    uworld_cfg = _as_dict(actions_cfg.get("uworld"))
    nbme_cfg = _as_dict(actions_cfg.get("nbme"))
    amboss_cfg = _as_dict(actions_cfg.get("amboss"))
    multi_missed_cfg = _as_dict(actions_cfg.get("multi_missed"))
    key_info_cfg = _as_dict(actions_cfg.get("key_info"))
    correct_guess_cfg = _as_dict(actions_cfg.get("correct_guess"))
    uw_correct_missed_cfg = _as_dict(actions_cfg.get(CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY))
    if not uw_correct_missed_cfg:
        uw_correct_missed_cfg = _as_dict(actions_cfg.get(LEGACY_CORRECT_TAG_MISSED_ACTION_KEY))
    other_cfg = _as_dict(actions_cfg.get("other"))

    default_menu_label = _default_text(("ui", "menu_label"), "Missed Tags")
    default_include_day_segment = _default_bool(("date", "include_day_segment"), True)
    default_split_weeks = _default_bool(("date", "split_weeks"), False)

    default_base_missed_tag = _default_string_list(("actions", "base", "tags"), fallback=["##Missed-Qs"])
    legacy_show_base_default_value = _get_path_value(
        ADD_MISSED_TAGS_DEFAULTS, ("actions", "base", "show_in_menu")
    )
    legacy_show_base_default = (
        _to_bool(legacy_show_base_default_value, SHOW_BASE_ACTION_IN_MISSED_TAGS_MENU)
        if legacy_show_base_default_value is not _MISSING
        else SHOW_BASE_ACTION_IN_MISSED_TAGS_MENU
    )
    default_show_base_plain_action = _default_bool(
        ("actions", "base", "menu_display"),
        legacy_show_base_default,
    )
    default_action_label_base = _default_text(("actions", "base", "label"), "Base")

    default_subset_1_name = _default_text(("actions", "uworld", "label"), "UWorld")
    default_subset_1_tag = _default_string_list(
        ("actions", "uworld", "base_tags"),
        fallback=[f"{default_base_missed_tag[0]}::*UW_Tests"],
    )
    default_test_tag_prefix = _default_text(("actions", "uworld", "default_tag_prefix"), "*UW_Tests")
    legacy_parent_range_default_value = _get_path_value(
        ADD_MISSED_TAGS_DEFAULTS,
        ("actions", "uworld", "test_super_range_block_size"),
    )
    legacy_parent_range_default = (
        _to_positive_int(legacy_parent_range_default_value, DEFAULT_UWORLD_PARENT_RANGE_BLOCK_SIZE)
        if legacy_parent_range_default_value is not _MISSING
        else DEFAULT_UWORLD_PARENT_RANGE_BLOCK_SIZE
    )
    default_test_parent_range_block_size = _default_positive_int(
        ("actions", "uworld", "test_parent_range_block_size"),
        legacy_parent_range_default,
    )
    default_test_range_block_size = _default_positive_int(
        ("actions", "uworld", "test_range_block_size"),
        DEFAULT_UWORLD_CHILD_RANGE_BLOCK_SIZE,
    )
    has_explicit_parent_range_block_size = (
        "test_parent_range_block_size" in uworld_cfg or "test_super_range_block_size" in uworld_cfg
    )
    resolved_test_parent_range_block_size = _read_positive_int(
        uworld_cfg,
        "test_parent_range_block_size",
        _read_positive_int(
            uworld_cfg,
            "test_super_range_block_size",
            default_test_parent_range_block_size,
        ),
    )
    # Backward compatibility: old configs only had `test_range_block_size` for a
    # single-level range model. When no parent range key exists, ignore that old
    # value and use the new child default so output stays 50 -> 5.
    resolved_test_range_block_size = (
        _read_positive_int(
            uworld_cfg,
            "test_range_block_size",
            default_test_range_block_size,
        )
        if has_explicit_parent_range_block_size
        else default_test_range_block_size
    )

    default_subset_2_name = _default_text(("actions", "nbme", "label"), "NBME")
    default_subset_2_tag = _default_string_list(
        ("actions", "nbme", "base_tags"),
        fallback=[f"{default_base_missed_tag[0]}::NBME"],
    )
    default_nbme_tag_prefix = _default_text(("actions", "nbme", "default_tag_prefix"), "NBME")

    default_amboss_label = _default_text(("actions", "amboss", "label"), "Amboss")
    default_amboss_base_tag = _default_text(
        ("actions", "amboss", "base_tag"),
        f"{default_base_missed_tag[0]}::Amboss",
    )
    default_amboss_blank_behavior = _default_text(
        ("actions", "amboss", "blank_behavior"),
        PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    )
    default_amboss_number_style = _default_text(
        ("actions", "amboss", "number_style"),
        PROMPT_STYLE_ROTATION_THEN_NUMBER,
    )
    default_amboss_remove_from_other_menu = _default_bool(
        ("actions", "amboss", "remove_from_other_menu"), True
    )

    default_action_label_multi_missed = _default_text(("actions", "multi_missed", "label"), "2x Missed")
    default_multi_miss_tag = _default_text(("actions", "multi_missed", "tag_segment"), "*2x")

    default_action_label_key_info = _default_text(("actions", "key_info", "label"), "Key Info")
    default_key_tag_base = _default_text(("actions", "key_info", "tag_base"), "#Custom::#KEY")

    default_action_label_correct_guess = _default_text(
        ("actions", "correct_guess", "label"),
        "Guessed Correct",
    )
    default_action_label_uw_correct_missed = _default_text(
        ("actions", CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY, "label"),
        DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL,
    )
    default_uw_correct_missed_tag_segment = _default_text(
        ("actions", CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY, "tag_segment"),
        CORRECT_MARKED_TAG_SEGMENT,
    )
    default_correct_guess_tags = _default_string_list(
        ("actions", "correct_guess", "tags"),
        fallback=["#Custom::correct_marked"],
    )
    default_correct_guess_include_rotation = _default_bool(
        ("actions", "correct_guess", "include_rotation"), True
    )
    default_correct_guess_rotation_lowercase = _default_bool(
        ("actions", "correct_guess", "rotation_lowercase"), True
    )
    default_correct_guess_unknown_segment = _default_text(
        ("actions", "correct_guess", "unknown_segment"),
        "unknown",
    )

    default_other_resources = _default_string_list(("actions", "other", "resources"), fallback=[])
    default_other_suffix = _default_text(("actions", "other", "tag_suffix"), "Other")
    default_other_submenu_enabled = _default_bool(("actions", "other", "submenu_bool"), True)
    default_other_submenu_label = _default_text(("actions", "other", "submenu_label"), "Other")

    resolved_base_missed_tag = _read_string_list(base_cfg, "tags", fallback=default_base_missed_tag)
    resolved_base_tag = _to_text(
        resolved_base_missed_tag[0] if resolved_base_missed_tag else default_base_missed_tag[0],
        default_base_missed_tag[0],
    )
    default_multi_miss_tags = [f"{resolved_base_tag}::{default_multi_miss_tag}"]
    resolved_multi_miss_tags = _read_string_list(
        multi_missed_cfg,
        "tags",
        fallback=default_multi_miss_tags,
    )
    default_uw_correct_missed_tags = [f"{resolved_base_tag}::{default_uw_correct_missed_tag_segment}"]
    resolved_uw_correct_missed_tags = _read_string_list(
        uw_correct_missed_cfg,
        "tags",
        fallback=default_uw_correct_missed_tags,
    )

    uworld_prompt_cfg = _build_prompt_action_config(
        uworld_cfg,
        default_kind=PROMPT_KIND_NUMBER,
        default_number_style=PROMPT_STYLE_RANGE_THEN_NUMBER,
        default_blank_behavior=PROMPT_BEHAVIOR_BASE_ONLY,
        default_title=PROMPT_UWORLD_TITLE,
        default_label=PROMPT_DEFAULT_LABEL,
        default_allow_freeform_child_segments=False,
        default_include_rotation_for_freeform=True,
        default_show_correct_marked_checkbox=PROMPT_SHOW_CORRECT_MARKED_CHECKBOX_DEFAULT,
    )
    nbme_prompt_cfg = _build_prompt_action_config(
        nbme_cfg,
        default_kind=PROMPT_KIND_FORM,
        default_number_style=PROMPT_STYLE_NUMBER_ONLY,
        default_blank_behavior=PROMPT_BEHAVIOR_BASE_ONLY,
        default_title=PROMPT_NBME_TITLE,
        default_label=PROMPT_NBME_LABEL,
        default_allow_freeform_child_segments=False,
        default_include_rotation_for_freeform=True,
        default_show_correct_marked_checkbox=PROMPT_SHOW_CORRECT_MARKED_CHECKBOX_DEFAULT,
    )
    amboss_prompt_cfg = _build_prompt_action_config(
        amboss_cfg,
        default_kind=PROMPT_KIND_NUMBER,
        default_number_style=default_amboss_number_style,
        default_blank_behavior=default_amboss_blank_behavior,
        default_title=PROMPT_AMBOSS_TITLE,
        default_label=PROMPT_AMBOSS_LABEL,
        default_allow_freeform_child_segments=AMBOSS_ALLOW_FREEFORM_CHILD_SEGMENTS,
        default_include_rotation_for_freeform=AMBOSS_FREEFORM_INCLUDE_ROTATION_SEGMENT,
        default_show_correct_marked_checkbox=PROMPT_SHOW_CORRECT_MARKED_CHECKBOX_DEFAULT,
    )

    default_rotation_schedule_raw = _default_value(("rotation", "schedule"))
    schedule_raw = rotation_cfg.get("schedule", default_rotation_schedule_raw)
    rotation_schedule = _normalize_rotation_schedule(schedule_raw)
    if not rotation_schedule:
        rotation_schedule = _normalize_rotation_schedule(default_rotation_schedule_raw)

    valid_schedule_policies = {SCHEDULE_POLICY["unknown"], SCHEDULE_POLICY["next"]}
    default_schedule_exhausted_policy = _default_text(
        ("rotation", "exhausted_policy"),
        SCHEDULE_POLICY["unknown"],
    ).lower()
    if default_schedule_exhausted_policy not in valid_schedule_policies:
        default_schedule_exhausted_policy = SCHEDULE_POLICY["unknown"]

    schedule_exhausted_policy = _read_text(
        rotation_cfg,
        "exhausted_policy",
        default_schedule_exhausted_policy,
    ).lower()
    if schedule_exhausted_policy not in valid_schedule_policies:
        schedule_exhausted_policy = SCHEDULE_POLICY["unknown"]

    default_rotation_parent_tag_segment = _default_text(("rotation", "parent_tag_segment"), "Rotation")
    resolved_other_suffix = _read_text(other_cfg, "tag_suffix", default_other_suffix)
    other_default_add_context = _read_action_add_missed_date_context(
        other_cfg,
        fallback=DEFAULT_ACTION_ADD_MISSED_DATE_CONTEXT["other_resource"],
    )

    other_resource_actions: list[OtherResourceActionConfig] = []
    other_action_add_context: dict[str, bool] = {}
    other_actions_raw = other_cfg.get("actions")
    if isinstance(other_actions_raw, list):
        for idx, raw_action in enumerate(other_actions_raw, start=1):
            action_cfg = _as_dict(raw_action)
            if not action_cfg:
                continue
            label_fallback = _to_text(action_cfg.get("tag_segment"), f"Other Resource {idx}")
            action_label = _read_text(action_cfg, "label", label_fallback)
            canonical_label = scrub_resource_label_to_tag(label_fallback) or f"Resource_{idx:02d}"
            fallback_tag = (
                f"{resolved_base_tag}::{resolved_other_suffix}::{canonical_label}"
                if resolved_other_suffix
                else f"{resolved_base_tag}::{canonical_label}"
            )
            action_tags = _read_string_list(action_cfg, "tags", fallback=[fallback_tag])
            action_slug = (
                re.sub(r"[^a-z0-9]+", "_", canonical_label.lower()).strip("_") or f"resource_{idx:02d}"
            )
            action_key = _to_text(action_cfg.get("action_key"), f"other_resource_{idx:02d}_{action_slug}")
            if canonical_label.lower() == "true-learn":
                action_key = _to_text(action_cfg.get("action_key"), "true_learn_test_prompt")
            prompt_defaults_kind = PROMPT_KIND_NONE
            prompt_defaults_style = PROMPT_STYLE_ROTATION_THEN_NUMBER
            prompt_defaults_blank = PROMPT_BEHAVIOR_BASE_PLUS_ROTATION
            prompt_defaults_title = (
                PROMPT_TRUE_LEARN_TITLE if canonical_label.lower() == "true-learn" else (PROMPT_DEFAULT_TITLE)
            )
            prompt_defaults_label = PROMPT_DEFAULT_LABEL
            if canonical_label.lower() == "true-learn":
                prompt_defaults_kind = PROMPT_KIND_NUMBER
            prompt_cfg = _build_prompt_action_config(
                action_cfg,
                default_kind=prompt_defaults_kind,
                default_number_style=prompt_defaults_style,
                default_blank_behavior=prompt_defaults_blank,
                default_title=prompt_defaults_title,
                default_label=prompt_defaults_label,
                default_allow_freeform_child_segments=False,
                default_include_rotation_for_freeform=True,
                default_show_correct_marked_checkbox=PROMPT_SHOW_CORRECT_MARKED_CHECKBOX_DEFAULT,
            )
            include_base_tag = _read_bool(action_cfg, "include_base_tag", False)
            add_context = _read_action_add_missed_date_context(
                action_cfg,
                fallback=other_default_add_context,
            )
            other_action_add_context[action_key] = add_context
            other_resource_actions.append(
                OtherResourceActionConfig(
                    action_key=action_key,
                    label=action_label,
                    tags=action_tags,
                    prompt=prompt_cfg,
                    include_base_tag=include_base_tag,
                )
            )
    if not other_resource_actions:
        fallback_resources = _read_string_list(other_cfg, "resources", fallback=default_other_resources)
        for idx, resource_name in enumerate(fallback_resources, start=1):
            canonical_label = scrub_resource_label_to_tag(resource_name)
            if not canonical_label:
                continue
            action_key = (
                f"other_resource_{idx:02d}_{re.sub(r'[^a-z0-9]+', '_', canonical_label.lower()).strip('_')}"
            )
            prompt_kind = PROMPT_KIND_NONE
            prompt_title = PROMPT_DEFAULT_TITLE
            include_base_tag = True
            if canonical_label.lower() == "true-learn":
                action_key = "true_learn_test_prompt"
                prompt_kind = PROMPT_KIND_NUMBER
                prompt_title = PROMPT_TRUE_LEARN_TITLE
                include_base_tag = False
            fallback_tag = (
                f"{resolved_base_tag}::{resolved_other_suffix}::{canonical_label}"
                if resolved_other_suffix
                else f"{resolved_base_tag}::{canonical_label}"
            )
            other_resource_actions.append(
                OtherResourceActionConfig(
                    action_key=action_key,
                    label=str(resource_name).strip() or canonical_label,
                    tags=[fallback_tag],
                    prompt=PromptActionConfig(
                        kind=prompt_kind,
                        number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,
                        blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                        title=prompt_title,
                        label=PROMPT_DEFAULT_LABEL,
                        allow_freeform_child_segments=False,
                        include_rotation_for_freeform=True,
                    ),
                    include_base_tag=include_base_tag,
                )
            )

    action_cfg_by_section = {
        "base": base_cfg,
        "uworld": uworld_cfg,
        "nbme": nbme_cfg,
        "amboss": amboss_cfg,
        "multi_missed": multi_missed_cfg,
        "key_info": key_info_cfg,
        "correct_guess": correct_guess_cfg,
        CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY: uw_correct_missed_cfg,
    }
    action_add_missed_date_context = dict(DEFAULT_ACTION_ADD_MISSED_DATE_CONTEXT)
    for action_key, source_section, fallback_key in ACTION_DATE_CONTEXT_RESOLUTION_SPECS:
        source_cfg = _as_dict(action_cfg_by_section.get(source_section))
        action_add_missed_date_context[action_key] = _read_action_add_missed_date_context(
            source_cfg,
            fallback=DEFAULT_ACTION_ADD_MISSED_DATE_CONTEXT[fallback_key],
        )
    other_add_context = other_default_add_context
    action_add_missed_date_context["other_resource"] = other_add_context
    action_add_missed_date_context["true_learn_test_prompt"] = other_add_context
    for action_spec in other_resource_actions:
        action_add_missed_date_context[action_spec.action_key] = other_action_add_context.get(
            action_spec.action_key,
            other_add_context,
        )

    return MissedTagsConfig(
        base_missed_tag=resolved_base_missed_tag,
        subset_1_name=_read_text(uworld_cfg, "label", default_subset_1_name),
        subset_1_tag=_read_string_list(
            uworld_cfg,
            "base_tags",
            fallback=default_subset_1_tag,
        ),
        subset_2_name=_read_text(nbme_cfg, "label", default_subset_2_name),
        subset_2_tag=_read_string_list(
            nbme_cfg,
            "base_tags",
            fallback=default_subset_2_tag,
        ),
        other_resources=_read_string_list(
            other_cfg,
            "resources",
            fallback=default_other_resources,
        ),
        other_submenu_enabled=_read_bool(
            other_cfg,
            "submenu_bool",
            default_other_submenu_enabled,
        ),
        other_submenu_label=_read_text(
            other_cfg,
            "submenu_label",
            default_other_submenu_label,
        ),
        rotation_schedule=rotation_schedule,
        schedule_exhausted_policy=schedule_exhausted_policy,
        missed_tags_menu_label=_read_text(ui_cfg, "menu_label", default_menu_label),
        include_day_segment=_read_bool(date_cfg, "include_day_segment", default_include_day_segment),
        split_weeks=_read_bool(date_cfg, "split_weeks", default_split_weeks),
        action_add_missed_date_context=action_add_missed_date_context,
        show_base_plain_action=_read_bool(
            base_cfg,
            "menu_display",
            _read_bool(base_cfg, "show_in_menu", default_show_base_plain_action),
        ),
        action_label_base=_read_text(base_cfg, "label", default_action_label_base),
        action_label_multi_missed=_read_text(multi_missed_cfg, "label", default_action_label_multi_missed),
        action_label_key_info=_read_text(key_info_cfg, "label", default_action_label_key_info),
        action_label_correct_guess=_read_text(correct_guess_cfg, "label", default_action_label_correct_guess),
        action_label_uw_correct_missed=_read_text(
            uw_correct_missed_cfg,
            "label",
            default_action_label_uw_correct_missed,
        ),
        uw_correct_missed_tag_segment=_read_text(
            uw_correct_missed_cfg,
            "tag_segment",
            default_uw_correct_missed_tag_segment,
        ),
        uw_correct_missed_tags=resolved_uw_correct_missed_tags,
        rotation_parent_tag_segment=_read_text(
            rotation_cfg,
            "parent_tag_segment",
            default_rotation_parent_tag_segment,
        ),
        multi_miss_tag=_read_text(multi_missed_cfg, "tag_segment", default_multi_miss_tag),
        multi_miss_tags=resolved_multi_miss_tags,
        default_test_tag_prefix=_read_text(uworld_cfg, "default_tag_prefix", default_test_tag_prefix),
        default_nbme_tag_prefix=_read_text(nbme_cfg, "default_tag_prefix", default_nbme_tag_prefix),
        other_suffix=resolved_other_suffix,
        key_tag_base=_read_text(key_info_cfg, "tag_base", default_key_tag_base),
        uworld_prompt=uworld_prompt_cfg,
        nbme_prompt=nbme_prompt_cfg,
        amboss_prompt=amboss_prompt_cfg,
        other_resource_actions=other_resource_actions,
        amboss_top_level_name=_read_text(amboss_cfg, "label", default_amboss_label),
        amboss_base_tag=_read_text(amboss_cfg, "base_tag", default_amboss_base_tag),
        amboss_blank_behavior=_read_text(amboss_cfg, "blank_behavior", default_amboss_blank_behavior),
        amboss_number_style=_read_text(amboss_cfg, "number_style", default_amboss_number_style),
        amboss_remove_from_other_menu=_read_bool(
            amboss_cfg,
            "remove_from_other_menu",
            default_amboss_remove_from_other_menu,
        ),
        correct_guess_tags=_read_string_list(
            correct_guess_cfg,
            "tags",
            fallback=default_correct_guess_tags,
        ),
        correct_guess_include_rotation=_read_bool(
            correct_guess_cfg,
            "include_rotation",
            default_correct_guess_include_rotation,
        ),
        correct_guess_rotation_lowercase=_read_bool(
            correct_guess_cfg,
            "rotation_lowercase",
            default_correct_guess_rotation_lowercase,
        ),
        correct_guess_unknown_segment=_read_text(
            correct_guess_cfg,
            "unknown_segment",
            default_correct_guess_unknown_segment,
        ),
        test_parent_range_block_size=resolved_test_parent_range_block_size,
        test_range_block_size=resolved_test_range_block_size,
    )


def base_tag_path(cfg: MissedTagsConfig, *parts: str) -> str:
    base = _resolved_base_tag(cfg)
    return "::".join([base, *[p for p in parts if p]])


def _resolved_base_tag(cfg: MissedTagsConfig) -> str:
    if cfg.base_missed_tag:
        base = str(cfg.base_missed_tag[0]).strip()
        if base:
            return base
    defaults = _default_string_list(("actions", "base", "tags"), fallback=["##Missed-Qs"])
    return defaults[0]


def _normalize_tag_segment_for_match(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return re.sub(r"^[^a-z0-9]+", "", normalized)


def _canonicalize_uworld_tag_segment(value: str) -> str:
    segment = str(value or "").strip()
    if not segment:
        return CANONICAL_UWORLD_TAG_SEGMENT
    if _normalize_tag_segment_for_match(segment) == "uw_tests":
        return CANONICAL_UWORLD_TAG_SEGMENT
    return segment


def _canonicalize_uworld_base_tag_path(tag_path: str) -> str:
    raw_parts = [str(part).strip() for part in str(tag_path or "").split("::") if str(part).strip()]
    if not raw_parts:
        return str(tag_path or "").strip()
    raw_parts[-1] = _canonicalize_uworld_tag_segment(raw_parts[-1])
    return "::".join(raw_parts)


def _tag_path_contains_segment(tag_path: str, *segments: str) -> bool:
    normalized_parts = [
        _normalize_tag_segment_for_match(part)
        for part in str(tag_path or "").split("::")
        if str(part).strip()
    ]
    normalized_parts = [part for part in normalized_parts if part]
    if not normalized_parts:
        return False

    for segment in segments:
        normalized_segment = _normalize_tag_segment_for_match(segment)
        if not normalized_segment:
            continue
        if any(
            part == normalized_segment or part.startswith(normalized_segment) for part in normalized_parts
        ):
            return True
    return False


def _uw_base_tag(cfg: MissedTagsConfig) -> str:
    # Honor explicit UWorld base_tags from config first.
    for cand in cfg.subset_1_tag:
        cand_text = str(cand).strip()
        if cand_text:
            return _canonicalize_uworld_base_tag_path(cand_text)

    # Backward compatibility: recover UWorld tags even if they were placed in
    # the NBME slot, including prefixed segments like "*UW_Tests".
    for cand in cfg.subset_2_tag:
        cand_text = str(cand).strip()
        if not cand_text:
            continue
        if "UW_BASE" in cand_text.upper() or _tag_path_contains_segment(cand_text, "uw", "uworld"):
            return _canonicalize_uworld_base_tag_path(cand_text)

    return base_tag_path(cfg, _canonicalize_uworld_tag_segment(cfg.default_test_tag_prefix))


def _format_uworld_test_tag(cfg: MissedTagsConfig, base_tag: str, test_number: int) -> str:
    parent_lower = (
        (test_number - 1) // cfg.test_parent_range_block_size
    ) * cfg.test_parent_range_block_size + 1
    parent_upper = parent_lower + cfg.test_parent_range_block_size - 1

    child_offset = test_number - parent_lower
    child_lower = parent_lower + ((child_offset // cfg.test_range_block_size) * cfg.test_range_block_size)
    child_upper = min(parent_upper, child_lower + cfg.test_range_block_size - 1)

    pad_width = max(DEFAULT_PARENT_RANGE_PAD_WIDTH, len(str(parent_upper)))
    parent_range_tag = f"{parent_lower:0{pad_width}d}-{parent_upper:0{pad_width}d}"
    if INCLUDE_UWORLD_CHILD_RANGE_SEGMENT:
        child_range_tag = f"{child_lower:02d}-{child_upper:02d}"
        return f"{base_tag}::{parent_range_tag}::{child_range_tag}::{test_number:02d}"
    return f"{base_tag}::{parent_range_tag}::{test_number:02d}"


def _normalize_correct_missed_source(value: str) -> str:
    candidate = str(value or "").strip()
    if candidate in UWORLD_CORRECT_MISSED_SOURCE_OPTIONS:
        return candidate
    return UWORLD_CORRECT_MISSED_SOURCE_OPTIONS[0]


def _correct_missed_input_key(source_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(source_name or "").strip().lower()).strip("_")
    return f"uw_correct_marked_input_{slug or 'uworld'}"


def _position_dialog_near_center(dialog, parent) -> None:
    try:
        screen = None

        if parent is not None:
            try:
                parent_window = parent.window()
                if parent_window is not None and parent_window.windowHandle() is not None:
                    screen = parent_window.windowHandle().screen()
            except Exception:
                screen = None

            if screen is None:
                try:
                    screen = parent.screen()
                except Exception:
                    screen = None

        if screen is None:
            screen = QApplication.primaryScreen()

        if screen is not None:
            rect = screen.availableGeometry()
            target_x = rect.x() + (rect.width() - dialog.width()) // 2 + PROMPT_DIALOG_OFFSET_CENTER_X
            target_y = rect.y() + (rect.height() - dialog.height()) // 2 + PROMPT_DIALOG_OFFSET_CENTER_Y
            min_x = rect.x() + PROMPT_DIALOG_SAFE_MARGIN
            min_y = rect.y() + PROMPT_DIALOG_SAFE_MARGIN
            max_x = rect.x() + rect.width() - dialog.width() - PROMPT_DIALOG_SAFE_MARGIN
            max_y = rect.y() + rect.height() - dialog.height() - PROMPT_DIALOG_SAFE_MARGIN

            if max_x >= min_x:
                target_x = min(max(target_x, min_x), max_x)
            else:
                target_x = rect.x() + max((rect.width() - dialog.width()) // 2, 0)

            if max_y >= min_y:
                target_y = min(max(target_y, min_y), max_y)
            else:
                target_y = rect.y() + max((rect.height() - dialog.height()) // 2, 0)

            dialog.move(target_x, target_y)
    except Exception:
        pass


def _prompt_correct_missed_source_and_input(parent, action_label: str) -> tuple[str, str, bool]:
    remembered_source = _normalize_correct_missed_source(
        _get_saved_prompt_input(UWORLD_CORRECT_MISSED_SOURCE_KEY)
    )
    source_inputs = {
        source: _get_saved_prompt_input(_correct_missed_input_key(source))
        for source in UWORLD_CORRECT_MISSED_SOURCE_OPTIONS
    }

    dialog = QDialog(parent)
    dialog.setWindowTitle(str(action_label or DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL))
    root = QVBoxLayout(dialog)

    buttons_layout = QHBoxLayout()
    source_buttons: dict[str, QPushButton] = {}
    for source_name in UWORLD_CORRECT_MISSED_SOURCE_OPTIONS:
        button = QPushButton(source_name, dialog)
        button.setCheckable(True)
        source_buttons[source_name] = button
        buttons_layout.addWidget(button)
    root.addLayout(buttons_layout)

    input_line = QLineEdit(dialog)
    root.addWidget(input_line)

    button_box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    root.addWidget(button_box)

    active_source = remembered_source

    def _select_source(source_name: str) -> None:
        nonlocal active_source
        current = active_source
        if current in source_buttons and current != source_name:
            source_inputs[current] = input_line.text()
        active_source = source_name

        for name, button in source_buttons.items():
            button.setChecked(name == source_name)

        input_line.setText(source_inputs.get(source_name, ""))
        if source_name == "UWorld":
            input_line.setPlaceholderText("Enter integer")
        elif source_name == "NBME":
            input_line.setPlaceholderText("Enter form # or path (e.g., CMS::OBGYN::6)")
        else:
            input_line.setPlaceholderText("Enter tag input")

    for source_name, button in source_buttons.items():
        button.clicked.connect(lambda _, name=source_name: _select_source(name))

    _select_source(remembered_source)
    _apply_prompt_dialog_size(
        dialog,
        min_width=CORRECT_MISSED_DIALOG_MIN_WIDTH,
        min_height=CORRECT_MISSED_DIALOG_MIN_HEIGHT,
    )
    _position_dialog_near_center(dialog, parent)

    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    accepted = bool(dialog.exec())
    if not accepted:
        return remembered_source, source_inputs.get(remembered_source, ""), False

    chosen_source = active_source
    source_inputs[chosen_source] = input_line.text()

    prompt_updates: dict[str, str] = {UWORLD_CORRECT_MISSED_SOURCE_KEY: chosen_source}
    for source_name in UWORLD_CORRECT_MISSED_SOURCE_OPTIONS:
        prompt_updates[_correct_missed_input_key(source_name)] = source_inputs.get(source_name, "")
    _save_prompt_inputs(prompt_updates)

    return chosen_source, source_inputs.get(chosen_source, ""), True


def _nbme_base_tag(cfg: MissedTagsConfig) -> str:
    # Honor explicit NBME base_tags from config first.
    for cand in cfg.subset_2_tag:
        cand_text = str(cand).strip()
        if cand_text:
            return cand_text

    for cand in cfg.subset_1_tag:
        cand_text = str(cand).strip()
        if not cand_text:
            continue
        upper_cand = cand_text.upper()
        if _tag_path_contains_segment(cand_text, "nbme") or "NBME_BASE" in upper_cand:
            return cand_text
        # Backward compatibility for older COMQUEST-only config overrides.
        if _tag_path_contains_segment(cand_text, "comquest") or "COMQUEST_BASE" in upper_cand:
            return cand_text

    return base_tag_path(cfg, cfg.default_nbme_tag_prefix)


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

    if cfg.schedule_exhausted_policy == SCHEDULE_POLICY["next"]:
        for idx, rotation, start, _ in parsed:
            if today < start:
                warning = (
                    f"No active rotation for {today.isoformat()}; using next window "
                    f"{rotation} ({start.isoformat()})."
                )
                return f"{idx:02d}", rotation, warning

    last_end = parsed[-1][3]
    if today > last_end:
        return "00", "Unknown", f"No rotation configured after {last_end.isoformat()}; using Unknown."
    return "00", "Unknown", f"No rotation configured for {today.isoformat()}; using Unknown."


def get_formatted_rotation_segment(cfg: MissedTagsConfig, rot_num_2d: str, rot_label: str) -> str:
    _ = cfg, rot_num_2d
    segment_label = str(rot_label or "").strip()
    if not segment_label:
        return "00_Unknown"
    if segment_label == "Unknown":
        return "00_Unknown"
    return segment_label


def get_rotation_segment(cfg: MissedTagsConfig) -> str:
    rot_num_2d, rot_label, _ = get_current_or_next_rotation_meta(cfg)
    return get_formatted_rotation_segment(cfg, rot_num_2d, rot_label)


def get_rotation_key_info_tag(cfg: MissedTagsConfig) -> str:
    rot_segment = get_rotation_segment(cfg)
    return f"{cfg.key_tag_base}::{rot_segment}"


def get_correct_guess_rotation_segment(cfg: MissedTagsConfig) -> str:
    rot_num_2d, rot_label, _ = get_current_or_next_rotation_meta(cfg)
    formatted_segment = get_formatted_rotation_segment(cfg, rot_num_2d, rot_label)
    raw = str(
        formatted_segment if formatted_segment != "00_Unknown" else cfg.correct_guess_unknown_segment
    ).strip()
    raw = raw if raw else cfg.correct_guess_unknown_segment
    slug = re.sub(r"\s+", "-", raw)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "", slug)
    if not slug:
        slug = cfg.correct_guess_unknown_segment
    return slug.lower() if cfg.correct_guess_rotation_lowercase else slug


def get_correct_guess_tags(cfg: MissedTagsConfig, subtag: str = "") -> list[str]:
    if cfg.correct_guess_include_rotation:
        rotation_segment = get_correct_guess_rotation_segment(cfg)
        tags = [f"{base_tag}::{rotation_segment}" for base_tag in cfg.correct_guess_tags]
    else:
        tags = list(cfg.correct_guess_tags)

    cleaned_subtag = str(subtag or "").strip()
    if not cleaned_subtag:
        return tags
    return [f"{tag}::{cleaned_subtag}" for tag in tags]


def get_missed_month_tag(cfg: MissedTagsConfig) -> str:
    now = datetime.now()
    base = _resolved_base_tag(cfg)
    month_segment = f"{now.strftime('%m')}_{now.strftime('%B')}"
    if cfg.include_day_segment:
        day_segment = now.strftime("%d")
        if cfg.split_weeks:
            week_segment = min(((now.day - 1) // 7) + 1, 4)
            return f"{base}::{now.year}::{month_segment}::week_{week_segment}::{day_segment}"
        return f"{base}::{now.year}::{month_segment}::{day_segment}"
    return f"{base}::{now.year}::{month_segment}"


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


def _should_add_missed_date_context(cfg: MissedTagsConfig, action_key: str) -> bool:
    if action_key in cfg.action_add_missed_date_context:
        return bool(cfg.action_add_missed_date_context[action_key])
    return action_key not in EXCLUDE_AUTO_MISS


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
    if _should_add_missed_date_context(runtime_cfg, action_key):
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


def _ensure_selected_notes(browser) -> bool:
    if browser.selectedNotes():
        return True
    showInfo(MSG_NO_NOTES_SELECTED)
    return False


def _add_prompt_action(
    browser,
    menu,
    *,
    label: str,
    cfg: MissedTagsConfig,
    base_tags: list[str],
    action_key: str,
    title: str,
    prompt_label: str,
    blank_behavior: str,
    number_style: str,
    pad_label: bool = True,
    allow_freeform_child_segments: bool = False,
    include_rotation_for_freeform: bool = True,
    show_correct_marked_checkbox: bool = False,
) -> None:
    action_text = f"{label:<24}" if pad_label else label
    action = QAction(action_text, browser)
    action.triggered.connect(
        make_test_prompt_handler(
            browser,
            cfg,
            base_tags,
            action_key=action_key,
            title=title,
            label=prompt_label,
            blank_behavior=blank_behavior,
            number_style=number_style,
            allow_freeform_child_segments=allow_freeform_child_segments,
            include_rotation_for_freeform=include_rotation_for_freeform,
            show_correct_marked_checkbox=show_correct_marked_checkbox,
        )
    )
    menu.addAction(action)


def _add_form_prompt_action(
    browser,
    menu,
    *,
    label: str,
    cfg: MissedTagsConfig,
    base_tags: list[str],
    action_key: str,
    title: str,
    prompt_label: str,
    pad_label: bool = True,
    show_correct_marked_checkbox: bool = False,
) -> None:
    action_text = f"{label:<24}" if pad_label else label
    action = QAction(action_text, browser)

    def on_trigger():
        saved_form_value = _get_saved_prompt_input(action_key)
        append_correct_marked = False
        checkbox_state_key = ""
        if show_correct_marked_checkbox:
            checkbox_state_key = _correct_marked_checkbox_state_key(action_key)
            saved_append_state = _get_saved_prompt_input(checkbox_state_key)
            default_append_state = _to_bool(saved_append_state, AMBOSS_APPEND_CORRECT_MARKED_DEFAULT)
            form_value, append_correct_marked, ok = _positioned_text_prompt_with_checkbox(
                browser,
                title=title,
                label=prompt_label,
                default_text=saved_form_value,
                checkbox_label=PROMPT_AMBOSS_APPEND_CORRECT_MARKED_LABEL,
                checkbox_checked=default_append_state,
            )
        else:
            form_value, ok = _positioned_text_prompt(
                browser,
                title,
                prompt_label,
                default_text=saved_form_value,
            )
        if not ok:
            return
        if checkbox_state_key:
            _save_prompt_input(checkbox_state_key, "1" if append_correct_marked else "0")

        form_value = (form_value or "").strip()
        if form_value == "":
            _save_prompt_input(action_key, "")
            showInfo(MSG_INVALID_NBME_INPUT)
            return

        nbme_child_path = _normalize_nbme_child_path(form_value)
        if not nbme_child_path:
            showInfo(MSG_INVALID_NBME_INPUT)
            return
        _save_prompt_input(action_key, form_value)

        if not _ensure_selected_notes(browser):
            return
        resolved_base_tags = [str(tag).strip() for tag in base_tags if str(tag).strip()]
        if not resolved_base_tags:
            return
        formatted_tags = [f"{tag}::{nbme_child_path}" for tag in resolved_base_tags]
        if append_correct_marked:
            formatted_tags = [
                _append_tag_segment(tag, AMBOSS_CORRECT_MARKED_TAG_SEGMENT) for tag in formatted_tags
            ]
        apply_tags_to_selected_notes(browser, formatted_tags, action_key=action_key, cfg=cfg)

    action.triggered.connect(on_trigger)
    menu.addAction(action)


def _add_schema_driven_action(
    browser,
    menu,
    *,
    label: str,
    cfg: MissedTagsConfig,
    tags: list[str],
    action_key: str,
    prompt_cfg: PromptActionConfig,
    pad_label: bool = True,
) -> None:
    resolved_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    if not resolved_tags:
        return

    if prompt_cfg.kind == PROMPT_KIND_NONE:
        action_label = f"{label:<24}" if pad_label else label
        add_static_action(browser, menu, action_label, resolved_tags, action_key=action_key, cfg=cfg)
        return

    if prompt_cfg.kind == PROMPT_KIND_FORM:
        _add_form_prompt_action(
            browser,
            menu,
            label=label,
            cfg=cfg,
            base_tags=resolved_tags,
            action_key=action_key,
            title=prompt_cfg.title,
            prompt_label=prompt_cfg.label,
            pad_label=pad_label,
            show_correct_marked_checkbox=prompt_cfg.show_correct_marked_checkbox,
        )
        return

    _add_prompt_action(
        browser,
        menu,
        label=label,
        cfg=cfg,
        base_tags=resolved_tags,
        action_key=action_key,
        title=prompt_cfg.title,
        prompt_label=prompt_cfg.label,
        blank_behavior=prompt_cfg.blank_behavior,
        number_style=prompt_cfg.number_style,
        pad_label=pad_label,
        allow_freeform_child_segments=prompt_cfg.allow_freeform_child_segments,
        include_rotation_for_freeform=prompt_cfg.include_rotation_for_freeform,
        show_correct_marked_checkbox=prompt_cfg.show_correct_marked_checkbox,
    )


def add_base_plain_action(browser, menu, cfg: MissedTagsConfig):
    action = QAction(cfg.action_label_base, browser)
    action.triggered.connect(
        lambda _: apply_tags_to_selected_notes(browser, cfg.base_missed_tag, action_key="base_plain", cfg=cfg)
    )
    menu.addAction(action)


def add_missed_tag_menu_items(browser, menu):
    cfg = load_runtime_config()

    tag_menu = QMenu(cfg.missed_tags_menu_label, browser)
    tag_menu.setStyleSheet(build_missed_tags_menu_stylesheet())

    add_uworld_tags(browser, tag_menu, cfg)
    add_uworld_correct_missed_tag(browser, tag_menu, cfg)
    add_nbme_tag(browser, tag_menu, cfg)
    add_amboss_tag(browser, tag_menu, cfg)
    if cfg.show_base_plain_action:
        add_base_plain_action(browser, tag_menu, cfg)

    add_multi_tag(browser, tag_menu, cfg)
    add_key_info_action(browser, tag_menu, cfg)

    add_correct_guess_action(browser, tag_menu, cfg)

    if cfg.other_submenu_enabled:
        submenu_label = str(cfg.other_submenu_label).strip() or "Other"
        other_menu = QMenu(submenu_label, browser)
        other_menu.setStyleSheet(build_missed_tags_menu_stylesheet())
        add_other_resources_actions(browser, other_menu, cfg)
        if other_menu.actions():
            tag_menu.addMenu(other_menu)
    else:
        add_other_resources_actions(browser, tag_menu, cfg)

    if tag_menu.actions():
        menu.addMenu(tag_menu)


def add_nbme_tag(browser, menu, cfg: MissedTagsConfig):
    base_tag = _nbme_base_tag(cfg)
    _add_schema_driven_action(
        browser,
        menu,
        label=cfg.subset_2_name,
        cfg=cfg,
        tags=[base_tag],
        action_key="nbme_form_prompt",
        prompt_cfg=cfg.nbme_prompt,
        pad_label=True,
    )


def add_amboss_tag(browser, menu, cfg: MissedTagsConfig):
    _add_schema_driven_action(
        browser,
        menu,
        label=cfg.amboss_top_level_name,
        cfg=cfg,
        tags=[cfg.amboss_base_tag],
        action_key="amboss_test_prompt",
        prompt_cfg=cfg.amboss_prompt,
        pad_label=True,
    )


def add_multi_tag(browser, menu, cfg: MissedTagsConfig):
    add_static_action(
        browser,
        menu,
        f"{cfg.action_label_multi_missed:<24}",
        list(cfg.multi_miss_tags),
        action_key="multi_missed",
        cfg=cfg,
    )


def add_uworld_tags(browser, menu, cfg: MissedTagsConfig):
    set_name = cfg.subset_1_name
    base = _uw_base_tag(cfg)
    if set_name and base:
        _add_schema_driven_action(
            browser,
            menu,
            label=set_name,
            cfg=cfg,
            tags=[base],
            action_key="uw_test_prompt",
            prompt_cfg=cfg.uworld_prompt,
            pad_label=True,
        )


def add_uworld_correct_missed_tag(browser, menu, cfg: MissedTagsConfig):
    action_label = str(cfg.action_label_uw_correct_missed or DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL).strip()
    action = QAction(action_label or DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL, browser)

    def on_trigger():
        if not _ensure_selected_notes(browser):
            return

        selected_source, source_input, ok = _prompt_correct_missed_source_and_input(browser, action.text())
        if not ok:
            return

        base_missed_tag = _resolved_base_tag(cfg)
        configured_base_tag = (
            str(cfg.uw_correct_missed_tags[0]).strip()
            if cfg.uw_correct_missed_tags
            else f"{base_missed_tag}::{CORRECT_MARKED_TAG_SEGMENT}"
        )
        configured_segment = _normalize_freeform_tag_path(cfg.uw_correct_missed_tag_segment)
        if not configured_segment:
            configured_segment = _normalize_freeform_tag_path(
                _extract_tag_suffix(configured_base_tag, CORRECT_MARKED_TAG_SEGMENT)
            )
        correct_marked_segment = configured_segment or CORRECT_MARKED_TAG_SEGMENT
        correct_marked_base_tag = configured_base_tag or f"{base_missed_tag}::{correct_marked_segment}"
        raw_input = str(source_input or "").strip()
        if selected_source == "UWorld":
            try:
                test_number = int(raw_input)
            except ValueError:
                showInfo(MSG_INVALID_INTEGER_TEST_NUMBER)
                return
            if test_number <= 0:
                showInfo(MSG_INVALID_INTEGER_TEST_NUMBER)
                return
            uworld_base_tag = _uw_base_tag(cfg)
            source_tag = _format_uworld_test_tag(cfg, uworld_base_tag, test_number)
            formatted_tag = f"{source_tag}::{correct_marked_segment}"
        elif selected_source == "NBME":
            nbme_child_path = _normalize_nbme_child_path(raw_input)
            if not nbme_child_path:
                showInfo(MSG_INVALID_NBME_INPUT)
                return
            nbme_base_tag = _nbme_base_tag(cfg)
            source_tag = f"{nbme_base_tag}::{nbme_child_path}"
            formatted_tag = f"{source_tag}::{correct_marked_segment}"
        elif selected_source == "Amboss":
            normalized_input = _normalize_freeform_tag_path(raw_input)
            if not normalized_input:
                showInfo(MSG_INVALID_CORRECT_MARKED_SOURCE_INPUT)
                return
            amboss_base_tag = str(cfg.amboss_base_tag).strip() or f"{base_missed_tag}::Amboss"
            source_tag = f"{amboss_base_tag}::{normalized_input}"
            formatted_tag = f"{source_tag}::{correct_marked_segment}"
        else:
            normalized_input = _normalize_freeform_tag_path(raw_input)
            if not normalized_input:
                showInfo(MSG_INVALID_CORRECT_MARKED_SOURCE_INPUT)
                return
            formatted_tag = f"{correct_marked_base_tag}::{normalized_input}"

        apply_tags_to_selected_notes(
            browser,
            [formatted_tag],
            action_key=ACTION_KEY_CORRECT_TAG_MISSED_PROMPT,
            cfg=cfg,
        )

    action.triggered.connect(on_trigger)
    menu.addAction(action)


def add_other_resources_actions(
    browser,
    menu,
    cfg: MissedTagsConfig,
    resources_override: list[str] | None = None,
):
    if resources_override is not None:
        other_actions = []
        for idx, resource_name in enumerate(resources_override, start=1):
            canonical = scrub_resource_label_to_tag(resource_name)
            if not canonical:
                continue
            action_key = (
                f"other_resource_{idx:02d}_{re.sub(r'[^a-z0-9]+', '_', canonical.lower()).strip('_')}"
            )
            prompt_cfg = PromptActionConfig(
                kind=PROMPT_KIND_NONE,
                number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,
                blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                title=PROMPT_DEFAULT_TITLE,
                label=PROMPT_DEFAULT_LABEL,
                allow_freeform_child_segments=False,
                include_rotation_for_freeform=True,
            )
            include_base_tag = True
            if canonical.lower() == "true-learn":
                action_key = "true_learn_test_prompt"
                prompt_cfg = PromptActionConfig(
                    kind=PROMPT_KIND_NUMBER,
                    number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,
                    blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                    title=PROMPT_TRUE_LEARN_TITLE,
                    label=PROMPT_DEFAULT_LABEL,
                    allow_freeform_child_segments=False,
                    include_rotation_for_freeform=True,
                )
                include_base_tag = False
            resource_tag = base_tag_path(cfg, cfg.other_suffix, canonical)
            other_actions.append(
                OtherResourceActionConfig(
                    action_key=action_key,
                    label=str(resource_name).strip() or canonical,
                    tags=[resource_tag],
                    prompt=prompt_cfg,
                    include_base_tag=include_base_tag,
                )
            )
    else:
        other_actions = list(cfg.other_resource_actions)

    for action_spec in other_actions:
        canonical_label = scrub_resource_label_to_tag(action_spec.label)
        if cfg.amboss_remove_from_other_menu and canonical_label.lower() == "amboss":
            continue
        action_tags = [str(tag).strip() for tag in action_spec.tags if str(tag).strip()]
        if not action_tags:
            continue
        if action_spec.include_base_tag and action_spec.prompt.kind == PROMPT_KIND_NONE:
            action_tags = list(cfg.base_missed_tag) + action_tags
        _add_schema_driven_action(
            browser,
            menu,
            label=action_spec.label,
            cfg=cfg,
            tags=action_tags,
            action_key=action_spec.action_key,
            prompt_cfg=action_spec.prompt,
            pad_label=False,
        )


def make_test_prompt_handler(
    browser,
    cfg: MissedTagsConfig,
    base_tags: list[str],
    action_key: str,
    title: str | None = None,
    label: str | None = None,
    blank_behavior: str = PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    number_style: str = PROMPT_STYLE_RANGE_THEN_NUMBER,
    allow_freeform_child_segments: bool = False,
    include_rotation_for_freeform: bool = True,
    show_correct_marked_checkbox: bool = False,
):
    def on_trigger():
        prompt_title = (title or PROMPT_DEFAULT_TITLE).strip() or PROMPT_DEFAULT_TITLE
        prompt_label = (label or PROMPT_DEFAULT_LABEL).strip() or PROMPT_DEFAULT_LABEL
        saved_test_num = _get_saved_prompt_input(action_key)
        append_correct_marked = False
        checkbox_state_key = ""
        if show_correct_marked_checkbox:
            checkbox_state_key = _correct_marked_checkbox_state_key(action_key)
            saved_append_state = _get_saved_prompt_input(checkbox_state_key)
            default_append_state = _to_bool(saved_append_state, AMBOSS_APPEND_CORRECT_MARKED_DEFAULT)
            test_num, append_correct_marked, ok = _positioned_text_prompt_with_checkbox(
                browser,
                title=prompt_title,
                label=prompt_label,
                default_text=saved_test_num,
                checkbox_label=PROMPT_AMBOSS_APPEND_CORRECT_MARKED_LABEL,
                checkbox_checked=default_append_state,
            )
        else:
            test_num, ok = _positioned_text_prompt(
                browser, prompt_title, prompt_label, default_text=saved_test_num
            )
        if not ok:
            return
        if checkbox_state_key:
            _save_prompt_input(checkbox_state_key, "1" if append_correct_marked else "0")
        test_num = (test_num or "").strip()
        rot_num_2d, rot_label, _ = get_current_or_next_rotation_meta(cfg)
        rotation_segment = get_formatted_rotation_segment(cfg, rot_num_2d, rot_label)

        resolved_base_tags = [str(tag).strip() for tag in base_tags if str(tag).strip()]
        if not resolved_base_tags:
            return

        def _build_formatted_tag(base_tag: str) -> str:
            if test_num == "":
                if allow_freeform_child_segments and not include_rotation_for_freeform:
                    return f"{base_tag}"
                if blank_behavior == PROMPT_BEHAVIOR_BASE_ONLY:
                    return f"{base_tag}"
                return f"{base_tag}::{rotation_segment}"

            if allow_freeform_child_segments:
                freeform_path = _normalize_freeform_tag_path(test_num)
                if freeform_path:
                    if include_rotation_for_freeform:
                        return f"{base_tag}::{rotation_segment}::{freeform_path}"
                    return f"{base_tag}::{freeform_path}"
                if blank_behavior == PROMPT_BEHAVIOR_BASE_ONLY:
                    return f"{base_tag}"
                if include_rotation_for_freeform:
                    return f"{base_tag}::{rotation_segment}"
                return f"{base_tag}"

            try:
                tn = int(test_num)
            except ValueError:
                if blank_behavior == PROMPT_BEHAVIOR_BASE_ONLY:
                    return f"{base_tag}"
                return f"{base_tag}::{rotation_segment}"

            if number_style == PROMPT_STYLE_ROTATION_THEN_NUMBER:
                return f"{base_tag}::{rotation_segment}::{tn:02d}"
            if number_style == PROMPT_STYLE_NUMBER_ONLY:
                return f"{base_tag}::{tn:02d}"
            return _format_uworld_test_tag(cfg, base_tag, tn)

        if test_num == "":
            _save_prompt_input(action_key, "")
        elif allow_freeform_child_segments:
            _save_prompt_input(action_key, test_num)
        else:
            try:
                int(test_num)
            except ValueError:
                pass
            else:
                _save_prompt_input(action_key, test_num)

        formatted_tags = [_build_formatted_tag(base_tag) for base_tag in resolved_base_tags]
        if append_correct_marked:
            formatted_tags = [
                _append_tag_segment(tag, AMBOSS_CORRECT_MARKED_TAG_SEGMENT) for tag in formatted_tags
            ]

        if not _ensure_selected_notes(browser):
            return
        apply_tags_to_selected_notes(browser, formatted_tags, action_key=action_key, cfg=cfg)

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
        if not _ensure_selected_notes(browser):
            return
        key_tag = get_rotation_key_info_tag(cfg)
        apply_tags_to_selected_notes(browser, [key_tag], action_key="add_key_info_action", cfg=cfg)

    action.triggered.connect(on_click)
    menu.addAction(action)


def add_correct_guess_action(browser, menu, cfg: MissedTagsConfig):
    action = QAction(cfg.action_label_correct_guess, browser)

    def on_trigger():
        if not _ensure_selected_notes(browser):
            return

        saved_subtag = _get_saved_prompt_input("correct_guess_subtag_prompt")
        subtag, ok = _positioned_text_prompt(
            browser,
            PROMPT_CORRECT_GUESS_SUBTAG_TITLE,
            PROMPT_CORRECT_GUESS_SUBTAG_LABEL,
            default_text=saved_subtag,
        )
        if not ok:
            return

        subtag = str(subtag or "").strip()
        if re.search(r"\s", subtag):
            showInfo(MSG_INVALID_CORRECT_GUESS_SUBTAG)
            return

        _save_prompt_input("correct_guess_subtag_prompt", subtag)
        apply_tags_to_selected_notes(
            browser,
            get_correct_guess_tags(cfg, subtag=subtag),
            action_key="correct_guess",
            cfg=cfg,
        )

    action.triggered.connect(on_trigger)
    menu.addAction(action)
