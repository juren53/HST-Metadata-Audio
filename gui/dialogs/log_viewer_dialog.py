"""
Pop-out Log Viewer Dialog for HAM GUI.

Ported from HPM's gui/dialogs/log_viewer_dialog.py
(Photos/Version-2/Framework/gui/dialogs/log_viewer_dialog.py). HPM's
version hosts an EnhancedLogWidget with level/batch/step filtering and
text search, built on a structured LogRecord that HPM's GUI handler
emits. HAM's LogManager/QtLogHandler (utils/log_manager.py,
utils/qt_log_handler.py) still emit plain (message, level) strings —
upgrading that to a filterable LogRecord is tracked as a follow-up in
docs/HSTL_Audio_Framework-Development_Plan.md. This port ships the
pop-out-window mechanic itself (useful on its own for keeping logs
visible on a second monitor) plus a simple text export, reusing HAM's
existing LogWidget rather than a filtering-capable one.
"""

from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor

from gui.widgets.log_widget import LogWidget


class LogViewerDialog(QDialog):
    """Pop-out log viewer window, mirroring the main Logs tab live."""

    closed = pyqtSignal()

    def __init__(self, parent=None, log_handler=None, initial_text: str = ""):
        super().__init__(parent)
        self._batch_name = None
        self._log_handler = log_handler

        self._init_ui(initial_text)
        self._setup_window()

        if self._log_handler is not None:
            self._log_handler.log_record.connect(self.log_widget.append)

    def _init_ui(self, initial_text: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.log_widget = LogWidget()
        self.log_widget.set_popped_out(True)
        if initial_text:
            self.log_widget.text_area.setPlainText(initial_text)
            self.log_widget.text_area.moveCursor(QTextCursor.MoveOperation.End)
        layout.addWidget(self.log_widget)

        export_layout = QHBoxLayout()
        export_layout.addStretch()
        export_btn = QPushButton("Export…")
        export_btn.setToolTip("Export the visible log text to a file")
        export_btn.clicked.connect(self._export_logs)
        export_layout.addWidget(export_btn)
        layout.addLayout(export_layout)

    def _setup_window(self):
        self.setWindowTitle("HAM Log Viewer")

        # Make it an independent window
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.resize(900, 550)

        # Position slightly offset from parent if available
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(parent_geo.x() + 50, parent_geo.y() + 50)

    def set_batch_name(self, batch_name):
        """Set the current batch name and update the title bar."""
        self._batch_name = batch_name
        if batch_name:
            self.setWindowTitle(f"HAM Log Viewer - {batch_name}")
        else:
            self.setWindowTitle("HAM Log Viewer")

    def _export_logs(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"ham_logs_{timestamp}.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", default_name, "Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.log_widget.text_area.toPlainText())
            QMessageBox.information(self, "Export Complete", f"Exported logs to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export logs:\n{e}")

    def closeEvent(self, event):
        if self._log_handler is not None:
            try:
                self._log_handler.log_record.disconnect(self.log_widget.append)
            except TypeError:
                pass  # already disconnected
        self.closed.emit()
        event.accept()

    def show_and_raise(self):
        """Show the dialog and bring it to front."""
        self.show()
        self.raise_()
        self.activateWindow()
