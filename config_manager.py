from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw


class ConfigManager:
    """Load effective config from `configs/` defaults + profile overrides."""

    ROOT_ADDON_NAME = "_Change_notes"

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
    def _configs_dir(cls) -> Path:
        return cls._addon_root() / "configs"

    @classmethod
    def _legacy_config_path(cls) -> Path:
        return cls._addon_root() / "config.json"

    @classmethod
    def _read_json_file(cls, path: Path) -> tuple[Any, str | None]:
        """Read JSON, tolerating historical fragment format in configs/*.json."""
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}, None

        try:
            return json.loads(raw), None
        except json.JSONDecodeError as exc:
            try:
                wrapped = "{\n" + raw + "\n}"
                return json.loads(wrapped), f"{path.name}: wrapped legacy fragment ({exc.msg})"
            except json.JSONDecodeError as wrapped_exc:
                raise ValueError(f"{path.name}: invalid JSON ({wrapped_exc.msg}) at line {wrapped_exc.lineno}") from wrapped_exc

    @classmethod
    def _normalize_section_payload(cls, section_hint: str, payload: Any) -> tuple[str, dict]:
        if not isinstance(payload, dict):
            raise ValueError(f"{section_hint}: expected JSON object at top level.")

        if len(payload) == 1:
            only_key, only_val = next(iter(payload.items()))
            if isinstance(only_val, dict):
                return str(only_key), only_val

        return section_hint, payload

    @classmethod
    def _load_legacy_defaults(cls) -> dict:
        path = cls._legacy_config_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @classmethod
    def load_defaults_from_configs(cls) -> tuple[dict, list[str]]:
        """Compile section defaults from configs/*.json with legacy-section fallback."""
        defaults: dict = {}
        errors: list[str] = []
        configs_dir = cls._configs_dir()

        if not configs_dir.exists():
            legacy_defaults = cls._load_legacy_defaults()
            return legacy_defaults, [f"Missing configs directory: {configs_dir} (using legacy config.json defaults)"]

        for path in sorted(configs_dir.glob("*.json")):
            if path.name.startswith("."):
                continue
            section_hint = path.stem
            try:
                payload, warning = cls._read_json_file(path)
                if warning:
                    errors.append(warning)
                section_key, section_data = cls._normalize_section_payload(section_hint, payload)
                defaults[section_key] = section_data
            except Exception as exc:
                errors.append(str(exc))

        # Legacy compatibility: keep config.json only as fallback for sections
        # not defined in configs/*.json.
        legacy_defaults = cls._load_legacy_defaults()
        if isinstance(legacy_defaults, dict):
            for key, value in legacy_defaults.items():
                if key in defaults:
                    continue
                if isinstance(key, str) and isinstance(value, dict):
                    defaults[key] = copy.deepcopy(value)
                    errors.append(
                        f"{key}: loaded from legacy config.json fallback (section missing in configs/)"
                    )

        return defaults, errors

    @classmethod
    def load_user_overrides(cls) -> dict:
        overrides = mw.addonManager.getConfig(cls.ROOT_ADDON_NAME) or {}
        return overrides if isinstance(overrides, dict) else {}

    @classmethod
    def load_effective_config(cls) -> tuple[dict, list[str]]:
        defaults, errors = cls.load_defaults_from_configs()
        overrides = cls.load_user_overrides()
        return cls.deep_merge_dicts(defaults, overrides), errors

    @classmethod
    def list_sections(cls) -> list[str]:
        effective, _ = cls.load_effective_config()
        return sorted(k for k in effective.keys() if isinstance(k, str))

    @classmethod
    def get_default_section(cls, section: str) -> dict:
        defaults, _ = cls.load_defaults_from_configs()
        data = defaults.get(section, {})
        return copy.deepcopy(data) if isinstance(data, dict) else {}

    @classmethod
    def get_override_section(cls, section: str) -> dict:
        overrides = cls.load_user_overrides()
        data = overrides.get(section, {})
        return copy.deepcopy(data) if isinstance(data, dict) else {}

    @classmethod
    def get_effective_section(cls, section: str) -> dict:
        defaults = cls.get_default_section(section)
        overrides = cls.get_override_section(section)
        return cls.deep_merge_dicts(defaults, overrides)

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
        - addon_name == _Change_notes: full effective config.
        - addon_name == section key: effective section.
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
        """Save config as overrides (full-root or section-level)."""
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
