
# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw


class ConfigManager:
    """Manages loading and saving add-on configuration."""

    def reload(self):
        """Reload the configuration from Anki."""
        self.config = self.load_config()

    def __init__(self, addon_name: str, global_config_name: str = None):
        self.addon_name = addon_name
        self.global_config_name = global_config_name
        self.config = self.load_config()

    def load_config(self):
        """Load the current configuration from Anki, optionally merging with a global config."""
        config = mw.addonManager.getConfig(self.addon_name) or {}
        if self.global_config_name:
            global_config = mw.addonManager.getConfig(self.global_config_name) or {}
            # Merge, ignoring empty string values in the module config
            return self.deep_merge_dicts(global_config, config)
        return config

    def save_config(self, new_config):
        """Save new configuration settings."""
        mw.addonManager.writeConfig(self.addon_name, new_config)
        self.config = new_config  # Update current instance

    def get(self, key, default=None):
        """Get a configuration value with a default fallback."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Set a configuration value and save it."""
        self.config[key] = value
        self.save_config(self.config)
    
    def load(self):
        return self.load_config()

    @staticmethod
    def deep_merge_dicts(base: dict, override: dict) -> dict:
        """Recursively merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = ConfigManager.deep_merge_dicts(result[key], value)
            elif value != "":
                result[key] = value
        return result
