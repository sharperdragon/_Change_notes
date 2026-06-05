from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw


class ConfigManager:
    """Load, migrate, and expose add-on configuration state."""

    ROOT_ADDON_NAME = "_Change_notes"

    # Legacy section keys that now map to canonical section keys.
    LEGACY_SECTION_RENAMES = {
        "merge_scheduling_config": "merge_scheduling",
        "Add_img_class": "add_img_class",
        "Add_table_class": "add_table_class",
    }

    MISSED_TAGS_CANONICAL_SECTION = "tag_missed_notes"
    MISSED_TAGS_LEGACY_SECTIONS = (
        "add_missed_tags",
        "tag_selected_notes_config",
        "add_tags",
    )

    CUSTOM_TAGS_CANONICAL_SECTION = "custom_tags_config"
    CUSTOM_TAGS_PRIMARY_CHILD_SECTION = "add_custom_tags_1"
    CUSTOM_TAGS_NUMBERED_CHILD_PATTERN = re.compile(r"^add_custom_tags_(\d+)$")
    CUSTOM_TAGS_LEGACY_CHILD_RENAMES = {
        "add_custom_tags": CUSTOM_TAGS_PRIMARY_CHILD_SECTION,
    }
    ADD_CUSTOM_TAGS_HARDCODED_OVERRIDE_KEYS = (
        "message_no_notes_selected",
        "message_applied_template",
    )
    LEGACY_GLOBAL_FUZZY_OPTS_SECTION = "global_fuzzy_opts"
    MERGE_TAGS_SECTION = "merge_tags_config"
    LEGACY_MERGE_TAGS_PARENTS_KEY = "merge_only_from_parents"
    CANONICAL_MERGE_TAGS_PARENTS_KEY = "merge_only_parents"
    MERGE_IMAGES_SECTION = "merge_images_config"
    HARD_MAX_GLOBAL_FUZZY_KEY = "max_fuzz"
    HARD_MAX_MERGE_TAGS_KEY = "max_fuzzy"
    HARD_MAX_MERGE_IMAGES_KEY = "max_threshold"
    DEPRECATED_MERGE_TAGS_THRESHOLD_KEYS = ("default_fuzzy", "min_fuzzy")
    DEPRECATED_MERGE_IMAGES_THRESHOLD_KEYS = ("default_threshold", "min_threshold")
    DEPRECATED_MERGE_SCHED_THRESHOLD_KEYS = ("default_fuzzy", "min_fuzzy")
    MISSED_TAGS_ROTATION_KEY = "rotation"
    MISSED_TAGS_LEGACY_BLOCK_KEY = "block"
    MISSED_CONTEXT_PARENT_TAG_SEGMENT = "Block"
    LEGACY_MISSED_CONTEXT_PARENT_TAG_SEGMENT = "Rotation"
    MISSED_TAGS_CANONICAL_TOP_LEVEL_KEYS = (
        "ui",
        "date",
        MISSED_TAGS_ROTATION_KEY,
        "actions",
        "runtime",
    )
    CANONICAL_UWORLD_TAG_SEGMENT = "*UW_Tests"

    def __init__(self, addon_name: str, global_config_name: str = None):
        self.addon_name = addon_name
        self.global_config_name = global_config_name
        self.last_load_errors: list[str] = []
        self.config = self.load_config()

    def reload(self):
        self.config = self.load_config()
        return self.config

    def load(self):
        return self.load_config()

    @classmethod
    def _addon_root(cls) -> Path:
        return Path(__file__).resolve().parent

    @classmethod
    def _default_config_path(cls) -> Path:
        return cls._addon_root() / "config.json"

    @classmethod
    def _load_runtime_config_raw(cls) -> dict:
        current = mw.addonManager.getConfig(cls.ROOT_ADDON_NAME) or {}
        return current if isinstance(current, dict) else {}

    @classmethod
    def _custom_tags_section_index(cls, key: Any) -> int | None:
        key_text = str(key).strip() if key is not None else ""
        match = cls.CUSTOM_TAGS_NUMBERED_CHILD_PATTERN.fullmatch(key_text)
        if not match:
            return None
        return int(match.group(1))

    @classmethod
    def is_numbered_custom_tags_section_key(cls, key: Any) -> bool:
        return cls._custom_tags_section_index(key) is not None

    @classmethod
    def is_custom_tags_leaf_section_key(cls, key: Any) -> bool:
        key_text = str(key).strip() if key is not None else ""
        return key_text in cls.CUSTOM_TAGS_LEGACY_CHILD_RENAMES or cls.is_numbered_custom_tags_section_key(
            key_text
        )

    @classmethod
    def ordered_numbered_custom_tags_sections(cls, source: Any) -> list[str]:
        if isinstance(source, dict):
            keys = source.keys()
        elif isinstance(source, (list, tuple, set)):
            keys = source
        else:
            return []

        numbered: list[tuple[int, str]] = []
        for key in keys:
            key_text = str(key).strip() if key is not None else ""
            index = cls._custom_tags_section_index(key_text)
            if index is None:
                continue
            numbered.append((index, key_text))

        numbered.sort(key=lambda item: (item[0], item[1]))
        ordered: list[str] = []
        seen: set[str] = set()
        for _index, key_text in numbered:
            if key_text in seen:
                continue
            seen.add(key_text)
            ordered.append(key_text)
        return ordered

    @classmethod
    def discover_custom_tags_sections(cls, root_cfg: Any = None) -> list[str]:
        """Return available custom-tag section names in display order."""
        if root_cfg is None:
            root_cfg, _ = cls.load_effective_config()

        if not isinstance(root_cfg, dict):
            return [cls.CUSTOM_TAGS_PRIMARY_CHILD_SECTION]

        canonical = root_cfg.get(cls.CUSTOM_TAGS_CANONICAL_SECTION)
        if isinstance(canonical, dict):
            canonical_sections = cls.ordered_numbered_custom_tags_sections(canonical)
            if canonical_sections:
                return canonical_sections
            if isinstance(canonical.get("add_custom_tags"), dict):
                return [cls.CUSTOM_TAGS_PRIMARY_CHILD_SECTION]

        top_level_sections = cls.ordered_numbered_custom_tags_sections(root_cfg)
        if top_level_sections:
            return top_level_sections

        if isinstance(root_cfg.get("add_custom_tags"), dict):
            return [cls.CUSTOM_TAGS_PRIMARY_CHILD_SECTION]

        return [cls.CUSTOM_TAGS_PRIMARY_CHILD_SECTION]

    @classmethod
    def _load_default_config_with_errors(cls) -> tuple[dict, list[str]]:
        path = cls._default_config_path()
        if not path.exists():
            return {}, [f"Missing default config file: {path}"]

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {}, [f"{path.name}: invalid JSON ({exc.msg}) at line {exc.lineno}"]
        except Exception as exc:
            return {}, [f"{path.name}: failed to read defaults ({exc})"]

        if not isinstance(payload, dict):
            return {}, [f"{path.name}: expected top-level JSON object"]

        return payload, []

    @classmethod
    def load_default_config(cls) -> dict:
        defaults, _ = cls._load_default_config_with_errors()
        return defaults

    @classmethod
    def load_raw_overrides(cls) -> dict:
        """Return exactly what Anki stores for this add-on (no defaults merged)."""
        return cls._load_runtime_config_raw()

    @classmethod
    def _sanitize_custom_tags_leaf(cls, payload: Any) -> dict[str, Any]:
        sanitized = copy.deepcopy(payload) if isinstance(payload, dict) else {}
        for key in cls.ADD_CUSTOM_TAGS_HARDCODED_OVERRIDE_KEYS:
            sanitized.pop(key, None)
        return sanitized

    @classmethod
    def sanitize_section_override(cls, section: str, payload: Any) -> dict[str, Any]:
        """Normalize/sanitize a section override before persisting it."""
        sanitized = copy.deepcopy(payload) if isinstance(payload, dict) else {}
        if section == cls.CUSTOM_TAGS_CANONICAL_SECTION:
            out: dict[str, Any] = {}
            if isinstance(sanitized, dict):
                for key, value in sanitized.items():
                    key_text = str(key)
                    if isinstance(value, dict):
                        out[key_text] = cls._sanitize_custom_tags_leaf(value)
                    else:
                        out[key_text] = copy.deepcopy(value)
            return out

        if cls.is_custom_tags_leaf_section_key(section):
            return cls._sanitize_custom_tags_leaf(sanitized)
        return sanitized

    @classmethod
    def _sanitize_overrides(cls, overrides: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        migrated = copy.deepcopy(overrides)
        changed = False

        custom_tags_payload = migrated.get(cls.CUSTOM_TAGS_CANONICAL_SECTION)
        if isinstance(custom_tags_payload, dict):
            cleaned_custom_tags = cls.sanitize_section_override(
                cls.CUSTOM_TAGS_CANONICAL_SECTION,
                custom_tags_payload,
            )
            if cleaned_custom_tags != custom_tags_payload:
                migrated[cls.CUSTOM_TAGS_CANONICAL_SECTION] = cleaned_custom_tags
                changed = True

        return migrated, changed

    @classmethod
    def _merge_legacy_into_canonical(
        cls,
        payload: dict,
        *,
        legacy_key: str,
        canonical_key: str,
    ) -> bool:
        if legacy_key not in payload:
            return False

        changed = False
        legacy_value = payload.pop(legacy_key)
        changed = True

        canonical_value = payload.get(canonical_key)
        if isinstance(legacy_value, dict):
            merged = copy.deepcopy(legacy_value)
            if isinstance(canonical_value, dict):
                # Canonical values win when the same key exists in both payloads.
                merged = cls.deep_merge_dicts(merged, canonical_value)
            if payload.get(canonical_key) != merged:
                payload[canonical_key] = merged
                changed = True
        elif canonical_key not in payload:
            payload[canonical_key] = copy.deepcopy(legacy_value)
            changed = True

        return changed

    @staticmethod
    def _merge_custom_tags_child(existing_value: Any, incoming_value: Any) -> Any:
        """Merge child payloads with existing (canonical) values taking precedence."""
        if isinstance(incoming_value, dict):
            if isinstance(existing_value, dict):
                return ConfigManager.deep_merge_dicts(incoming_value, existing_value)
            return copy.deepcopy(incoming_value)
        return copy.deepcopy(existing_value) if existing_value is not None else copy.deepcopy(incoming_value)

    @classmethod
    def _migrate_custom_tags_sections(cls, payload: dict) -> bool:
        """Canonicalize custom tags config under `custom_tags_config`."""
        changed = False
        canonical_key = cls.CUSTOM_TAGS_CANONICAL_SECTION

        canonical_value = payload.get(canonical_key)
        had_canonical_key = canonical_key in payload
        if isinstance(canonical_value, dict):
            canonical_cfg = copy.deepcopy(canonical_value)
        else:
            canonical_cfg = {}
            if had_canonical_key:
                changed = True

        # Canonicalize legacy child key inside custom_tags_config.
        for legacy_child, canonical_child in cls.CUSTOM_TAGS_LEGACY_CHILD_RENAMES.items():
            if legacy_child not in canonical_cfg:
                continue
            legacy_child_value = canonical_cfg.pop(legacy_child)
            changed = True
            existing_canonical = canonical_cfg.get(canonical_child)
            canonical_cfg[canonical_child] = cls._merge_custom_tags_child(
                existing_canonical,
                legacy_child_value,
            )

        # Move any top-level legacy/numbered sections under custom_tags_config.
        top_level_sections = []
        if "add_custom_tags" in payload:
            top_level_sections.append("add_custom_tags")
        top_level_sections.extend(cls.ordered_numbered_custom_tags_sections(payload))

        for top_level_key in top_level_sections:
            if top_level_key not in payload:
                continue

            if top_level_key == "add_custom_tags":
                child_key = cls.CUSTOM_TAGS_PRIMARY_CHILD_SECTION
            else:
                child_key = top_level_key

            legacy_value = payload.pop(top_level_key)
            changed = True
            existing_child = canonical_cfg.get(child_key)
            canonical_cfg[child_key] = cls._merge_custom_tags_child(existing_child, legacy_value)

        if had_canonical_key or canonical_cfg:
            if payload.get(canonical_key) != canonical_cfg:
                payload[canonical_key] = canonical_cfg
                changed = True

        return changed

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _to_text(value: Any, fallback: str = "") -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text or fallback

    @staticmethod
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

    @staticmethod
    def _to_positive_int(value: Any) -> int | None:
        try:
            parsed = int(str(value).strip())
        except Exception:
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _to_string_list(value: Any, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            out = [str(v).strip() for v in value if v is not None and str(v).strip()]
            return out or list(fallback)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return list(fallback)

    @staticmethod
    def _normalize_tag_segment_for_match(value: Any) -> str:
        normalized = str(value or "").strip().lower()
        return re.sub(r"^[^a-z0-9]+", "", normalized)

    @classmethod
    def _canonicalize_uworld_tag_segment(cls, value: Any) -> str:
        segment = cls._to_text(value, "")
        if not segment:
            return cls.CANONICAL_UWORLD_TAG_SEGMENT
        if cls._normalize_tag_segment_for_match(segment) == "uw_tests":
            return cls.CANONICAL_UWORLD_TAG_SEGMENT
        return segment

    @classmethod
    def _canonicalize_uworld_base_tag_path(cls, tag_path: Any) -> str:
        parts = [str(part).strip() for part in str(tag_path or "").split("::") if str(part).strip()]
        if not parts:
            return cls._to_text(tag_path, "")
        parts[-1] = cls._canonicalize_uworld_tag_segment(parts[-1])
        return "::".join(parts)

    @classmethod
    def _canonical_missed_tags_subset(cls, payload: dict[str, Any]) -> dict[str, Any]:
        subset: dict[str, Any] = {}
        for key in cls.MISSED_TAGS_CANONICAL_TOP_LEVEL_KEYS:
            if key in payload:
                subset[key] = copy.deepcopy(payload[key])
        legacy_rotation = payload.get(cls.MISSED_TAGS_LEGACY_BLOCK_KEY)
        canonical_rotation = subset.get(cls.MISSED_TAGS_ROTATION_KEY)
        if isinstance(legacy_rotation, dict):
            if isinstance(canonical_rotation, dict):
                # Prefer block syntax when overlapping with rotation keys.
                subset[cls.MISSED_TAGS_ROTATION_KEY] = cls.deep_merge_dicts(
                    canonical_rotation, legacy_rotation
                )
            elif cls.MISSED_TAGS_ROTATION_KEY not in subset:
                subset[cls.MISSED_TAGS_ROTATION_KEY] = copy.deepcopy(legacy_rotation)
        return subset

    @classmethod
    def _build_child_tag(cls, primary_tag: str, segment: str) -> str:
        normalized_primary = cls._to_text(primary_tag, "##Missed-Qs")
        normalized_segment = cls._to_text(segment, "")
        if not normalized_segment:
            return normalized_primary
        if normalized_segment == normalized_primary or normalized_segment.startswith(
            f"{normalized_primary}::"
        ):
            return normalized_segment
        return f"{normalized_primary}::{normalized_segment}"

    @classmethod
    def _extract_tag_suffix(cls, tag: str, fallback: str) -> str:
        parts = [part.strip() for part in str(tag).split("::") if part.strip()]
        if not parts:
            return fallback
        return parts[-1]

    @classmethod
    def _resolve_friend_action_tags(
        cls,
        action_cfg: dict[str, Any],
        *,
        primary_tag: str,
        default_child_of_primary: bool,
        default_segments: list[str],
        default_absolute_tags: list[str],
    ) -> list[str]:
        child_of_primary = cls._to_bool(
            action_cfg.get("child_of_primary_missed"),
            default_child_of_primary,
        )
        if child_of_primary:
            segment_source = action_cfg.get("tag_segment")
            if segment_source is None:
                segment_source = action_cfg.get("tag_segments")
            segments = cls._to_string_list(segment_source, default_segments)
            return [cls._build_child_tag(primary_tag, seg) for seg in segments]

        return cls._to_string_list(action_cfg.get("absolute_tags"), default_absolute_tags)

    @classmethod
    def _copy_friend_action_label(
        cls,
        source_action: dict[str, Any],
        target_action: dict[str, Any],
    ) -> None:
        label = cls._to_text(source_action.get("menu_label", source_action.get("label")), "")
        if label:
            target_action["label"] = label

    @classmethod
    def _apply_friend_add_date_context(
        cls,
        *,
        source_action: dict[str, Any],
        action_defaults: dict[str, Any],
        target_action: dict[str, Any],
    ) -> None:
        if "add_missed_date_context" in source_action:
            target_action["add_missed_date_context"] = cls._to_bool(
                source_action.get("add_missed_date_context"),
                True,
            )
            return

        if "add_missed_date_context" in action_defaults:
            target_action["add_missed_date_context"] = cls._to_bool(
                action_defaults.get("add_missed_date_context"),
                True,
            )

    @classmethod
    def _translate_friend_missed_tags_config(cls, legacy_value: dict[str, Any]) -> dict[str, Any]:
        """Map friend-style `add_missed_tags` keys into canonical missed-tags keys."""
        if not isinstance(legacy_value, dict):
            return {}

        translated: dict[str, Any] = {}

        action_defaults = cls._as_dict(legacy_value.get("action_defaults"))
        action_defaults_prompt = cls._as_dict(action_defaults.get("prompt"))
        legacy_actions = cls._as_dict(legacy_value.get("actions"))

        primary_tag = cls._to_text(legacy_value.get("primary_missed_tag"), "##Missed-Qs")
        default_child_of_primary = cls._to_bool(
            action_defaults.get("child_of_primary_missed"),
            True,
        )

        if "menu_label" in legacy_value:
            translated.setdefault("ui", {})["menu_label"] = cls._to_text(
                legacy_value.get("menu_label"),
                "Missed Tags",
            )

        if "include_day_segment" in legacy_value:
            translated.setdefault("date", {})["include_day_segment"] = cls._to_bool(
                legacy_value.get("include_day_segment"),
                True,
            )
        elif "include_day_segment" in action_defaults:
            translated.setdefault("date", {})["include_day_segment"] = cls._to_bool(
                action_defaults.get("include_day_segment"),
                True,
            )

        if "split_weeks" in legacy_value:
            translated.setdefault("date", {})["split_weeks"] = cls._to_bool(
                legacy_value.get("split_weeks"),
                False,
            )
        elif "split_weeks" in action_defaults:
            translated.setdefault("date", {})["split_weeks"] = cls._to_bool(
                action_defaults.get("split_weeks"),
                False,
            )

        translated_actions: dict[str, Any] = {}

        base_cfg = cls._as_dict(legacy_actions.get("base"))
        if base_cfg or "primary_missed_tag" in legacy_value:
            base_action: dict[str, Any] = {}
            if base_cfg:
                cls._copy_friend_action_label(base_cfg, base_action)
                if "menu_display" in base_cfg:
                    base_action["menu_display"] = cls._to_bool(base_cfg.get("menu_display"), True)
                elif "show_in_menu" in base_cfg:
                    base_action["menu_display"] = cls._to_bool(base_cfg.get("show_in_menu"), True)
            base_action["tags"] = cls._resolve_friend_action_tags(
                base_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=False,
                default_segments=[""],
                default_absolute_tags=[primary_tag],
            )
            cls._apply_friend_add_date_context(
                source_action=base_cfg,
                action_defaults=action_defaults,
                target_action=base_action,
            )
            translated_actions["base"] = base_action

        uworld_cfg = cls._as_dict(legacy_actions.get("uworld"))
        if uworld_cfg:
            uworld_action: dict[str, Any] = {}
            cls._copy_friend_action_label(uworld_cfg, uworld_action)
            uworld_tags = cls._resolve_friend_action_tags(
                uworld_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=default_child_of_primary,
                default_segments=["*UW_Tests"],
                default_absolute_tags=[f"{primary_tag}::*UW_Tests"],
            )
            uworld_tags = [cls._canonicalize_uworld_base_tag_path(tag) for tag in uworld_tags]
            uworld_action["base_tags"] = uworld_tags
            configured_default_prefix = cls._to_text(uworld_cfg.get("default_tag_prefix"), "")
            if configured_default_prefix:
                uworld_action["default_tag_prefix"] = cls._canonicalize_uworld_tag_segment(
                    configured_default_prefix
                )
            else:
                extracted_suffix = cls._extract_tag_suffix(uworld_tags[0], "*UW_Tests")
                uworld_action["default_tag_prefix"] = cls._canonicalize_uworld_tag_segment(extracted_suffix)

            uworld_prompt = cls._as_dict(uworld_cfg.get("prompt"))
            parent_range_block_size = cls._to_positive_int(
                uworld_prompt.get(
                    "parent_range_block_size",
                    uworld_cfg.get("test_parent_range_block_size"),
                )
            )
            range_block_size = cls._to_positive_int(
                uworld_prompt.get(
                    "range_block_size",
                    uworld_cfg.get(
                        "test_range_block_size",
                        action_defaults_prompt.get("range_block_size"),
                    ),
                )
            )
            if parent_range_block_size is None:
                parent_range_block_size = range_block_size
            if parent_range_block_size is not None:
                uworld_action["test_parent_range_block_size"] = parent_range_block_size
            if range_block_size is not None:
                uworld_action["test_range_block_size"] = range_block_size

            cls._apply_friend_add_date_context(
                source_action=uworld_cfg,
                action_defaults=action_defaults,
                target_action=uworld_action,
            )
            translated_actions["uworld"] = uworld_action

        nbme_cfg = cls._as_dict(legacy_actions.get("nbme"))
        if nbme_cfg:
            nbme_action: dict[str, Any] = {}
            cls._copy_friend_action_label(nbme_cfg, nbme_action)
            nbme_tags = cls._resolve_friend_action_tags(
                nbme_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=default_child_of_primary,
                default_segments=["NBME"],
                default_absolute_tags=[f"{primary_tag}::NBME"],
            )
            nbme_action["base_tags"] = nbme_tags
            nbme_action["default_tag_prefix"] = cls._to_text(
                nbme_cfg.get("default_tag_prefix"),
                cls._extract_tag_suffix(nbme_tags[0], "NBME"),
            )
            cls._apply_friend_add_date_context(
                source_action=nbme_cfg,
                action_defaults=action_defaults,
                target_action=nbme_action,
            )
            translated_actions["nbme"] = nbme_action

        amboss_cfg = cls._as_dict(legacy_actions.get("amboss"))
        if amboss_cfg:
            amboss_action: dict[str, Any] = {}
            cls._copy_friend_action_label(amboss_cfg, amboss_action)
            amboss_tags = cls._resolve_friend_action_tags(
                amboss_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=default_child_of_primary,
                default_segments=["Amboss"],
                default_absolute_tags=[f"{primary_tag}::Amboss"],
            )
            if amboss_tags:
                amboss_action["base_tag"] = amboss_tags[0]

            amboss_prompt = cls._as_dict(amboss_cfg.get("prompt"))
            number_style = cls._to_text(
                amboss_prompt.get("number_style", amboss_cfg.get("number_style")),
                "",
            )
            if number_style in {"rotation_then_number", "range_then_number", "number_only"}:
                amboss_action["number_style"] = number_style

            if "blank_behavior" in amboss_cfg:
                amboss_action["blank_behavior"] = cls._to_text(
                    amboss_cfg.get("blank_behavior"),
                    "base_plus_rotation",
                )
            elif "kind" in amboss_prompt:
                # Friend-schema prompts fall back to base tag when blank/non-numeric.
                amboss_action["blank_behavior"] = "base_only"

            if "remove_from_other_menu" in amboss_cfg:
                amboss_action["remove_from_other_menu"] = cls._to_bool(
                    amboss_cfg.get("remove_from_other_menu"),
                    True,
                )

            cls._apply_friend_add_date_context(
                source_action=amboss_cfg,
                action_defaults=action_defaults,
                target_action=amboss_action,
            )
            translated_actions["amboss"] = amboss_action

        multi_missed_cfg = cls._as_dict(legacy_actions.get("multi_missed"))
        if multi_missed_cfg:
            multi_action: dict[str, Any] = {}
            cls._copy_friend_action_label(multi_missed_cfg, multi_action)
            multi_tags = cls._resolve_friend_action_tags(
                multi_missed_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=default_child_of_primary,
                default_segments=["2x"],
                default_absolute_tags=[f"{primary_tag}::2x"],
            )
            multi_action["tags"] = multi_tags
            if "tag_segment" in multi_missed_cfg:
                multi_action["tag_segment"] = cls._to_text(
                    multi_missed_cfg.get("tag_segment"),
                    "2x",
                )
            else:
                resolved_segment = cls._to_text(multi_tags[0], "2x") if multi_tags else "2x"
                primary_prefix = f"{primary_tag}::"
                if resolved_segment.startswith(primary_prefix):
                    resolved_segment = resolved_segment[len(primary_prefix) :]
                elif resolved_segment == primary_tag:
                    resolved_segment = ""
                multi_action["tag_segment"] = resolved_segment or "2x"

            cls._apply_friend_add_date_context(
                source_action=multi_missed_cfg,
                action_defaults=action_defaults,
                target_action=multi_action,
            )
            translated_actions["multi_missed"] = multi_action

        correct_guess_cfg = cls._as_dict(legacy_actions.get("correct_guess"))
        if correct_guess_cfg:
            correct_guess_action: dict[str, Any] = {}
            cls._copy_friend_action_label(correct_guess_cfg, correct_guess_action)
            correct_guess_action["tags"] = cls._resolve_friend_action_tags(
                correct_guess_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=False,
                default_segments=["correct_marked"],
                default_absolute_tags=["#Custom::correct_marked"],
            )
            cls._apply_friend_add_date_context(
                source_action=correct_guess_cfg,
                action_defaults=action_defaults,
                target_action=correct_guess_action,
            )
            translated_actions["correct_guess"] = correct_guess_action

        uw_correct_missed_cfg = cls._as_dict(legacy_actions.get("correct_tag_missed"))
        if not uw_correct_missed_cfg:
            uw_correct_missed_cfg = cls._as_dict(legacy_actions.get("uw_correct_missed"))
        if uw_correct_missed_cfg:
            uw_correct_missed_action: dict[str, Any] = {}
            cls._copy_friend_action_label(uw_correct_missed_cfg, uw_correct_missed_action)
            uw_correct_tags = cls._resolve_friend_action_tags(
                uw_correct_missed_cfg,
                primary_tag=primary_tag,
                default_child_of_primary=True,
                default_segments=["correct_marked"],
                default_absolute_tags=[f"{primary_tag}::correct_marked"],
            )
            resolved_tag = cls._to_text(
                uw_correct_tags[0] if uw_correct_tags else f"{primary_tag}::correct_marked",
                f"{primary_tag}::correct_marked",
            )
            primary_prefix = f"{primary_tag}::"
            if resolved_tag.startswith(primary_prefix):
                uw_correct_missed_action["tag_segment"] = resolved_tag[len(primary_prefix) :]
                uw_correct_missed_action["child_of_primary_missed"] = True
            else:
                uw_correct_missed_action["absolute_tags"] = [resolved_tag]
                uw_correct_missed_action["child_of_primary_missed"] = False
            uw_correct_missed_action["tags"] = uw_correct_tags

            cls._apply_friend_add_date_context(
                source_action=uw_correct_missed_cfg,
                action_defaults=action_defaults,
                target_action=uw_correct_missed_action,
            )
            translated_actions["correct_tag_missed"] = uw_correct_missed_action

        other_cfg = cls._as_dict(legacy_actions.get("other"))
        if other_cfg:
            other_action: dict[str, Any] = {}
            other_tagging = cls._as_dict(other_cfg.get("tagging"))

            resources: list[str] = []
            translated_other_actions: list[dict[str, Any]] = []
            legacy_other_actions = other_cfg.get("actions")
            if isinstance(legacy_other_actions, list):
                for item in legacy_other_actions:
                    if not isinstance(item, dict):
                        continue
                    tag_segment = cls._to_text(item.get("tag_segment"), "")
                    if tag_segment:
                        resources.append(tag_segment)
                    translated_item: dict[str, Any] = {}
                    cls._copy_friend_action_label(item, translated_item)
                    for key in (
                        "child_of_primary_missed",
                        "absolute_tags",
                        "tag_segment",
                        "tag_segments",
                        "add_missed_date_context",
                    ):
                        if key in item:
                            translated_item[key] = copy.deepcopy(item[key])
                    prompt_cfg = cls._as_dict(item.get("prompt"))
                    if prompt_cfg:
                        translated_item["prompt"] = copy.deepcopy(prompt_cfg)
                    if translated_item:
                        translated_other_actions.append(translated_item)
            if not resources:
                resources = cls._to_string_list(other_cfg.get("resources"), [])
            if resources:
                other_action["resources"] = resources
            if translated_other_actions:
                other_action["actions"] = translated_other_actions

            if cls._to_bool(other_tagging.get("tag_segment_group"), True):
                other_action["tag_suffix"] = cls._to_text(
                    other_tagging.get("group_segment"),
                    "Other",
                )
            elif "tag_suffix" in other_cfg:
                other_action["tag_suffix"] = cls._to_text(other_cfg.get("tag_suffix"), "Other")

            if "add_missed_date_context" in other_tagging:
                other_action["add_missed_date_context"] = cls._to_bool(
                    other_tagging.get("add_missed_date_context"),
                    True,
                )
            elif "add_missed_date_context" in action_defaults:
                other_action["add_missed_date_context"] = cls._to_bool(
                    action_defaults.get("add_missed_date_context"),
                    True,
                )

            if other_action:
                translated_actions["other"] = other_action

        if translated_actions:
            translated["actions"] = translated_actions

        return translated

    @classmethod
    def _migrate_missed_tags_sections(cls, payload: dict) -> bool:
        changed = False
        merged_legacy: dict = {}

        for legacy_key in cls.MISSED_TAGS_LEGACY_SECTIONS:
            if legacy_key not in payload:
                continue

            legacy_value = payload.pop(legacy_key)
            changed = True
            if isinstance(legacy_value, dict):
                if legacy_key == "add_missed_tags":
                    canonical_subset = cls._canonical_missed_tags_subset(legacy_value)
                    translated_friend_cfg = cls._translate_friend_missed_tags_config(legacy_value)
                    merged_value = cls.deep_merge_dicts(canonical_subset, translated_friend_cfg)
                    merged_legacy = cls.deep_merge_dicts(merged_legacy, merged_value)
                else:
                    merged_legacy = cls.deep_merge_dicts(merged_legacy, legacy_value)

        if not merged_legacy:
            return changed

        canonical_value = payload.get(cls.MISSED_TAGS_CANONICAL_SECTION)
        if isinstance(canonical_value, dict):
            # Canonical values win when overlapping with merged legacy values.
            merged_canonical = cls.deep_merge_dicts(merged_legacy, canonical_value)
        else:
            merged_canonical = merged_legacy

        if payload.get(cls.MISSED_TAGS_CANONICAL_SECTION) != merged_canonical:
            payload[cls.MISSED_TAGS_CANONICAL_SECTION] = merged_canonical
            changed = True

        return changed

    @classmethod
    def _migrate_missed_tags_rotation_key(cls, payload: dict[str, Any]) -> bool:
        """Canonicalize missed-tags rotation config key from legacy `block`."""
        section = payload.get(cls.MISSED_TAGS_CANONICAL_SECTION)
        if not isinstance(section, dict):
            return False

        legacy_key = cls.MISSED_TAGS_LEGACY_BLOCK_KEY
        canonical_key = cls.MISSED_TAGS_ROTATION_KEY
        changed = False
        if legacy_key in section:
            changed = True
            legacy_value = section.pop(legacy_key)
            canonical_value = section.get(canonical_key)
            if isinstance(legacy_value, dict):
                if isinstance(canonical_value, dict):
                    # Prefer block syntax when both keys are present.
                    section[canonical_key] = cls.deep_merge_dicts(canonical_value, legacy_value)
                elif canonical_key not in section:
                    section[canonical_key] = copy.deepcopy(legacy_value)
            elif canonical_key not in section:
                section[canonical_key] = copy.deepcopy(legacy_value)

        rotation_cfg = section.get(canonical_key)
        if not isinstance(rotation_cfg, dict):
            return changed

        parent_tag_segment = cls._to_text(rotation_cfg.get("parent_tag_segment"), "")
        parent_tag_parts = [part.strip() for part in parent_tag_segment.split("::") if part.strip()]
        final_parent_tag_segment = parent_tag_parts[-1] if parent_tag_parts else parent_tag_segment
        legacy_parent_segment = cls._normalize_tag_segment_for_match(
            cls.LEGACY_MISSED_CONTEXT_PARENT_TAG_SEGMENT
        )
        if cls._normalize_tag_segment_for_match(final_parent_tag_segment) == legacy_parent_segment:
            rotation_cfg["parent_tag_segment"] = cls.MISSED_CONTEXT_PARENT_TAG_SEGMENT
            changed = True

        if "winter_break_label" in rotation_cfg:
            rotation_cfg.pop("winter_break_label", None)
            changed = True
        if "post_rotation_label" in rotation_cfg:
            rotation_cfg.pop("post_rotation_label", None)
            changed = True

        schedule = rotation_cfg.get("schedule")
        if isinstance(schedule, list):
            normalized_schedule: list[Any] = []
            schedule_changed = False
            for item in schedule:
                if not isinstance(item, dict):
                    normalized_schedule.append(copy.deepcopy(item))
                    continue

                normalized_item = copy.deepcopy(item)
                if "segment_label" not in normalized_item and "label" in normalized_item:
                    normalized_item["segment_label"] = normalized_item.get("label")
                    schedule_changed = True
                if "label" in normalized_item:
                    normalized_item.pop("label", None)
                    schedule_changed = True
                normalized_schedule.append(normalized_item)

            if schedule_changed:
                rotation_cfg["schedule"] = normalized_schedule
                changed = True

        return changed

    @classmethod
    def _normalize_missed_tags_uworld_values(cls, payload: dict[str, Any]) -> bool:
        section = payload.get(cls.MISSED_TAGS_CANONICAL_SECTION)
        if not isinstance(section, dict):
            return False

        actions = section.get("actions")
        if not isinstance(actions, dict):
            return False

        changed = False

        base = actions.get("base")
        if isinstance(base, dict):
            if "menu_display" not in base and "show_in_menu" in base:
                base["menu_display"] = cls._to_bool(base.get("show_in_menu"), True)
                changed = True
            if "show_in_menu" in base:
                del base["show_in_menu"]
                changed = True

        # Canonicalize action key name for the combined correct-tag action.
        if "uw_correct_missed" in actions:
            legacy_action = actions.get("uw_correct_missed")
            if "correct_tag_missed" not in actions and isinstance(legacy_action, dict):
                actions["correct_tag_missed"] = legacy_action
                changed = True
            del actions["uw_correct_missed"]
            changed = True

        uworld = actions.get("uworld")
        if not isinstance(uworld, dict):
            return changed

        if "base_tags" in uworld:
            original_base_tags = uworld.get("base_tags")
            normalized_base_tags = [
                cls._canonicalize_uworld_base_tag_path(tag)
                for tag in cls._to_string_list(original_base_tags, fallback=[])
            ]
            if normalized_base_tags != cls._to_string_list(original_base_tags, fallback=[]):
                uworld["base_tags"] = normalized_base_tags
                changed = True

        if "default_tag_prefix" in uworld:
            original_prefix = cls._to_text(uworld.get("default_tag_prefix"), "")
            if cls._normalize_tag_segment_for_match(original_prefix) == "uw_tests":
                if original_prefix != cls.CANONICAL_UWORLD_TAG_SEGMENT:
                    uworld["default_tag_prefix"] = cls.CANONICAL_UWORLD_TAG_SEGMENT
                    changed = True

        return changed

    @classmethod
    def _migrate_global_fuzzy_opts_section(cls, payload: dict) -> bool:
        """Move legacy root `global_fuzzy_opts` into `global_config.fuzzy_opts`."""
        legacy_key = cls.LEGACY_GLOBAL_FUZZY_OPTS_SECTION
        if legacy_key not in payload:
            return False

        changed = False
        legacy_value = payload.pop(legacy_key)
        changed = True

        if not isinstance(legacy_value, dict):
            return changed

        global_cfg = payload.get("global_config")
        if not isinstance(global_cfg, dict):
            global_cfg = {}
            payload["global_config"] = global_cfg
            changed = True

        existing_fuzzy_opts = global_cfg.get("fuzzy_opts")
        if isinstance(existing_fuzzy_opts, dict):
            # Canonical nested values win when keys overlap.
            merged_fuzzy_opts = cls.deep_merge_dicts(legacy_value, existing_fuzzy_opts)
        else:
            merged_fuzzy_opts = copy.deepcopy(legacy_value)

        if global_cfg.get("fuzzy_opts") != merged_fuzzy_opts:
            global_cfg["fuzzy_opts"] = merged_fuzzy_opts
            changed = True

        return changed

    @classmethod
    def _migrate_merge_tags_parent_keys(cls, payload: dict) -> bool:
        """Normalize merge_tags parent list to `merge_only_parents` only."""
        section = payload.get(cls.MERGE_TAGS_SECTION)
        if not isinstance(section, dict):
            return False

        legacy_key = cls.LEGACY_MERGE_TAGS_PARENTS_KEY
        canonical_key = cls.CANONICAL_MERGE_TAGS_PARENTS_KEY
        if legacy_key not in section:
            return False

        changed = True
        legacy_value = section.pop(legacy_key)

        if canonical_key not in section:
            section[canonical_key] = copy.deepcopy(legacy_value)

        return changed

    @classmethod
    def _remove_hardcoded_threshold_max_keys(cls, payload: dict) -> bool:
        """Drop max-threshold keys that are now hardcoded to 1.0."""
        changed = False

        global_cfg = payload.get("global_config")
        if isinstance(global_cfg, dict):
            fuzzy_opts = global_cfg.get("fuzzy_opts")
            if isinstance(fuzzy_opts, dict) and cls.HARD_MAX_GLOBAL_FUZZY_KEY in fuzzy_opts:
                fuzzy_opts.pop(cls.HARD_MAX_GLOBAL_FUZZY_KEY, None)
                changed = True

        merge_tags_cfg = payload.get(cls.MERGE_TAGS_SECTION)
        if isinstance(merge_tags_cfg, dict) and cls.HARD_MAX_MERGE_TAGS_KEY in merge_tags_cfg:
            merge_tags_cfg.pop(cls.HARD_MAX_MERGE_TAGS_KEY, None)
            changed = True

        merge_images_cfg = payload.get(cls.MERGE_IMAGES_SECTION)
        if isinstance(merge_images_cfg, dict) and cls.HARD_MAX_MERGE_IMAGES_KEY in merge_images_cfg:
            merge_images_cfg.pop(cls.HARD_MAX_MERGE_IMAGES_KEY, None)
            changed = True

        return changed

    @classmethod
    def _remove_deprecated_per_section_threshold_keys(cls, payload: dict) -> bool:
        """Drop legacy per-section fuzzy threshold keys in favor of global_config.fuzzy_opts."""
        changed = False

        merge_tags_cfg = payload.get(cls.MERGE_TAGS_SECTION)
        if isinstance(merge_tags_cfg, dict):
            for key in cls.DEPRECATED_MERGE_TAGS_THRESHOLD_KEYS:
                if key in merge_tags_cfg:
                    merge_tags_cfg.pop(key, None)
                    changed = True

        merge_images_cfg = payload.get(cls.MERGE_IMAGES_SECTION)
        if isinstance(merge_images_cfg, dict):
            for key in cls.DEPRECATED_MERGE_IMAGES_THRESHOLD_KEYS:
                if key in merge_images_cfg:
                    merge_images_cfg.pop(key, None)
                    changed = True

        merge_sched_cfg = payload.get("merge_scheduling")
        if isinstance(merge_sched_cfg, dict):
            for key in cls.DEPRECATED_MERGE_SCHED_THRESHOLD_KEYS:
                if key in merge_sched_cfg:
                    merge_sched_cfg.pop(key, None)
                    changed = True

        return changed

    @classmethod
    def _prune_value_against_default(cls, value: Any, default_value: Any, missing: Any) -> Any:
        """Return `missing` when value is fully redundant vs defaults."""

        def _prune(inner_value: Any, inner_default: Any) -> Any:
            if isinstance(inner_value, dict) and isinstance(inner_default, dict):
                pruned: dict[str, Any] = {}
                for key, child_value in inner_value.items():
                    if key in inner_default:
                        child_pruned = _prune(child_value, inner_default[key])
                        if child_pruned is not missing:
                            pruned[key] = child_pruned
                    else:
                        pruned[key] = copy.deepcopy(child_value)
                return pruned if pruned else missing

            return missing if inner_value == inner_default else copy.deepcopy(inner_value)

        return _prune(value, default_value)

    @classmethod
    def prune_redundant_overrides(cls, overrides: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Drop override keys that match shipped defaults exactly."""
        if not isinstance(overrides, dict):
            return {}, False

        defaults = cls.load_default_config()
        if not isinstance(defaults, dict) or not defaults:
            return copy.deepcopy(overrides), False

        pruned: dict[str, Any] = {}
        changed = False
        sentinel = object()

        for key, value in overrides.items():
            default_value = defaults.get(key, sentinel)
            if default_value is sentinel:
                pruned[key] = copy.deepcopy(value)
                continue

            pruned_value = cls._prune_value_against_default(value, default_value, sentinel)
            if pruned_value is sentinel:
                changed = True
                continue

            if pruned_value != value:
                changed = True
            pruned[key] = pruned_value

        if pruned != overrides:
            changed = True

        return pruned, changed

    @classmethod
    def migrate_legacy_config(cls, current_config: dict) -> dict:
        """Return a migrated override payload using canonical section keys."""
        if not isinstance(current_config, dict):
            return {}

        migrated = copy.deepcopy(current_config)
        for legacy_key, canonical_key in cls.LEGACY_SECTION_RENAMES.items():
            cls._merge_legacy_into_canonical(
                migrated,
                legacy_key=legacy_key,
                canonical_key=canonical_key,
            )

        cls._migrate_custom_tags_sections(migrated)
        cls._migrate_missed_tags_sections(migrated)
        cls._migrate_missed_tags_rotation_key(migrated)
        cls._normalize_missed_tags_uworld_values(migrated)
        cls._migrate_global_fuzzy_opts_section(migrated)
        cls._migrate_merge_tags_parent_keys(migrated)
        cls._remove_hardcoded_threshold_max_keys(migrated)
        cls._remove_deprecated_per_section_threshold_keys(migrated)
        return migrated

    @classmethod
    def migrate_overrides_once(cls) -> tuple[dict, list[str], bool]:
        """Migrate/sanitize stored overrides and persist only if changes are needed."""
        raw_overrides = cls.load_raw_overrides()
        migrated = cls.migrate_legacy_config(raw_overrides)

        notices: list[str] = []
        if migrated != raw_overrides:
            notices.append("Migrated legacy section keys to canonical keys.")

        sanitized, sanitized_changed = cls._sanitize_overrides(migrated)
        if sanitized_changed:
            notices.append("Removed deprecated add_custom_tags message override keys.")

        pruned, pruned_changed = cls.prune_redundant_overrides(sanitized)
        if pruned_changed:
            notices.append("Pruned redundant override keys that matched defaults.")

        changed = pruned != raw_overrides
        if changed:
            mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, pruned)

        return pruned if isinstance(pruned, dict) else {}, notices, changed

    @classmethod
    def load_effective_config(cls) -> tuple[dict, list[str]]:
        """Return migrated overrides merged with shipped defaults."""
        migrated_overrides, _, _ = cls.migrate_overrides_once()
        defaults, errors = cls._load_default_config_with_errors()
        effective = cls.deep_merge_missing(migrated_overrides, defaults)
        return effective if isinstance(effective, dict) else {}, errors

    @classmethod
    def load_normalized_config(cls) -> tuple[dict, list[str]]:
        """Backward-compatible alias for effective config loading."""
        return cls.load_effective_config()

    @classmethod
    def load_user_overrides(cls) -> dict:
        """Deprecated alias. Prefer `load_raw_overrides()` for stored overrides."""
        return cls.load_raw_overrides()

    @classmethod
    def list_sections(cls) -> list[str]:
        effective, _ = cls.load_effective_config()
        return sorted(k for k in effective.keys() if isinstance(k, str))

    @classmethod
    def get_default_section(cls, section: str) -> dict:
        defaults = cls.load_default_config()
        data = defaults.get(section, {})
        return copy.deepcopy(data) if isinstance(data, dict) else {}

    @classmethod
    def get_override_section(cls, section: str) -> dict:
        overrides = cls.load_raw_overrides()
        data = overrides.get(section, {})
        return copy.deepcopy(data) if isinstance(data, dict) else {}

    @classmethod
    def get_effective_section(cls, section: str) -> dict:
        effective, _ = cls.load_effective_config()
        data = effective.get(section, {})
        return copy.deepcopy(data) if isinstance(data, dict) else {}

    @classmethod
    def get_effective_section_with_aliases(
        cls,
        section: str,
        aliases: list[str] | tuple[str, ...] = (),
    ) -> dict:
        effective, _ = cls.load_effective_config()
        for key in (section, *aliases):
            data = effective.get(key)
            if isinstance(data, dict):
                return copy.deepcopy(data)
        return {}

    @classmethod
    def save_section_override(cls, section: str, section_override: dict):
        if not isinstance(section_override, dict):
            raise ValueError(f"Section override for '{section}' must be a JSON object.")

        overrides, _, _ = cls.migrate_overrides_once()
        updated = copy.deepcopy(overrides)
        updated[section] = cls.sanitize_section_override(section, section_override)
        updated, _ = cls.prune_redundant_overrides(updated)

        if updated != overrides:
            mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, updated)

    @classmethod
    def clear_section_override(cls, section: str):
        overrides, _, _ = cls.migrate_overrides_once()
        if section in overrides:
            updated = copy.deepcopy(overrides)
            del updated[section]
            mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, updated)

    @classmethod
    def clear_all_overrides(cls):
        mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, {})

    def load_config(self):
        """
        Backward-compatible load behavior:
        - addon_name == _Change_notes: full effective config.
        - addon_name == section key: effective section config.
        - with global_config_name: deep-merge global section + target section.
        """
        effective, errors = self.load_effective_config()
        self.last_load_errors = errors

        if self.addon_name == self.ROOT_ADDON_NAME:
            if self.global_config_name:
                target = effective.get(self.global_config_name, {})
                return copy.deepcopy(target) if isinstance(target, dict) else {}
            return effective

        section_data = effective.get(self.addon_name, {})
        section_dict = copy.deepcopy(section_data) if isinstance(section_data, dict) else {}

        if self.global_config_name:
            global_section = effective.get(self.global_config_name, {})
            global_dict = copy.deepcopy(global_section) if isinstance(global_section, dict) else {}
            return self.deep_merge_dicts(global_dict, section_dict)

        return section_dict

    def save_config(self, new_config):
        """Save config as root override payload or section-level override payload."""
        if not isinstance(new_config, dict):
            raise ValueError("Configuration must be a JSON object.")

        if self.addon_name == self.ROOT_ADDON_NAME:
            migrated = self.migrate_legacy_config(new_config)
            sanitized, _ = self._sanitize_overrides(migrated)
            pruned, _ = self.prune_redundant_overrides(sanitized)
            mw.addonManager.writeConfig(self.ROOT_ADDON_NAME, pruned)
            self.config = copy.deepcopy(pruned)
            return

        self.save_section_override(self.addon_name, new_config)
        self.config = copy.deepcopy(new_config)

    def get(self, key, default=None):
        if not isinstance(self.config, dict):
            return default
        return self.config.get(key, default)

    def set(self, key, value):
        if not isinstance(self.config, dict):
            self.config = {}
        self.config[key] = value
        self.save_config(self.config)

    @staticmethod
    def deep_merge_dicts(base: dict, override: dict) -> dict:
        """Recursively merge dictionaries. Lists/scalars are replaced."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = ConfigManager.deep_merge_dicts(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    @staticmethod
    def deep_merge_missing(user_cfg: Any, default_cfg: Any) -> Any:
        """Recursively add only missing keys from defaults into user config."""
        if not isinstance(default_cfg, dict):
            return copy.deepcopy(user_cfg)

        if not isinstance(user_cfg, dict):
            return copy.deepcopy(default_cfg)

        result = copy.deepcopy(user_cfg)
        for key, default_value in default_cfg.items():
            if key not in result:
                result[key] = copy.deepcopy(default_value)
            elif isinstance(default_value, dict) and isinstance(result.get(key), dict):
                result[key] = ConfigManager.deep_merge_missing(result[key], default_value)

        return result
