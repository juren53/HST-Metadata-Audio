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
| 4 | Album Art Embedding | Stub |
| 5 | Output Validation & Reporting | Stub |

**Step 2** reads the CSV, validates all required fields, and converts dates from `DD-MMM-YY` format to ISO 8601.

**Step 3** embeds all ID3v2.3 tag frames via Mutagen — including title, date, description, speakers, copyright, ISRC, genre, and custom TXXX frames — then saves each MP3 with `v2_version=3`. Original files are backed up to `output/tmp/` before any writes.

**Step 4** will use Pillow to overlay the accession number on the base thumbnail image (`HST-thumbnail-c.png`) and embed the result as an APIC (album art) frame.

## Running HAM

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

# Run all steps
python hstl_audio.py run --all

# Run a specific step
python hstl_audio.py run --step 3

# Check dependency status
python hstl_audio.py validate --dependencies
```

## CSV Metadata Fields

| Field | ID3 Frame | Notes |
|---|---|---|
| `title` | TIT2 | Recording title |
| `Accession Number` | TSRC, TOFN, TXXX:ISBJ, TXXX:IPRD | Multiple frames |
| `Date` | TDAT, TYER, TORY, TRDA, TXXX:ICRD | DD-MMM-YY → ISO 8601 |
| `Restrictions` | TIT3 | Subtitle / access note |
| `Description` | COMM, TEXT | Comment and lyrics frames |
| `Place` | TXXX:TLOC | Custom location frame |
| `Speakers` | IPLS | Involved people list |
| `Production and Copyright` | TCOP, TPUB, WOAS, WXXX | Copyright + publisher |

All tags saved as **ID3v2.3** (required for TDAT, TRDA, TORY, TYER, IPLS frames).

## Project Structure

```
Audio/
├── ham_gui.py                 # PyQt6 GUI launcher
├── hstl_audio.py              # CLI entry point
├── run.ps1                    # PowerShell launcher (venv + deps)
├── requirements.txt
├── __init__.py                # Version constants
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
│   ├── step4_thumbnail_embed.py  # Stub
│   └── step5_validation.py    # Stub
├── utils/
│   ├── batch_registry.py      # YAML batch registry
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
