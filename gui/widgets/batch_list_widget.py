"""
Batch List Widget for HAM GUI.

Displays all registered batch projects in a table and emits signals
when the user selects a batch or requests a lifecycle action.

STUB – basic table display implemented; context-menu actions are placeholders.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QMenu,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction

from utils.batch_registry import BatchRegistry


class BatchListWidget(QWidget):
    """Batch management panel (left column of the Batches tab)."""

    batch_selected = pyqtSignal(str, dict)            # (batch_id, batch_info)
    batch_action_requested = pyqtSignal(str, str)      # (action, batch_id)

    _COLUMNS = ["Name", "Progress", "Status", "Last Accessed", "Data Directory"]

    def __init__(self, registry: BatchRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Batch Projects")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self._COLUMNS))
        self.table.setHorizontalHeaderLabels(self._COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            len(self._COLUMNS) - 1, QHeaderView.ResizeMode.Stretch
        )
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.select_btn = QPushButton("Open Selected Batch")
        self.select_btn.clicked.connect(self._open_selected)
        self.new_btn = QPushButton("New Batch…")
        self.new_btn.clicked.connect(lambda: self.batch_action_requested.emit("new", ""))
        btn_row.addWidget(self.select_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.new_btn)
        layout.addLayout(btn_row)

    def refresh(self):
        """Reload registry data and repopulate table."""
        batches = self.registry.list_batches_summary()
        self.table.setRowCount(len(batches))
        self._batch_ids: list = []

        for row, b in enumerate(batches):
            self._batch_ids.append(b["id"])
            last = (b.get("last_accessed") or "")[:10]
            for col, value in enumerate([
                b["name"], b["progress"], b["status"], last, b["data_directory"]
            ]):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

    def _on_double_click(self, index):
        self._open_selected()

    def _open_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._batch_ids):
            return
        batch_id = self._batch_ids[row]
        batch_info = self.registry.get_batch(batch_id)
        if batch_info:
            self.batch_selected.emit(batch_id, batch_info)

    def _show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(getattr(self, "_batch_ids", [])):
            return
        batch_id = self._batch_ids[row]

        menu = QMenu(self)
        actions = [
            ("Open", "open"),
            ("Batch Info…", "info"),
            (None, None),
            ("Mark Complete", "complete"),
            ("Archive", "archive"),
            ("Reactivate", "reactivate"),
            (None, None),
            ("Remove from Registry…", "remove"),
        ]
        for label, action_id in actions:
            if label is None:
                menu.addSeparator()
            else:
                act = QAction(label, self)
                act.triggered.connect(
                    lambda checked=False, a=action_id, bid=batch_id:
                        (self._open_selected() if a == "open"
                         else self.batch_action_requested.emit(a, bid))
                )
                menu.addAction(act)

        menu.exec(self.table.viewport().mapToGlobal(pos))
