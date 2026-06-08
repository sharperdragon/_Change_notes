# pyright: reportMissingImports=false
from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .missed_tags_constants import (
    CANONICAL_UWORLD_TAG_SEGMENT,
    DEFAULT_PARENT_RANGE_PAD_WIDTH,
    EXCLUDE_AUTO_MISS,
    INCLUDE_UWORLD_CHILD_RANGE_SEGMENT,
    LEGACY_MISSED_CONTEXT_PARENT_TAG_SEGMENT,
    MISSED_CONTEXT_PARENT_TAG_SEGMENT,
    SCHEDULE_POLICY,
    UWORLD_CORRECT_MISSED_SOURCE_OPTIONS,
)
from .shared.defaults import ADD_MISSED_TAGS_DEFAULTS

if TYPE_CHECKING:
    from .missed_tags_config import MissedTagsConfig

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


def _normalize_missed_context_parent_tag_segment(
    value: Any,
    fallback: str = MISSED_CONTEXT_PARENT_TAG_SEGMENT,
) -> str:
    segment = str(value or "").strip() or fallback
    segment_parts = [part.strip() for part in segment.split("::") if part.strip()]
    final_segment = segment_parts[-1] if segment_parts else segment
    if _normalize_tag_segment_for_match(final_segment) == _normalize_tag_segment_for_match(
        LEGACY_MISSED_CONTEXT_PARENT_TAG_SEGMENT
    ):
        return MISSED_CONTEXT_PARENT_TAG_SEGMENT
    return segment


def _build_child_tag(primary_tag: str, segment: str) -> str:
    normalized_primary = str(primary_tag or "").strip() or "##Missed-Qs"
    normalized_segment = str(segment or "").strip()
    if not normalized_segment:
        return normalized_primary
    if normalized_segment == normalized_primary or normalized_segment.startswith(f"{normalized_primary}::"):
        return normalized_segment
    return f"{normalized_primary}::{normalized_segment}"


def _extract_tag_suffix(tag: Any, fallback: str) -> str:
    parts = [part.strip() for part in str(tag or "").split("::") if part.strip()]
    return parts[-1] if parts else fallback


def _append_tag_segment(tag: str, segment: str) -> str:
    base = str(tag or "").strip()
    suffix = str(segment or "").strip()
    if not base or not suffix:
        return base
    parts = [part.strip() for part in base.split("::") if part.strip()]
    if parts and parts[-1] == suffix:
        return base
    return f"{base}::{suffix}"


def base_tag_path(cfg: MissedTagsConfig, *parts: str) -> str:
    base = _resolved_base_tag(cfg)
    return "::".join([base, *[p for p in parts if p]])


def _resolved_base_tag(cfg: MissedTagsConfig) -> str:
    if cfg.base_missed_tag:
        base = str(cfg.base_missed_tag[0]).strip()
        if base:
            return base
    defaults = ADD_MISSED_TAGS_DEFAULTS.get("actions", {}).get("base", {}).get("tags", ["##Missed-Qs"])
    if isinstance(defaults, list) and defaults:
        default_base = str(defaults[0]).strip()
        if default_base:
            return default_base
    return "##Missed-Qs"


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
    parent_segment = _normalize_missed_context_parent_tag_segment(cfg.rotation_parent_tag_segment)
    return base_tag_path(cfg, parent_segment, segment), warning


def _should_add_missed_date_context(cfg: MissedTagsConfig, action_key: str) -> bool:
    if action_key in cfg.action_add_missed_date_context:
        return bool(cfg.action_add_missed_date_context[action_key])
    return action_key not in EXCLUDE_AUTO_MISS
