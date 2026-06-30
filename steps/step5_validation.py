"""
Step 5 – Output Validation & Reporting

For each MP3 in output/processed/ (Step 4 output):
  1. Open with Mutagen ID3; confirm required frames are present
  2. Verify APIC front-cover frame (album art from Step 4)
  3. Cross-reference TIT2 / TALB against csv_records (if available)
  4. Check file size is reasonable (> MIN_FILE_BYTES, < MAX_FILE_BYTES)
  5. Write a timestamped human-readable report to reports/

Returns pass if every file passes every check; fail if any file fails.
"""

import datetime
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult


_MIN_FILE_BYTES = 10_000          # 10 KB  — suspiciously small
_MAX_FILE_BYTES = 100_000_000     # 100 MB — suspiciously large

_REQUIRED_FRAMES = ["TIT2", "TALB", "TPE1", "TRDA", "TCON"]

_SEPARATOR = "─" * 60


def _tz_abbr() -> str:
    tz_full = time.tzname[time.localtime().tm_isdst]
    return "".join(w[0] for w in tz_full.split())


def _size_str(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    return f"{n / 1_024:.1f} KB"


def _apic_size(tags) -> Optional[int]:
    for key in tags:
        if key.startswith("APIC"):
            return len(tags[key].data)
    return None


# ── per-file validation ────────────────────────────────────────────────────────

def _validate_file(
    mp3_path: Path,
    record_map: Dict[str, dict],
) -> Tuple[bool, List[str], List[str]]:
    """Returns (passed, errors, info_lines) for the report."""
    from mutagen.id3 import ID3, ID3NoHeaderError
    from mutagen.id3._util import ID3NoHeaderError as _ID3NHE  # noqa: F811

    errors: List[str] = []
    info: List[str] = []
    an = mp3_path.stem

    # --- file size ---
    size = mp3_path.stat().st_size
    info.append(f"  size:   {_size_str(size)}")
    if size < _MIN_FILE_BYTES:
        errors.append(f"File too small ({_size_str(size)}) — may be corrupt or empty")
    elif size > _MAX_FILE_BYTES:
        errors.append(f"File suspiciously large ({_size_str(size)})")

    # --- open ID3 ---
    try:
        tags = ID3(str(mp3_path))
    except (ID3NoHeaderError, _ID3NHE):
        errors.append("No ID3 header found")
        return False, errors, info
    except Exception as exc:
        errors.append(f"Failed to open ID3: {exc}")
        return False, errors, info

    # --- required frames ---
    for frame in _REQUIRED_FRAMES:
        if frame not in tags:
            errors.append(f"Missing frame: {frame}")

    # --- APIC ---
    apic_size = _apic_size(tags)
    if apic_size is None:
        errors.append("APIC (album art) frame missing")
        info.append("  art:    MISSING")
    else:
        info.append(f"  art:    embedded (APIC, {_size_str(apic_size)})")

    # --- text field readback ---
    title = str(tags["TIT2"]) if "TIT2" in tags else ""
    album = str(tags["TALB"]) if "TALB" in tags else ""
    trda  = str(tags["TRDA"]) if "TRDA" in tags else ""
    info.append(f"  title:  {title[:80]}")
    info.append(f"  date:   {trda}")

    # --- cross-reference against CSV ---
    record = record_map.get(an)
    if record:
        if album != an:
            errors.append(f"TALB mismatch: expected '{an}', found '{album}'")
        expected_title = record.get("title", "")
        if expected_title and title != expected_title:
            errors.append(
                f"TIT2 mismatch: expected '{expected_title[:60]}', found '{title[:60]}'"
            )

    passed = len(errors) == 0
    return passed, errors, info


# ── Step class ─────────────────────────────────────────────────────────────────

class Step5_Validation(StepProcessor):
    """Output validation and summary reporting."""

    def __init__(self):
        super().__init__(5, "Output Validation & Reporting")

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        if not context.paths.processed_dir.exists():
            result.add_error("output/processed/ not found — run Step 4 first")
        elif not any(context.paths.processed_dir.glob("*.mp3")):
            result.add_error("No MP3 files in output/processed/ — run Step 4 first")
        try:
            import mutagen  # noqa: F401
        except ImportError:
            result.add_error("mutagen is not installed — run: pip install mutagen")
        return result

    def execute(self, context: ProcessingContext) -> StepResult:
        mp3_files = sorted(context.paths.processed_dir.glob("*.mp3"))
        records: List[dict] = context.get_data("csv_records") or []
        record_map = {r["accession_number"]: r for r in records}

        passed_files, failed_files = [], []
        report_lines: List[str] = []

        for mp3 in mp3_files:
            passed, errors, info = _validate_file(mp3, record_map)
            status = "PASS" if passed else "FAIL"
            report_lines.append(f"{status}  {mp3.name}")
            report_lines.extend(info)
            if errors:
                for err in errors:
                    report_lines.append(f"  ERROR: {err}")
            report_lines.append("")
            (passed_files if passed else failed_files).append(mp3.name)

        self._write_report(context, mp3_files, passed_files, failed_files, report_lines)

        summary = (
            f"{len(mp3_files)} files checked — "
            f"{len(passed_files)} passed, {len(failed_files)} failed"
        )
        self.logger.info(summary)
        for name in failed_files:
            self.logger.error(f"Validation failed: {name}")

        context.set_data("validation_passed", len(failed_files) == 0)
        context.set_data("validation_summary", summary)

        success = len(failed_files) == 0
        return StepResult(success, summary, files_processed=list(mp3_files))

    def _write_report(
        self,
        context: ProcessingContext,
        mp3_files,
        passed_files: List[str],
        failed_files: List[str],
        detail_lines: List[str],
    ):
        now = datetime.datetime.now()
        ts_display = now.strftime("%Y-%m-%d %H%M ") + _tz_abbr()
        ts_file    = now.strftime("%Y%m%d_%H%M%S")

        context.paths.reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = context.paths.reports_dir / f"step5_report_{ts_file}.txt"

        lines = [
            "Step 5 – Output Validation Report",
            f"Generated: {ts_display}",
            "",
            f"Output directory: {context.paths.processed_dir}",
            f"Total files:  {len(mp3_files)}",
            f"  Passed:     {len(passed_files)}",
            f"  Failed:     {len(failed_files)}",
            "",
            _SEPARATOR,
            "",
        ]
        lines.extend(detail_lines)
        lines.append(_SEPARATOR)
        if failed_files:
            lines.append("")
            lines.append("FAILED FILES:")
            for name in failed_files:
                lines.append(f"  {name}")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        self.logger.info(f"Report written: {report_path.name}")
        context.set_data("validation_report", str(report_path))

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        report_path = context.get_data("validation_report")
        if not report_path or not Path(report_path).exists():
            result.add_warning("Validation report was not written")
        if not context.get_data("validation_passed"):
            result.add_warning("One or more output files failed validation — check report")
        return result
