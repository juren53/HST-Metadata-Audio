"""
Step 1 Dialog — CSV & MP3 Preparation, for HAM GUI.

Ported from HPM's gui/dialogs/step1_dialog.py
(Photos/Version-2/Framework/gui/dialogs/step1_dialog.py) — same
Browse-then-validate-then-copy-into-project shape, adapted: HAM's Step 1
needs both a CSV metadata file *and* a folder of MP3 source files (HPM's
Step 1 only ever handles a single Excel spreadsheet). This closes a real
gap in HAM: before this dialog existed, there was no GUI way to get a
CSV or MP3 files into a batch's input/ directories at all — the user had
to drop them in via File Explorer before clicking Run Step 1.

MP3 import runs on a QThread (a production batch can be thousands of
files — see docs/HSTL_Audio_Framework-Development_Plan.md's 3,757-file
dataset), mirroring the QThread worker pattern used elsewhere in HAM
(gui/workers.py, HPM's own per-step dialog threads such as
CSVConversionThread in HPM's step2_dialog.py). The CSV copy is a single
small file, so it runs synchronously on the button click.
"""

import csv
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QDialogButtonBox, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import QThread, pyqtSignal

from config.settings import REQUIRED_CSV_COLUMNS
from utils.file_utils import safe_copy, find_csv, count_mp3s


class Step1ImportThread(QThread):
    """Copies every .mp3 in a source folder into the batch's input/mp3/.

    Additive, not a replace: files already present (by name) are skipped
    rather than re-copied, so importing from more than one source folder
    across separate runs of the dialog just adds to what's there.
    """

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, dict)   # success, stats
    error = pyqtSignal(str)

    def __init__(self, source_dir: str, dest_dir: str):
        super().__init__()
        self.source_dir = source_dir
        self.dest_dir = dest_dir

    def run(self):
        try:
            src_files = sorted(Path(self.source_dir).glob("*.mp3"))
            if not src_files:
                self.error.emit("No .mp3 files found in the selected folder.")
                return

            self.progress.emit(f"Found {len(src_files)} MP3 file(s) to import...")
            dest_dir = Path(self.dest_dir)
            copied = skipped = failed = 0

            for i, src in enumerate(src_files, 1):
                dst = dest_dir / src.name
                if dst.exists():
                    skipped += 1
                elif safe_copy(src, dst):
                    copied += 1
                else:
                    failed += 1
                if i % 50 == 0 or i == len(src_files):
                    self.progress.emit(f"Copied {i}/{len(src_files)}...")

            self.finished.emit(
                True,
                {"copied": copied, "skipped": skipped, "failed": failed, "total": len(src_files)},
            )
        except Exception as exc:  # noqa: BLE001 - surface any import failure to the GUI
            self.error.emit(str(exc))


class Step1Dialog(QDialog):
    """Dialog for Step 1: CSV & MP3 Preparation."""

    def __init__(self, paths, parent=None, batch_id=None):
        super().__init__(parent)
        self.paths = paths
        self.batch_id = batch_id
        self._import_thread = None

        self.setWindowTitle("Step 1: CSV & MP3 Preparation")
        self.setMinimumWidth(620)

        self._init_ui()
        self._refresh_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h2>Step 1: CSV & MP3 Preparation</h2>"))

        desc = QLabel(
            "<p>Select the batch's CSV metadata file and the folder containing its "
            "source MP3 files. Both are copied into the batch's <code>input/</code> "
            "directories; Step 1 then validates and matches them.</p>"
            f"<p><b>Required CSV columns:</b> {', '.join(REQUIRED_CSV_COLUMNS)}</p>"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(12)

        csv_row = QHBoxLayout()
        self.csv_status_label = QLabel()
        csv_row.addWidget(self.csv_status_label, 1)
        self._csv_browse_btn = QPushButton("Browse CSV…")
        self._csv_browse_btn.clicked.connect(self._browse_csv)
        csv_row.addWidget(self._csv_browse_btn)
        layout.addLayout(csv_row)

        mp3_row = QHBoxLayout()
        self.mp3_status_label = QLabel()
        mp3_row.addWidget(self.mp3_status_label, 1)
        self._mp3_browse_btn = QPushButton("Import MP3 Folder…")
        self._mp3_browse_btn.clicked.connect(self._browse_mp3_folder)
        mp3_row.addWidget(self._mp3_browse_btn)
        layout.addLayout(mp3_row)

        layout.addSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(140)
        layout.addWidget(self.output_text)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setText("Continue")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _refresh_status(self):
        csv_path = find_csv(self.paths.input_csv_dir)
        if csv_path:
            self.csv_status_label.setText(f"CSV: {csv_path.name}")
        else:
            self.csv_status_label.setText("CSV: (none selected)")

        mp3_count = count_mp3s(self.paths.input_mp3_dir)
        self.mp3_status_label.setText(f"MP3s in input/mp3/: {mp3_count}")

        self._ok_button.setEnabled(bool(csv_path) and mp3_count > 0)

    def _set_busy(self, busy: bool):
        self._csv_browse_btn.setEnabled(not busy)
        self._mp3_browse_btn.setEnabled(not busy)
        self.progress_bar.setVisible(busy)
        if not busy:
            self._refresh_status()

    # ------------------------------------------------------------------
    # CSV import
    # ------------------------------------------------------------------

    def _browse_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV Metadata File", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return
        src = Path(file_path)

        try:
            with open(src, newline="", encoding="utf-8-sig") as fh:
                headers = csv.DictReader(fh).fieldnames or []
        except Exception as e:
            QMessageBox.critical(self, "Cannot Read CSV", f"Could not read the selected file:\n{e}")
            return

        missing = [c for c in REQUIRED_CSV_COLUMNS if c not in headers]
        if missing:
            QMessageBox.warning(
                self,
                "Missing Required Columns",
                "The selected CSV is missing required columns:\n\n"
                + "\n".join(missing)
                + "\n\nSelect a different file, or fix the CSV and try again.",
            )
            return

        # Replace any existing CSV(s) so PathManager.find_csv_file() stays unambiguous
        self.paths.input_csv_dir.mkdir(parents=True, exist_ok=True)
        for old in self.paths.input_csv_dir.glob("*.csv"):
            try:
                old.unlink()
            except OSError:
                pass

        dst = self.paths.input_csv_dir / src.name
        if safe_copy(src, dst):
            self.output_text.append(f"✓ Copied CSV: {src.name}")
        else:
            QMessageBox.critical(self, "Copy Failed", f"Could not copy {src.name} into the batch.")
        self._refresh_status()

    # ------------------------------------------------------------------
    # MP3 import
    # ------------------------------------------------------------------

    def _browse_mp3_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select MP3 Source Folder", "")
        if not folder:
            return

        self.paths.input_mp3_dir.mkdir(parents=True, exist_ok=True)
        self.output_text.append(f"Importing MP3 files from: {folder}")
        self._set_busy(True)

        self._import_thread = Step1ImportThread(folder, str(self.paths.input_mp3_dir))
        self._import_thread.progress.connect(self.output_text.append)
        self._import_thread.finished.connect(self._on_import_finished)
        self._import_thread.error.connect(self._on_import_error)
        self._import_thread.start()

    def _on_import_finished(self, success: bool, stats: dict):
        self.output_text.append(
            f"✓ Import complete: {stats['copied']} copied, {stats['skipped']} already present, "
            f"{stats['failed']} failed (of {stats['total']} found)"
        )
        self._set_busy(False)

    def _on_import_error(self, message: str):
        self.output_text.append(f"✗ {message}")
        self._set_busy(False)
        QMessageBox.warning(self, "Import Failed", message)
