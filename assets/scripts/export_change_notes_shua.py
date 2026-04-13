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
BASE_FILES_TO_COPY = (
    "modules/add_custom_tags.py",
    "modules/add_missed_tags.py",
    "configs/add_custom_tags.json",
)
CANONICAL_MISSED_TAGS_SECTION = "tag_missed_qid_notes"
LEGACY_MISSED_TAGS_SECTION = "add_missed_tags"
CANONICAL_MISSED_TAGS_CONFIG_REL = "configs/tag_missed_qid_notes.json"
LEGACY_MISSED_TAGS_CONFIG_REL = "configs/add_missed_tags.json"
SOURCE_CONFIG_MANAGER_FILE = "config_manager.py"
SOURCE_LEGACY_CONFIG_FILE = "config.json"
TARGET_INIT_FILE = "__init__.py"
TARGET_CONFIG_MANAGER_FILE = "config_manager.py"
TARGET_CONFIG_FILE = "config.json"
CUSTOM_TAGS_MENU_LABEL = "Custom Tags"
TARGET_CONFIG_SECTIONS = ("add_custom_tags", CANONICAL_MISSED_TAGS_SECTION)
CUSTOM_TAGS_ONLY_PRESET_LABEL = "Key 🔑"
CUSTOM_TAGS_ONLY_PRESET_TAG = "#Custom::#KEY"
TRUE_LEARN_RESOURCE_LABEL = "True-Learn"
DEFAULT_SUBSET_2_NAME = "🧠NBME"
DEFAULT_SUBSET_2_TAG = "##Missed-Qs::NBME"
# -----------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _resolve_missed_tags_config_source(source_root: Path) -> Path:
    canonical_path = source_root / CANONICAL_MISSED_TAGS_CONFIG_REL
    if canonical_path.exists():
        return canonical_path

    legacy_path = source_root / LEGACY_MISSED_TAGS_CONFIG_REL
    if legacy_path.exists():
        return legacy_path

    raise FileNotFoundError(f"Missing missed-tags config file. Checked: {canonical_path} and {legacy_path}")


def _ensure_required_sources_exist(source_root: Path) -> None:
    missing: list[str] = []
    for rel in (*BASE_FILES_TO_COPY, SOURCE_CONFIG_MANAGER_FILE):
        if not (source_root / rel).exists():
            missing.append(rel)
    try:
        _resolve_missed_tags_config_source(source_root)
    except FileNotFoundError as exc:
        missing.append(str(exc))
    if missing:
        details = "\n".join(f"- {item}" for item in missing)
        raise FileNotFoundError(f"Missing required source files:\n{details}")


def _cleanup_and_prepare_target(target_root: Path) -> None:
    if CLEAN_TARGET and target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)


def _copy_selected_files(source_root: Path, target_root: Path) -> None:
    for rel in BASE_FILES_TO_COPY:
        src = source_root / rel
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    missed_src = _resolve_missed_tags_config_source(source_root)
    missed_dst = target_root / CANONICAL_MISSED_TAGS_CONFIG_REL
    missed_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(missed_src, missed_dst)


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
    cfg = missed_tags_module.load_runtime_config()

    tag_menu = QMenu(cfg.missed_tags_menu_label, browser)
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

    missed_tags_module.add_uworld_tags(browser, tag_menu, cfg)
    missed_tags_module.add_amboss_tag(browser, tag_menu, cfg)
    missed_tags_module.add_base_plain_action(browser, tag_menu, cfg)
    missed_tags_module.add_multi_tag(browser, tag_menu, cfg)
    missed_tags_module.add_correct_guess_action(browser, tag_menu, cfg)
    missed_tags_module.add_other_resources_actions(
        browser,
        tag_menu,
        cfg,
        resources_override=[TRUE_LEARN_RESOURCE_LABEL],
    )

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

    missed_defaults = _read_json(_resolve_missed_tags_config_source(source_root))
    if not isinstance(missed_defaults, dict):
        raise ValueError("Expected JSON object in missed-tags config source")
    config_defaults[CANONICAL_MISSED_TAGS_SECTION] = missed_defaults

    for section in TARGET_CONFIG_SECTIONS:
        if section == CANONICAL_MISSED_TAGS_SECTION:
            continue
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
                if section == CANONICAL_MISSED_TAGS_SECTION:
                    section_payload = source_payload.get(CANONICAL_MISSED_TAGS_SECTION)
                    if not isinstance(section_payload, dict):
                        section_payload = source_payload.get(LEGACY_MISSED_TAGS_SECTION)
                else:
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
    config_path = target_root / CANONICAL_MISSED_TAGS_CONFIG_REL
    if not config_path.exists():
        return

    payload = _read_json(config_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {config_path}")

    if "subset_2_name" in payload and "subset_tag_2" in payload:
        return

    payload.setdefault("subset_2_name", DEFAULT_SUBSET_2_NAME)
    payload.setdefault("subset_tag_2", [DEFAULT_SUBSET_2_TAG])
    _write_json(config_path, payload)


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
