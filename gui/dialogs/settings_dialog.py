"""
Settings Dialog for HAM GUI.

Ported from HPM's gui/dialogs/settings_dialog.py
(Photos/Version-2/Framework/gui/dialogs/settings_dialog.py), trimmed to
the capabilities HAM's LogManager and theme system currently support:

- Appearance: reuses MainWindow's existing theme-selection flow
  (_show_theme_dialog) instead of porting HPM's separate ThemeDialog
- Logging: verbosity level only. HPM's SettingsDialog also exposes a
  master enable/disable switch, a per-batch-logging toggle, console
  capture, and a GUI log buffer size — HAM's LogManager
  (utils/log_manager.py) doesn't port those yet (no set_enabled,
  set_per_batch_logging, or console capture; LogWidget has no buffer
  limit), so those controls are left out rather than wired to nothing
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox,
    QGroupBox, QPushButton, QComboBox,
)
from PyQt6.QtCore import QSettings

from utils.log_manager import LogManager


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 220)

        self.settings = QSettings("HSTL", "AudioMetadata")
        self.log_manager = LogManager.instance()

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("<h2>Application Settings</h2>")
        layout.addWidget(label)

        # Appearance
        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout(theme_group)
        theme_desc = QLabel("Customize the application's visual theme:")
        theme_layout.addWidget(theme_desc)
        theme_btn = QPushButton("Change Theme…")
        theme_btn.clicked.connect(self._open_theme_dialog)
        theme_layout.addWidget(theme_btn)
        layout.addWidget(theme_group)

        # Logging
        logging_group = QGroupBox("Logging")
        logging_layout = QVBoxLayout(logging_group)

        verbosity_layout = QHBoxLayout()
        verbosity_layout.addWidget(QLabel("Verbosity Level:"))

        self.verbosity_combo = QComboBox()
        self.verbosity_combo.addItem("Minimal (Errors and warnings only)", "minimal")
        self.verbosity_combo.addItem("Normal (Key actions)", "normal")
        self.verbosity_combo.addItem("Detailed (All operations)", "detailed")
        self.verbosity_combo.setToolTip(
            "Controls how much detail is captured in the session/batch logs\n"
            "and shown in the Logs tab.\n"
            "Minimal: Only errors and warnings\n"
            "Normal: Key actions and status messages\n"
            "Detailed: All operations including debug info"
        )
        verbosity_layout.addWidget(self.verbosity_combo, 1)
        logging_layout.addLayout(verbosity_layout)

        layout.addWidget(logging_group)
        layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_settings(self):
        verbosity = self.settings.value("logging/verbosity", "normal")
        index = self.verbosity_combo.findData(verbosity)
        if index >= 0:
            self.verbosity_combo.setCurrentIndex(index)

    def _save_and_accept(self):
        verbosity = self.verbosity_combo.currentData()
        self.settings.setValue("logging/verbosity", verbosity)
        self.log_manager.set_verbosity(verbosity)
        self.accept()

    def _open_theme_dialog(self):
        """Reuse MainWindow's existing theme-selection flow."""
        parent = self.parent()
        if parent is not None and hasattr(parent, "_show_theme_dialog"):
            parent._show_theme_dialog()
