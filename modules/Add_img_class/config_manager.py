import os, io, json
from aqt import mw

class ConfigManager:
    """Manages loading and saving add-on configuration."""

    _ALIASES = {
        "ultra-wide_ratio": "ultra_wide_ratio",  # normalize hyphenated key
        "tall_ratio_min": "tall_ratio",          # accept either spelling
    }

    def __init__(self, addon_name: str):
        self.addon_name = addon_name
        self.config = self.load_config()

    def load_config(self):
        """Load the current configuration from config.json in this module folder."""
        here = os.path.dirname(__file__)
        path = os.path.join(here, "config.json")
        try:
            with io.open(path, "r", encoding="utf-8") as f:
                config = json.load(f) or {}
        except Exception:
            config = {}

        # normalize aliases
        for alias, canonical in self._ALIASES.items():
            if alias in config and canonical not in config:
                config[canonical] = config[alias]

        return config

    def save_config(self, new_config):
        """Save new configuration settings back to config.json in this module folder."""
        here = os.path.dirname(__file__)
        path = os.path.join(here, "config.json")
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2)
        self.config = new_config  # update current instance

    def get(self, key, default=None):
        """Get a configuration value with a default fallback."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Set a configuration value and save it."""
        self.config[key] = value
        self.save_config(self.config)