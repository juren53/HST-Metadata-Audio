"""
New Batch Dialog for HAM GUI.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QFileDialog, QDialogButtonBox, QLabel,
)


class NewBatchDialog(QDialog):
    """Prompt the user for a batch name and data directory."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Batch Project")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Create a new HAM batch project.\n"
                                "MP3 files go in: <data_dir>/input/mp3/\n"
                                "CSV file goes in: <data_dir>/input/csv/"))

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. SR59_Series")
        form.addRow("Project name:", self.name_edit)

        dir_row = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Select a folder…")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        dir_row.addWidget(self.dir_edit)
        dir_row.addWidget(browse_btn)
        form.addRow("Data directory:", dir_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Data Directory")
        if folder:
            self.dir_edit.setText(folder)
            if not self.name_edit.text():
                self.name_edit.setText(Path(folder).name)

    def get_values(self):
        return self.name_edit.text().strip(), self.dir_edit.text().strip()
