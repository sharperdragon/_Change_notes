import json
import os

import markdown
from aqt import mw
from aqt.qt import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    Qt,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import askUser, showInfo


class ConfigDialog(QDialog):
    """Section-aware config editor: defaults vs overrides vs effective values."""

    def __init__(self, addon_name: str, config_manager_cls, parent=None):
        super().__init__(parent or mw)
        self.addon_name = addon_name
        self.config_manager_cls = config_manager_cls
        self.config_manager = config_manager_cls("_Change_notes")

        self.setWindowTitle(f"{addon_name} Add-on Configuration")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        screen = mw.app.primaryScreen().availableGeometry()
        margin = 100
        self.setGeometry(
            screen.x() + margin,
            screen.y() + margin,
            screen.width() - 2 * margin,
            screen.height() - 2 * margin,
        )

        main_layout = QVBoxLayout()

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Section:"))
        self.section_selector = QComboBox()
        self.section_selector.currentTextChanged.connect(self._on_section_changed)
        top_row.addWidget(self.section_selector, stretch=1)

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.reload_config)
        top_row.addWidget(reload_button)
        main_layout.addLayout(top_row)

        self.status_label = QLabel(
            "Defaults source: configs/*.json | Editable source: Anki profile override."
        )
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("Section Override (editable JSON object)"))
        self.override_editor = QTextEdit()
        self.override_editor.setMinimumSize(260, 220)
        left_layout.addWidget(self.override_editor, stretch=1)

        button_row = QHBoxLayout()
        save_button = QPushButton("Save Section Override")
        save_button.clicked.connect(self.save_section_override)
        button_row.addWidget(save_button)

        restore_button = QPushButton("Restore Section Defaults")
        restore_button.clicked.connect(self.restore_section_defaults)
        button_row.addWidget(restore_button)
        left_layout.addLayout(button_row)

        clear_all_button = QPushButton("Restore All Defaults")
        clear_all_button.clicked.connect(self.restore_all_defaults)
        left_layout.addWidget(clear_all_button)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(QLabel("Default Section (read-only)"))
        self.default_view = QTextEdit()
        self.default_view.setReadOnly(True)
        self.default_view.setMinimumHeight(150)
        right_layout.addWidget(self.default_view)

        right_layout.addWidget(QLabel("Effective Section (read-only)"))
        self.effective_view = QTextEdit()
        self.effective_view.setReadOnly(True)
        self.effective_view.setMinimumHeight(150)
        right_layout.addWidget(self.effective_view)

        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setHtml(self.load_guide())
        right_layout.addWidget(self.help_text, stretch=1)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([int(self.width() * 0.42), int(self.width() * 0.58)])
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)
        self.reload_config()
        self.raise_()
        self.activateWindow()

    def load_guide(self):
        guide_path = os.path.join(
            mw.addonManager.addonsFolder(), self.addon_name, "config.md"
        )
        try:
            with open(guide_path, "r", encoding="utf-8") as file:
                return markdown.markdown(file.read())
        except FileNotFoundError:
            return "<b>Configuration Guide Not Found.</b>"

    def reload_config(self):
        current = self.section_selector.currentText()
        self.config_manager.reload()
        sections = self.config_manager_cls.list_sections()

        self.section_selector.blockSignals(True)
        self.section_selector.clear()
        self.section_selector.addItems(sections)
        self.section_selector.blockSignals(False)

        if not sections:
            self.section_selector.setEnabled(False)
            self.override_editor.setPlainText("{}")
            self.default_view.clear()
            self.effective_view.clear()
            self.status_label.setText("No config sections found in configs/*.json.")
            return

        self.section_selector.setEnabled(True)
        if current and current in sections:
            self.section_selector.setCurrentText(current)
            self._on_section_changed(current)
        else:
            self.section_selector.setCurrentIndex(0)
            self._on_section_changed(self.section_selector.currentText())

    def _on_section_changed(self, section: str):
        if not section:
            return

        default_section = self.config_manager_cls.get_default_section(section)
        override_section = self.config_manager_cls.get_override_section(section)
        effective_section = self.config_manager_cls.get_effective_section(section)

        self.override_editor.setPlainText(
            json.dumps(override_section, indent=2, ensure_ascii=False)
        )
        self.default_view.setPlainText(
            json.dumps(default_section, indent=2, ensure_ascii=False)
        )
        self.effective_view.setPlainText(
            json.dumps(effective_section, indent=2, ensure_ascii=False)
        )

        if self.config_manager.last_load_errors:
            errs = "; ".join(self.config_manager.last_load_errors[:3])
            self.status_label.setText(
                f"Section '{section}'. Defaults from configs/*.json. Load warnings: {errs}"
            )
        else:
            self.status_label.setText(
                f"Section '{section}'. Editing writes profile override only."
            )

    def save_section_override(self):
        section = self.section_selector.currentText()
        if not section:
            showInfo("No section selected.")
            return

        try:
            override = json.loads(self.override_editor.toPlainText() or "{}")
            if not isinstance(override, dict):
                showInfo("Section override must be a JSON object.")
                return
            self.config_manager_cls.save_section_override(section, override)
            self.reload_config()
            self.section_selector.setCurrentText(section)
            showInfo(f"Saved override for '{section}'.")
        except json.JSONDecodeError:
            showInfo("Invalid JSON format in section override.")
        except Exception as exc:
            showInfo(f"Failed to save override: {exc}")

    def restore_section_defaults(self):
        section = self.section_selector.currentText()
        if not section:
            return
        self.config_manager_cls.clear_section_override(section)
        self.reload_config()
        self.section_selector.setCurrentText(section)
        showInfo(f"Restored defaults for '{section}'.")

    def restore_all_defaults(self):
        if not askUser("Clear all profile overrides and use defaults from configs/?"):
            return
        self.config_manager_cls.clear_all_overrides()
        self.reload_config()
        showInfo("All overrides cleared. Using defaults from configs/.")
