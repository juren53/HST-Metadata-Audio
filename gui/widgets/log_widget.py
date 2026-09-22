"""
Log Widget for HAM GUI.

Ported from HPM's gui/widgets/enhanced_log_widget.py
(Photos/Version-2/Framework/gui/widgets/enhanced_log_widget.py), adapted:
- 5 steps (1-5) in the Step filter, not 8
- Level filter/priority includes HAM's SUCCESS level and CRITICAL, which
  HPM's dropdown omits (see utils/log_manager.LEVEL_PRIORITY)
- No forced dark background or per-level text color — HAM's LogWidget
  follows the app's current theme (light/dark) rather than overriding it,
  unlike HPM's EnhancedLogWidget which always renders on a fixed dark pane

Used identically in the main Logs tab and in the pop-out LogViewerDialog
(gui/dialogs/log_viewer_dialog.py) — pop_out_requested/set_popped_out()
is how a single widget class serves both roles, matching HPM's design.
"""

from datetime import datetime
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QComboBox, QLineEdit, QCheckBox, QFileDialog, QMessageBox,
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from utils.log_manager import LogRecord, LEVEL_PRIORITY


class LogFilterBar(QWidget):
    """Filter controls for the log viewer."""

    filter_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(
            ["ALL", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        )
        self.level_combo.setMinimumWidth(90)
        self.level_combo.currentTextChanged.connect(self.filter_changed)
        layout.addWidget(self.level_combo)

        layout.addWidget(QLabel("Batch:"))
        self.batch_combo = QComboBox()
        self.batch_combo.addItem("All Batches", None)
        self.batch_combo.setMinimumWidth(140)
        self.batch_combo.currentTextChanged.connect(self.filter_changed)
        layout.addWidget(self.batch_combo)

        layout.addWidget(QLabel("Step:"))
        self.step_combo = QComboBox()
        self.step_combo.addItem("All Steps", None)
        for i in range(1, 6):
            self.step_combo.addItem(f"Step {i}", i)
        self.step_combo.setMinimumWidth(80)
        self.step_combo.currentTextChanged.connect(self.filter_changed)
        layout.addWidget(self.step_combo)

        layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter log messages...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.filter_changed)
        layout.addWidget(self.search_edit, 1)

        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        layout.addWidget(self.auto_scroll_check)

    def get_level_filter(self) -> str:
        return self.level_combo.currentText()

    def get_batch_filter(self) -> Optional[str]:
        return self.batch_combo.currentData()

    def get_step_filter(self) -> Optional[int]:
        return self.step_combo.currentData()

    def get_search_text(self) -> str:
        return self.search_edit.text()

    def is_auto_scroll(self) -> bool:
        return self.auto_scroll_check.isChecked()

    def add_batch_option(self, batch_id: str, batch_name: str):
        for i in range(self.batch_combo.count()):
            if self.batch_combo.itemData(i) == batch_id:
                return
        display_name = f"{batch_name} ({batch_id[:8]})"
        self.batch_combo.addItem(display_name, batch_id)


class LogWidget(QWidget):
    """Log display pane with level/batch/step filtering, search, and export."""

    pop_out_requested = pyqtSignal()

    def __init__(self, parent=None, max_records: int = 2000):
        super().__init__(parent)
        self._log_records: List[LogRecord] = []
        self._max_records = max_records
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.filter_bar = LogFilterBar()
        self.filter_bar.filter_changed.connect(self._apply_filters)
        layout.addWidget(self.filter_bar)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text_area.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        layout.addWidget(self.text_area)

        btn_row = QHBoxLayout()
        self.status_label = QLabel("0 log entries")
        btn_row.addWidget(self.status_label)
        btn_row.addStretch()

        self.pop_out_btn = QPushButton("Pop Out")
        self.pop_out_btn.setToolTip("Open logs in a separate window")
        self.pop_out_btn.clicked.connect(self.pop_out_requested)
        btn_row.addWidget(self.pop_out_btn)

        export_btn = QPushButton("Export…")
        export_btn.setToolTip("Export the currently filtered logs to a file")
        export_btn.clicked.connect(self._export_logs)
        btn_row.addWidget(export_btn)

        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Record ingestion
    # ------------------------------------------------------------------

    @pyqtSlot(object)
    def append_log(self, record: LogRecord):
        """Add a LogRecord to the display. Thread-safe when connected to
        GUILogHandler.log_emitted (Qt auto-queues cross-thread signals)."""
        self._log_records.append(record)

        if len(self._log_records) > self._max_records:
            self._log_records = self._log_records[-self._max_records:]
            self._apply_filters()
            return

        if self._matches_filters(record):
            self._append_formatted_record(record)
        self._update_status()

    def append(self, message: str, level: str = "INFO"):
        """Convenience wrapper for plain text (no batch/step context)."""
        self.append_log(
            LogRecord(
                timestamp=datetime.now(),
                level=level,
                level_no=LEVEL_PRIORITY.get(level, 20),
                source="",
                message=message,
            )
        )

    def _matches_filters(self, record: LogRecord) -> bool:
        return record.matches_filter(
            level_filter=self.filter_bar.get_level_filter(),
            batch_filter=self.filter_bar.get_batch_filter(),
            step_filter=self.filter_bar.get_step_filter(),
            search_text=self.filter_bar.get_search_text(),
        )

    def _append_formatted_record(self, record: LogRecord):
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(record.format_display() + "\n")
        if self.filter_bar.is_auto_scroll():
            self.text_area.setTextCursor(cursor)
            self.text_area.ensureCursorVisible()

    def _apply_filters(self):
        self.text_area.clear()
        filtered_count = 0
        for record in self._log_records:
            if self._matches_filters(record):
                self._append_formatted_record(record)
                filtered_count += 1
        self._update_status(filtered_count)

    def _update_status(self, filtered_count: Optional[int] = None):
        total = len(self._log_records)
        if filtered_count is None:
            filtered_count = sum(1 for r in self._log_records if self._matches_filters(r))
        if filtered_count == total:
            self.status_label.setText(f"{total} log entries")
        else:
            self.status_label.setText(f"Showing {filtered_count} of {total} entries")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

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
                f.write(f"HAM Log Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write("Filters Applied:\n")
                f.write(f"  Level: {self.filter_bar.get_level_filter()}\n")
                f.write(f"  Batch: {self.filter_bar.get_batch_filter() or 'All'}\n")
                f.write(f"  Step: {self.filter_bar.get_step_filter() or 'All'}\n")
                f.write(f"  Search: {self.filter_bar.get_search_text() or 'None'}\n")
                f.write("\n" + "-" * 60 + "\n\n")

                count = 0
                for record in self._log_records:
                    if self._matches_filters(record):
                        f.write(record.format_display() + "\n")
                        count += 1
                f.write(f"\n--- Exported {count} entries ---\n")

            QMessageBox.information(
                self, "Export Complete", f"Exported {count} log entries to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export logs:\n{e}")

    def clear(self):
        self._log_records.clear()
        self.text_area.clear()
        self._update_status()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_batch_option(self, batch_id: str, batch_name: str):
        self.filter_bar.add_batch_option(batch_id, batch_name)

    def set_max_records(self, max_records: int):
        self._max_records = max_records
        if len(self._log_records) > max_records:
            self._log_records = self._log_records[-max_records:]
            self._apply_filters()

    def set_popped_out(self, popped_out: bool):
        """Hide the Pop Out button when this instance IS the pop-out window."""
        self.pop_out_btn.setVisible(not popped_out)

    def get_records(self) -> List[LogRecord]:
        return self._log_records.copy()
