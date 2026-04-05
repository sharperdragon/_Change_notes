#!/usr/bin/env python3
"""Build a portable _change_notes_shua export with only missed/custom tag modules."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

# --------------------------- USER-TUNABLE CONSTANTS ---------------------------
SOURCE_ADDON_DIR = Path("/Users/claytongoddard/Library/Application Support/Anki2/addons21/_Change_notes")
TARGET_EXPORT_DIR = Path(
    "/Users/claytongoddard/Library/Application Support/Anki2/addons21/_Change_notes/_change_notes_shua"
)
CONFIG_ROOT_KEY = "_change_notes_shua"
CLEAN_TARGET = True
FILES_TO_COPY = (
    "modules/add_custom_tags.py",
    "modules/add_missed_tags.py",
    "configs/add_custom_tags.json",
    "configs/add_missed_tags.json",
)
SOURCE_CONFIG_MANAGER_FILE = "config_manager.py"
SOURCE_LEGACY_CONFIG_FILE = "config.json"
TARGET_INIT_FILE = "__init__.py"
TARGET_CONFIG_MANAGER_FILE = "config_manager.py"
TARGET_CONFIG_FILE = "config.json"
CUSTOM_TAGS_MENU_LABEL = "Custom Tags"
TARGET_CONFIG_SECTIONS = ("add_custom_tags", "add_missed_tags")
CUSTOM_TAGS_ONLY_PRESET_LABEL = "Key 🔑"
CUSTOM_TAGS_ONLY_PRESET_TAG = "#Custom::#KEY"
TRUE_LEARN_RESOURCE_LABEL = "True-Learn"
DEFAULT_SUBSET_2_NAME = "♿️COMQUEST"
DEFAULT_SUBSET_2_TAG = "##Missed-Qs::COMQUEST"
# -----------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _ensure_required_sources_exist(source_root: Path) -> None:
    missing: list[str] = []
    for rel in (*FILES_TO_COPY, SOURCE_CONFIG_MANAGER_FILE):
        if not (source_root / rel).exists():
            missing.append(rel)
    if missing:
        details = "\n".join(f"- {item}" for item in missing)
        raise FileNotFoundError(f"Missing required source files:\n{details}")


def _cleanup_and_prepare_target(target_root: Path) -> None:
    if CLEAN_TARGET and target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)


def _copy_selected_files(source_root: Path, target_root: Path) -> None:
    for rel in FILES_TO_COPY:
        src = source_root / rel
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _build_export_init(custom_tags_menu_label: str) -> str:
    return f'''"""Portable _change_notes_shua addon: missed/custom tags only."""

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import QMenu

from .modules.add_custom_tags import add_custom_tag_menu_items
from .modules import add_missed_tags as missed_tags_module

CUSTOM_TAGS_MENU_LABEL = "{custom_tags_menu_label}"
TRUE_LEARN_RESOURCE_LABEL = "{TRUE_LEARN_RESOURCE_LABEL}"


def add_limited_missed_tag_menu_items(browser, menu):
    """Render only the six allowed Missed Tags actions for the export addon."""
    missed_tags_module._reload_runtime_config()

    tag_menu = QMenu(missed_tags_module.MISSED_TAGS_MENU_LABEL, browser)
    tag_menu.setStyleSheet(
        """
        QMenu::item {{
            padding-top: 4.5px;
            padding-bottom: 4.5px;
            padding-left: 6px;
            padding-right: 6px;
        }}
        QMenu::item:selected {{
            background-color: rgba(120, 160, 255, 60);
        }}
    """
    )

    missed_tags_module.add_uworld_tags(browser, tag_menu)
    missed_tags_module.add_amboss_tag(browser, tag_menu)
    missed_tags_module.add_base_plain_action(browser, tag_menu)
    missed_tags_module.add_multi_tag(browser, tag_menu)
    missed_tags_module.add_correct_guess_action(browser, tag_menu)

    original_resources = list(missed_tags_module.OTHER_RESOURCES)
    try:
        missed_tags_module.OTHER_RESOURCES = [TRUE_LEARN_RESOURCE_LABEL]
        missed_tags_module.add_other_resources_actions(browser, tag_menu)
    finally:
        missed_tags_module.OTHER_RESOURCES = original_resources

    if tag_menu.actions():
        menu.addSeparator()
        menu.addMenu(tag_menu)


def on_browser_will_show_context_menu(browser: Browser, menu):
    if not browser.selectedNotes():
        return

    add_limited_missed_tag_menu_items(browser, menu)
    add_custom_tag_menu_items(browser, menu, menu_label=CUSTOM_TAGS_MENU_LABEL)


if not getattr(mw, "_change_notes_shua_menu_injected", False):
    gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)
    mw._change_notes_shua_menu_injected = True
'''


def _build_export_config_manager(source_config_manager_text: str, config_root_key: str) -> str:
    updated_text, replace_count = re.subn(
        r'ROOT_ADDON_NAME\s*=\s*["\'][^"\']+["\']',
        f'ROOT_ADDON_NAME = "{config_root_key}"',
        source_config_manager_text,
        count=1,
    )
    if replace_count != 1:
        raise ValueError("Could not update ROOT_ADDON_NAME in source config_manager.py")
    return updated_text


def _build_minimal_config(source_root: Path) -> dict[str, Any]:
    config_defaults: dict[str, Any] = {}
    for section in TARGET_CONFIG_SECTIONS:
        section_path = source_root / "configs" / f"{section}.json"
        section_payload = _read_json(section_path)
        if not isinstance(section_payload, dict):
            raise ValueError(f"Expected JSON object in {section_path}")
        config_defaults[section] = section_payload

    source_legacy_config = source_root / SOURCE_LEGACY_CONFIG_FILE
    if source_legacy_config.exists():
        source_payload = _read_json(source_legacy_config)
        if isinstance(source_payload, dict):
            for section in TARGET_CONFIG_SECTIONS:
                section_payload = source_payload.get(section)
                if isinstance(section_payload, dict):
                    config_defaults[section] = section_payload

    custom_cfg = config_defaults.get("add_custom_tags")
    if isinstance(custom_cfg, dict):
        custom_cfg["presets"] = [
            {
                "label": CUSTOM_TAGS_ONLY_PRESET_LABEL,
                "tags": [CUSTOM_TAGS_ONLY_PRESET_TAG],
            }
        ]

    return config_defaults


def _restrict_export_custom_tags_config(target_root: Path) -> None:
    config_path = target_root / "configs" / "add_custom_tags.json"
    if not config_path.exists():
        return

    payload = _read_json(config_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {config_path}")

    payload["submenu_label"] = CUSTOM_TAGS_MENU_LABEL
    payload["presets"] = [
        {
            "label": CUSTOM_TAGS_ONLY_PRESET_LABEL,
            "tags": [CUSTOM_TAGS_ONLY_PRESET_TAG],
        }
    ]
    _write_json(config_path, payload)


def _ensure_subset2_defaults_in_missed_tags(target_root: Path) -> None:
    module_path = target_root / "modules" / "add_missed_tags.py"
    if not module_path.exists():
        return

    text = module_path.read_text(encoding="utf-8")
    has_subset2_name = "SUBSET_2_NAME =" in text
    has_subset2_tag = "SUBSET_2_TAG =" in text
    if has_subset2_name and has_subset2_tag:
        return

    anchor = 'SUBSET_1_TAG = ["##Missed-Qs::UW_Tests"]\n'
    insertion_lines: list[str] = []
    if not has_subset2_name:
        insertion_lines.append(f'SUBSET_2_NAME = "{DEFAULT_SUBSET_2_NAME}"')
    if not has_subset2_tag:
        insertion_lines.append(f'SUBSET_2_TAG = ["{DEFAULT_SUBSET_2_TAG}"]')
    insertion = "\n".join(insertion_lines) + "\n"

    if anchor in text:
        text = text.replace(anchor, anchor + insertion, 1)
    else:
        marker = "# ? Other resources"
        if marker not in text:
            raise ValueError("Could not place SUBSET_2 defaults in exported add_missed_tags.py")
        text = text.replace(marker, insertion + "\n" + marker, 1)

    module_path.write_text(text, encoding="utf-8")


def _write_generated_files(source_root: Path, target_root: Path) -> None:
    init_text = _build_export_init(CUSTOM_TAGS_MENU_LABEL)
    (target_root / TARGET_INIT_FILE).write_text(init_text, encoding="utf-8")

    source_config_manager_text = (source_root / SOURCE_CONFIG_MANAGER_FILE).read_text(encoding="utf-8")
    export_config_manager_text = _build_export_config_manager(source_config_manager_text, CONFIG_ROOT_KEY)
    (target_root / TARGET_CONFIG_MANAGER_FILE).write_text(export_config_manager_text, encoding="utf-8")

    minimal_config = _build_minimal_config(source_root)
    _write_json(target_root / TARGET_CONFIG_FILE, minimal_config)
    _restrict_export_custom_tags_config(target_root)
    _ensure_subset2_defaults_in_missed_tags(target_root)


def _validate_paths(source_root: Path, target_root: Path) -> None:
    source_resolved = source_root.resolve()
    target_resolved = target_root.resolve()
    if not source_resolved.exists():
        raise FileNotFoundError(f"SOURCE_ADDON_DIR does not exist: {source_resolved}")
    if source_resolved == target_resolved:
        raise ValueError("SOURCE_ADDON_DIR and TARGET_EXPORT_DIR cannot be the same path.")
    if target_resolved == Path(target_resolved.anchor):
        raise ValueError("Refusing to operate on filesystem root as target.")


def export_change_notes_shua() -> None:
    source_root = SOURCE_ADDON_DIR
    target_root = TARGET_EXPORT_DIR

    _validate_paths(source_root, target_root)
    _ensure_required_sources_exist(source_root)
    _cleanup_and_prepare_target(target_root)
    _copy_selected_files(source_root, target_root)
    _write_generated_files(source_root, target_root)

    print("Export complete.")
    print(f"Source: {source_root}")
    print(f"Target: {target_root}")


if __name__ == "__main__":
    export_change_notes_shua()
