# pyright: reportMissingImports=false
from __future__ import annotations

import re
from typing import Any

from aqt.qt import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ..config_manager import ConfigManager
from .missed_tags_constants import (
    AMBOSS_APPEND_CORRECT_MARKED_STATE_KEY,
    CANONICAL_CONFIG_SECTION,
    DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL,
    UWORLD_CORRECT_MISSED_SOURCE_KEY,
    UWORLD_CORRECT_MISSED_SOURCE_OPTIONS,
)
from .missed_tags_tag_utils import _correct_missed_input_key, _normalize_correct_missed_source

# Prompt offset in pixels from screen center.
# 0,0 centers the prompt in the active screen.
PROMPT_DIALOG_OFFSET_CENTER_X = 200
PROMPT_DIALOG_OFFSET_CENTER_Y = -50
# Prompt sizing (tunable): increase these if dialog captions/labels appear clipped.
PROMPT_DIALOG_MIN_WIDTH = 250
PROMPT_DIALOG_MIN_HEIGHT = 0
PROMPT_CHECKBOX_TOP_PADDING_PX = 8

# Keep a small margin so prompt windows never hug screen edges.
PROMPT_DIALOG_SAFE_MARGIN = 16
CORRECT_MISSED_DIALOG_MIN_WIDTH = 180
CORRECT_MISSED_DIALOG_MIN_HEIGHT = 0


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

def _load_missed_tags_override_section() -> dict[str, Any]:
    section_override = ConfigManager.get_override_section(CANONICAL_CONFIG_SECTION)
    return section_override if isinstance(section_override, dict) else {}


def _get_saved_prompt_input(prompt_key: str) -> str:
    if not prompt_key:
        return ""
    section_override = _load_missed_tags_override_section()
    runtime_cfg = _as_dict(section_override.get("runtime"))
    last_inputs = _as_dict(runtime_cfg.get("last_prompt_inputs"))
    value = last_inputs.get(prompt_key, "")
    return value if isinstance(value, str) else ""


def _save_prompt_inputs(prompt_values: dict[str, str]) -> None:
    if not isinstance(prompt_values, dict):
        return
    normalized_updates: dict[str, str] = {}
    for raw_key, raw_value in prompt_values.items():
        key = str(raw_key or "").strip()
        if not key:
            continue
        normalized_updates[key] = str(raw_value)
    if not normalized_updates:
        return

    try:
        section_override = _load_missed_tags_override_section()
        runtime_cfg = _as_dict(section_override.get("runtime"))
        last_inputs = _as_dict(runtime_cfg.get("last_prompt_inputs"))

        has_change = False
        for key, value in normalized_updates.items():
            current_value = last_inputs.get(key)
            if not isinstance(current_value, str) or current_value != value:
                has_change = True
                break
        if not has_change:
            return

        updated_override = ConfigManager.deep_merge_dicts({}, section_override)
        updated_runtime_cfg = _as_dict(updated_override.get("runtime"))
        updated_last_inputs = _as_dict(updated_runtime_cfg.get("last_prompt_inputs"))
        updated_last_inputs.update(normalized_updates)
        updated_runtime_cfg["last_prompt_inputs"] = updated_last_inputs
        updated_override["runtime"] = updated_runtime_cfg
        ConfigManager.save_section_override(CANONICAL_CONFIG_SECTION, updated_override)
    except Exception:
        # Prompt memory should never block tagging behavior.
        return


def _save_prompt_input(prompt_key: str, prompt_value: str) -> None:
    _save_prompt_inputs({prompt_key: prompt_value})


def _apply_prompt_dialog_size(dialog, min_width: int, min_height: int) -> None:
    """Apply a stable minimum size so title/labels are not clipped."""
    width = max(int(min_width), int(dialog.sizeHint().width()))
    height = max(int(min_height), int(dialog.sizeHint().height()))
    dialog.setMinimumSize(width, height)
    dialog.resize(width, height)


def _positioned_text_prompt(parent, title: str, label: str, default_text: str = "") -> tuple[str, bool]:
    dialog = QInputDialog(parent)
    dialog.setInputMode(QInputDialog.InputMode.TextInput)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(default_text)
    _apply_prompt_dialog_size(
        dialog,
        min_width=PROMPT_DIALOG_MIN_WIDTH,
        min_height=PROMPT_DIALOG_MIN_HEIGHT,
    )
    _position_dialog_near_center(dialog, parent)

    accepted = bool(dialog.exec())
    return dialog.textValue(), accepted


def _positioned_text_prompt_with_checkbox(
    parent,
    *,
    title: str,
    label: str,
    default_text: str,
    checkbox_label: str,
    checkbox_checked: bool,
) -> tuple[str, bool, bool]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)

    root = QVBoxLayout(dialog)
    prompt_label = QLabel(label, dialog)
    root.addWidget(prompt_label)

    input_line = QLineEdit(dialog)
    input_line.setText(default_text)
    root.addWidget(input_line)

    if PROMPT_CHECKBOX_TOP_PADDING_PX > 0:
        root.addSpacing(PROMPT_CHECKBOX_TOP_PADDING_PX)

    checkbox = QCheckBox(checkbox_label, dialog)
    checkbox_font = checkbox.font()
    checkbox_font.setBold(True)
    checkbox.setFont(checkbox_font)
    checkbox.setChecked(bool(checkbox_checked))
    root.addWidget(checkbox)

    button_box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    root.addWidget(button_box)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    _apply_prompt_dialog_size(
        dialog,
        min_width=PROMPT_DIALOG_MIN_WIDTH,
        min_height=PROMPT_DIALOG_MIN_HEIGHT,
    )
    _position_dialog_near_center(dialog, parent)

    accepted = bool(dialog.exec())
    return input_line.text(), bool(checkbox.isChecked()), accepted


