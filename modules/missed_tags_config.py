# pyright: reportMissingImports=false
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..config_manager import ConfigManager
from .missed_tags_constants import (
    ACTION_DATE_CONTEXT_RESOLUTION_SPECS,
    ACTION_KEY_CORRECT_TAG_MISSED_PROMPT,
    AMBOSS_ALLOW_FREEFORM_CHILD_SEGMENTS,
    AMBOSS_FREEFORM_INCLUDE_ROTATION_SEGMENT,
    CANONICAL_CONFIG_SECTION,
    CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY,
    CORRECT_MARKED_TAG_SEGMENT,
    DEFAULT_ACTION_ADD_MISSED_DATE_CONTEXT,
    DEFAULT_OPEN_ENDED_ROTATION_END,
    DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL,
    DEFAULT_UWORLD_CHILD_RANGE_BLOCK_SIZE,
    DEFAULT_UWORLD_PARENT_RANGE_BLOCK_SIZE,
    LEGACY_CORRECT_TAG_MISSED_ACTION_KEY,
    MISSED_CONTEXT_PARENT_TAG_SEGMENT,
    PROMPT_AMBOSS_LABEL,
    PROMPT_AMBOSS_TITLE,
    PROMPT_BEHAVIOR_BASE_ONLY,
    PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    PROMPT_DEFAULT_LABEL,
    PROMPT_DEFAULT_TITLE,
    PROMPT_KIND_FORM,
    PROMPT_KIND_NONE,
    PROMPT_KIND_NUMBER,
    PROMPT_NBME_LABEL,
    PROMPT_NBME_TITLE,
    PROMPT_SHOW_CORRECT_MARKED_CHECKBOX_DEFAULT,
    PROMPT_STYLE_NUMBER_ONLY,
    PROMPT_STYLE_RANGE_THEN_NUMBER,
    PROMPT_STYLE_ROTATION_THEN_NUMBER,
    PROMPT_TRUE_LEARN_TITLE,
    PROMPT_UWORLD_TITLE,
    SCHEDULE_POLICY,
    SHOW_BASE_ACTION_IN_MISSED_TAGS_MENU,
    STANDARDIZED_ACTION_SCHEMA_SPECS,
    VALID_PROMPT_BLANK_BEHAVIORS,
    VALID_PROMPT_KINDS,
    VALID_PROMPT_NUMBER_STYLES,
)
from .missed_tags_tag_utils import (
    _build_child_tag,
    _canonicalize_uworld_base_tag_path,
    _canonicalize_uworld_tag_segment,
    _extract_tag_suffix,
    _normalize_missed_context_parent_tag_segment,
    scrub_resource_label_to_tag,
)
from .shared.defaults import ADD_MISSED_TAGS_DEFAULTS

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
            action_cfg["tag_base"] = (
                _to_text(resolved_tags[0], "#Custom::#KEY") if resolved_tags else "#Custom::#KEY"
            )
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

    default_rotation_schedule_raw = _default_value(("block", "schedule"))
    schedule_raw = rotation_cfg.get("schedule", default_rotation_schedule_raw)
    rotation_schedule = _normalize_rotation_schedule(schedule_raw)
    if not rotation_schedule:
        rotation_schedule = _normalize_rotation_schedule(default_rotation_schedule_raw)

    valid_schedule_policies = {SCHEDULE_POLICY["unknown"], SCHEDULE_POLICY["next"]}
    default_schedule_exhausted_policy = _default_text(
        ("block", "exhausted_policy"),
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

    default_rotation_parent_tag_segment = _normalize_missed_context_parent_tag_segment(
        _default_text(("block", "parent_tag_segment"), MISSED_CONTEXT_PARENT_TAG_SEGMENT),
    )
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
        rotation_parent_tag_segment=_normalize_missed_context_parent_tag_segment(
            _read_text(
                rotation_cfg,
                "parent_tag_segment",
                default_rotation_parent_tag_segment,
            ),
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
