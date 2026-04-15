import copy
import html
import json
import os
from dataclasses import dataclass
from typing import Any

import markdown
from aqt import mw
from aqt.qt import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPalette,
    QPushButton,
    QSplitter,
    Qt,
    QTabWidget,
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

MISSED_TAGS_CANONICAL_SECTION = "tag_missed_qid_notes"
ADD_CUSTOM_TAGS_SECTION = "add_custom_tags"
ADD_CUSTOM_TAGS_SECTION_2 = "add_custom_tags_2"

CATEGORY_SECTION_MAP: list[tuple[str, list[str]]] = [
    (
        "Global",
        [
            "global_config",
            "global_fuzzy_opts",
        ],
    ),
    (
        "Custom Tags",
        [
            "add_custom_tags",
            "add_custom_tags_2",
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
    "add_missed_tags",
    "tag_selected_notes_config",
    "add_tags",
    "merge_scheduling_config",
}

SECTION_UI_METADATA: dict[str, dict[str, Any]] = {
    "global_config": {"label": "Global Config", "form_schema": None},
    "global_fuzzy_opts": {"label": "Global Fuzzy Options", "form_schema": None},
    "add_custom_tags": {"label": "Add Custom Tags", "form_schema": None},
    "add_custom_tags_2": {"label": "Add Custom Tags 2", "form_schema": None},
    MISSED_TAGS_CANONICAL_SECTION: {"label": "Tag Missed QID Notes", "form_schema": None},
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
