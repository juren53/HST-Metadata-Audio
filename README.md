# HSTL Audio Metadata (HAM)

An end-to-end framework for embedding archival metadata into MP3 sound recordings from the Harry S. Truman Presidential Library (HSTL) for submission to the National Archives and Records Administration (NARA) catalog.

## Overview

Approximately 2,000 audio files (MP3) require standardized ID3v2.3 metadata tags and custom album art before upload to the NARA catalog. HAM automates this as a five-step pipeline driven by a CSV export from the HSTL internal database.

Metadata is written using **[Mutagen](https://mutagen.readthedocs.io/)** — a pure-Python ID3 library that gives precise control over tag frames and versions. FFmpeg is retained as a fallback tool for manual inspection and validation of embedded tags.

## Five-Step Pipeline

| Step | Name | Status |
|---|---|---|
| 1 | CSV Preparation & Validation | Implemented |
| 2 | CSV Validation & Date Conversion | Implemented |
| 3 | Metadata Tag Embedding | Implemented |
| 4 | Album Art Embedding | Implemented |
| 5 | Output Validation & Reporting | Implemented |

**Step 1** copies the CSV export into the batch and imports MP3s from one or more source folders, matching each CSV row to `<Accession Number>.mp3`. The match result (matched / no MP3 / no CSV row) and the source folders are shown in the Current Batch → Input Files panel.

**Step 2** validates the required fields and converts dates to ISO 8601, writing them to a new `Date ISO` column in the batch's copy of the CSV so later steps can run in separate sessions. Accepted formats include `May 14, 1948`, `January, 1952`, `1961`, `1961-06-15` and the legacy `15-Jun-61`. Date ranges (`X - Y`) are stored as ISO intervals (`1946-09-21/1947-10-22`), with the start date used for the year and DDMM tags. Blank dates become `0000-00-00` with a warning; any unparseable date fails the step.

**Step 3** copies each matched MP3 to `output/tmp/` and embeds the ID3v2.3 frames listed below via Mutagen (originals in `input/` are never modified). Every file is read back and checked against the CSV, an external spot check is run with exiftool (ffprobe fallback), and a summary is written to `reports/step3_tag_report.txt`.

**Step 4** uses Pillow to draw the accession number on the album-art template (`assets/HST-blank-album-art.jpg`), embeds it as an APIC front-cover frame, and saves the finished MP3 to `output/processed/`. Each output's audio length is checked against its source.

**Step 5** checks every file in `output/processed/` — readable audio, file size, required frames (TIT2, TALB, TPE1, TRDA, TCON), album art, and title/album against the CSV — and writes a timestamped report to `reports/`.

## Running HAM

### Windows executable

Download `HAM.exe` from the latest release — no Python install needed:

**https://github.com/juren53/HST-Metadata-Audio/releases/latest**

(Current release: [v0.3.9](https://github.com/juren53/HST-Metadata-Audio/releases/tag/v0.3.9).) Batches are tracked in `~/.hstl_audio_framework/config/batch_registry.yaml`, shared with the source version.

### GUI (recommended)

```powershell
.\run.ps1
```

Creates a `.venv`, installs dependencies on first run, and launches the PyQt6 desktop application.

### CLI

```bash
python hstl_audio.py --help

# Initialize a new batch
python hstl_audio.py init "Round 4" --data-dir "C:\path\to\data"

# List batches
python hstl_audio.py batches

# Run all steps (--config goes before the subcommand)
python hstl_audio.py --config "C:\path\to\batch\config\project_config.yaml" run --all

# Run a specific step
python hstl_audio.py --config "C:\path\to\batch\config\project_config.yaml" run --step 3

# Check dependency status
python hstl_audio.py validate --dependencies
```

## CSV Metadata Fields

| Field | ID3 Frame | Notes |
|---|---|---|
| `title` | TIT2 | Recording title |
| `Accession Number` | TALB, TOFN, TXXX:IPRD | TOFN is `<Accession Number>.mp3`; also drawn on the album art |
| `Date` (via `Date ISO`) | TRDA, TYER, TORY, TDAT | TRDA = ISO date or interval; TDAT (DDMM) only for full dates |
| `Date` (original text) | TXXX:ICRD | As entered in the CSV |
| `Description` + `Date` | TIT3, COMM, TXXX:ISBJ | Description followed by the original date |
| `Restrictions` | TCOP | Access / copyright note |
| `Production and Copyright` | TPUB | Publisher |
| `Place` | TXXX:TLOC | Custom location frame |
| `Speakers` | IPLS | Stored as (involvement, person) with a blank involvement |

Fixed values on every file: TPE1 `Harry S. Truman Library`, TIT1 `NARA-HST-SRC Sound Recordings Collection`, TCON `speech`, TSRC `Harry S. Truman Library`, WOAS (Library sound-recordings page), WXXX (NARA catalog), and TEXT `HAM v<version>`.

All tags are saved as **ID3v2.3** (required for the TDAT, TRDA, TORY, TYER and IPLS frames). Read them back with `ID3(path, translate=False)` — Mutagen's default load converts the v2.3 date frames to v2.4 ones.

## Project Structure

```
Audio/
├── ham_gui.py                 # PyQt6 GUI launcher
├── hstl_audio.py              # CLI entry point
├── run.ps1                    # PowerShell launcher (venv + deps)
├── HAM.spec                   # PyInstaller build for HAM.exe
├── version_info.txt           # Windows exe version resource
├── requirements.txt
├── __init__.py                # Version constants
├── assets/
│   └── HST-blank-album-art.jpg  # Step 4 album-art template
├── config/
│   ├── config_manager.py      # YAML-backed batch configuration
│   └── settings.py            # Defaults and required CSV columns
├── core/
│   └── pipeline.py            # Step orchestrator
├── steps/
│   ├── base_step.py           # StepProcessor ABC
│   ├── step1_csv_prep.py      # CSV prep & MP3 matching
│   ├── step2_csv_validation.py
│   ├── step3_metadata_embed.py
│   ├── step4_thumbnail_embed.py  # Album art (APIC)
│   └── step5_validation.py    # Output checks & report
├── utils/
│   ├── batch_registry.py      # YAML batch registry (~/.hstl_audio_framework/config)
│   ├── path_manager.py        # Batch directory layout
│   ├── logger.py              # HAMLogger with SUCCESS level
│   ├── validator.py           # ValidationResult dataclass
│   └── file_utils.py
├── gui/
│   ├── main_window.py         # 4-tab QMainWindow
│   ├── theme.py               # ThemeManager integration (6 themes)
│   ├── zoom_manager.py        # Font-scaling zoom (75%–200%)
│   ├── widgets/
│   └── dialogs/
├── docs/
│   └── HSTL_Audio_Framework-Development_Plan.md
└── analysis/                  # Working files and catalog exports
```

## Dependencies

| Package | Purpose |
|---|---|
| [mutagen](https://mutagen.readthedocs.io/) ≥ 1.47 | ID3v2.3 tag embedding (primary) |
| [Pillow](https://python-pillow.org/) ≥ 10.0 | Album art generation (Step 4) |
| [PyYAML](https://pyyaml.org/) ≥ 6.0 | Batch registry and config files |
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) ≥ 6.6 | Desktop GUI |
| [colorama](https://github.com/tartley/colorama) ≥ 0.4.6 | CLI colour output |
| [tqdm](https://tqdm.github.io/) ≥ 4.66 | CLI progress bars |

### FFmpeg (optional)

FFmpeg is **not required** to run HAM. It is useful as a fallback tool for independently verifying that ID3 tags were embedded correctly:

```bash
# Inspect tags written by Mutagen
ffprobe -v quiet -print_format json -show_format output.mp3

# Manually embed album art for comparison/testing
ffmpeg -i input.mp3 -i thumbnail.jpg \
  -map 0 -map 1 -c copy \
  -id3v2_version 3 \
  output.mp3
```

## Related Projects

- **HPM** — HSTL Photo Metadata Framework (`HST-Metadata/Photos/Version-2/Framework/`)
- **ATW** — Audio Tag Writer prototype (`audio-tag-writer/`) — the standalone script that preceded HAM; icon set reused in HAM GUI
