"""
Step Widget for HAM GUI.

Displays the 5-step pipeline for the currently selected batch and
lets the user run individual steps.

STUB – UI skeleton implemented; step execution hooks are placeholders.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QProgressBar, QFrame, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt

from config.config_manager import ConfigManager

_STEP_LABELS = {
    1: "CSV Preparation & Validation",
    2: "CSV Validation & Date Conversion",
    3: "Metadata Tag Embedding",
    4: "Album Art Embedding",
    5: "Output Validation & Reporting",
}

class StepWidget(QWidget):
    """Step execution panel for the Current Batch tab (left column)."""

    step_executed = pyqtSignal(int, bool)  # (step_num, success)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config: ConfigManager = None
        self.batch_id: str = ""
        self.batch_info: dict = {}
        self._step_btns: dict = {}
        self._step_status: dict = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        self.batch_label = QLabel("No batch selected")
        self.batch_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.batch_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 5)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        for step_num in range(1, 6):
            layout.addWidget(self._build_step_row(step_num))

        layout.addStretch()

        run_all_btn = QPushButton("Run All Steps (from next incomplete)")
        run_all_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        run_all_btn.clicked.connect(self._run_all)
        layout.addWidget(run_all_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def _build_step_row(self, step_num: int) -> QGroupBox:
        group = QGroupBox(f"Step {step_num}: {_STEP_LABELS[step_num]}")
        row = QHBoxLayout(group)
        row.setContentsMargins(8, 6, 8, 6)

        status_lbl = QLabel("○ Pending")
        status_lbl.setFixedWidth(100)
        self._step_status[step_num] = status_lbl

        run_btn = QPushButton(f"Run Step {step_num}")
        run_btn.setFixedWidth(110)
        run_btn.clicked.connect(lambda checked=False, n=step_num: self._run_step(n))
        run_btn.setEnabled(False)
        self._step_btns[step_num] = run_btn

        row.addWidget(status_lbl)
        row.addStretch()
        row.addWidget(run_btn)
        return group

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def set_batch(self, config: ConfigManager, batch_id: str, batch_info: dict):
        self.config = config
        self.batch_id = batch_id
        self.batch_info = batch_info
        name = batch_info.get("name", "Unnamed")
        self.batch_label.setText(f"Batch: {name}")
        for btn in self._step_btns.values():
            btn.setEnabled(True)
        self._refresh_step_status()

    def _refresh_step_status(self):
        if self.config is None:
            return
        done_count = 0
        for step_num in range(1, 6):
            is_done = self.config.get_step_status(step_num)
            lbl = self._step_status[step_num]
            if is_done:
                lbl.setText("done")
                lbl.setStyleSheet("color: #4caf50; font-weight: bold;")
                done_count += 1
            else:
                lbl.setText("○ Pending")
                lbl.setStyleSheet("")
        self.progress_bar.setValue(done_count)

    # ──────────────────────────────────────────────────────────────────────
    # Step execution
    # ──────────────────────────────────────────────────────────────────────

    def _run_step(self, step_num: int):
        # TODO: run in a QThread so the GUI stays responsive during long steps
        if self.config is None:
            return
        from pathlib import Path
        from utils.path_manager import PathManager
        from steps.base_step import ProcessingContext
        from utils.logger import get_logger
        from steps.step1_csv_prep import Step1_CSVPrep
        from steps.step2_csv_validation import Step2_CSVValidation
        from steps.step3_metadata_embed import Step3_MetadataEmbed
        from steps.step4_thumbnail_embed import Step4_ThumbnailEmbed
        from steps.step5_validation import Step5_Validation

        _STEP_CLASSES = {
            1: Step1_CSVPrep,
            2: Step2_CSVValidation,
            3: Step3_MetadataEmbed,
            4: Step4_ThumbnailEmbed,
            5: Step5_Validation,
        }

        data_dir = Path(self.config.get("project.data_directory"))
        paths = PathManager(data_dir)
        logger = get_logger("ham-gui-step")
        context = ProcessingContext(paths, self.config, logger, batch_id=self.batch_id)

        step = _STEP_CLASSES[step_num]()
        result = step.run(context)

        self.log_to_gui(f"Step {step_num}: {'OK' if result.success else 'FAILED'} — {result.message}")
        self._refresh_step_status()
        self.step_executed.emit(step_num, result.success)

    def _run_all(self):
        if self.config is None:
            return
        next_step = self.config.get_next_step()
        if next_step is None:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self.parent(), "Done", "All steps already completed!")
            return
        for step_num in range(next_step, 6):
            self._run_step(step_num)
            if not self.config.get_step_status(step_num):
                break

    def log_to_gui(self, msg: str):
        """Placeholder — wire to the Logs tab in a future session."""
        pass
