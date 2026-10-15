"""
Step 3 – Metadata Tag Embedding

Copies MP3 files from input/mp3/ → output/tmp/, then uses Mutagen to write
ID3v2.3 tags for each record from the validated CSV (Step 2 output: the
batch CSV with its Date ISO column).

Validation (per the Development Plan's Step 3 row):
  - Mutagen write success: every written file is re-opened and its key
    frames read back; any failed write or mismatch fails the step
  - MP3 count vs CSV row count: tagged / CSV-only / MP3-only counts are
    logged and reported (a partial batch is a warning, not a failure)
  - Spot-check with an external tool: a random sample of tagged files is
    read with exiftool (or ffprobe if exiftool isn't installed) and its
    title/album compared with the CSV

Writes reports/step3_tag_report.txt.

Tag mappings are drawn from the ATW prototype (audio-tags-12d.py) and the
field table in docs/HSTL_Audio_Framework-Development_Plan.md.
"""

import json
import random
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult
from steps.step2_csv_validation import load_records

try:
    from __init__ import __version__ as _HAM_VERSION
except ImportError:  # imported outside the app (e.g. a test harness)
    _HAM_VERSION = "unknown"

_TOOL_VERSION = f"HAM v{_HAM_VERSION}"
_STATIC_ARTIST = "Harry S. Truman Library"
_STATIC_GROUPING = "NARA-HST-SRC Sound Recordings Collection"
_STATIC_GENRE = "speech"
_STATIC_SOURCE_URL = "https://www.trumanlibrary.gov/library/sound-recordings-collection"
_STATIC_CATALOG_URL = "https://catalog.archives.gov/"
_STATIC_TSRC = "Harry S. Truman Library"

# Frames re-read after each save to confirm the write took
_READBACK_FRAMES = ("TIT2", "TALB", "TRDA", "TYER")

# Don't flash a console window per subprocess when running as the GUI exe
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _check_mutagen() -> bool:
    try:
        import mutagen  # noqa: F401
        return True
    except ImportError:
        return False


def _external_read(mp3: Path) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """Read title/album/date with an external tool, independent of Mutagen.

    Returns (tool_name, {"title", "album", "date"}), or (None, None) if
    neither exiftool nor ffprobe is installed. Raises on tool failure.
    """
    if shutil.which("exiftool"):
        out = subprocess.run(
            ["exiftool", "-j", "-charset", "filename=utf8",
             "-ID3:Title", "-ID3:Album", "-ID3:RecordingDates", str(mp3)],
            capture_output=True, text=True, encoding="utf-8",
            timeout=30, check=True, creationflags=_NO_WINDOW,
        ).stdout
        data = json.loads(out)[0]
        return "exiftool", {
            "title": str(data.get("Title", "")),
            "album": str(data.get("Album", "")),
            "date":  str(data.get("RecordingDates", "")),
        }
    if shutil.which("ffprobe"):
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(mp3)],
            capture_output=True, text=True, encoding="utf-8",
            timeout=30, check=True, creationflags=_NO_WINDOW,
        ).stdout
        tags = {k.lower(): v for k, v in json.loads(out).get("format", {}).get("tags", {}).items()}
        return "ffprobe", {
            "title": tags.get("title", ""),
            "album": tags.get("album", ""),
            "date":  tags.get("tdat", tags.get("date", "")),
        }
    return None, None


