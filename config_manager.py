from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw


class ConfigManager:
    """Load and normalize add-on config using root config.json defaults."""

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
    def migrate_legacy_config(cls, current_config: dict) -> dict:
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
        return migrated

    @classmethod
    def load_normalized_config(cls) -> tuple[dict, list[str]]:
        defaults, errors = cls._load_default_config_with_errors()
        current = cls._load_runtime_config_raw()

        migrated = cls.migrate_legacy_config(current)
        normalized = cls.deep_merge_missing(migrated, defaults)

        if normalized != current:
            mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, normalized)

        return normalized if isinstance(normalized, dict) else {}, errors

    @classmethod
    def load_user_overrides(cls) -> dict:
        """Return normalized active config stored by Anki."""
        normalized, _ = cls.load_normalized_config()
        return normalized

    @classmethod
    def load_effective_config(cls) -> tuple[dict, list[str]]:
        return cls.load_normalized_config()

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
        overrides = cls.load_user_overrides()
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

        overrides = cls.load_user_overrides()
        overrides[section] = section_override
        mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, overrides)

    @classmethod
    def clear_section_override(cls, section: str):
        overrides = cls.load_user_overrides()
        if section in overrides:
            del overrides[section]
            mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, overrides)

    @classmethod
    def clear_all_overrides(cls):
        mw.addonManager.writeConfig(cls.ROOT_ADDON_NAME, {})

    def load_config(self):
        """
        Backward-compatible load behavior:
        - addon_name == _Change_notes: full normalized config.
        - addon_name == section key: normalized section config.
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
        """Save config as active config (root) or section-level payload."""
        if not isinstance(new_config, dict):
            raise ValueError("Configuration must be a JSON object.")

        if self.addon_name == self.ROOT_ADDON_NAME:
            mw.addonManager.writeConfig(self.ROOT_ADDON_NAME, new_config)
        else:
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
