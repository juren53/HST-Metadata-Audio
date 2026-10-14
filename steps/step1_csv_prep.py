"""
Step 1 – CSV Preparation & Validation

Checks that:
  - A CSV file exists in input/csv/
  - MP3 files exist in input/mp3/
  - All REQUIRED_CSV_COLUMNS are present in the CSV
  - MP3 filenames match the CSV's Accession Numbers

Each MP3 is named for its recording's Accession Number, so the CSV row
with Accession Number "SR59-108" matches input/mp3/SR59-108.mp3. This is
the same rule Step 3 uses to look up a file's metadata.

Populates context.shared_data:
  "csv_path"             – Path to the CSV file
  "matched_mp3s"         – set of MP3 filenames matched to a CSV row
  "unmatched_csv_files"  – CSV-listed filenames absent from input/mp3/
  "unmatched_mp3_files"  – MP3 files in input/mp3/ with no CSV entry
"""

import csv
import io
from datetime import datetime
from pathlib import Path

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult
from config.settings import REQUIRED_CSV_COLUMNS
from utils.file_utils import read_csv_text


class Step1_CSVPrep(StepProcessor):
    """CSV preparation: column validation and MP3/CSV filename matching."""

    def __init__(self):
        super().__init__(1, "CSV Preparation & Validation")

    # ── validate_inputs ───────────────────────────────────────────────────

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        if not context.paths.input_csv_dir.exists():
            result.add_error(f"input/csv/ not found: {context.paths.input_csv_dir}")
        if not context.paths.input_mp3_dir.exists():
            result.add_error(f"input/mp3/ not found: {context.paths.input_mp3_dir}")
        return result

    # ── execute ───────────────────────────────────────────────────────────

    def execute(self, context: ProcessingContext) -> StepResult:
        # 1. Locate CSV
        csv_path = context.paths.find_csv_file()
        if csv_path is None:
            return StepResult(False, "No CSV file found in input/csv/")

        self.logger.info(f"CSV: {csv_path.name}")

        # 2. Read CSV and validate columns
        try:
            text, _ = read_csv_text(csv_path)
            reader = csv.DictReader(io.StringIO(text, newline=""))
            headers = reader.fieldnames or []
            rows = list(reader)
        except Exception as e:
            return StepResult(False, f"Cannot read CSV: {e}")

        missing_cols = [c for c in REQUIRED_CSV_COLUMNS if c not in headers]
        if missing_cols:
            return StepResult(False, f"Missing required columns: {missing_cols}")

        self.logger.info(f"CSV rows: {len(rows)}  |  Columns: {len(headers)}")

        # 3. Expected MP3 filename for each row: <Accession Number>.mp3
        csv_filenames: set[str] = set()
        blank_rows = 0
        for row in rows:
            an = (row.get("Accession Number") or "").strip()
            if an:
                csv_filenames.add(f"{an}.mp3")
            else:
                blank_rows += 1

        if blank_rows:
            self.logger.warning(f"{blank_rows} CSV row(s) have no Accession Number")
        self.logger.info(f"Unique Accession Numbers in CSV: {len(csv_filenames)}")

        # 4. Collect MP3 files present in input/mp3/
        mp3_paths = context.paths.get_mp3_files()
        mp3_names: set[str] = {p.name for p in mp3_paths}

        self.logger.info(f"MP3 files in input/mp3/: {len(mp3_names)}")

        # 5. Match
        matched_mp3s       = csv_filenames & mp3_names
        unmatched_csv      = sorted(csv_filenames - mp3_names)
        unmatched_mp3      = sorted(mp3_names - csv_filenames)

        self.logger.info(f"Matched: {len(matched_mp3s)}  |  "
                         f"CSV-only: {len(unmatched_csv)}  |  "
                         f"MP3-only: {len(unmatched_mp3)}")

        for f in unmatched_csv:
            self.logger.warning(f"  CSV row has no MP3 file: {f}")
        for f in unmatched_mp3:
            self.logger.warning(f"  MP3 file has no CSV row: {f}")

        # 6. Write report
        self._write_report(context, csv_path, rows,
                           matched_mp3s, unmatched_csv, unmatched_mp3)

        # 7. Populate shared_data for downstream steps
        context.shared_data["csv_path"]            = csv_path
        context.shared_data["matched_mp3s"]        = matched_mp3s
        context.shared_data["unmatched_csv_files"] = unmatched_csv
        context.shared_data["unmatched_mp3_files"] = unmatched_mp3

        if not matched_mp3s:
            return StepResult(False, "No MP3 files matched any CSV Accession Number — "
                                     "files must be named <Accession Number>.mp3")

        msg = (f"Matched {len(matched_mp3s)} of {len(csv_filenames)} CSV Accession Numbers "
               f"({len(mp3_names)} MP3s in input/mp3/)")
        # Saved with the batch config so the GUI's Input Files panel can show it
        context.config.set("step_results.step1", {
            "matched":    len(matched_mp3s),
            "csv_total":  len(csv_filenames),
            "mp3_total":  len(mp3_names),
            "summary":    msg,
            "run_at":     datetime.now().isoformat(timespec="seconds"),
        })
        return StepResult(True, msg, files_processed=len(matched_mp3s))

    # ── validate_outputs ──────────────────────────────────────────────────

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        if not context.shared_data.get("matched_mp3s"):
            result.add_error("shared_data['matched_mp3s'] is empty after Step 1")
        if "csv_path" not in context.shared_data:
            result.add_error("shared_data['csv_path'] not set after Step 1")
        return result

    # ── private ───────────────────────────────────────────────────────────

    def _write_report(self, context, csv_path, rows,
                      matched, unmatched_csv, unmatched_mp3):
        report_path = context.paths.reports_dir / "step1_prep_report.txt"
        try:
            context.paths.reports_dir.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as fh:
                fh.write("HAM Step 1 – CSV Preparation Report\n")
                fh.write("=" * 50 + "\n\n")
                fh.write(f"CSV file      : {csv_path.name}\n")
                fh.write(f"CSV rows      : {len(rows)}\n")
                fh.write("Match rule    : <Accession Number>.mp3\n\n")
                fh.write(f"Matched       : {len(matched)}\n")
                fh.write(f"CSV-only      : {len(unmatched_csv)}\n")
                fh.write(f"MP3-only      : {len(unmatched_mp3)}\n\n")
                if unmatched_csv:
                    fh.write("CSV rows with no matching MP3:\n")
                    for f in unmatched_csv:
                        fh.write(f"  {f}\n")
                    fh.write("\n")
                if unmatched_mp3:
                    fh.write("MP3 files with no CSV row:\n")
                    for f in unmatched_mp3:
                        fh.write(f"  {f}\n")
            self.logger.info(f"Report: {report_path}")
        except Exception as e:
            self.logger.warning(f"Could not write Step 1 report: {e}")
