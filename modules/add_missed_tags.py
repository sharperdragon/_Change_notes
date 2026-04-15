# pyright: reportMissingImports=false
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aqt.qt import QAction, QInputDialog, QMenu
from aqt.utils import showInfo, tooltip

from ..config_manager import ConfigManager
from .shared.defaults import ADD_MISSED_TAGS_DEFAULTS
from .shared.menu_styles import build_missed_tags_menu_stylesheet

# ! ----------------------------- CONFIG SECTIONS -----------------------------
CANONICAL_CONFIG_SECTION = "tag_missed_qid_notes"
# ! -------------------------------------------------------------------------

# ! --------------------------- CHANGE-PRONE VALUES ---------------------------
SCHEDULE_POLICY = {
    "unknown": "unknown",
    "next": "next",
}
DEFAULT_OPEN_ENDED_ROTATION_END = "2099-12-31"

PROMPT_BEHAVIOR = {
    "base_plus_rotation": "base_plus_rotation",
    "base_only": "base_only",
}

PROMPT_STYLE = {
    "rotation_then_number": "rotation_then_number",
    "range_then_number": "range_then_number",
}

CONFIG_PATHS: dict[str, tuple[str, ...]] = {
    "ui.menu_label": ("ui", "menu_label"),
    "date.include_day_segment": ("date", "include_day_segment"),
    "rotation.schedule": ("rotation", "schedule"),
    "rotation.exhausted_policy": ("rotation", "exhausted_policy"),
    "rotation.parent_tag_segment": ("rotation", "parent_tag_segment"),
    "rotation.winter_break_label": ("rotation", "winter_break_label"),
    "rotation.post_rotation_label": ("rotation", "post_rotation_label"),
    "actions.base.label": ("actions", "base", "label"),
    "actions.base.tags": ("actions", "base", "tags"),
    "actions.uworld.label": ("actions", "uworld", "label"),
    "actions.uworld.base_tags": ("actions", "uworld", "base_tags"),
    "actions.uworld.default_tag_prefix": ("actions", "uworld", "default_tag_prefix"),
    "actions.uworld.test_range_block_size": ("actions", "uworld", "test_range_block_size"),
    "actions.nbme.label": ("actions", "nbme", "label"),
    "actions.nbme.base_tags": ("actions", "nbme", "base_tags"),
    "actions.nbme.default_tag_prefix": ("actions", "nbme", "default_tag_prefix"),
    "actions.amboss.label": ("actions", "amboss", "label"),
    "actions.amboss.base_tag": ("actions", "amboss", "base_tag"),
    "actions.amboss.blank_behavior": ("actions", "amboss", "blank_behavior"),
    "actions.amboss.number_style": ("actions", "amboss", "number_style"),
    "actions.amboss.remove_from_other_menu": ("actions", "amboss", "remove_from_other_menu"),
    "actions.multi_missed.label": ("actions", "multi_missed", "label"),
    "actions.multi_missed.tag_segment": ("actions", "multi_missed", "tag_segment"),
    "actions.key_info.label": ("actions", "key_info", "label"),
    "actions.key_info.tag_base": ("actions", "key_info", "tag_base"),
    "actions.correct_guess.label": ("actions", "correct_guess", "label"),
    "actions.correct_guess.tags": ("actions", "correct_guess", "tags"),
    "actions.correct_guess.include_rotation": ("actions", "correct_guess", "include_rotation"),
    "actions.correct_guess.rotation_lowercase": ("actions", "correct_guess", "rotation_lowercase"),
    "actions.correct_guess.unknown_segment": ("actions", "correct_guess", "unknown_segment"),
    "actions.other.resources": ("actions", "other", "resources"),
    "actions.other.tag_suffix": ("actions", "other", "tag_suffix"),
}