class Step3_MetadataEmbed(StepProcessor):
    """Embed ID3 metadata tags into MP3 files using Mutagen."""

    def __init__(self):
        super().__init__(3, "Metadata Tag Embedding")

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        if not _check_mutagen():
            result.add_error("mutagen is not installed. Run: pip install mutagen")
        records = load_records(context)
        if not records:
            result.add_error("CSV has no converted dates (Date ISO column). Run Step 2 first.")
        mp3s = list(context.paths.input_mp3_dir.glob("*.mp3"))
        if not mp3s:
            result.add_error(f"No MP3 files found in {context.paths.input_mp3_dir}")
        return result

    def execute(self, context: ProcessingContext) -> StepResult:
        from mutagen.id3 import (
            ID3, ID3NoHeaderError,
            TIT1, TIT2, TIT3, TALB, TPE1, COMM, TCOP, TPUB, TSRC,
            TDAT, TYER, TORY, TRDA, TOFN, TCON, WOAS, WXXX, TEXT,
            TXXX, IPLS,
        )

        records: List[Dict] = load_records(context)
        record_map = {r["accession_number"]: r for r in records}

        working_dir = context.paths.working_dir
        working_dir.mkdir(parents=True, exist_ok=True)

        # Clear MP3s left by an earlier run, so Step 4 only sees this run's output
        stale = list(working_dir.glob("*.mp3"))
        for f in stale:
            f.unlink()
        if stale:
            self.logger.info(f"Cleared {len(stale)} MP3(s) from an earlier run in output/tmp/")

        tagged: List[Path] = []
        no_record: List[str] = []           # MP3s with no CSV row
        failed: List[Tuple[str, str]] = []  # (accession number, reason)

        for src_mp3 in sorted(context.paths.input_mp3_dir.glob("*.mp3")):
            an = src_mp3.stem  # filename without .mp3 = accession number
            record = record_map.get(an)
            if record is None:
                self.logger.warning(f"No CSV record for {an} — skipped")
                no_record.append(src_mp3.name)
                continue

            dst_mp3 = working_dir / src_mp3.name
            try:
                shutil.copy2(src_mp3, dst_mp3)
                try:
                    tags = ID3(str(dst_mp3))
                except ID3NoHeaderError:
                    tags = ID3()

                desc = record["description"]
                date_orig = record["date_original"]
                desc_date = f"{desc} {date_orig}".strip()

                tags.update_to_v23()

                tags["TIT2"] = TIT2(encoding=3, text=record["title"])
                tags["TIT1"] = TIT1(encoding=3, text=_STATIC_GROUPING)
                tags["TIT3"] = TIT3(encoding=3, text=desc_date)
                tags["TALB"] = TALB(encoding=3, text=an)
                tags["TPE1"] = TPE1(encoding=3, text=_STATIC_ARTIST)
                tags["COMM"] = COMM(encoding=3, lang="eng", desc="Comment", text=desc_date)
                tags["TCOP"] = TCOP(encoding=3, text=record["restrictions"])
                tags["TPUB"] = TPUB(encoding=3, text=record["copyright"])
                tags["TSRC"] = TSRC(encoding=3, text=_STATIC_TSRC)
                if record["date_ddmm"]:  # partial dates (e.g. "1961") have no DDMM
                    tags["TDAT"] = TDAT(encoding=3, text=record["date_ddmm"])
                tags["TYER"] = TYER(encoding=3, text=record["date_year"])
                tags["TORY"] = TORY(encoding=3, text=record["date_year"])
                tags["TRDA"] = TRDA(encoding=3, text=record["date_iso"])
                tags["TOFN"] = TOFN(encoding=3, text=f"{an}.mp3")
                tags["TCON"] = TCON(encoding=3, text=_STATIC_GENRE)
                tags["WOAS"] = WOAS(url=_STATIC_SOURCE_URL)
                tags["WXXX"] = WXXX(encoding=3, desc="", url=_STATIC_CATALOG_URL)
                tags["TEXT"] = TEXT(encoding=3, text=_TOOL_VERSION)
                tags["TXXX:ISBJ"] = TXXX(encoding=3, desc="ISBJ", text=desc_date)
                tags["TXXX:IPRD"] = TXXX(encoding=3, desc="IPRD", text=an)
                tags["TXXX:TLOC"] = TXXX(encoding=3, desc="TLOC", text=record["place"])
                tags["TXXX:ICRD"] = TXXX(encoding=3, desc="ICRD", text=date_orig)

                # IPLS: Involved People List (ID3v2.3 only) — Speakers field.
                # Pairs are (involvement, person); no role, so involvement is blank.
                if record["speakers"]:
                    tags["IPLS"] = IPLS(encoding=3, people=[["", record["speakers"]]])

                tags.save(str(dst_mp3), v2_version=3)

                # Read back from disk to confirm the write took
                problem = self._readback(dst_mp3, record)
                if problem:
                    raise ValueError(problem)

                tagged.append(dst_mp3)
                self.logger.info(f"Tagged: {an}")

            except Exception as e:
                self.logger.error(f"Failed to tag {an}: {e}")
                failed.append((an, str(e)))
                dst_mp3.unlink(missing_ok=True)  # don't hand a bad file to Step 4

        # MP3 count vs CSV row count
        mp3_names = {p.stem for p in context.paths.input_mp3_dir.glob("*.mp3")}
        csv_only = sorted(an for an in record_map if an not in mp3_names)
        self.logger.info(
            f"Tagged {len(tagged)} of {len(record_map)} CSV rows  |  "
            f"CSV rows with no MP3: {len(csv_only)}  |  MP3s with no CSV row: {len(no_record)}"
        )
        if csv_only or no_record:
            self.logger.warning("MP3 count does not match CSV row count — "
                                "see reports/step3_tag_report.txt")

        # Spot-check a sample with an external tool
        sample_size = self.get_step_config(context, "spot_check_count", 3)
        spot_lines, spot_errors = self._spot_check(tagged, record_map, sample_size)
        for an, reason in spot_errors:
            failed.append((an, f"spot-check: {reason}"))

        self._write_report(context, tagged, record_map, csv_only, no_record,
                           failed, spot_lines)

        context.set_data("tagged_mp3s", tagged)
        msg = (f"Tagged {len(tagged)} of {len(record_map)} CSV rows; "
               f"{len(no_record)} MP3(s) with no CSV row skipped")
        if failed:
            return StepResult(False, f"{len(failed)} file(s) failed tagging or verification "
                                     f"— see reports/step3_tag_report.txt ({msg})")
        return StepResult(True, msg,
                          data={"tagged": len(tagged), "skipped": len(no_record),
                                "csv_only": len(csv_only)},
                          files_processed=tagged)

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        tagged = context.get_data("tagged_mp3s") or []
        if len(tagged) == 0:
            result.add_error("No MP3 files were tagged in output/tmp/")
        return result

    # ── private ───────────────────────────────────────────────────────────

    @staticmethod
    def _readback(mp3: Path, record: Dict) -> Optional[str]:
        """Re-open the saved file and compare key frames; return a problem or None."""
        from mutagen.id3 import ID3

        # translate=False: Mutagen otherwise folds v2.3 TRDA/TYER/TDAT into TDRC
        tags = ID3(str(mp3), translate=False)
        if tags.version[:2] != (2, 3):
            return f"saved as ID3v2.{tags.version[1]}, expected v2.3"
        expected = {
            "TIT2": record["title"],
            "TALB": record["accession_number"],
            "TRDA": record["date_iso"],
            "TYER": record["date_year"],
        }
        for frame in _READBACK_FRAMES:
            if frame not in tags:
                return f"{frame} missing after save"
            if str(tags[frame]) != expected[frame]:
                return f"{frame} reads back as '{tags[frame]}', expected '{expected[frame]}'"
        return None

    def _spot_check(self, tagged: List[Path], record_map: Dict[str, Dict],
                    sample_size: int) -> Tuple[List[str], List[Tuple[str, str]]]:
        """Read a random sample with exiftool/ffprobe; compare title and album."""
        lines: List[str] = []
        errors: List[Tuple[str, str]] = []
        sample = random.sample(tagged, min(sample_size, len(tagged)))
        for mp3 in sample:
            an = mp3.stem
            try:
                tool, found = _external_read(mp3)
            except Exception as e:  # noqa: BLE001 - a tool failure is a warning, not a bad file
                self.logger.warning(f"Spot-check of {an} could not run: {e}")
                lines.append(f"  {an}: could not run external tool ({e})")
                continue
            if tool is None:
                self.logger.warning("Spot-check skipped — neither exiftool nor ffprobe is installed")
                lines.append("  skipped: neither exiftool nor ffprobe is installed")
                break

            record = record_map[an]
            bad = [f"{field} is '{found[field]}', expected '{want}'"
                   for field, want in (("title", record["title"]), ("album", an))
                   if found[field] != want]
            status = "FAIL" if bad else "OK"
            lines.append(f"  {status}  {an} ({tool}): title='{found['title'][:60]}' "
                         f"album='{found['album']}' date='{found['date']}'")
            if bad:
                errors.append((an, "; ".join(bad)))
                self.logger.error(f"Spot-check {an} ({tool}): {'; '.join(bad)}")
            else:
                self.logger.info(f"Spot-check {an} ({tool}): OK")
        return lines, errors

    def _write_report(self, context, tagged, record_map, csv_only, no_record,
                      failed, spot_lines):
        report_path = context.paths.reports_dir / "step3_tag_report.txt"
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as fh:
                fh.write("HAM Step 3 — Metadata Tag Report\n")
                fh.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}  ({_TOOL_VERSION})\n")
                fh.write("=" * 50 + "\n\n")
                fh.write(f"CSV rows            : {len(record_map)}\n")
                fh.write(f"Tagged              : {len(tagged)}\n")
                fh.write(f"Failed              : {len(failed)}\n")
                fh.write(f"CSV rows with no MP3: {len(csv_only)}\n")
                fh.write(f"MP3s with no CSV row: {len(no_record)}\n\n")
                fh.write("Spot-check (external tool):\n")
                fh.writelines(line + "\n" for line in spot_lines or ["  (no files tagged)"])
                if failed:
                    fh.write("\nFailed:\n")
                    fh.writelines(f"  {an}: {reason}\n" for an, reason in failed)
                if no_record:
                    fh.write("\nMP3s with no CSV row (not tagged):\n")
                    fh.writelines(f"  {name}\n" for name in no_record)
                if csv_only:
                    fh.write("\nCSV rows with no MP3:\n")
                    fh.writelines(f"  {an}\n" for an in csv_only)
            self.logger.info(f"Report written: {report_path}")
        except OSError as e:
            self.logger.warning(f"Could not write Step 3 report: {e}")
