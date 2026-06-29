"""
Batch Info Dialog for HAM GUI (stub).
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox

from utils.batch_registry import BatchRegistry


class BatchInfoDialog(QDialog):
    """Display detailed information about a batch."""

    def __init__(self, batch_id: str, registry: BatchRegistry, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Information")
        self.setMinimumWidth(400)
        batch = registry.get_batch(batch_id) or {}

        layout = QVBoxLayout(self)
        lines = [f"<b>{k}:</b> {v}" for k, v in batch.items()]
        label = QLabel("<br>".join(lines))
        label.setWordWrap(True)
        layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
