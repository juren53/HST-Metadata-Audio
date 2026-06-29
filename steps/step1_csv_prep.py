"""
Step 1 – CSV Preparation & Validation

Checks that:
  - A CSV file exists in input/csv/
  - MP3 files exist in input/mp3/
  - All REQUIRED_CSV_COLUMNS are present in the CSV
  - MP3 filenames match Sound_File URLs in the CSV

Matching logic adapted from match-audio-files.py. Each Sound_File_N cell
may contain a full URL (e.g. https://…/SR62-122.mp3) or a bare filename;
the URL prefix is stripped to extract the basename for comparison.

Populates context.shared_data:
  "csv_path"             – Path to the CSV file
  "sound_file_cols"      – list of Sound_File column names found
  "matched_mp3s"         – set of MP3 basenames matched to a CSV row
  "unmatched_csv_files"  – CSV-listed filenames absent from input/mp3/
  "unmatched_mp3_files"  – MP3 files in input/mp3/ with no CSV entry
"""

import csv
from pathlib import Path

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult
from config.settings import REQUIRED_CSV_COLUMNS


def _basename(value: str) -> str:
    """Strip URL prefix and return bare filename."""
    return value.strip().split("/")[-1] if isinstance(value, str) else ""


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
            with open(csv_path, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                headers = reader.fieldnames or []
                rows = list(reader)
        except Exception as e:
            return StepResult(False, f"Cannot read CSV: {e}")

        missing_cols = [c for c in REQUIRED_CSV_COLUMNS if c not in headers]
        if missing_cols:
            return StepResult(False, f"Missing required columns: {missing_cols}")

        self.logger.info(f"CSV rows: {len(rows)}  |  Columns: {len(headers)}")

        # 3. Identify Sound_File columns (by name prefix, then by position fallback)
        sound_cols = [h for h in headers if h.lower().startswith("sound_file")]
        if not sound_cols:
            # Fallback: all columns beyond the required set
            n = len(REQUIRED_CSV_COLUMNS)
            sound_cols = headers[n:n + 10]

        if not sound_cols:
            return StepResult(False, "No Sound_File columns found in CSV")

        self.logger.info(f"Sound_File columns ({len(sound_cols)}): {sound_cols[0]} … {sound_cols[-1]}")

        # 4. Collect all CSV-listed MP3 basenames
        csv_filenames: set[str] = set()
        for row in rows:
            for col in sound_cols:
                name = _basename(row.get(col, ""))
                if name.lower().endswith(".mp3"):
                    csv_filenames.add(name)

        self.logger.info(f"Unique MP3 filenames in CSV: {len(csv_filenames)}")

        # 5. Collect MP3 files present in input/mp3/
        mp3_paths = context.paths.get_mp3_files()
        mp3_names: set[str] = {p.name for p in mp3_paths}

        self.logger.info(f"MP3 files in input/mp3/: {len(mp3_names)}")

        # 6. Match
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

        # 7. Write report
        self._write_report(context, csv_path, rows, sound_cols,
                           matched_mp3s, unmatched_csv, unmatched_mp3)

        # 8. Populate shared_data for downstream steps
        context.shared_data["csv_path"]            = csv_path
        context.shared_data["sound_file_cols"]     = sound_cols
        context.shared_data["matched_mp3s"]        = matched_mp3s
        context.shared_data["unmatched_csv_files"] = unmatched_csv
        context.shared_data["unmatched_mp3_files"] = unmatched_mp3

        if not matched_mp3s:
            return StepResult(False, "No MP3 files matched any CSV row — check filenames")

        msg = (f"Matched {len(matched_mp3s)} of {len(csv_filenames)} CSV-listed files "
               f"({len(mp3_names)} MP3s in input/mp3/)")
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

    def _write_report(self, context, csv_path, rows, sound_cols,
                      matched, unmatched_csv, unmatched_mp3):
        report_path = context.paths.reports_dir / "step1_prep_report.txt"
        try:
            context.paths.reports_dir.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as fh:
                fh.write("HAM Step 1 – CSV Preparation Report\n")
                fh.write("=" * 50 + "\n\n")
                fh.write(f"CSV file      : {csv_path.name}\n")
                fh.write(f"CSV rows      : {len(rows)}\n")
                fh.write(f"Sound_File cols: {', '.join(sound_cols)}\n\n")
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
