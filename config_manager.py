from __future__ import annotations

import copy
import json
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

    MISSED_TAGS_CANONICAL_SECTION = "tag_missed_qid_notes"
    MISSED_TAGS_LEGACY_SECTIONS = (
        "add_missed_tags",
        "tag_selected_notes_config",
        "add_tags",
    )

    ADD_CUSTOM_TAGS_SECTIONS = (
        "add_custom_tags",
        "add_custom_tags_2",
    )
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
    def sanitize_section_override(cls, section: str, payload: Any) -> dict[str, Any]:
        """Normalize/sanitize a section override before persisting it."""
        sanitized = copy.deepcopy(payload) if isinstance(payload, dict) else {}
        if section in cls.ADD_CUSTOM_TAGS_SECTIONS:
            for key in cls.ADD_CUSTOM_TAGS_HARDCODED_OVERRIDE_KEYS:
                sanitized.pop(key, None)
        return sanitized

    @classmethod
    def _sanitize_overrides(cls, overrides: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        migrated = copy.deepcopy(overrides)
        changed = False

        for section in cls.ADD_CUSTOM_TAGS_SECTIONS:
            payload = migrated.get(section)
            if not isinstance(payload, dict):
                continue
            cleaned = cls.sanitize_section_override(section, payload)
            if cleaned != payload:
                migrated[section] = cleaned
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

        cls._migrate_missed_tags_sections(migrated)
        cls._migrate_global_fuzzy_opts_section(migrated)
        cls._migrate_merge_tags_parent_keys(migrated)
        cls._remove_hardcoded_threshold_max_keys(migrated)
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

        changed = sanitized != raw_overrides
        if changed:
            mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, sanitized)

        return sanitized if isinstance(sanitized, dict) else {}, notices, changed

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
            mw.addonManager.writeConfig(self.ROOT_ADDON_NAME, sanitized)
            self.config = copy.deepcopy(sanitized)
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