MSG_NO_NOTES_SELECTED = "❌ No notes selected."
MSG_INVALID_INTEGER_TEST_NUMBER = "❌ Please enter a valid integer test number."
PROMPT_DEFAULT_TITLE = "Enter Test Number"
PROMPT_DEFAULT_LABEL = "Test #:"
PROMPT_NBME_TITLE = "Enter NBME Form"
PROMPT_NBME_LABEL = "Form #:"
PROMPT_AMBOSS_TITLE = "Enter Amboss Test Number"
PROMPT_UWORLD_TITLE = "Enter UWorld Test Number"
PROMPT_TRUE_LEARN_TITLE = "Enter True-Learn Test Number"
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
    include_day_segment: bool
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


def _default_value(path_key: str) -> Any:
    path = CONFIG_PATHS[path_key]
    value = _get_path_value(ADD_MISSED_TAGS_DEFAULTS, path)
    if value is _MISSING:
        raise KeyError(f"Missing default at path: {'.'.join(path)}")
    return value


def _default_text(path_key: str, fallback: str) -> str:
    return _to_text(_default_value(path_key), fallback)


def _default_bool(path_key: str, fallback: bool) -> bool:
    return _to_bool(_default_value(path_key), fallback)


def _default_positive_int(path_key: str, fallback: int) -> int:
    return _to_positive_int(_default_value(path_key), fallback)


def _default_string_list(path_key: str, fallback: list[str]) -> list[str]:
    return _to_string_list(_default_value(path_key), fallback=fallback)


def _read_text(data: dict[str, Any], key: str, fallback: str) -> str:
    return _to_text(data.get(key, fallback), fallback)


def _read_bool(data: dict[str, Any], key: str, fallback: bool) -> bool:
    return _to_bool(data.get(key, fallback), fallback)


def _read_positive_int(data: dict[str, Any], key: str, fallback: int) -> int:
    return _to_positive_int(data.get(key, fallback), fallback)


def _read_string_list(data: dict[str, Any], key: str, fallback: list[str]) -> list[str]:
    return _to_string_list(data.get(key, fallback), fallback=fallback)


def _normalize_rotation_schedule(raw: Any) -> list[tuple[str, str, str]]:
    normalized: list[tuple[str, str, str]] = []
    if not isinstance(raw, list):
        return normalized

    for item in raw:
        label = start = end = ""
        if isinstance(item, dict):
            label = str(item.get("label", "")).strip()
            start = str(item.get("start", "")).strip()
            end = str(item.get("end", "")).strip() or DEFAULT_OPEN_ENDED_ROTATION_END
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            label = str(item[0]).strip()
            start = str(item[1]).strip()
            end = str(item[2]).strip() if len(item) >= 3 else DEFAULT_OPEN_ENDED_ROTATION_END
            if not end:
                end = DEFAULT_OPEN_ENDED_ROTATION_END

        if not label or not start:
            continue
        try:
            datetime.strptime(start, "%Y-%m-%d")
            datetime.strptime(end, "%Y-%m-%d")
        except Exception:
            continue

        normalized.append((label, start, end))
    return normalized


def _load_merged_missed_tags_config() -> dict[str, Any]:
    # Centralized migration lives in the root ConfigManager.
    ConfigManager.migrate_overrides_once()
    section_cfg = ConfigManager(CANONICAL_CONFIG_SECTION).load()
    return section_cfg if isinstance(section_cfg, dict) else {}


