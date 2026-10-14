"""
Step 2 – CSV Validation & Date Conversion

Reads the CSV metadata file, converts dates to ISO 8601 (see parse_date
for the accepted formats; blank dates become 0000-00-00), validates field
completeness, and writes the converted dates into a "Date ISO" column of
the batch's copy of the CSV (input/csv/), next to the original "Date".

Later steps (run separately in the GUI, or as separate CLI invocations)
rebuild their records from that column via load_records(), so nothing
depends on Step 2's in-memory results surviving between runs.

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


DATE_ISO_COLUMN = "Date ISO"


def _read_csv_rows(csv_file: Path) -> Tuple[List[str], List[List[str]]]:
    """Read the CSV as plain lists, not dicts: exports can repeat a header
    (e.g. "Recording Speed" twice), and DictReader would drop one copy."""
    text, _ = read_csv_text(csv_file)
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def records_from_csv(csv_file: Path) -> Optional[List[Dict]]:
    """Build Step 3/5 records from a CSV that Step 2 has already processed.

    Returns None if the CSV has no Date ISO column (Step 2 not run since
    the CSV was imported). Rows without an Accession Number are skipped,
    as Step 2 does.
    """
    headers, rows = _read_csv_rows(csv_file)
    if DATE_ISO_COLUMN not in headers:
        return None

    records: List[Dict] = []
    for values in rows:
        # Required columns have unique names, so a dict view is safe here
        row = dict(zip(headers, values))
        an = row.get("Accession Number", "").strip()
        if not an:
            continue
        date_iso = row.get(DATE_ISO_COLUMN, "").strip()
        start = date_iso.split("/")[0]          # a range's start date
        records.append({
            "accession_number": an,
            "title":            row.get("title", "").strip(),
            "date_original":    " ".join(row.get("Date", "").split()),
            "date_iso":         date_iso,
            "date_year":        start[:4],
            # TDAT is DDMM; only a full date (or 0000-00-00) has one
            "date_ddmm":        start[8:10] + start[5:7] if len(start) == 10 else "",
            "restrictions":     row.get("Restrictions", "").strip(),
            "description":      row.get("Description", "").strip(),
            "place":            row.get("Place", "").strip(),
            "speakers":         row.get("Speakers", "").strip(),
            "copyright":        row.get("Production and Copyright", "").strip(),
        })
    return records


def load_records(context: ProcessingContext) -> Optional[List[Dict]]:
    """Records from this run's context if Step 2 ran in it, otherwise
    rebuilt from the batch CSV's Date ISO column. None if neither exists."""
    records = context.get_data("csv_records")
    if records:
        return records
    csv_file = context.paths.find_csv_file()
    if csv_file is None:
        return None
    records = records_from_csv(csv_file)
    if records:
        context.set_data("csv_records", records)
    return records


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

        errors: List[str] = []
        warnings: List[str] = []

        try:
            headers, rows = _read_csv_rows(csv_file)
        except Exception as e:
            return StepResult(False, f"Failed to read CSV: {e}")

        missing = [c for c in REQUIRED_CSV_COLUMNS if c not in headers]
        if missing:
            return StepResult(False, f"Missing required CSV columns: {', '.join(missing)}")

        an_idx = headers.index("Accession Number")
        date_idx = headers.index("Date")

        # Convert every row's date; collect all problems before failing
        iso_values: List[str] = []
        for line_num, values in enumerate(rows, start=2):
            an = values[an_idx].strip() if an_idx < len(values) else ""
            date_str = values[date_idx].strip() if date_idx < len(values) else ""

            if not an:
                warnings.append(f"Row {line_num}: empty Accession Number — skipped")
                iso_values.append("")
                continue

            if not date_str:
                warnings.append(f"Row {line_num} ({an}): no Date — using {BLANK_DATE_ISO}")
                iso_values.append(BLANK_DATE_ISO)
                continue

            dates = parse_date(date_str)
            if dates is None:
                errors.append(f"Row {line_num} ({an}): invalid date '{date_str}'")
                iso_values.append("")
            else:
                iso_values.append(dates["date_iso"])

        for w in warnings:
            self.logger.warning(w)
        for err in errors:
            self.logger.error(err)

        if errors:
            return StepResult(False, f"{len(errors)} date error(s) found — fix CSV and re-run")

        # Write the Date ISO column next to Date (replacing it on a re-run)
        if DATE_ISO_COLUMN in headers:
            iso_idx = headers.index(DATE_ISO_COLUMN)
            for values, iso in zip(rows, iso_values):
                values.extend([""] * (iso_idx + 1 - len(values)))
                values[iso_idx] = iso
        else:
            iso_idx = date_idx + 1
            headers.insert(iso_idx, DATE_ISO_COLUMN)
            for values, iso in zip(rows, iso_values):
                values.extend([""] * (iso_idx - len(values)))
                values.insert(iso_idx, iso)

        try:
            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
        except OSError as e:
            return StepResult(False, f"Could not write {DATE_ISO_COLUMN} column to CSV: {e}")
        self.logger.info(f"Wrote {DATE_ISO_COLUMN} column to {csv_file.name}")

        records = records_from_csv(csv_file) or []
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
