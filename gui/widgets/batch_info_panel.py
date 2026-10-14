"""
Batch Info Panel for the Current Batch tab (right column).

Shows batch registry metadata, per-step completion status, and a live
scan of input/csv/ and input/mp3/ whenever a batch is loaded.
"""

from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel,
    QPushButton, QGroupBox, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.config_manager import ConfigManager
from utils.path_manager import PathManager


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

        self._progress_summary = QLabel("No batch selected")
        self._progress_summary.setStyleSheet("font-weight: bold;")
        vbox.addWidget(self._progress_summary)

        return group

    def _build_files_group(self) -> QGroupBox:
        group = QGroupBox("Input Files")
        vbox = QVBoxLayout(group)

        # One form for both blocks so their value columns line up
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)

        # Files on disk (live scan)

        self._csv_val = QLabel("—")
        self._csv_val.setWordWrap(True)
        self._mp3_count_val = QLabel("—")

        form.addRow("CSV:", self._csv_val)
        form.addRow("MP3s:", self._mp3_count_val)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        form.addRow(line)

        # Last Step 1 match result (saved in the batch config by Step 1)
        self._match_header = QLabel("Step 1 Match")
        self._match_header.setStyleSheet("font-weight: bold;")
        form.addRow(self._match_header)

        self._matched_val = QLabel("—")
        self._no_mp3_val = QLabel("—")
        self._no_csv_val = QLabel("—")

        form.addRow("Matched:", self._matched_val)
        form.addRow("No MP3:", self._no_mp3_val)
        form.addRow("No CSV row:", self._no_csv_val)
        vbox.addLayout(form)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        refresh_btn.clicked.connect(self._refresh_file_counts)
        vbox.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)
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

        # Step completion summary
        done_count = sum(
            1 for i in range(1, 6) if config and config.get_step_status(i)
        )
        self._progress_summary.setText(f"{done_count} of 5 steps complete")

        # Last Step 1 match result
        self._show_step1_match(config.get("step_results.step1") if config else None)

        # File counts
        self._refresh_file_counts()

    def clear(self):
        """Reset to no-batch-selected state."""
        for lbl in (self._name_val, self._id_val, self._status_val,
                    self._created_val, self._accessed_val, self._dir_val,
                    self._csv_val, self._mp3_count_val):
            lbl.setText("—")
        self._show_step1_match(None)
        self._progress_summary.setText("No batch selected")
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
            self._csv_val.setText(f"{csv_path.name}  ({size_str})")
        else:
            self._csv_val.setText("None found in input/csv/")

        mp3s = paths.get_mp3_files()
        self._mp3_count_val.setText(f"{len(mp3s)} file{'s' if len(mp3s) != 1 else ''}"
                                    if mp3s else "None found in input/mp3/")

    def _show_step1_match(self, result: dict | None):
        """Fill the Step 1 Match block from the saved step_results.step1."""
        if not result or "matched" not in result:
            self._match_header.setText("Step 1 Match")
            self._matched_val.setText("Step 1 not run yet")
            self._matched_val.setStyleSheet("")
            self._no_mp3_val.setText("—")
            self._no_csv_val.setText("—")
            return

        header = "Step 1 Match"
        try:
            run_at = datetime.fromisoformat(result["run_at"])
            header += f"  ({run_at:%b %d, %H:%M})"
        except (KeyError, TypeError, ValueError):
            pass  # results saved before run_at was recorded
        self._match_header.setText(header)

        matched = result["matched"]
        csv_total = result.get("csv_total", 0)
        mp3_total = result.get("mp3_total", 0)
        # matched is the overlap of the two sets, so these are exact
        no_mp3 = csv_total - matched
        no_csv = mp3_total - matched

        if matched == 0:
            color = "#f44336"   # red: nothing matched
        elif no_mp3 == 0 and no_csv == 0:
            color = "#4caf50"   # green: everything matched
        else:
            color = "#ff9800"   # amber: partial match
        self._matched_val.setText(f"{matched} of {csv_total}")
        self._matched_val.setStyleSheet(f"color: {color}; font-weight: bold;")
        self._no_mp3_val.setText(f"{no_mp3} CSV row{'s' if no_mp3 != 1 else ''}")
        self._no_csv_val.setText(f"{no_csv} MP3{'s' if no_csv != 1 else ''}")

    def _open_data_dir(self):
        if self._data_dir and self._data_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._data_dir)))
