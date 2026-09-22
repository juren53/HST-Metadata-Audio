"""
Pop-out Log Viewer Dialog for HAM GUI.

Ported from HPM's gui/dialogs/log_viewer_dialog.py
(Photos/Version-2/Framework/gui/dialogs/log_viewer_dialog.py). Now that
LogWidget itself carries the LogRecord/filtering upgrade (see
utils/log_manager.py and gui/widgets/log_widget.py), this dialog is the
thin wrapper HPM's version is too — level/batch/step filtering, search,
and export all come from the shared LogWidget, used identically here and
in the main Logs tab (mirroring how HPM reuses EnhancedLogWidget in both
places).
"""

from typing import List, Optional

from PyQt6.QtWidgets import QDialog, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

from gui.widgets.log_widget import LogWidget
from utils.log_manager import LogRecord


class LogViewerDialog(QDialog):
    """Pop-out log viewer window, mirroring the main Logs tab live."""

    closed = pyqtSignal()

    def __init__(
        self,
        parent=None,
        log_handler=None,
        initial_records: Optional[List[LogRecord]] = None,
    ):
        super().__init__(parent)
        self._batch_name = None
        self._log_handler = log_handler

        self._init_ui(initial_records or [])
        self._setup_window()

        if self._log_handler is not None:
            self._log_handler.log_emitted.connect(self.log_widget.append_log)

    def _init_ui(self, initial_records: List[LogRecord]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.log_widget = LogWidget()
        self.log_widget.set_popped_out(True)
        for record in initial_records:
            self.log_widget.append_log(record)
        layout.addWidget(self.log_widget)

    def _setup_window(self):
        self.setWindowTitle("HAM Log Viewer")

        # Make it an independent window
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.resize(1000, 600)

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

    def add_batch_option(self, batch_id: str, batch_name: str):
        """Add a batch to the filter dropdown."""
        self.log_widget.add_batch_option(batch_id, batch_name)

    def closeEvent(self, event):
        if self._log_handler is not None:
            try:
                self._log_handler.log_emitted.disconnect(self.log_widget.append_log)
            except TypeError:
                pass  # already disconnected
        self.closed.emit()
        event.accept()

    def show_and_raise(self):
        """Show the dialog and bring it to front."""
        self.show()
        self.raise_()
        self.activateWindow()
