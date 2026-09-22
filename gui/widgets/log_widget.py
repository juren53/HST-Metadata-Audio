"""
Log Widget for HAM GUI.

Simple timestamped log viewer in the Logs tab. The Pop Out button
(pop_out_requested signal) mirrors HPM's EnhancedLogWidget pop-out
mechanic — see gui/dialogs/log_viewer_dialog.py.
"""

from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal


class LogWidget(QWidget):
    """Scrollable log display pane."""

    pop_out_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text_area.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        layout.addWidget(self.text_area)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.pop_out_btn = QPushButton("Pop Out")
        self.pop_out_btn.setToolTip("Open logs in a separate window")
        self.pop_out_btn.clicked.connect(self.pop_out_requested)
        btn_row.addWidget(self.pop_out_btn)
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

    def append(self, message: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {message}"
        self.text_area.append(line)
        self.text_area.moveCursor(QTextCursor.MoveOperation.End)

    def clear(self):
        self.text_area.clear()

    def set_popped_out(self, popped_out: bool):
        """Hide the Pop Out button when this instance IS the pop-out window."""
        self.pop_out_btn.setVisible(not popped_out)
