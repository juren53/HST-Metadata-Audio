"""
Step Widget for HAM GUI.

Displays the 5-step pipeline for the currently selected batch and
lets the user run individual steps.

Step execution runs on a background QThread (gui.workers.StepRunner) so
the UI stays responsive during long steps, ported from HPM's per-step
QThread worker pattern (Photos/Version-2/Framework/gui/dialogs/step5_dialog.py).
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
        self._qt_log_handler = None   # set via set_log_handler()
        self._active_runners: dict = {}  # step_num -> StepRunner (keeps it alive)
        self._run_all_active = False
        self._init_ui()

    def set_log_handler(self, handler):
        """Wire a QtLogHandler so step log records reach the GUI and log file."""
        self._qt_log_handler = handler

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

        self.run_all_btn = QPushButton("Run All Steps (from next incomplete)")
        self.run_all_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.run_all_btn.clicked.connect(self._run_all)
        layout.addWidget(self.run_all_btn, alignment=Qt.AlignmentFlag.AlignLeft)

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
        self._refresh_step_status()
        self._refresh_button_states()

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
        if self.config is None or step_num in self._active_runners:
            return
        import time
        from pathlib import Path
        from utils.path_manager import PathManager
        from steps.base_step import ProcessingContext
        from utils.logger import get_logger
        from steps.step1_csv_prep import Step1_CSVPrep
        from steps.step2_csv_validation import Step2_CSVValidation
        from steps.step3_metadata_embed import Step3_MetadataEmbed
        from steps.step4_thumbnail_embed import Step4_ThumbnailEmbed
        from steps.step5_validation import Step5_Validation
        from gui.workers import StepRunner

        _STEP_CLASSES = {
            1: Step1_CSVPrep,
            2: Step2_CSVValidation,
            3: Step3_MetadataEmbed,
            4: Step4_ThumbnailEmbed,
            5: Step5_Validation,
        }

        data_dir = Path(self.config.get("project.data_directory"))
        paths = PathManager(data_dir)

        # Unique logger name per run avoids handler accumulation across runs
        logger_name = f"ham-step{step_num}-{int(time.time())}"
        ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = paths.logs_dir / f"step{step_num}_{ts}.log"
        logger = get_logger(logger_name, log_file=log_file)

        if self._qt_log_handler is not None:
            logger.addHandler(self._qt_log_handler)

        # Also feed the batch's consolidated log file, if LogManager has one
        # set up for this batch (this per-run logger isn't a child of the
        # shared "ham" logger, so it won't inherit that handler otherwise).
        from utils.log_manager import LogManager
        batch_handler = LogManager.instance().get_batch_handler(self.batch_id)
        if batch_handler is not None:
            logger.addHandler(batch_handler)

        context = ProcessingContext(paths, self.config, logger, batch_id=self.batch_id)
        step = _STEP_CLASSES[step_num]()

        status_lbl = self._step_status[step_num]
        status_lbl.setText("⏳ Running…")
        status_lbl.setStyleSheet("color: #2196f3; font-weight: bold;")

        runner = StepRunner(step_num, step, context, parent=self)
        runner.finished.connect(self._on_step_finished)
        runner.error.connect(self._on_step_error)
        self._active_runners[step_num] = runner
        self._refresh_button_states()
        runner.start()

    def _on_step_finished(self, step_num: int, result):
        self._active_runners.pop(step_num, None)
        level = "INFO" if result.success else "ERROR"
        self.log_to_gui(
            f"Step {step_num}: {'OK' if result.success else 'FAILED'} — {result.message}",
            level,
        )
        self._refresh_step_status()
        self._refresh_button_states()
        self.step_executed.emit(step_num, result.success)
        if self._run_all_active:
            self._continue_run_all(step_num, result.success)

    def _on_step_error(self, step_num: int, message: str):
        self._active_runners.pop(step_num, None)
        self.log_to_gui(f"Step {step_num}: FAILED — {message}", "ERROR")
        self._refresh_step_status()
        self._refresh_button_states()
        self.step_executed.emit(step_num, False)
        if self._run_all_active:
            self._run_all_active = False

    def _refresh_button_states(self):
        """Disable step controls while any step is running (steps share
        the batch's tmp/ working files, so only one may run at a time)."""
        running = bool(self._active_runners)
        has_batch = self.config is not None
        for btn in self._step_btns.values():
            btn.setEnabled(has_batch and not running)
        self.run_all_btn.setEnabled(has_batch and not running)

    def _run_all(self):
        if self.config is None or self._run_all_active or self._active_runners:
            return
        next_step = self.config.get_next_step()
        if next_step is None:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self.parent(), "Done", "All steps already completed!")
            return
        self._run_all_active = True
        self._run_step(next_step)

    def _continue_run_all(self, completed_step_num: int, success: bool):
        if not success:
            self._run_all_active = False
            return
        next_step = self.config.get_next_step()
        if next_step is None or next_step <= completed_step_num:
            self._run_all_active = False
            return
        self._run_step(next_step)

    def log_to_gui(self, msg: str, level: str = "INFO"):
        """Forward a message to the GUI log via the QtLogHandler signal."""
        if self._qt_log_handler is not None:
            self._qt_log_handler.log_record.emit(msg, level)