def _correct_marked_checkbox_state_key(action_key: str) -> str:
    normalized_action = str(action_key or "").strip()
    if normalized_action == "amboss_test_prompt":
        return AMBOSS_APPEND_CORRECT_MARKED_STATE_KEY
    slug = re.sub(r"[^a-z0-9]+", "_", normalized_action.lower()).strip("_")
    return f"append_correct_marked_{slug or 'default'}"


def _position_dialog_near_center(dialog, parent) -> None:
    try:
        screen = None

        if parent is not None:
            try:
                parent_window = parent.window()
                if parent_window is not None and parent_window.windowHandle() is not None:
                    screen = parent_window.windowHandle().screen()
            except Exception:
                screen = None

            if screen is None:
                try:
                    screen = parent.screen()
                except Exception:
                    screen = None

        if screen is None:
            screen = QApplication.primaryScreen()

        if screen is not None:
            rect = screen.availableGeometry()
            target_x = rect.x() + (rect.width() - dialog.width()) // 2 + PROMPT_DIALOG_OFFSET_CENTER_X
            target_y = rect.y() + (rect.height() - dialog.height()) // 2 + PROMPT_DIALOG_OFFSET_CENTER_Y
            min_x = rect.x() + PROMPT_DIALOG_SAFE_MARGIN
            min_y = rect.y() + PROMPT_DIALOG_SAFE_MARGIN
            max_x = rect.x() + rect.width() - dialog.width() - PROMPT_DIALOG_SAFE_MARGIN
            max_y = rect.y() + rect.height() - dialog.height() - PROMPT_DIALOG_SAFE_MARGIN

            if max_x >= min_x:
                target_x = min(max(target_x, min_x), max_x)
            else:
                target_x = rect.x() + max((rect.width() - dialog.width()) // 2, 0)

            if max_y >= min_y:
                target_y = min(max(target_y, min_y), max_y)
            else:
                target_y = rect.y() + max((rect.height() - dialog.height()) // 2, 0)

            dialog.move(target_x, target_y)
    except Exception:
        pass


def _prompt_correct_missed_source_and_input(parent, action_label: str) -> tuple[str, str, bool]:
    remembered_source = _normalize_correct_missed_source(
        _get_saved_prompt_input(UWORLD_CORRECT_MISSED_SOURCE_KEY)
    )
    source_inputs = {
        source: _get_saved_prompt_input(_correct_missed_input_key(source))
        for source in UWORLD_CORRECT_MISSED_SOURCE_OPTIONS
    }

    dialog = QDialog(parent)
    dialog.setWindowTitle(str(action_label or DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL))
    root = QVBoxLayout(dialog)

    buttons_layout = QHBoxLayout()
    source_buttons: dict[str, QPushButton] = {}
    for source_name in UWORLD_CORRECT_MISSED_SOURCE_OPTIONS:
        button = QPushButton(source_name, dialog)
        button.setCheckable(True)
        source_buttons[source_name] = button
        buttons_layout.addWidget(button)
    root.addLayout(buttons_layout)

    input_line = QLineEdit(dialog)
    root.addWidget(input_line)

    button_box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    root.addWidget(button_box)

    active_source = remembered_source

    def _select_source(source_name: str) -> None:
        nonlocal active_source
        current = active_source
        if current in source_buttons and current != source_name:
            source_inputs[current] = input_line.text()
        active_source = source_name

        for name, button in source_buttons.items():
            button.setChecked(name == source_name)

        input_line.setText(source_inputs.get(source_name, ""))
        if source_name == "UWorld":
            input_line.setPlaceholderText("Enter integer")
        elif source_name == "NBME":
            input_line.setPlaceholderText("Enter form # or path (e.g., CMS::OBGYN::6)")
        else:
            input_line.setPlaceholderText("Enter tag input")

    for source_name, button in source_buttons.items():
        button.clicked.connect(lambda _, name=source_name: _select_source(name))

    _select_source(remembered_source)
    _apply_prompt_dialog_size(
        dialog,
        min_width=CORRECT_MISSED_DIALOG_MIN_WIDTH,
        min_height=CORRECT_MISSED_DIALOG_MIN_HEIGHT,
    )
    _position_dialog_near_center(dialog, parent)

    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    accepted = bool(dialog.exec())
    if not accepted:
        return remembered_source, source_inputs.get(remembered_source, ""), False

    chosen_source = active_source
    source_inputs[chosen_source] = input_line.text()

    prompt_updates: dict[str, str] = {UWORLD_CORRECT_MISSED_SOURCE_KEY: chosen_source}
    for source_name in UWORLD_CORRECT_MISSED_SOURCE_OPTIONS:
        prompt_updates[_correct_missed_input_key(source_name)] = source_inputs.get(source_name, "")
    _save_prompt_inputs(prompt_updates)

    return chosen_source, source_inputs.get(chosen_source, ""), True
