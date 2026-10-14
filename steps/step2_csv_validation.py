"""
Step 2 – CSV Validation & Date Conversion

Reads the CSV metadata file, converts dates to ISO 8601 (see parse_date
for the accepted formats; blank dates become 0000-00-00), validates field
completeness, and stores a clean record list in context.

Extracted from audio-tags-12d.py (v0.12d).
"""

import csv
import datetime
import io
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult
from config.settings import REQUIRED_CSV_COLUMNS
from utils.file_utils import read_csv_text


_MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# Stored for rows with no Date, so every MP3 still gets date tags
BLANK_DATE_ISO = "0000-00-00"

_RE_DD_MMM_YY   = re.compile(r"^(\d{1,2})-([A-Za-z]{3,})-(\d{2}|\d{4})$")   # 15-Jun-61
_RE_MONTH_D_Y   = re.compile(r"^([A-Za-z]{3,})\.? (\d{1,2}), (\d{4})$")     # May 14, 1948
_RE_MONTH_Y     = re.compile(r"^([A-Za-z]{3,})\.?,? (\d{4})$")              # January, 1952
_RE_YEAR        = re.compile(r"^(\d{4})$")                                  # 1961
_RE_ISO         = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")                  # 1961-06-15


def _month(name: str) -> Optional[int]:
    return _MONTH_MAP.get(name[:3].capitalize())


def _parse_single(text: str) -> Optional[Tuple[int, Optional[int], Optional[int]]]:
    """Parse one date to (year, month, day); month/day are None for
    partial dates. Returns None if the text isn't a recognized date."""
    try:
        if m := _RE_MONTH_D_Y.match(text):
            mon, day, year = _month(m[1]), int(m[2]), int(m[3])
        elif m := _RE_DD_MMM_YY.match(text):
            day, mon, year = int(m[1]), _month(m[2]), int(m[3])
            if year < 100:
                year += 1900
        elif m := _RE_ISO.match(text):
            year, mon, day = int(m[1]), int(m[2]), int(m[3])
        elif m := _RE_MONTH_Y.match(text):
            mon = _month(m[1])
            if mon is None:
                return None
            return int(m[2]), mon, None
        elif m := _RE_YEAR.match(text):
            return int(m[1]), None, None
        else:
            return None
        if mon is None:
            return None
        datetime.date(year, mon, day)  # reject impossible dates like Feb 30
        return year, mon, day
    except ValueError:
        return None


def _iso(year: int, mon: Optional[int], day: Optional[int]) -> str:
    """ISO 8601, reduced precision for partial dates: 1961, 1961-06, 1961-06-15."""
    if mon is None:
        return f"{year:04d}"
    if day is None:
        return f"{year:04d}-{mon:02d}"
    return f"{year:04d}-{mon:02d}-{day:02d}"


def parse_date(date_str: str) -> Optional[Dict[str, str]]:
    """Convert a CSV Date cell to the date fields Step 3 embeds.

    Accepts "May 14, 1948", "January, 1952", "1961", "15-Jun-61",
    "1961-06-15", and ranges of any of these ("A - B", possibly split
    across lines). A range is stored as an ISO 8601 interval (A/B); its
    start date supplies the year and DDMM tags. Returns None if the text
    isn't a recognized date. A blank cell is handled by the caller.
    """
    text = " ".join(date_str.split())  # collapse line breaks and runs of spaces
    parts = [p.strip() for p in text.split(" - ")]
    if len(parts) > 2:
        return None
    parsed = [_parse_single(p) for p in parts]
    if any(p is None for p in parsed):
        return None

    year, mon, day = parsed[0]
    iso = "/".join(_iso(*p) for p in parsed)
    return {
        "date_original": text,
        "date_iso":      iso,
        "date_year":     f"{year:04d}",
        # TDAT is DDMM; only a full date has one
        "date_ddmm":     f"{day:02d}{mon:02d}" if day else "",
    }


def iso_date(date_str: str) -> Optional[str]:
    """Return the ISO 8601 form of a CSV Date cell, or None."""
    d = parse_date(date_str)
    return d["date_iso"] if d else None


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
            text, _ = read_csv_text(csv_file)
            with io.StringIO(text, newline="") as f:
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
                    if not date_str:
                        warnings.append(f"Row {line_num} ({an}): no Date — "
                                        f"using {BLANK_DATE_ISO}")
                        dates = {"date_original": "", "date_iso": BLANK_DATE_ISO,
                                 "date_year": "0000", "date_ddmm": "0000"}
                    else:
                        dates = parse_date(date_str)
                        if dates is None:
                            errors.append(f"Row {line_num} ({an}): invalid date '{date_str}'")
                            continue

                    records.append({
                        "accession_number": an,
                        "title":            row.get("title", "").strip(),
                        **dates,
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
