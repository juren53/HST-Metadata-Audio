"""
Step 3 – Metadata Tag Embedding

Copies MP3 files from input/mp3/ → output/tmp/, then uses Mutagen to write
ID3v2.3 tags for each record from the validated CSV (Step 2 output).

Tag mappings are drawn from the ATW prototype (audio-tags-12d.py) and the
field table in docs/HSTL_Audio_Framework-Development_Plan.md.
"""

import shutil
from io import BytesIO
from pathlib import Path
from typing import Dict, List

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult

_TOOL_VERSION = "HAM v0.1.0"
_STATIC_ARTIST = "Harry S. Truman Library"
_STATIC_GROUPING = "NARA-HST-SRC Sound Recordings Collection"
_STATIC_GENRE = "speech"
_STATIC_SOURCE_URL = "https://www.trumanlibrary.gov/library/sound-recordings-collection"
_STATIC_CATALOG_URL = "https://catalog.archives.gov/"
_STATIC_TSRC = "Harry S. Truman Library"


def _check_mutagen() -> bool:
    try:
        import mutagen  # noqa: F401
        return True
    except ImportError:
        return False


class Step3_MetadataEmbed(StepProcessor):
    """Embed ID3 metadata tags into MP3 files using Mutagen."""

    def __init__(self):
        super().__init__(3, "Metadata Tag Embedding")

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        if not _check_mutagen():
            result.add_error("mutagen is not installed. Run: pip install mutagen")
        records = context.get_data("csv_records")
        if not records:
            result.add_error("No CSV records found. Run Step 2 first.")
        mp3s = list(context.paths.input_mp3_dir.glob("*.mp3"))
        if not mp3s:
            result.add_error(f"No MP3 files found in {context.paths.input_mp3_dir}")
        return result

    def execute(self, context: ProcessingContext) -> StepResult:
        from mutagen.id3 import (
            ID3, ID3NoHeaderError,
            TIT1, TIT2, TIT3, TALB, TPE1, COMM, TCOP, TPUB, TSRC,
            TDAT, TYER, TORY, TRDA, TOFN, TCON, WOAS, WXXX, TEXT,
            TXXX, IPLS, APIC,
        )
        from mutagen.id3._util import ID3NoHeaderError

        records: List[Dict] = context.get_data("csv_records")
        record_map = {r["accession_number"]: r for r in records}

        working_dir = context.paths.working_dir
        working_dir.mkdir(parents=True, exist_ok=True)

        processed = []
        skipped = []

        for src_mp3 in sorted(context.paths.input_mp3_dir.glob("*.mp3")):
            an = src_mp3.stem  # filename without .mp3 = accession number
            record = record_map.get(an)
            if record is None:
                self.logger.warning(f"No CSV record for {an} — skipped")
                skipped.append(src_mp3)
                continue

            dst_mp3 = working_dir / src_mp3.name
            shutil.copy2(src_mp3, dst_mp3)

            try:
                try:
                    tags = ID3(str(dst_mp3))
                except ID3NoHeaderError:
                    tags = ID3()

                desc = record["description"]
                date_orig = record["date_original"]
                desc_date = f"{desc} {date_orig}"

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

                # IPLS: Involved People List (ID3v2.3 only) — Speakers field
                if record["speakers"]:
                    tags["IPLS"] = IPLS(encoding=3, people=[[record["speakers"], ""]])

                tags.save(str(dst_mp3), v2_version=3)
                processed.append(dst_mp3)
                self.logger.info(f"Tagged: {an}")

            except Exception as e:
                self.logger.error(f"Failed to tag {an}: {e}")
                skipped.append(src_mp3)

        msg = f"Tagged {len(processed)} files; skipped {len(skipped)}"
        self.logger.info(msg)
        context.set_data("tagged_mp3s", processed)
        return StepResult(True, msg, data={"tagged": len(processed), "skipped": len(skipped)},
                          files_processed=processed)

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        tagged = context.get_data("tagged_mp3s") or []
        records = context.get_data("csv_records") or []
        if len(tagged) == 0:
            result.add_error("No MP3 files were tagged in output/tmp/")
        elif len(tagged) != len(records):
            result.add_warning(
                f"Tagged {len(tagged)} files but CSV has {len(records)} records"
            )
        return result
