"""
Step 2 – CSV Validation & Date Conversion

Reads the CSV metadata file, converts dates from DD-MMM-YY → ISO 8601,
validates field completeness, and stores a clean record list in context.

Extracted from audio-tags-12d.py (v0.12d).
"""

import csv
import datetime
from pathlib import Path
from typing import List, Dict, Optional

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult
from config.settings import REQUIRED_CSV_COLUMNS


_MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def parse_date(date_str: str) -> Optional[datetime.date]:
    """Convert DD-MMM-YY (e.g. '15-Jun-61') to a datetime.date, or None."""
    parts = date_str.strip().split("-")
    if len(parts) != 3:
        return None
    day_s, mon_s, yr_s = parts
    month_num = _MONTH_MAP.get(mon_s[:3])
    if month_num is None:
        return None
    try:
        year = int(yr_s)
        if year < 100:
            year += 1900
        return datetime.date(year, month_num, int(day_s))
    except ValueError:
        return None


def iso_date(date_str: str) -> Optional[str]:
    """Return ISO 8601 string (YYYY-MM-DD) or None."""
    d = parse_date(date_str)
    return d.isoformat() if d else None


class Step2_CSVValidation(StepProcessor):
    """Date conversion and field validation for the metadata CSV."""

    def __init__(self):
        super().__init__(2, "CSV Validation & Date Conversion")

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        csv_file = context.paths.find_csv_file()
        if csv_file is None:
            result.add_error(
                f"No CSV file found in {context.paths.input_csv_dir}. "
                "Place your metadata CSV in input/csv/."
            )
        return result

    def execute(self, context: ProcessingContext) -> StepResult:
        csv_file = context.paths.find_csv_file()
        self.logger.info(f"Reading CSV: {csv_file}")

        records: List[Dict] = []
        errors: List[str] = []
        warnings: List[str] = []

        try:
            with open(csv_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)

                # Check required columns
                fieldnames = reader.fieldnames or []
                missing = [c for c in REQUIRED_CSV_COLUMNS if c not in fieldnames]
                if missing:
                    return StepResult(
                        False,
                        f"Missing required CSV columns: {', '.join(missing)}"
                    )

                for line_num, row in enumerate(reader, start=2):
                    an = row.get("Accession Number", "").strip()
                    date_str = row.get("Date", "").strip()

                    if not an:
                        warnings.append(f"Row {line_num}: empty Accession Number — skipped")
                        continue

                    # Date conversion
                    dt = parse_date(date_str)
                    if dt is None:
                        errors.append(f"Row {line_num} ({an}): invalid date '{date_str}'")
                        continue

                    records.append({
                        "accession_number": an,
                        "title":            row.get("title", "").strip(),
                        "date_original":    date_str,
                        "date_iso":         dt.isoformat(),
                        "date_year":        str(dt.year),
                        "date_ddmm":        f"{dt.day:02d}{dt.month:02d}",
                        "restrictions":     row.get("Restrictions", "").strip(),
                        "description":      row.get("Description", "").strip(),
                        "place":            row.get("Place", "").strip(),
                        "speakers":         row.get("Speakers", "").strip(),
                        "copyright":        row.get("Production and Copyright", "").strip(),
                    })

        except Exception as e:
            return StepResult(False, f"Failed to read CSV: {e}")

        for w in warnings:
            self.logger.warning(w)
        for err in errors:
            self.logger.error(err)

        if errors:
            return StepResult(False, f"{len(errors)} date error(s) found — fix CSV and re-run")

        context.set_data("csv_records", records)
        context.set_data("csv_file", str(csv_file))
        self.logger.info(f"CSV validated: {len(records)} records loaded")
        return StepResult(True, f"{len(records)} records loaded successfully",
                          data={"record_count": len(records)})

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        records = context.get_data("csv_records")
        if not records:
            result.add_error("No records stored in context after Step 2")
        return result
