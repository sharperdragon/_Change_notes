import copy
import html
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import markdown
from aqt import mw
from aqt.qt import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPalette,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    Qt,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import askUser, showInfo

# --------------------------- USER-TUNABLE CONSTANTS ---------------------------
WINDOW_MARGIN = 100
JSON_INDENT = 2
MAX_STATUS_WARNINGS = 3
OVERRIDE_EDITOR_MIN_WIDTH = 260
OVERRIDE_EDITOR_MIN_HEIGHT = 220
CATEGORY_SPLITTER_LEFT_RATIO = 0.68
CATEGORY_HELP_MIN_WIDTH = 320
TAB_WIDGET_CHROME_WIDTH = 48
TAB_WIDGET_BASE_MIN_WIDTH = 460
TAB_MD_DIRECTORY = "tab_md"
RESTORE_FOCUS_ON_TAB_CHANGE = True
HELP_MARKDOWN_EXTENSIONS = ("fenced_code",)
HELP_DOC_PADDING_PX = 8
HELP_DOC_FONT_SIZE_PX = 13
HELP_DOC_LINE_HEIGHT = 1.45
HELP_DOC_CODE_BG_ALPHA = 0.16
HELP_DOC_PRE_BG_ALPHA = 0.10
HELP_DOC_PRE_BORDER_ALPHA = 0.24
HELP_DOC_LINK_DECORATION = "none"

STATUS_DEFAULT_TEXT = (
    "Defaults source: config.json (root) | Edits are local until Save All or closing this window."
)
STATUS_NO_SECTIONS_TEXT = "No config sections found in configured category mappings."
RELOAD_CONFIRM_TEXT = "Discard unsaved editor changes and reload saved config?"
RESTORE_ALL_CONFIRM_TEXT = "Reset all visible section editors to defaults and save now?"
RESTORE_ALL_SUCCESS_TEXT = "Restored defaults for all visible sections."
RESTORE_ALL_IN_MEMORY_TEXT = (
    "Reset all visible section editors to defaults in-memory. Save All or close to persist."
)

SECTION_EDITOR_LABEL = "Section Override (editable JSON object)"
SECTION_RESTORE_BUTTON_TEXT = "Restore Section Defaults"
SAVE_ALL_BUTTON_TEXT = "Save All Tabs"
SAVE_ALL_SUCCESS_TEXT = "Saved overrides for all visible sections."
CANCEL_BUTTON_TEXT = "Cancel"
SAVE_CLOSE_BUTTON_TEXT = "Save & Close"
AUTO_SAVE_ON_RESTORE_ALL = True
PRUNE_EMPTY_SECTION_OVERRIDES = True

HYBRID_WINDOW_MARGIN = 120
HYBRID_FIELD_MIN_WIDTH = 320
HYBRID_TEXT_AREA_MIN_HEIGHT = 82
HYBRID_CUSTOM_TAGS_MIN_ROWS = 3
HYBRID_CUSTOM_TAGS_LABEL_COLUMN_WIDTH = 220
HYBRID_CUSTOM_TAGS_GROUP_COLUMN_WIDTH = 80
HYBRID_FORM_SECTION_KEYS = (
    "global_config",
    "tag_missed_notes",
    "custom_tags_config",
    "merge_tags_config",
    "merge_images_config",
    "merge_scheduling",
    "add_table_class",
    "add_img_class",
    "delete_empty_notes_config",
    "batch_note_change_config",
    "tag_dupes_config",
)

HYBRID_SETTINGS_STATUS_TEXT = (
    "Friendly settings save to Anki's add-on config. Use Advanced for full JSON."
)
HYBRID_RESTORE_CONFIRM_TEXT = "Restore defaults for all settings shown in this window?"
HYBRID_RESTORE_SUCCESS_TEXT = "Restored defaults for the settings shown in this window."
HYBRID_ADVANCED_DISCARD_CONFIRM_TEXT = (
    "Opening Advanced will reload this settings window when it closes. "
    "Discard unsaved changes in this window?"
)

CATEGORY_DOC_FILES: dict[str, str] = {
    "Global": "global.md",
    "Custom Tags": "custom_tags.md",
    "Missed Tags": "missed_tags.md",
    "Merge Settings": "merge_settings.md",
    "Add CSS class": "add_css_class.md",
    "Other": "other.md",
}

DOC_MISSING_TEMPLATE = (
    "# {category}\\n\\nNo markdown guide found for this category.\\n\\nExpected file: `{relative_path}`"
)
DOC_EMPTY_TEMPLATE = (
    "# {category}\\n\\n"
    "This category guide is currently empty.\\n\\n"
    "Add markdown content to `{relative_path}`."
)
DOC_LOAD_ERROR_TEMPLATE = "# {category}\\n\\nFailed to load category guide.\\n\\nError: `{error}`"

MISSED_TAGS_CANONICAL_SECTION = "tag_missed_notes"
CUSTOM_TAGS_CANONICAL_SECTION = "custom_tags_config"

CATEGORY_SECTION_MAP: list[tuple[str, list[str]]] = [
    (
        "Global",
        [
            "global_config",
        ],
    ),
    (
        "Custom Tags",
        [
            CUSTOM_TAGS_CANONICAL_SECTION,
        ],
    ),
    (
        "Missed Tags",
        [
            MISSED_TAGS_CANONICAL_SECTION,
        ],
    ),
    (
        "Merge Settings",
        [
            "merge_tags_config",
            "merge_images_config",
            "merge_images_and_tags_config",
            "merge_scheduling",
        ],
    ),
    (
        "Add CSS class",
        [
            "add_table_class",
            "add_img_class",
        ],
    ),
    (
        "Other",
        [
            "delete_empty_notes_config",
            "batch_note_change_config",
            "tag_dupes_config",
        ],
    ),
]

HIDDEN_LEGACY_SECTIONS = {
    "add_custom_tags",
    "add_custom_tags_1",
    "add_custom_tags_2",
    "add_missed_tags",
    "tag_selected_notes_config",
    "add_tags",
    "merge_scheduling_config",
}

SECTION_UI_METADATA: dict[str, dict[str, Any]] = {
    "global_config": {"label": "Global Config", "form_schema": None},
    CUSTOM_TAGS_CANONICAL_SECTION: {"label": "Custom Tags Config", "form_schema": None},
    MISSED_TAGS_CANONICAL_SECTION: {"label": "Tag Missed Notes", "form_schema": None},
    "merge_tags_config": {"label": "Merge Tags", "form_schema": None},
    "merge_images_config": {"label": "Merge Images", "form_schema": None},
    "merge_images_and_tags_config": {"label": "Merge Images + Tags", "form_schema": None},
    "merge_scheduling": {"label": "Merge Scheduling", "form_schema": None},
    "add_table_class": {"label": "Add Table Class", "form_schema": None},
    "add_img_class": {"label": "Add Image Class", "form_schema": None},
    "delete_empty_notes_config": {"label": "Delete Empty Notes", "form_schema": None},
    "batch_note_change_config": {"label": "Batch Note Change", "form_schema": None},
    "tag_dupes_config": {"label": "Tag Duplicates", "form_schema": None},
}

ACRONYM_WORDS = {
    "api": "API",
    "id": "ID",
    "img": "IMG",
    "json": "JSON",
    "nbme": "NBME",
    "qid": "QID",
    "ui": "UI",
    "uw": "UW",
}
# -----------------------------------------------------------------------------


@dataclass
class SectionTabState:
    section_key: str
    container: QWidget
    override_editor: QTextEdit


@dataclass
class CategoryTabState:
    name: str
    container: QWidget
    section_tabs: QTabWidget
    help_view: QWidget


@dataclass
class HybridFieldBinding:
    section_key: str
    path: tuple[str, ...]
    widget: QWidget
    kind: str


@dataclass
class HybridCustomTagsSection:
    section_key: str
    menu_label: QLineEdit
    table: QTableWidget