def _normalize_missed_tags_config(raw_cfg: dict[str, Any]) -> dict[str, Any]:
    defaults = ConfigManager.deep_merge_dicts({}, ADD_MISSED_TAGS_DEFAULTS)
    if not isinstance(raw_cfg, dict):
        return defaults
    # Canonical keys only: no per-key legacy alias remapping in this module.
    return ConfigManager.deep_merge_dicts(defaults, raw_cfg)


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
    other_cfg = _as_dict(actions_cfg.get("other"))

    default_menu_label = _default_text("ui.menu_label", "Missed Tags")
    default_include_day_segment = _default_bool("date.include_day_segment", True)

    default_base_missed_tag = _default_string_list("actions.base.tags", fallback=["##Missed-Qs"])
    default_action_label_base = _default_text("actions.base.label", "Base")

    default_subset_1_name = _default_text("actions.uworld.label", "UWorld")
    default_subset_1_tag = _default_string_list(
        "actions.uworld.base_tags",
        fallback=[f"{default_base_missed_tag[0]}::UW_Tests"],
    )
    default_test_tag_prefix = _default_text("actions.uworld.default_tag_prefix", "UW_Tests")
    default_test_range_block_size = _default_positive_int("actions.uworld.test_range_block_size", 25)

    default_subset_2_name = _default_text("actions.nbme.label", "NBME")
    default_subset_2_tag = _default_string_list(
        "actions.nbme.base_tags",
        fallback=[f"{default_base_missed_tag[0]}::NBME"],
    )
    default_nbme_tag_prefix = _default_text("actions.nbme.default_tag_prefix", "NBME")

    default_amboss_label = _default_text("actions.amboss.label", "Amboss")
    default_amboss_base_tag = _default_text(
        "actions.amboss.base_tag", f"{default_base_missed_tag[0]}::Amboss"
    )
    default_amboss_blank_behavior = _default_text(
        "actions.amboss.blank_behavior",
        PROMPT_BEHAVIOR["base_plus_rotation"],
    )
    default_amboss_number_style = _default_text(
        "actions.amboss.number_style",
        PROMPT_STYLE["rotation_then_number"],
    )
    default_amboss_remove_from_other_menu = _default_bool("actions.amboss.remove_from_other_menu", True)

    default_action_label_multi_missed = _default_text("actions.multi_missed.label", "2x Missed")
    default_multi_miss_tag = _default_text("actions.multi_missed.tag_segment", "2x")

    default_action_label_key_info = _default_text("actions.key_info.label", "Key Info")
    default_key_tag_base = _default_text("actions.key_info.tag_base", "#Custom::#KEY")

    default_action_label_correct_guess = _default_text("actions.correct_guess.label", "Guessed Correct")
    default_correct_guess_tags = _default_string_list(
        "actions.correct_guess.tags",
        fallback=["#Custom::correct_marked"],
    )
    default_correct_guess_include_rotation = _default_bool("actions.correct_guess.include_rotation", True)
    default_correct_guess_rotation_lowercase = _default_bool("actions.correct_guess.rotation_lowercase", True)
    default_correct_guess_unknown_segment = _default_text("actions.correct_guess.unknown_segment", "unknown")

    default_other_resources = _default_string_list("actions.other.resources", fallback=[])
    default_other_suffix = _default_text("actions.other.tag_suffix", "Other")

    default_rotation_schedule_raw = _default_value("rotation.schedule")
    schedule_raw = rotation_cfg.get("schedule", default_rotation_schedule_raw)
    rotation_schedule = _normalize_rotation_schedule(schedule_raw)
    if not rotation_schedule:
        rotation_schedule = _normalize_rotation_schedule(default_rotation_schedule_raw)

    valid_schedule_policies = {SCHEDULE_POLICY["unknown"], SCHEDULE_POLICY["next"]}
    default_schedule_exhausted_policy = _default_text(
        "rotation.exhausted_policy",
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

    default_rotation_parent_tag_segment = _default_text("rotation.parent_tag_segment", "Rotation")
    default_winter_break_label = _default_text("rotation.winter_break_label", "Winter-break")
    default_post_rotation_label = _default_text("rotation.post_rotation_label", "Dedicated")

    return MissedTagsConfig(
        base_missed_tag=_read_string_list(
            base_cfg,
            "tags",
            fallback=default_base_missed_tag,
        ),
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
        rotation_schedule=rotation_schedule,
        schedule_exhausted_policy=schedule_exhausted_policy,
        missed_tags_menu_label=_read_text(ui_cfg, "menu_label", default_menu_label),
        include_day_segment=_read_bool(date_cfg, "include_day_segment", default_include_day_segment),
        action_label_base=_read_text(base_cfg, "label", default_action_label_base),
        action_label_multi_missed=_read_text(multi_missed_cfg, "label", default_action_label_multi_missed),
        action_label_key_info=_read_text(key_info_cfg, "label", default_action_label_key_info),
        action_label_correct_guess=_read_text(correct_guess_cfg, "label", default_action_label_correct_guess),
        rotation_parent_tag_segment=_read_text(
            rotation_cfg,
            "parent_tag_segment",
            default_rotation_parent_tag_segment,
        ),
        winter_break_tag_label=_read_text(rotation_cfg, "winter_break_label", default_winter_break_label),
        post_rotation_tag_label=_read_text(rotation_cfg, "post_rotation_label", default_post_rotation_label),
        multi_miss_tag=_read_text(multi_missed_cfg, "tag_segment", default_multi_miss_tag),
        default_test_tag_prefix=_read_text(uworld_cfg, "default_tag_prefix", default_test_tag_prefix),
        default_nbme_tag_prefix=_read_text(nbme_cfg, "default_tag_prefix", default_nbme_tag_prefix),
        other_suffix=_read_text(other_cfg, "tag_suffix", default_other_suffix),
        key_tag_base=_read_text(key_info_cfg, "tag_base", default_key_tag_base),
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
        test_range_block_size=_read_positive_int(
            uworld_cfg,
            "test_range_block_size",
            default_test_range_block_size,
        ),
    )


def base_tag_path(cfg: MissedTagsConfig, *parts: str) -> str:
    base = _resolved_base_tag(cfg)
    return "::".join([base, *[p for p in parts if p]])


def _resolved_base_tag(cfg: MissedTagsConfig) -> str:
    if cfg.base_missed_tag:
        base = str(cfg.base_missed_tag[0]).strip()
        if base:
            return base
    defaults = _default_string_list("actions.base.tags", fallback=["##Missed-Qs"])
    return defaults[0]


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
    base = _resolved_base_tag(cfg)
    month_segment = f"{now.strftime('%m')}_{now.strftime('%B')}"
    if cfg.include_day_segment:
        return f"{base}::{now.year}::{month_segment}::{now.strftime('%d')}"
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
    base_tag: str,
    action_key: str,
    title: str,
    prompt_label: str,
    blank_behavior: str,
    number_style: str,
    pad_label: bool = True,
) -> None:
    action_text = f"{label:<24}" if pad_label else label
    action = QAction(action_text, browser)
    action.triggered.connect(
        make_test_prompt_handler(
            browser,
            cfg,
            base_tag,
            action_key=action_key,
            title=title,
            label=prompt_label,
            blank_behavior=blank_behavior,
            number_style=number_style,
        )
    )
    menu.addAction(action)


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
    add_nbme_tag(browser, tag_menu, cfg)
    add_amboss_tag(browser, tag_menu, cfg)
    add_base_plain_action(browser, tag_menu, cfg)

    add_multi_tag(browser, tag_menu, cfg)

    add_correct_guess_action(browser, tag_menu, cfg)

    add_other_resources_actions(browser, tag_menu, cfg)

    if tag_menu.actions():
        menu.addMenu(tag_menu)


