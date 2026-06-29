"""
Batch Info Panel for the Current Batch tab (right column).

Shows batch registry metadata, per-step completion status, and a live
scan of input/csv/ and input/mp3/ whenever a batch is loaded.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.config_manager import ConfigManager
from utils.path_manager import PathManager

_STEP_LABELS = {
    1: "CSV Preparation & Validation",
    2: "CSV Validation & Date Conversion",
    3: "Metadata Tag Embedding",
    4: "Album Art Embedding",
    5: "Output Validation & Reporting",
}


class BatchInfoPanel(QWidget):
    """Right-column panel showing batch details, step status, and file counts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data_dir: Path | None = None
        self._init_ui()

    # ── construction ──────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(10)

        header = QLabel("Batch Information")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        layout.addWidget(self._build_details_group())
        layout.addWidget(self._build_pipeline_group())
        layout.addWidget(self._build_files_group())
        layout.addWidget(self._build_dir_group())
        layout.addStretch()

    def _build_details_group(self) -> QGroupBox:
        group = QGroupBox("Batch Details")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)

        def _val():
            lbl = QLabel("—")
            lbl.setWordWrap(True)
            return lbl

        self._name_val     = _val()
        self._id_val       = _val()
        self._id_val.setStyleSheet("font-family: monospace;")
        self._status_val   = _val()
        self._created_val  = _val()
        self._accessed_val = _val()

        form.addRow("Name:",          self._name_val)
        form.addRow("Batch ID:",      self._id_val)
        form.addRow("Status:",        self._status_val)
        form.addRow("Created:",       self._created_val)
        form.addRow("Last Accessed:", self._accessed_val)
        return group

    def _build_pipeline_group(self) -> QGroupBox:
        group = QGroupBox("Pipeline Progress")
        vbox = QVBoxLayout(group)
        vbox.setSpacing(4)

        self._progress_summary = QLabel("No batch selected")
        self._progress_summary.setStyleSheet("font-weight: bold;")
        vbox.addWidget(self._progress_summary)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        vbox.addWidget(sep)

        self._step_labels: dict[int, QLabel] = {}
        for i in range(1, 6):
            lbl = QLabel(f"Step {i}:  ○ Pending  —  {_STEP_LABELS[i]}")
            lbl.setWordWrap(True)
            self._step_labels[i] = lbl
            vbox.addWidget(lbl)

        return group

    def _build_files_group(self) -> QGroupBox:
        group = QGroupBox("Input Files")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)

        self._csv_name_val = QLabel("—")
        self._csv_name_val.setWordWrap(True)
        self._csv_size_val = QLabel("—")
        self._mp3_count_val = QLabel("—")

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        refresh_btn.clicked.connect(self._refresh_file_counts)

        form.addRow("CSV File:", self._csv_name_val)
        form.addRow("CSV Size:", self._csv_size_val)
        form.addRow("MP3 Files:", self._mp3_count_val)
        form.addRow("", refresh_btn)
        return group

    def _build_dir_group(self) -> QGroupBox:
        group = QGroupBox("Data Directory")
        vbox = QVBoxLayout(group)

        self._dir_val = QLabel("—")
        self._dir_val.setWordWrap(True)
        self._dir_val.setStyleSheet("font-family: monospace;")

        self._open_btn = QPushButton("Open Folder")
        self._open_btn.setFixedWidth(110)
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._open_data_dir)

        vbox.addWidget(self._dir_val)
        vbox.addWidget(self._open_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        return group

    # ── public API ────────────────────────────────────────────────────────

    def set_batch(self, config: ConfigManager, batch_id: str, batch_info: dict):
        """Populate all fields for the newly selected batch."""
        # Batch details
        self._name_val.setText(batch_info.get("name", "—"))
        self._id_val.setText(batch_id or "—")
        self._status_val.setText(batch_info.get("status", "—"))
        self._created_val.setText((batch_info.get("created") or "—")[:10])
        self._accessed_val.setText((batch_info.get("last_accessed") or "—")[:10])

        # Data directory
        data_dir_str = batch_info.get("data_directory", "")
        self._data_dir = Path(data_dir_str) if data_dir_str else None
        self._dir_val.setText(data_dir_str or "—")
        self._open_btn.setEnabled(bool(self._data_dir and self._data_dir.exists()))

        # Per-step completion
        done_count = 0
        if config:
            for i in range(1, 6):
                is_done = config.get_step_status(i)
                lbl = self._step_labels[i]
                if is_done:
                    lbl.setText(f"Step {i}:  ✓ Done  —  {_STEP_LABELS[i]}")
                    lbl.setStyleSheet("color: #4caf50;")
                    done_count += 1
                else:
                    lbl.setText(f"Step {i}:  ○ Pending  —  {_STEP_LABELS[i]}")
                    lbl.setStyleSheet("")
        self._progress_summary.setText(f"{done_count} of 5 steps complete")

        # File counts
        self._refresh_file_counts()

    def clear(self):
        """Reset to no-batch-selected state."""
        for lbl in (self._name_val, self._id_val, self._status_val,
                    self._created_val, self._accessed_val, self._dir_val,
                    self._csv_name_val, self._csv_size_val, self._mp3_count_val):
            lbl.setText("—")
        self._progress_summary.setText("No batch selected")
        for i, lbl in self._step_labels.items():
            lbl.setText(f"Step {i}:  ○ Pending  —  {_STEP_LABELS[i]}")
            lbl.setStyleSheet("")
        self._open_btn.setEnabled(False)
        self._data_dir = None

    # ── private ───────────────────────────────────────────────────────────

    def _refresh_file_counts(self):
        if not self._data_dir:
            return
        paths = PathManager(self._data_dir)

        csv_path = paths.find_csv_file()
        if csv_path and csv_path.exists():
            size_bytes = csv_path.stat().st_size
            if size_bytes >= 1_048_576:
                size_str = f"{size_bytes / 1_048_576:.1f} MB"
            else:
                size_str = f"{size_bytes / 1024:.1f} KB"
            self._csv_name_val.setText(csv_path.name)
            self._csv_size_val.setText(size_str)
        else:
            self._csv_name_val.setText("None found in input/csv/")
            self._csv_size_val.setText("—")

        mp3s = paths.get_mp3_files()
        self._mp3_count_val.setText(f"{len(mp3s)} file{'s' if len(mp3s) != 1 else ''}"
                                    if mp3s else "None found in input/mp3/")

    def _open_data_dir(self):
        if self._data_dir and self._data_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._data_dir)))
