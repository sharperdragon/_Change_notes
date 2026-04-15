from ...config_manager import ConfigManager as RootConfigManager


class ConfigManager:
    """Compatibility wrapper that proxies to the root ConfigManager."""

    SECTION_NAME = "add_table_class"
    LEGACY_SECTION_NAME = "Add_table_class"

    def __init__(self, addon_name: str):
        self.addon_name = addon_name
        self.config = self.load_config()

    def load_config(self):
        defaults = RootConfigManager.get_default_section(self.SECTION_NAME)
        effective = RootConfigManager.get_effective_section_with_aliases(
            self.SECTION_NAME,
            aliases=(self.LEGACY_SECTION_NAME,),
        )
        return RootConfigManager.deep_merge_dicts(defaults, effective)

    def load(self):
        return self.load_config()

    def save_config(self, new_config):
        if not isinstance(new_config, dict):
            raise ValueError("Configuration must be a JSON object.")
        RootConfigManager.save_section_override(self.SECTION_NAME, new_config)
        self.config = new_config

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config(self.config)