def add_nbme_tag(browser, menu, cfg: MissedTagsConfig):
    base_tag = _nbme_base_tag(cfg)
    action = QAction(f"{cfg.subset_2_name:<24}", browser)

    def on_trigger():
        prompt_title = PROMPT_NBME_TITLE
        prompt_label = PROMPT_NBME_LABEL
        form_value, ok = QInputDialog.getText(browser, prompt_title, prompt_label)
        if not ok:
            return

        try:
            form_number = int((form_value or "").strip())
        except ValueError:
            showInfo(MSG_INVALID_INTEGER_TEST_NUMBER)
            return

        if form_number <= 0:
            showInfo(MSG_INVALID_INTEGER_TEST_NUMBER)
            return

        if not _ensure_selected_notes(browser):
            return

        formatted_tag = f"{base_tag}::Form_{form_number}"
        apply_tags_to_selected_notes(browser, [formatted_tag], action_key="nbme_form_prompt", cfg=cfg)

    action.triggered.connect(on_trigger)
    menu.addAction(action)


def add_amboss_tag(browser, menu, cfg: MissedTagsConfig):
    _add_prompt_action(
        browser,
        menu,
        label=cfg.amboss_top_level_name,
        cfg=cfg,
        base_tag=cfg.amboss_base_tag,
        action_key="amboss_test_prompt",
        title=PROMPT_AMBOSS_TITLE,
        prompt_label=PROMPT_DEFAULT_LABEL,
        blank_behavior=cfg.amboss_blank_behavior,
        number_style=cfg.amboss_number_style,
    )


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
        _add_prompt_action(
            browser,
            menu,
            label=set_name,
            cfg=cfg,
            base_tag=base,
            action_key="uw_test_prompt",
            title=PROMPT_UWORLD_TITLE,
            prompt_label=PROMPT_DEFAULT_LABEL,
            blank_behavior=PROMPT_BEHAVIOR["base_only"],
            number_style=PROMPT_STYLE["range_then_number"],
        )


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
            _add_prompt_action(
                browser,
                menu,
                label=label,
                cfg=cfg,
                base_tag=base_tag,
                action_key="true_learn_test_prompt",
                title=PROMPT_TRUE_LEARN_TITLE,
                prompt_label=PROMPT_DEFAULT_LABEL,
                blank_behavior=PROMPT_BEHAVIOR["base_plus_rotation"],
                number_style=PROMPT_STYLE["rotation_then_number"],
                pad_label=False,
            )
            continue

        resource_tag = base_tag_path(cfg, cfg.other_suffix, canonical)
        action = QAction(label, browser)

        def on_click(_, rtag=resource_tag):
            if not _ensure_selected_notes(browser):
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
    blank_behavior: str = PROMPT_BEHAVIOR["base_plus_rotation"],
    number_style: str = PROMPT_STYLE["range_then_number"],
):
    def on_trigger():
        prompt_title = (title or PROMPT_DEFAULT_TITLE).strip() or PROMPT_DEFAULT_TITLE
        prompt_label = (label or PROMPT_DEFAULT_LABEL).strip() or PROMPT_DEFAULT_LABEL
        test_num, ok = QInputDialog.getText(browser, prompt_title, prompt_label)
        if not ok:
            return
        test_num = (test_num or "").strip()
        rot_num_2d, rot_label, _ = get_current_or_next_rotation_meta(cfg)
        rotation_segment = get_formatted_rotation_segment(cfg, rot_num_2d, rot_label)

        if test_num == "":
            if blank_behavior == PROMPT_BEHAVIOR["base_only"]:
                formatted_tag = f"{base_tag}"
            else:
                formatted_tag = f"{base_tag}::{rotation_segment}"
        else:
            try:
                tn = int(test_num)
            except ValueError:
                if blank_behavior == PROMPT_BEHAVIOR["base_only"]:
                    formatted_tag = f"{base_tag}"
                else:
                    formatted_tag = f"{base_tag}::{rotation_segment}"
            else:
                if number_style == PROMPT_STYLE["rotation_then_number"]:
                    formatted_tag = f"{base_tag}::{rotation_segment}::{tn:02d}"
                else:
                    lower = ((tn - 1) // cfg.test_range_block_size) * cfg.test_range_block_size + 1
                    upper = lower + cfg.test_range_block_size - 1
                    range_tag = f"{lower}-{upper}"
                    formatted_tag = f"{base_tag}::{range_tag}::{tn:02d}"

        if not _ensure_selected_notes(browser):
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
        if not _ensure_selected_notes(browser):
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