class HybridConfigDialog(QDialog):
    """Friendly tabbed settings window backed by Anki add-on config overrides."""

    def __init__(self, addon_name: str, config_manager_cls, parent=None):
        # * Keep this dialog parented directly to Anki's main window so modality/focus works reliably.
        parent_window = parent or mw
        super().__init__(parent_window, Qt.WindowType.Window)
        self.addon_name = addon_name
        self.config_manager_cls = config_manager_cls
        self.mgr = mw.addonManager
        self.effective_config: dict[str, Any] = {}
        self._last_loaded_form_sections: dict[str, dict[str, Any]] = {}
        self._advanced_config_editor: QDialog | None = None
        self._suppress_focus_restore = False
        self.bindings: list[HybridFieldBinding] = []
        self.custom_tag_sections: list[HybridCustomTagsSection] = []
        self.rotation_schedule_table: QTableWidget | None = None

        self.setWindowTitle(f"{addon_name} Settings")

        # * ApplicationModal prevents the Add-ons window from trapping focus above this dialog.
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        screen = mw.app.primaryScreen().availableGeometry()
        self.setGeometry(
            screen.x() + HYBRID_WINDOW_MARGIN,
            screen.y() + HYBRID_WINDOW_MARGIN,
            screen.width() - 2 * HYBRID_WINDOW_MARGIN,
            screen.height() - 2 * HYBRID_WINDOW_MARGIN,
        )

        self.main_layout = QVBoxLayout(self)
        self.status_label = QLabel(HYBRID_SETTINGS_STATUS_TEXT)
        self.status_label.setWordWrap(True)
        self.main_layout.addWidget(self.status_label)

        self.tabs = QTabWidget(self)
        self._configure_tab_widget_for_full_labels(self.tabs)
        self.main_layout.addWidget(self.tabs, stretch=1)

        buttons_row = QHBoxLayout()
        advanced_button = QPushButton("Advanced")
        advanced_button.clicked.connect(self.open_advanced_editor)
        buttons_row.addWidget(advanced_button)

        restore_button = QPushButton("Restore Defaults")
        restore_button.clicked.connect(self.restore_defaults)
        buttons_row.addWidget(restore_button)

        buttons_row.addStretch(1)

        cancel_button = QPushButton(CANCEL_BUTTON_TEXT)
        cancel_button.clicked.connect(self.reject)
        buttons_row.addWidget(cancel_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_close)
        save_button.setDefault(True)
        buttons_row.addWidget(save_button)

        self.main_layout.addLayout(buttons_row)
        self.reload_from_config()

    def _configure_tab_widget_for_full_labels(self, tab_widget: QTabWidget):
        tab_bar = tab_widget.tabBar()
        tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
        tab_bar.setExpanding(False)
        tab_bar.setUsesScrollButtons(True)

    def reload_from_config(self):
        self.effective_config, errors = self.config_manager_cls.load_effective_config()
        self._rebuild_tabs()
        self._refresh_form_snapshot()
        if errors:
            self.status_label.setText(
                HYBRID_SETTINGS_STATUS_TEXT + " Load warnings: " + "; ".join(errors[:MAX_STATUS_WARNINGS])
            )
        else:
            self.status_label.setText(HYBRID_SETTINGS_STATUS_TEXT)

    def showEvent(self, event):
        """Bring the hybrid settings dialog to the front after Qt finishes showing it."""
        super().showEvent(event)

        # * Qt often needs one event-loop tick before activateWindow() works.
        QTimer.singleShot(0, self._restore_dialog_focus)
        QTimer.singleShot(100, self._restore_dialog_focus)

    def _restore_dialog_focus(self):
        """Raise and activate this dialog without forcing it above unrelated apps."""
        if not self.isVisible() or self._suppress_focus_restore:
            return

        self.raise_()
        self.activateWindow()

    def _raise_advanced_editor(self):
        advanced = self._advanced_config_editor
        if advanced is None or not advanced.isVisible():
            return
        advanced.raise_()
        advanced.activateWindow()

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    def _get_section(self, section_key: str) -> dict[str, Any]:
        return self._as_dict(self.effective_config.get(section_key))

    def _get_path(self, section_key: str, path: tuple[str, ...], fallback: Any = None) -> Any:
        current: Any = self._get_section(section_key)
        for part in path:
            if not isinstance(current, dict) or part not in current:
                return fallback
            current = current[part]
        return current

    def _get_first_path(
        self,
        section_key: str,
        paths: tuple[tuple[str, ...], ...],
        fallback: Any = None,
    ) -> Any:
        for path in paths:
            value = self._get_path(section_key, path, None)
            if value is not None:
                return value
        return fallback

    @staticmethod
    def _set_path(section: dict[str, Any], path: tuple[str, ...], value: Any):
        current = section
        for part in path[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = child
        current[path[-1]] = value

    @staticmethod
    def _split_lines(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    @staticmethod
    def _split_tags(text: str) -> list[str]:
        normalized = text.replace(",", "\n")
        return [line.strip() for line in normalized.splitlines() if line.strip()]

    @staticmethod
    def _join_lines(value: Any) -> str:
        if isinstance(value, list):
            return "\n".join(str(item) for item in value if item is not None)
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _new_scroll_tab(self) -> tuple[QWidget, QVBoxLayout]:
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        return outer, content_layout

    def _add_group(self, parent_layout: QVBoxLayout, title: str) -> QFormLayout:
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        parent_layout.addWidget(group)
        return form

    def _bind(self, section_key: str, path: tuple[str, ...], widget: QWidget, kind: str):
        self.bindings.append(HybridFieldBinding(section_key, path, widget, kind))

    def _add_line(
        self,
        form: QFormLayout,
        label: str,
        section_key: str,
        path: tuple[str, ...],
        fallback: str = "",
    ) -> QLineEdit:
        widget = QLineEdit()
        widget.setMinimumWidth(HYBRID_FIELD_MIN_WIDTH)
        widget.setText(str(self._get_path(section_key, path, fallback) or ""))
        form.addRow(label, widget)
        self._bind(section_key, path, widget, "line")
        return widget

    def _add_bool(
        self,
        form: QFormLayout,
        label: str,
        section_key: str,
        path: tuple[str, ...],
        fallback: bool = False,
    ) -> QCheckBox:
        widget = QCheckBox()
        widget.setChecked(self._truthy(self._get_path(section_key, path, fallback)))
        form.addRow(label, widget)
        self._bind(section_key, path, widget, "bool")
        return widget

    def _add_int(
        self,
        form: QFormLayout,
        label: str,
        section_key: str,
        path: tuple[str, ...],
        minimum: int = 0,
        maximum: int = 100000,
        fallback: int = 0,
    ) -> QSpinBox:
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        try:
            widget.setValue(int(self._get_path(section_key, path, fallback)))
        except Exception:
            widget.setValue(fallback)
        form.addRow(label, widget)
        self._bind(section_key, path, widget, "int")
        return widget

    def _add_float(
        self,
        form: QFormLayout,
        label: str,
        section_key: str,
        path: tuple[str, ...],
        minimum: float = 0.0,
        maximum: float = 999.0,
        decimals: int = 4,
        step: float = 0.01,
        fallback: float = 0.0,
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setDecimals(decimals)
        widget.setSingleStep(step)
        try:
            widget.setValue(float(self._get_path(section_key, path, fallback)))
        except Exception:
            widget.setValue(fallback)
        form.addRow(label, widget)
        self._bind(section_key, path, widget, "float")
        return widget

    def _add_combo(
        self,
        form: QFormLayout,
        label: str,
        section_key: str,
        path: tuple[str, ...],
        options: list[str],
        fallback: str,
    ) -> QComboBox:
        widget = QComboBox()
        widget.addItems(options)
        value = str(self._get_path(section_key, path, fallback) or fallback)
        if value not in options:
            widget.addItem(value)
        widget.setCurrentText(value)
        form.addRow(label, widget)
        self._bind(section_key, path, widget, "combo")
        return widget

    def _add_text_list(
        self,
        form: QFormLayout,
        label: str,
        section_key: str,
        path: tuple[str, ...],
        fallback: Any = None,
    ) -> QTextEdit:
        widget = QTextEdit()
        widget.setAcceptRichText(False)
        widget.setMinimumHeight(HYBRID_TEXT_AREA_MIN_HEIGHT)
        widget.setPlainText(self._join_lines(self._get_path(section_key, path, fallback or [])))
        form.addRow(label, widget)
        self._bind(section_key, path, widget, "string_list")
        return widget

    def _make_table(self, columns: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setMinimumHeight(150)
        return table

    def _configure_custom_tags_table_columns(self, table: QTableWidget):
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, HYBRID_CUSTOM_TAGS_LABEL_COLUMN_WIDTH)
        table.setColumnWidth(1, HYBRID_CUSTOM_TAGS_GROUP_COLUMN_WIDTH)

    def _add_table_row(self, table: QTableWidget, values: list[Any] | None = None):
        row = table.rowCount()
        table.insertRow(row)
        values = values or []
        for column in range(table.columnCount()):
            text = str(values[column]) if column < len(values) and values[column] is not None else ""
            table.setItem(row, column, QTableWidgetItem(text))

    def _remove_selected_table_rows(self, table: QTableWidget):
        rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        if not rows and table.rowCount() > 0:
            rows = [table.rowCount() - 1]
        for row in rows:
            table.removeRow(row)

    def _table_text(self, table: QTableWidget, row: int, column: int) -> str:
        item = table.item(row, column)
        return item.text().strip() if item else ""

    def _rebuild_tabs(self):
        self.tabs.clear()
        self.bindings.clear()
        self.custom_tag_sections.clear()
        self.rotation_schedule_table = None

        self.tabs.addTab(self._build_global_tab(), "Global")
        self.tabs.addTab(self._build_missed_tags_tab(), "Missed Tags")
        self.tabs.addTab(self._build_custom_tags_tab(), "Custom Tags")
        self.tabs.addTab(self._build_merge_tab(), "Merge")
        self.tabs.addTab(self._build_add_css_class_tab(), "Add CSS Class")
        self.tabs.addTab(self._build_other_tab(), "Other")

    def _build_global_tab(self) -> QWidget:
        tab, layout = self._new_scroll_tab()
        form = self._add_group(layout, "Shared Defaults")
        self._add_line(form, "Default note type", "global_config", ("default_note_type",))
        self._add_line(form, "Log folder", "global_config", ("log_folder",))
        self._add_float(
            form,
            "Default fuzzy threshold",
            "global_config",
            ("fuzzy_opts", "default_fuzz"),
            0.0,
            1.0,
            fallback=0.97,
        )
        self._add_float(
            form,
            "Minimum fuzzy threshold",
            "global_config",
            ("fuzzy_opts", "min_fuzz"),
            0.0,
            1.0,
            fallback=0.55,
        )

        separator_form = self._add_group(layout, "Browser Context Menu Separators")
        for key in (
            "missed_tags_menu",
            "add_custom_tags_1",
            "add_custom_tags_2",
            "add_custom_tags_3",
            "other_actions_menu",
            "add_img_class_action",
            "merge_menu",
            "edit_menu",
        ):
            self._add_bool(
                separator_form,
                key,
                "global_config",
                ("main_context_menu_separator_before", key),
            )
        self._add_bool(
            separator_form,
            "After Edit Menu",
            "global_config",
            ("main_context_menu_separator_after_edit_menu",),
        )
        layout.addStretch(1)
        return tab

    def _action_value(self, action_key: str, field: str, fallback: str = "") -> str:
        return str(
            self._get_first_path(
                MISSED_TAGS_CANONICAL_SECTION,
                (
                    ("actions", action_key, field),
                    ("actions", action_key, "menu_label" if field == "label" else field),
                ),
                fallback,
            )
            or ""
        )

    def _build_missed_tags_tab(self) -> QWidget:
        tab, layout = self._new_scroll_tab()

        general = self._add_group(layout, "Menu and Date")
        self._add_line(general, "Menu label", MISSED_TAGS_CANONICAL_SECTION, ("ui", "menu_label"))
        self._add_bool(
            general,
            "Include day segment",
            MISSED_TAGS_CANONICAL_SECTION,
            ("date", "include_day_segment"),
            True,
        )
        self._add_bool(
            general,
            "Split days into weeks",
            MISSED_TAGS_CANONICAL_SECTION,
            ("date", "split_weeks"),
            False,
        )

        rotation = self._add_group(layout, "Rotation")
        self._add_line(
            rotation,
            "Parent tag segment",
            MISSED_TAGS_CANONICAL_SECTION,
            ("block", "parent_tag_segment"),
            str(
                self._get_first_path(
                    MISSED_TAGS_CANONICAL_SECTION,
                    (("rotation", "parent_tag_segment"), ("block", "parent_tag_segment")),
                    "Block",
                )
            ),
        )
        exhausted = QComboBox()
        exhausted.addItems(["unknown", "next"])
        exhausted_value = str(
            self._get_first_path(
                MISSED_TAGS_CANONICAL_SECTION,
                (("rotation", "exhausted_policy"), ("block", "exhausted_policy")),
                "unknown",
            )
            or "unknown"
        )
        if exhausted_value not in {"unknown", "next"}:
            exhausted_value = "unknown"
        exhausted.setCurrentText(exhausted_value)
        rotation.addRow("When outside schedule", exhausted)
        self._bind(MISSED_TAGS_CANONICAL_SECTION, ("block", "exhausted_policy"), exhausted, "combo")

        schedule_group = QGroupBox("Rotation Schedule")
        schedule_layout = QVBoxLayout(schedule_group)
        self.rotation_schedule_table = self._make_table(["Segment Label", "Start", "End"])
        schedule = self._get_first_path(
            MISSED_TAGS_CANONICAL_SECTION,
            (("rotation", "schedule"), ("block", "schedule")),
            [],
        )
        for item in self._as_list(schedule):
            item_dict = self._as_dict(item)
            self._add_table_row(
                self.rotation_schedule_table,
                [
                    item_dict.get("segment_label", item_dict.get("label", "")),
                    item_dict.get("start", ""),
                    item_dict.get("end", ""),
                ],
            )
        if self.rotation_schedule_table.rowCount() == 0:
            self._add_table_row(self.rotation_schedule_table, ["", "", ""])
        schedule_layout.addWidget(self.rotation_schedule_table)
        schedule_buttons = QHBoxLayout()
        add_button = QPushButton("Add Row")
        add_button.clicked.connect(lambda: self._add_table_row(self.rotation_schedule_table))
        schedule_buttons.addWidget(add_button)
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(lambda: self._remove_selected_table_rows(self.rotation_schedule_table))
        schedule_buttons.addWidget(remove_button)
        schedule_buttons.addStretch(1)
        schedule_layout.addLayout(schedule_buttons)
        layout.addWidget(schedule_group)

        actions = self._add_group(layout, "Core Actions")
        for action_key, label_text, segment_text in (
            ("uworld", "UWorld label", "UWorld tag segment"),
            ("nbme", "NBME label", "NBME tag segment"),
            ("amboss", "Amboss label", "Amboss tag segment"),
            ("multi_missed", "2x missed label", "2x missed tag segment"),
            ("correct_tag_missed", "Correct + missed label", "Correct + missed tag segment"),
        ):
            label = QLineEdit(self._action_value(action_key, "label"))
            label.setMinimumWidth(HYBRID_FIELD_MIN_WIDTH)
            actions.addRow(label_text, label)
            self._bind(MISSED_TAGS_CANONICAL_SECTION, ("actions", action_key, "menu_label"), label, "line")

            segment = QLineEdit(self._action_value(action_key, "tag_segment"))
            segment.setMinimumWidth(HYBRID_FIELD_MIN_WIDTH)
            actions.addRow(segment_text, segment)
            self._bind(MISSED_TAGS_CANONICAL_SECTION, ("actions", action_key, "tag_segment"), segment, "line")

        self._add_line(
            actions,
            "Key info label",
            MISSED_TAGS_CANONICAL_SECTION,
            ("actions", "key_info", "menu_label"),
            self._action_value("key_info", "label"),
        )
        self._add_text_list(
            actions,
            "Key info tags",
            MISSED_TAGS_CANONICAL_SECTION,
            ("actions", "key_info", "absolute_tags"),
            self._get_first_path(
                MISSED_TAGS_CANONICAL_SECTION,
                (("actions", "key_info", "absolute_tags"), ("actions", "key_info", "tags")),
                [],
            ),
        )
        self._add_line(
            actions,
            "Correct guess label",
            MISSED_TAGS_CANONICAL_SECTION,
            ("actions", "correct_guess", "menu_label"),
            self._action_value("correct_guess", "label"),
        )
        self._add_text_list(
            actions,
            "Correct guess tags",
            MISSED_TAGS_CANONICAL_SECTION,
            ("actions", "correct_guess", "absolute_tags"),
            self._get_first_path(
                MISSED_TAGS_CANONICAL_SECTION,
                (("actions", "correct_guess", "absolute_tags"), ("actions", "correct_guess", "tags")),
                [],
            ),
        )
        layout.addStretch(1)
        return tab

    def _build_custom_tags_tab(self) -> QWidget:
        tab, layout = self._new_scroll_tab()
        custom_cfg = self._as_dict(self.effective_config.get(CUSTOM_TAGS_CANONICAL_SECTION))
        section_keys = self.config_manager_cls.discover_custom_tags_sections(self.effective_config)
        for section_key in section_keys:
            section_cfg = self._as_dict(custom_cfg.get(section_key))
            group = QGroupBox(section_key)
            group_layout = QVBoxLayout(group)
            form = QFormLayout()
            menu_label = QLineEdit(str(section_cfg.get("menu_label", "")))
            menu_label.setMinimumWidth(HYBRID_FIELD_MIN_WIDTH)
            form.addRow("Menu label", menu_label)
            group_layout.addLayout(form)

            table = self._make_table(["Label", "Group", "Tags"])
            self._configure_custom_tags_table_columns(table)
            table.setMinimumHeight(max(150, HYBRID_CUSTOM_TAGS_MIN_ROWS * 34))
            for preset in self._as_list(section_cfg.get("presets")):
                preset_dict = self._as_dict(preset)
                self._add_table_row(
                    table,
                    [
                        preset_dict.get("label", ""),
                        preset_dict.get("group", ""),
                        self._join_lines(preset_dict.get("tags", [])),
                    ],
                )
            if table.rowCount() == 0:
                self._add_table_row(table, ["", "", ""])
            group_layout.addWidget(table)

            buttons = QHBoxLayout()
            add_button = QPushButton("Add Preset")
            add_button.clicked.connect(lambda _checked=False, target=table: self._add_table_row(target))
            buttons.addWidget(add_button)
            remove_button = QPushButton("Remove Selected")
            remove_button.clicked.connect(
                lambda _checked=False, target=table: self._remove_selected_table_rows(target)
            )
            buttons.addWidget(remove_button)
            buttons.addStretch(1)
            group_layout.addLayout(buttons)
            layout.addWidget(group)
            self.custom_tag_sections.append(HybridCustomTagsSection(section_key, menu_label, table))

        layout.addStretch(1)
        return tab

    def _build_merge_tab(self) -> QWidget:
        tab, layout = self._new_scroll_tab()

        merge_tags = self._add_group(layout, "Merge Tags")
        self._add_line(merge_tags, "Result tag", "merge_tags_config", ("base_tag",))
        self._add_line(merge_tags, "Comparison field", "merge_tags_config", ("comparison_field",))
        self._add_bool(merge_tags, "Only selected notes", "merge_tags_config", ("merge_select_only",))
        self._add_bool(merge_tags, "Ask fuzzy threshold each time", "merge_tags_config", ("ask_fuzzy_each_time",))
        self._add_text_list(merge_tags, "Only merge parent tags", "merge_tags_config", ("merge_only_parents",))
        self._add_text_list(merge_tags, "Excluded tags", "merge_tags_config", ("excluded_tags",))

        merge_images = self._add_group(layout, "Merge Images")
        self._add_text_list(merge_images, "Allowed note types", "merge_images_config", ("allowed_models",))
        self._add_text_list(
            merge_images,
            "Fields to scan for images",
            "merge_images_config",
            ("fields_to_scan_for_images",),
        )
        self._add_text_list(merge_images, "Excluded tags", "merge_images_config", ("excluded_tags",))
        self._add_bool(
            merge_images,
            "Copy Sketchy links",
            "merge_images_config",
            ("merge_behavior", "copy_sketchy_links"),
            True,
        )
        self._add_bool(
            merge_images,
            "Show log popup",
            "merge_images_config",
            ("logging", "enable_log_popup"),
            True,
        )
        self._add_bool(
            merge_images,
            "Save log to desktop",
            "merge_images_config",
            ("logging", "save_log_to_desktop"),
            True,
        )
        self._add_line(
            merge_images,
            "Log filename prefix",
            "merge_images_config",
            ("logging", "log_filename_prefix"),
        )
        for key, label in (
            ("add_to_merged", "Merged tag"),
            ("add_to_donor", "Donor tag"),
            ("add_to_unchanged", "Unchanged tag"),
            ("no_images_found", "No images found tag"),
        ):
            self._add_line(merge_images, label, "merge_images_config", ("tagging", key))

        scheduling = self._add_group(layout, "Merge Scheduling")
        self._add_int(
            scheduling,
            "Similarity threshold",
            "merge_scheduling",
            ("merge_similarity_threshold",),
            0,
            100,
            85,
        )
        self._add_int(scheduling, "Merge field index", "merge_scheduling", ("merge_field_index",), 0, 100, 0)
        self._add_combo(
            scheduling,
            "Multi-card policy",
            "merge_scheduling",
            ("multi_card_policy",),
            ["skip", "first", "all"],
            "skip",
        )
        self._add_bool(scheduling, "Use text replacements", "merge_scheduling", ("use_text_replacements",), True)
        self._add_line(scheduling, "Log path", "merge_scheduling", ("scheduling_merge_log_path",))
        self._add_line(scheduling, "Tag on merge", "merge_scheduling", ("tag_on_merge",))
        layout.addStretch(1)
        return tab

    def _build_add_css_class_tab(self) -> QWidget:
        tab, layout = self._new_scroll_tab()

        table_class = self._add_group(layout, "Tables")
        self._add_bool(table_class, "Apply to existing classes", "add_table_class", ("apply_to_existing_classes",), True)
        self._add_line(table_class, "Log path", "add_table_class", ("log_path",))

        image_class = self._add_group(layout, "Images")
        self._add_int(image_class, "Small width", "add_img_class", ("small_width",), 1, 10000, 340)
        self._add_float(image_class, "Square min ratio", "add_img_class", ("square_min",), 0.0, 10.0, fallback=0.9)
        self._add_float(image_class, "Square max ratio", "add_img_class", ("square_max",), 0.0, 10.0, fallback=1.19)
        self._add_float(image_class, "Tall ratio", "add_img_class", ("tall_ratio",), 0.0, 10.0, fallback=0.9)
        self._add_float(
            image_class,
            "Landscape min ratio",
            "add_img_class",
            ("landscape_ratio_min",),
            0.0,
            10.0,
            fallback=1.19,
        )
        self._add_float(
            image_class,
            "Ultra-wide ratio",
            "add_img_class",
            ("ultra-wide_ratio",),
            0.0,
            10.0,
            fallback=1.9,
        )
        layout.addStretch(1)
        return tab

    def _build_other_tab(self) -> QWidget:
        tab, layout = self._new_scroll_tab()

        delete_notes = self._add_group(layout, "Delete Empty Notes")
        self._add_text_list(
            delete_notes,
            "Protected note types",
            "delete_empty_notes_config",
            ("protected_notes",),
        )

        batch = self._add_group(layout, "Batch Note Change")
        self._add_bool(batch, "Allow single type override", "batch_note_change_config", ("allow_single_type_override",), True)
        self._add_bool(
            batch,
            "Hide menu when one type selected",
            "batch_note_change_config",
            ("hide_menu_when_one_type_selected",),
        )
        self._add_bool(batch, "Auto-confirm mappings", "batch_note_change_config", ("auto_confirm_mappings",))
        self._add_bool(batch, "Show progress", "batch_note_change_config", ("show_progress",), True)
        self._add_bool(batch, "Enable backup", "batch_note_change_config", ("enable_backup",), True)
        self._add_int(batch, "Batch size", "batch_note_change_config", ("batch_size",), 1, 100000, 200)
        self._add_line(batch, "Backup directory", "batch_note_change_config", ("backup_directory",))
        self._add_line(batch, "Last target model", "batch_note_change_config", ("last_target_model",))
        self._add_line(batch, "Last mapping profile", "batch_note_change_config", ("last_mapping_profile",))
        self._add_line(batch, "Tag on change", "batch_note_change_config", ("tag_on_change",))

        dupes = self._add_group(layout, "Tag Duplicates")
        self._add_line(dupes, "Base tag", "tag_dupes_config", ("base_tag",))
        self._add_line(dupes, "Comparison field", "tag_dupes_config", ("comparison_field",))
        self._add_line(dupes, "Multiple tag child", "tag_dupes_config", ("multi_tag_child",))
        self._add_bool(dupes, "Tag unmatched", "tag_dupes_config", ("tag_unmatched",), True)
        self._add_line(dupes, "Unmatched tag", "tag_dupes_config", ("unmatched_tag",))
        layout.addStretch(1)
        return tab

    def _binding_value(self, binding: HybridFieldBinding) -> Any:
        widget = binding.widget
        if binding.kind == "line":
            return widget.text().strip() if isinstance(widget, QLineEdit) else ""
        if binding.kind == "bool":
            return bool(widget.isChecked()) if isinstance(widget, QCheckBox) else False
        if binding.kind == "int":
            return int(widget.value()) if isinstance(widget, QSpinBox) else 0
        if binding.kind == "float":
            return float(widget.value()) if isinstance(widget, QDoubleSpinBox) else 0.0
        if binding.kind == "combo":
            return widget.currentText().strip() if isinstance(widget, QComboBox) else ""
        if binding.kind == "string_list":
            return self._split_lines(widget.toPlainText()) if isinstance(widget, QTextEdit) else []
        return None

    def _validate_date(self, value: str, label: str, show_errors: bool = True) -> bool:
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except Exception:
            if show_errors:
                showInfo(f"{label} must use YYYY-MM-DD.")
            return False

    def _collect_rotation_schedule(self, show_errors: bool = True) -> list[dict[str, str]] | None:
        table = self.rotation_schedule_table
        if table is None:
            return []

        schedule: list[dict[str, str]] = []
        for row in range(table.rowCount()):
            segment_label = self._table_text(table, row, 0)
            start = self._table_text(table, row, 1)
            end = self._table_text(table, row, 2)
            if not segment_label and not start and not end:
                continue
            if not segment_label or not start or not end:
                if show_errors:
                    showInfo("Each rotation schedule row needs Segment Label, Start, and End.")
                return None
            if not self._validate_date(start, f"Rotation row {row + 1} start", show_errors):
                return None
            if not self._validate_date(end, f"Rotation row {row + 1} end", show_errors):
                return None
            if start > end:
                if show_errors:
                    showInfo(f"Rotation row {row + 1} starts after it ends.")
                return None
            schedule.append({"segment_label": segment_label, "start": start, "end": end})
        return schedule

    def _collect_custom_tags(self, sections: dict[str, dict[str, Any]], show_errors: bool = True):
        custom_cfg = sections.setdefault(CUSTOM_TAGS_CANONICAL_SECTION, {})
        for custom_section in self.custom_tag_sections:
            existing = self._as_dict(custom_cfg.get(custom_section.section_key))
            updated = copy.deepcopy(existing)
            updated["menu_label"] = custom_section.menu_label.text().strip()
            presets: list[dict[str, Any]] = []
            table = custom_section.table
            for row in range(table.rowCount()):
                label = self._table_text(table, row, 0)
                group = self._table_text(table, row, 1)
                tags = self._split_tags(self._table_text(table, row, 2))
                if not label and not group and not tags:
                    continue
                if not label or not tags:
                    if show_errors:
                        showInfo(
                            f"Custom tag section '{custom_section.section_key}' row {row + 1} needs a label and at least one tag."
                        )
                    return False
                preset: dict[str, Any] = {"label": label, "tags": tags}
                if group:
                    preset["group"] = group
                presets.append(preset)
            updated["presets"] = presets
            custom_cfg[custom_section.section_key] = updated
        return True

    def _collect_sections_from_form(self, show_errors: bool = True) -> dict[str, dict[str, Any]] | None:
        sections: dict[str, dict[str, Any]] = {}
        for section_key in HYBRID_FORM_SECTION_KEYS:
            sections[section_key] = copy.deepcopy(self._get_section(section_key))

        for binding in self.bindings:
            section = sections.setdefault(binding.section_key, {})
            self._set_path(section, binding.path, self._binding_value(binding))

        missed = sections.setdefault(MISSED_TAGS_CANONICAL_SECTION, {})
        if "rotation" in missed:
            rotation_cfg = missed.pop("rotation")
            block_cfg = self._as_dict(missed.get("block"))
            missed["block"] = self.config_manager_cls.deep_merge_dicts(
                self._as_dict(rotation_cfg),
                block_cfg,
            )

        schedule = self._collect_rotation_schedule(show_errors)
        if schedule is None:
            return None
        self._set_path(missed, ("block", "schedule"), schedule)

        if not self._collect_custom_tags(sections, show_errors):
            return None

        global_cfg = sections.get("global_config", {})
        fuzzy = self._as_dict(global_cfg.get("fuzzy_opts"))
        if float(fuzzy.get("min_fuzz", 0)) > float(fuzzy.get("default_fuzz", 1)):
            if show_errors:
                showInfo("Minimum fuzzy threshold cannot be greater than the default fuzzy threshold.")
            return None

        img_cfg = sections.get("add_img_class", {})
        if float(img_cfg.get("square_min", 0)) > float(img_cfg.get("square_max", 0)):
            if show_errors:
                showInfo("Image square min ratio cannot be greater than square max ratio.")
            return None

        return sections

    def _refresh_form_snapshot(self):
        sections = self._collect_sections_from_form(show_errors=False)
        self._last_loaded_form_sections = sections if sections is not None else {}

    def _has_unsaved_form_changes(self) -> bool:
        sections = self._collect_sections_from_form(show_errors=False)
        if sections is None:
            return True
        return sections != self._last_loaded_form_sections

    def save_and_close(self):
        sections = self._collect_sections_from_form()
        if sections is None:
            return
        try:
            for section_key in HYBRID_FORM_SECTION_KEYS:
                self.config_manager_cls.save_section_override(section_key, sections.get(section_key, {}))
        except Exception as exc:
            showInfo(f"Failed to save settings: {exc}")
            return
        self.accept()

    def restore_defaults(self):
        if not askUser(HYBRID_RESTORE_CONFIRM_TEXT):
            return
        try:
            for section_key in HYBRID_FORM_SECTION_KEYS:
                self.config_manager_cls.clear_section_override(section_key)
        except Exception as exc:
            showInfo(f"Failed to restore defaults: {exc}")
            return
        self.reload_from_config()
        showInfo(HYBRID_RESTORE_SUCCESS_TEXT)

    def open_advanced_editor(self):
        """Open Anki's built-in JSON config editor and close this friendly window."""
        if self._has_unsaved_form_changes() and not askUser(HYBRID_ADVANCED_DISCARD_CONFIRM_TEXT):
            return

        try:
            from aqt.addons import ConfigEditor
        except Exception as exc:
            showInfo(f"Could not open Anki's default config editor: {exc}")
            return

        try:
            current_config = mw.addonManager.getConfig(self.addon_name) or {}
            advanced = ConfigEditor(self, self.addon_name, current_config)
        except Exception as exc:
            showInfo(f"Could not open Anki's default config editor: {exc}")
            return

        self._advanced_config_editor = advanced
        self._suppress_focus_restore = True
        mw._change_notes_advanced_config_editor = advanced
        mw._change_notes_hybrid_config_dialog = self

        def _on_advanced_finished(_result: int):
            self._suppress_focus_restore = False
            self._advanced_config_editor = None
            if getattr(mw, "_change_notes_advanced_config_editor", None) is advanced:
                delattr(mw, "_change_notes_advanced_config_editor")
            if getattr(mw, "_change_notes_hybrid_config_dialog", None) is self:
                delattr(mw, "_change_notes_hybrid_config_dialog")
            self.deleteLater()

        advanced.finished.connect(_on_advanced_finished)
        advanced.show()
        QTimer.singleShot(0, self._raise_advanced_editor)
        QTimer.singleShot(100, self._raise_advanced_editor)
        QTimer.singleShot(300, self._raise_advanced_editor)
        QTimer.singleShot(0, self.accept)


class ConfigDialog(QDialog):
    """Category-based config editor with per-section JSON override panes."""

    def __init__(self, addon_name: str, config_manager_cls, parent=None):
        parent_window = parent or mw.app.activeModalWidget() or mw.app.activeWindow() or mw
        super().__init__(parent_window)
        self.addon_name = addon_name
        self.config_manager_cls = config_manager_cls
        self.config_manager = config_manager_cls("_Change_notes")

        self._section_tabs: dict[str, SectionTabState] = {}
        self._category_tabs: dict[int, CategoryTabState] = {}
        self._section_locations: dict[str, tuple[int, int]] = {}
        self._location_sections: dict[tuple[int, int], str] = {}
        self._visible_sections: list[str] = []
        self._active_section_key: str | None = None
        self._reverting_tab_change = False
        self._migration_notice: str | None = None
        self._skip_save_on_close = False

        self.setWindowTitle(f"{addon_name} Add-on Configuration")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        screen = mw.app.primaryScreen().availableGeometry()
        self.setGeometry(
            screen.x() + WINDOW_MARGIN,
            screen.y() + WINDOW_MARGIN,
            screen.width() - 2 * WINDOW_MARGIN,
            screen.height() - 2 * WINDOW_MARGIN,
        )

        main_layout = QVBoxLayout()

        controls_row = QHBoxLayout()
        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.reload_config)
        controls_row.addWidget(reload_button)

        save_all_button = QPushButton(SAVE_ALL_BUTTON_TEXT)
        save_all_button.clicked.connect(self.save_all_tabs)
        controls_row.addWidget(save_all_button)

        restore_all_button = QPushButton("Restore All Defaults")
        restore_all_button.clicked.connect(self.restore_all_defaults)
        controls_row.addWidget(restore_all_button)

        controls_row.addStretch(1)
        main_layout.addLayout(controls_row)

        self.status_label = QLabel(STATUS_DEFAULT_TEXT)
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

        self.category_tabs = QTabWidget()
        self.category_tabs.setObjectName("category_tabs")
        self.category_tabs.currentChanged.connect(self._on_category_changed)
        self._configure_tab_widget_for_full_labels(self.category_tabs)
        main_layout.addWidget(self.category_tabs, stretch=1)

        bottom_buttons_row = QHBoxLayout()
        bottom_buttons_row.addStretch(1)

        cancel_button = QPushButton(CANCEL_BUTTON_TEXT)
        cancel_button.clicked.connect(self._on_cancel_clicked)
        bottom_buttons_row.addWidget(cancel_button)

        save_close_button = QPushButton(SAVE_CLOSE_BUTTON_TEXT)
        save_close_button.clicked.connect(self._on_save_and_close_clicked)
        save_close_button.setDefault(True)
        bottom_buttons_row.addWidget(save_close_button)

        main_layout.addLayout(bottom_buttons_row)

        self.setLayout(main_layout)
        self.reload_config()

    def _addon_base_path(self) -> str:
        return os.path.join(mw.addonManager.addonsFolder(), self.addon_name)

    def _slug(self, value: str) -> str:
        return value.strip().lower().replace(" ", "_").replace("-", "_")

    def _relative_doc_path_for_category(self, category_name: str) -> str:
        doc_name = CATEGORY_DOC_FILES.get(category_name, "")
        return os.path.join(TAB_MD_DIRECTORY, doc_name) if doc_name else TAB_MD_DIRECTORY

    @staticmethod
    def _rgba(color, alpha: float) -> str:
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha:.3f})"

    def _help_doc_shell_css(self) -> str:
        palette = self.palette() or mw.app.palette()
        window = palette.color(QPalette.ColorRole.Window)
        text = palette.color(QPalette.ColorRole.Text)
        link = palette.color(QPalette.ColorRole.Link)
        base = palette.color(QPalette.ColorRole.Base)

        return (
            "body {"
            f"background-color: {window.name()};"
            f"color: {text.name()};"
            f"margin: 0; padding: {HELP_DOC_PADDING_PX}px;"
            f"font-size: {HELP_DOC_FONT_SIZE_PX}px;"
            f"line-height: {HELP_DOC_LINE_HEIGHT};"
            "}"
            "h1, h2, h3 { margin-top: 0.7em; margin-bottom: 0.28em; }"
            "p, ul, ol, pre { margin-top: 0.24em; margin-bottom: 0.52em; }"
            f"a {{ color: {link.name()}; text-decoration: {HELP_DOC_LINK_DECORATION}; }}"
            "code {"
            f"background-color: {self._rgba(base, HELP_DOC_CODE_BG_ALPHA)};"
            "padding: 1px 3px; border-radius: 3px;"
            "}"
            "pre {"
            f"background-color: {self._rgba(base, HELP_DOC_PRE_BG_ALPHA)};"
            f"border: 1px solid {self._rgba(text, HELP_DOC_PRE_BORDER_ALPHA)};"
            "padding: 6px 8px; border-radius: 4px; overflow-x: auto;"
            "}"
            "hr { border: 0; border-top: 1px solid rgba(127,127,127,0.28); margin: 0.75em 0; }"
        )

    def _render_help_html(self, markdown_source: str) -> str:
        rendered_body = markdown.markdown(
            markdown_source,
            extensions=list(HELP_MARKDOWN_EXTENSIONS),
        )
        css = self._help_doc_shell_css()
        return f"<html><head><style>{css}</style></head><body>{rendered_body}</body></html>"

    def _load_category_doc_html(self, category_name: str) -> str:
        doc_name = CATEGORY_DOC_FILES.get(category_name)
        markdown_source = ""
        if not doc_name:
            markdown_source = DOC_MISSING_TEMPLATE.format(
                category=category_name,
                relative_path=self._relative_doc_path_for_category(category_name),
            )
            return self._render_help_html(markdown_source)

        relative_doc_path = os.path.join(TAB_MD_DIRECTORY, doc_name)
        full_doc_path = os.path.join(self._addon_base_path(), relative_doc_path)

        try:
            if not os.path.exists(full_doc_path):
                markdown_source = DOC_MISSING_TEMPLATE.format(
                    category=category_name,
                    relative_path=relative_doc_path,
                )
                return self._render_help_html(markdown_source)

            with open(full_doc_path, "r", encoding="utf-8") as file:
                raw_markdown = file.read().strip()

            if not raw_markdown:
                markdown_source = DOC_EMPTY_TEMPLATE.format(
                    category=category_name,
                    relative_path=relative_doc_path,
                )
                return self._render_help_html(markdown_source)

            return self._render_help_html(raw_markdown)
        except Exception as exc:
            markdown_source = DOC_LOAD_ERROR_TEMPLATE.format(
                category=category_name,
                error=html.escape(str(exc)),
            )
            return self._render_help_html(markdown_source)

    def _configure_tab_widget_for_full_labels(self, tab_widget: QTabWidget):
        tab_bar = tab_widget.tabBar()
        tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
        tab_bar.setExpanding(False)
        tab_bar.setUsesScrollButtons(True)

    def _apply_tab_width_constraints(self):
        self._configure_tab_widget_for_full_labels(self.category_tabs)
        category_tabs_min_width = TAB_WIDGET_BASE_MIN_WIDTH
        self.category_tabs.tabBar().setMinimumWidth(max(0, category_tabs_min_width - TAB_WIDGET_CHROME_WIDTH))
        self.category_tabs.setMinimumWidth(category_tabs_min_width)
        for category_state in self._category_tabs.values():
            section_tabs = category_state.section_tabs
            self._configure_tab_widget_for_full_labels(section_tabs)
            section_tabs_min_width = TAB_WIDGET_BASE_MIN_WIDTH
            section_tabs.tabBar().setMinimumWidth(max(0, section_tabs_min_width - TAB_WIDGET_CHROME_WIDTH))
            section_tabs.setMinimumWidth(section_tabs_min_width)

    def _display_label_for_section(self, section_key: str) -> str:
        metadata = SECTION_UI_METADATA.get(section_key, {})
        configured_label = metadata.get("label")
        if isinstance(configured_label, str) and configured_label.strip():
            return configured_label.strip()

        base = section_key[:-7] if section_key.endswith("_config") else section_key
        words = [part for part in base.replace("-", "_").split("_") if part]
        if not words:
            return section_key
        pretty = [ACRONYM_WORDS.get(word.lower(), word.capitalize()) for word in words]
        return " ".join(pretty)

    def _append_migration_notice(self, message: str):
        text = message.strip()
        if not text:
            return
        if self._migration_notice:
            self._migration_notice = f"{self._migration_notice} {text}"
        else:
            self._migration_notice = text

    def _sanitize_override_payload(self, section_key: str, payload: Any) -> dict[str, Any]:
        return self.config_manager_cls.sanitize_section_override(section_key, payload)

    def _ordered_visible_sections(self) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for _, section_keys in CATEGORY_SECTION_MAP:
            for section_key in section_keys:
                if section_key in seen:
                    continue
                if section_key in HIDDEN_LEGACY_SECTIONS:
                    continue
                ordered.append(section_key)
                seen.add(section_key)
        return ordered

    def _run_startup_migrations(self) -> bool:
        _, notices, changed = self.config_manager_cls.migrate_overrides_once()
        for notice in notices:
            self._append_migration_notice(notice)
        return changed

    def _set_status_for_section(self, section_key: str | None):
        prefix = ""
        if self._migration_notice:
            prefix = self._migration_notice + " "
            self._migration_notice = None

        if not section_key:
            self.status_label.setText(prefix + STATUS_NO_SECTIONS_TEXT)
            return

        if self.config_manager.last_load_errors:
            errs = "; ".join(self.config_manager.last_load_errors[:MAX_STATUS_WARNINGS])
            self.status_label.setText(
                prefix + f"Section '{section_key}'. Defaults from config.json. Load warnings: {errs}"
            )
            return

        self.status_label.setText(
            prefix + f"Section '{section_key}'. Edits are local until Save All or closing this window."
        )

    def _create_section_tab(self, section_key: str) -> SectionTabState:
        tab_container = QWidget()
        tab_container.setObjectName(f"section_container__{self._slug(section_key)}")
        tab_layout = QVBoxLayout(tab_container)

        tab_layout.addWidget(QLabel(SECTION_EDITOR_LABEL))
        override_editor = QTextEdit()
        override_editor.setObjectName(f"override_editor__{self._slug(section_key)}")
        override_editor.setMinimumSize(OVERRIDE_EDITOR_MIN_WIDTH, OVERRIDE_EDITOR_MIN_HEIGHT)
        tab_layout.addWidget(override_editor, stretch=1)

        restore_button = QPushButton(SECTION_RESTORE_BUTTON_TEXT)
        restore_button.clicked.connect(
            lambda _checked=False, key=section_key: self.restore_section_defaults(key)
        )
        tab_layout.addWidget(restore_button)

        return SectionTabState(
            section_key=section_key,
            container=tab_container,
            override_editor=override_editor,
        )

    def _refresh_section_editor(self, section_key: str, refresh_override_editor: bool):
        state = self._section_tabs.get(section_key)
        if not state:
            return

        override_section = self._sanitize_override_payload(
            section_key,
            self.config_manager_cls.get_override_section(section_key),
        )
        if refresh_override_editor:
            state.override_editor.setPlainText(
                json.dumps(override_section, indent=JSON_INDENT, ensure_ascii=False)
            )

    def _no_sections_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel("No configured sections in this category.")
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)
        return widget

    def _create_category_tab(
        self,
        category_index: int,
        category_name: str,
        section_keys: list[str],
    ) -> CategoryTabState:
        container = QWidget()
        layout = QVBoxLayout(container)

        section_tabs = QTabWidget()
        section_tabs.setObjectName(f"section_tabs__{self._slug(category_name)}")
        section_tabs.currentChanged.connect(
            lambda _index, cat_idx=category_index: self._on_section_tab_changed(cat_idx)
        )
        self._configure_tab_widget_for_full_labels(section_tabs)

        for section_key in section_keys:
            if section_key not in self._visible_sections:
                continue

            section_state = self._create_section_tab(section_key)
            self._section_tabs[section_key] = section_state
            sub_index = section_tabs.addTab(
                section_state.container,
                self._display_label_for_section(section_key),
            )
            section_tabs.setTabToolTip(sub_index, section_key)
            self._section_locations[section_key] = (category_index, sub_index)
            self._location_sections[(category_index, sub_index)] = section_key
            self._refresh_section_editor(section_key, refresh_override_editor=True)

        help_view = QTextEdit(container)
        help_view.setObjectName(f"help_view__{self._slug(category_name)}")
        help_view.setReadOnly(True)
        help_view.setMinimumWidth(CATEGORY_HELP_MIN_WIDTH)
        help_view.setHtml(self._load_category_doc_html(category_name))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName(f"category_splitter__{self._slug(category_name)}")
        if section_tabs.count() == 0:
            splitter.addWidget(self._no_sections_widget())
        else:
            splitter.addWidget(section_tabs)
        splitter.addWidget(help_view)

        left_size = int(self.width() * CATEGORY_SPLITTER_LEFT_RATIO)
        right_size = max(CATEGORY_HELP_MIN_WIDTH, self.width() - left_size)
        splitter.setSizes([left_size, right_size])

        layout.addWidget(splitter)

        return CategoryTabState(
            name=category_name,
            container=container,
            section_tabs=section_tabs,
            help_view=help_view,
        )

    def _rebuild_category_tabs(self, preferred_section_key: str | None):
        self.category_tabs.blockSignals(True)
        self.category_tabs.clear()
        self._section_tabs.clear()
        self._category_tabs.clear()
        self._section_locations.clear()
        self._location_sections.clear()

        for category_index, (category_name, section_keys) in enumerate(CATEGORY_SECTION_MAP):
            category_state = self._create_category_tab(category_index, category_name, section_keys)
            self._category_tabs[category_index] = category_state
            self.category_tabs.addTab(category_state.container, category_name)

        self._apply_tab_width_constraints()
        self.category_tabs.blockSignals(False)

        if not self._section_locations:
            self._active_section_key = None
            self._set_status_for_section(None)
            return

        if preferred_section_key not in self._section_locations:
            preferred_section_key = self._visible_sections[0] if self._visible_sections else None

        if preferred_section_key:
            self._select_section(preferred_section_key)
            self._set_status_for_section(preferred_section_key)

    def _section_key_from_current_selection(self) -> str | None:
        category_index = self.category_tabs.currentIndex()
        if category_index < 0:
            return None

        category_state = self._category_tabs.get(category_index)
        if not category_state:
            return None

        sub_index = category_state.section_tabs.currentIndex()
        if sub_index < 0:
            return None

        return self._location_sections.get((category_index, sub_index))

    def _select_section(self, section_key: str) -> bool:
        location = self._section_locations.get(section_key)
        if location is None:
            return False

        category_index, sub_index = location
        category_state = self._category_tabs.get(category_index)
        if not category_state:
            return False

        self._reverting_tab_change = True

        self.category_tabs.blockSignals(True)
        self.category_tabs.setCurrentIndex(category_index)
        self.category_tabs.blockSignals(False)

        category_state.section_tabs.blockSignals(True)
        category_state.section_tabs.setCurrentIndex(sub_index)
        category_state.section_tabs.blockSignals(False)

        self._reverting_tab_change = False
        self._active_section_key = section_key
        return True

    def _parse_override_from_editor(self, section_key: str) -> tuple[bool, dict | str]:
        state = self._section_tabs.get(section_key)
        if not state:
            return False, f"Section '{section_key}' is unavailable."

        raw_text = state.override_editor.toPlainText().strip()
        try:
            parsed = json.loads(raw_text or "{}")
        except json.JSONDecodeError as exc:
            return (
                False,
                (f"Invalid JSON in '{section_key}'. Line {exc.lineno}, column {exc.colno}: {exc.msg}"),
            )

        if not isinstance(parsed, dict):
            return False, f"Section override for '{section_key}' must be a JSON object."

        return True, parsed

    def _collect_parsed_overrides(self) -> tuple[bool, dict[str, dict] | str, str | None]:
        parsed_overrides: dict[str, dict] = {}
        for section_key in self._visible_sections:
            ok, payload_or_error = self._parse_override_from_editor(section_key)
            if not ok:
                return False, str(payload_or_error), section_key
            parsed_overrides[section_key] = payload_or_error
        return True, parsed_overrides, None

    def _has_unsaved_editor_changes(self) -> bool:
        for section_key in self._visible_sections:
            state = self._section_tabs.get(section_key)
            if not state:
                continue

            ok, payload_or_error = self._parse_override_from_editor(section_key)
            if not ok:
                # Invalid JSON is still an unsaved editor state.
                return True

            editor_override = self._sanitize_override_payload(section_key, payload_or_error)
            saved_override = self._sanitize_override_payload(
                section_key,
                self.config_manager_cls.get_override_section(section_key),
            )
            if editor_override != saved_override:
                return True

        return False

    def _write_visible_overrides(self, parsed_overrides: dict[str, dict]) -> tuple[bool, str | None]:
        try:
            existing_overrides = self.config_manager_cls.load_raw_overrides()
            merged_overrides = (
                copy.deepcopy(existing_overrides) if isinstance(existing_overrides, dict) else {}
            )

            for section_key, override in parsed_overrides.items():
                cleaned_override = self._sanitize_override_payload(section_key, override)
                if PRUNE_EMPTY_SECTION_OVERRIDES and not cleaned_override:
                    merged_overrides.pop(section_key, None)
                else:
                    merged_overrides[section_key] = cleaned_override

            merged_overrides, _ = self.config_manager_cls.prune_redundant_overrides(merged_overrides)

            if merged_overrides != existing_overrides:
                mw.addonManager.writeConfig(
                    self.config_manager_cls.ROOT_ADDON_NAME,
                    merged_overrides,
                )

            self.config_manager.reload()
            for section_key in self._visible_sections:
                self._refresh_section_editor(section_key, refresh_override_editor=True)
            self._set_status_for_section(self._active_section_key)
            return True, None
        except Exception as exc:
            return False, f"Failed to save visible sections: {exc}"

    def _save_all_from_editors(self, announce_success: bool) -> bool:
        if not self._visible_sections:
            return True

        ok, payload_or_error, error_section = self._collect_parsed_overrides()
        if not ok:
            if error_section:
                self._select_section(error_section)
            showInfo(str(payload_or_error))
            return False

        saved, error = self._write_visible_overrides(payload_or_error)
        if not saved:
            showInfo(error or "Failed to save all tabs.")
            return False

        if announce_success:
            showInfo(SAVE_ALL_SUCCESS_TEXT)
        return True

    def _reload_config_from_storage(self):
        current_section_key = self._active_section_key
        self._run_startup_migrations()
        self.config_manager.reload()

        self._visible_sections = self._ordered_visible_sections()
        self._rebuild_category_tabs(current_section_key)

    def reload_config(self):
        if self._has_unsaved_editor_changes() and not askUser(RELOAD_CONFIRM_TEXT):
            return
        self._reload_config_from_storage()

    def _handle_section_change(self):
        if self._reverting_tab_change:
            return

        new_section_key = self._section_key_from_current_selection()
        previous_section_key = self._active_section_key

        if previous_section_key and previous_section_key != new_section_key:
            valid, payload_or_error = self._parse_override_from_editor(previous_section_key)
            if not valid:
                showInfo(str(payload_or_error))
                self._select_section(previous_section_key)
                return

        self._active_section_key = new_section_key
        self._set_status_for_section(self._active_section_key)
        if RESTORE_FOCUS_ON_TAB_CHANGE:
            QTimer.singleShot(0, self._restore_dialog_focus)

    def _restore_dialog_focus(self):
        if not self.isVisible():
            return
        self.raise_()
        self.activateWindow()

    def _on_category_changed(self, _new_index: int):
        self._handle_section_change()

    def _on_section_tab_changed(self, _category_index: int):
        self._handle_section_change()

    def save_all_tabs(self):
        if not self._visible_sections:
            showInfo("No sections available to save.")
            return
        self._save_all_from_editors(announce_success=True)

    def _on_cancel_clicked(self):
        self._skip_save_on_close = True
        self.close()

    def _on_save_and_close_clicked(self):
        if not self._save_all_from_editors(announce_success=False):
            return
        self._skip_save_on_close = True
        self.close()

    def restore_section_defaults(self, section_key: str):
        if not section_key:
            return

        state = self._section_tabs.get(section_key)
        if not state:
            return

        state.override_editor.setPlainText(json.dumps({}, indent=JSON_INDENT, ensure_ascii=False))
        if self._active_section_key != section_key:
            self._active_section_key = section_key
            self._select_section(section_key)
        self._set_status_for_section(self._active_section_key)
        showInfo(
            f"Reset '{section_key}' editor to defaults in-memory. Save All or close this window to persist."
        )

    def restore_all_defaults(self):
        if not askUser(RESTORE_ALL_CONFIRM_TEXT):
            return

        for section_key in self._visible_sections:
            state = self._section_tabs.get(section_key)
            if not state:
                continue
            state.override_editor.setPlainText(json.dumps({}, indent=JSON_INDENT, ensure_ascii=False))

        self._set_status_for_section(self._active_section_key)
        if AUTO_SAVE_ON_RESTORE_ALL:
            if not self._save_all_from_editors(announce_success=False):
                return
            showInfo(RESTORE_ALL_SUCCESS_TEXT)
            return

        showInfo(RESTORE_ALL_IN_MEMORY_TEXT)

    def closeEvent(self, event):
        if self._skip_save_on_close:
            event.accept()
            return
        if self._save_all_from_editors(announce_success=False):
            event.accept()
        else:
            event.ignore()

    def reject(self):
        self.close()
