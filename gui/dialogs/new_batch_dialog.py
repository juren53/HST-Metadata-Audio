"""
New Batch Dialog for HAM GUI.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QFileDialog, QDialogButtonBox,
    QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt


_DEFAULT_ROOT = r"C:\Data\HSTL_Audio_Batches"


class NewBatchDialog(QDialog):
    """Prompt the user for a batch name; derive a unique data directory."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Batch Project")
        self.setMinimumWidth(480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Create a new HAM batch project.\n"
            "A sub-folder named after the batch will be created inside the root directory."
        ))

        form = QFormLayout()

        # --- Batch name ---
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. SR59_Series")
        self.name_edit.textChanged.connect(self._update_preview)
        form.addRow("Batch name:", self.name_edit)

        # --- Root directory (parent) ---
        root_row = QHBoxLayout()
        self.root_edit = QLineEdit(_DEFAULT_ROOT)
        self.root_edit.textChanged.connect(self._update_preview)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        root_row.addWidget(self.root_edit)
        root_row.addWidget(browse_btn)
        form.addRow("Batches root:", root_row)

        layout.addLayout(form)

        # --- Live preview of computed data_dir ---
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("font-family: monospace; color: gray;")
        layout.addWidget(self._preview_label)
        self._update_preview()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_preview(self):
        name = self.name_edit.text().strip()
        root = self.root_edit.text().strip()
        if name and root:
            path = str(Path(root) / name)
            self._preview_label.setText(f"Will be created at: {path}")
        else:
            self._preview_label.setText("Will be created at: (enter batch name above)")

    def _browse(self):
        default = Path(self.root_edit.text().strip() or _DEFAULT_ROOT)
        if not default.exists():
            reply = QMessageBox.question(
                self, "Create Directory?",
                f"{default} does not exist.\n\nCreate it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    default.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not create directory:\n{e}")
        start = str(default) if default.exists() else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Batches Root Directory", start)
        if folder:
            self.root_edit.setText(folder)

    def _on_accept(self):
        name = self.name_edit.text().strip()
        root = self.root_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a batch name.")
            return
        if not root:
            QMessageBox.warning(self, "Missing Directory", "Please select a batches root directory.")
            return
        self.accept()

    def get_values(self):
        """Return (batch_name, data_dir) where data_dir = root / batch_name."""
        name = self.name_edit.text().strip()
        root = Path(self.root_edit.text().strip())
        return name, str(root / name)
