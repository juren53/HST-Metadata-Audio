# Changelog - HSTL Audio Metadata Framework

All notable changes to the HSTL Audio Metadata Framework (HAM) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note for maintainers:** Every version header **must** include a date, a 4-digit 24-hour time, and the `CDT/CST` timezone label.
> Correct format: `## HAM [X.Y.Z] - YYYY-MM-DD HHMM CDT`
> Example: `## HAM [0.1.0] - 2026-05-02 1800 CDT`

---

## HAM [0.0.2] - 2026-05-02 1800 CDT

### Changed
- **Framework renamed** — "HSTL Audio Framework" → "HSTL Audio Metadata Framework" throughout
  development plan documentation
  - **Files Modified**: `docs/HSTL_Audio_Framework-Development_Plan.md`

- **Metadata tag library decision** — Step 3 (metadata embedding) will use the **Mutagen**
  Python library instead of FFmpeg; FFmpeg retained for Step 4 thumbnail image generation only
  - **Files Modified**: `docs/HSTL_Audio_Framework-Development_Plan.md`

- **Prototype reference updated** — all references to `audio-tags-09.py` updated to
  `audio-tags-12d.py` (v0.12d) as the canonical prototype
  - **Files Modified**: `docs/HSTL_Audio_Framework-Development_Plan.md`

### Added
- **`match-audio-files.py`** — utility script that matches MP3 files in the working directory
  against accession numbers from a CSV file; reports match counts and unmatched files;
  incorporated into the plan as a Step 1 pre-flight utility

- **Audio Metadata Tag Field Mappings table** — expanded tag table reflecting the v0.12d
  prototype, including:
  - Added `TCON` (Genre = speech), `dc:description`, `xmpDM:logComment`, `©cmt`, `©pub`,
    `dc:publisher` fields present in v0.12d
  - Mutagen Notes column identifying native frames vs. TXXX workarounds
  - Correction: `ISRC` key renamed to correct Mutagen frame name `TSRC`
  - `ISBJ`, `IPRD`, `TLOC`, `ICRD` flagged as TXXX frames (no native ID3 equivalent)
  - XMP and iTunes © tags (`dc:description`, `xmpDM:logComment`, `©cmt`, `©pub`,
    `dc:publisher`) removed from HAM tag set — not supported by Mutagen for MP3 files
  - ID3v2.3-only frames (`TDAT`, `TRDA`, `TORY`, `TYER`, `IPLS`) flagged as requiring
    `v2_version=3` on save
  - **Files Modified**: `docs/HSTL_Audio_Framework-Development_Plan.md`

### Fixed
- **Known bug flagged** — `IPLS` (Speakers) is hardcoded in the v0.12d prototype;
  noted as a known issue to correct in the HAM framework implementation
  - **Files Modified**: `docs/HSTL_Audio_Framework-Development_Plan.md`

---

## HAM [0.0.1] - 2026-04-20 0000 CDT

### Added
- **Development Plan** (`docs/HSTL_Audio_Framework-Development_Plan.md`) — initial
  framework design document covering:
  - Proposed project directory structure
  - Core architecture patterns (plugin/pipeline/configuration-driven/multi-batch)
  - Five-step process overview with validation requirements
  - CLI interface design with full command reference
  - Data directory and configuration file structure
  - ID3 tag field mappings (based on `audio-tags-09.py` v0.09)
  - Multi-batch workflow and batch lifecycle states
  - Implementation strategy and development order
  - Dependencies, testing strategy, and risk mitigation

---

## Prototype History (audio-tags.py / ATW)

> The following documents the evolution of the audio tagging prototype script that preceded
> the HAM framework. This code is the reference implementation for Steps 2–4.

| Version | Date            | Description                                                                 |
| ------- | --------------- | --------------------------------------------------------------------------- |
| v0.12d  | 05 Oct 2024     | Added additional description tags; date string appended to description fields for Round 4 testing |
| v0.11   | 21 Sep 2024     | Code migrated to Windows 11; removed tag key prefixes; updated base album cover image |
| v0.09   | 31 Aug 2024     | Updated tag list per LAA guidance email of 2024-08-13                      |
| v0.08   | 03 Jul 2024     | Fixed single-digit day problem using `dt.isoformat()[:10][-2:]`            |
| v0.07   | 01 Jul 2024     | Renamed to `audio-tags.py`; `csv_filename` variable introduced              |
| v0.06   | 30 Jun 2024     | Intermediate FFmpeg output written to `tmp/` directory                     |
| v0.05   | 29 Jun 2024     | Tagged MP3s written to `processed/` directory                              |
| v0.04   | 29 Jun 2024     | Custom thumbnails embedded into MP3 files via FFmpeg                       |
| v0.03   | 26 Jun 2024     | ID3 metadata tags written to MP3 files via FFmpeg                         |
| v0.02   | 25 Jun 2024     | Metadata read from CSV file using `csv.DictReader`                        |
| v0.01   | 24 Jun 2024     | Initial script; date conversion from `LIST_Audio-Dates.txt`               |
