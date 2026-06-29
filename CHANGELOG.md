# Changelog - HSTL Audio Metadata Framework

All notable changes to the HSTL Audio Metadata Framework (HAM) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note for maintainers:** Every version header **must** include a date, a 4-digit 24-hour time, and the `CDT/CST` timezone label.
> Correct format: `## HAM [X.Y.Z] - YYYY-MM-DD HHMM CDT`
> Example: `## HAM [0.1.0] - 2026-05-02 1800 CDT`

---

## HAM [0.1.4] - 2026-06-29 1830 CDT

### Added
- **Step 1 implemented** (`steps/step1_csv_prep.py`) — CSV preparation and
  MP3/CSV filename matching; replaces stub:
  - Locates the CSV in `input/csv/`; validates all `REQUIRED_CSV_COLUMNS` present
  - Detects Sound\_File columns by name prefix (`sound_file*`), falls back to
    positional columns beyond the required set
  - Strips full URL prefixes from Sound\_File values to extract bare MP3 basenames
    (adapted from `match-audio-files.py`)
  - Reports matched / CSV-only / MP3-only file counts via logger
  - Writes `reports/step1_prep_report.txt` with full match detail
  - Populates `context.shared_data`: `csv_path`, `sound_file_cols`,
    `matched_mp3s`, `unmatched_csv_files`, `unmatched_mp3_files`
  - Fails only when no matches found; unmatched files are warnings

### Fixed
- **New Batch button** on Batches tab was dead — `_handle_batch_action()` called
  `registry.get_batch("")` before checking the action, got `None`, and returned
  early; `"new"` is now intercepted before the registry lookup and routed to
  `_new_batch()` (workaround: File → New Batch… still worked)

---

## HAM [0.1.3] - 2026-06-29 1040 CDT

### Added
- **`run.ps1`** — PowerShell launcher; auto-creates `.venv`, installs
  `requirements.txt` on first run or when it changes, then launches `ham_gui.py`;
  patterned after HPM `run.ps1`
- **Help menu** expanded to match HPM: User Guide (F1), Change Log, HAM Issue
  Tracker — all open GitHub URLs via `QDesktopServices`/`webbrowser`; `_open_url()`
  helper with `webbrowser` fallback
  - User Guide → `https://github.com/juren53/HST-Metadata-Audio/blob/master/README.md`
  - Change Log → `https://github.com/juren53/HST-Metadata-Audio/blob/master/CHANGELOG.md`
  - Issue Tracker → `https://github.com/juren53/HST-Metadata-Audio/issues`

### Changed
- **Step widget layout** — step rows now centred in a 720 px max-width column with
  horizontal stretch spacers; status label fixed at 100 px, Run Step button fixed at
  110 px; Run All button left-aligned and non-stretching (was full-width)
- **Step 4 label** renamed from "Thumbnail Creation & Embedding" to "Album Art
  Embedding" in `step_widget.py`, `step4_thumbnail_embed.py`

---

## HAM [0.1.2] - 2026-06-29 0948 CDT

### Added
- **ZoomManager** (`gui/zoom_manager.py`) — singleton font-scaling manager; mirrors
  `gui/zoom_manager.py` in HPM and the canonical `~/Projects/zoom-manager` module
  - 8 discrete zoom levels: 75%–200% (0.75 / 0.85 / 1.0 / 1.15 / 1.3 / 1.5 / 1.75 / 2.0)
  - Persists zoom level via `QSettings("HSTL", "AudioMetadata")` key `ui/zoom_level`
  - Emits `zoom_changed(float)` signal; base font captured once at startup
- **View menu** in `gui/main_window.py` — Zoom In (Ctrl++ / Ctrl+=), Zoom Out (Ctrl+-),
  Reset Zoom (Ctrl+0); View sits between Edit and Batch in the menu bar
- **Ctrl+Wheel zoom** — `wheelEvent` in `MainWindow` zooms in/out when Ctrl held
- Base font initialized in `ham_gui.py` immediately after `app.setStyle("Fusion")`;
  zoom preference applied at window load, saved at window close

---

## HAM [0.1.1] - 2026-06-29 0940 CDT

### Added
- **ThemeManager integration** (`gui/theme.py`) — wires `~/Projects/ThemeManager`
  into the HAM GUI; provides 6 built-in themes: light, dark, solarized\_light,
  solarized\_dark, dracula, github
- **Edit → Theme Selection…** menu item — `QInputDialog` theme picker that applies
  the Fusion palette immediately and persists selection to QSettings
- Theme loaded from QSettings on startup; default is **dark**; falls back to dark
  if saved theme is not available in the registry

### Fixed
- **`app.setStyle("Fusion")`** added to `ham_gui.py` — without this, ThemeManager's
  palette is applied to the native Windows style engine, causing menus and controls
  to render incorrectly ("blown out")
- **Default theme changed** from `light` to `dark` in `gui/theme.py`

---

## HAM [0.1.0] - 2026-06-29 1200 CDT

### Added
- **Full framework scaffold** — Phase 1 CLI and Phase 2 GUI skeleton, structured after HPM
  (HSTL Photo Metadata Framework):

  **Core infrastructure (fully functional):**
  - `__init__.py` — version string (`0.1.0`), app name constants
  - `config/config_manager.py` — YAML-backed ConfigManager with dot-notation get/set,
    5-step status tracking, config validation
  - `config/settings.py` — DEFAULT_SETTINGS dict, REQUIRED_CSV_COLUMNS list
  - `utils/validator.py` — ValidationResult dataclass (errors, warnings, merge)
  - `utils/path_manager.py` — PathManager; all batch directory paths in one place
  - `utils/logger.py` — HAMLogger with SUCCESS level, colour console output, file handler
  - `utils/file_utils.py` — safe_copy, count_mp3s, list_mp3s, open_in_explorer
  - `utils/batch_registry.py` — BatchRegistry YAML store; full CRUD + lifecycle management
  - `steps/base_step.py` — StepProcessor ABC, ProcessingContext, StepResult
  - `core/pipeline.py` — Pipeline orchestrator; dry-run and continue-on-error flags

  **Step modules:**
  - `steps/step2_csv_validation.py` — **fully implemented**: reads CSV, converts
    DD-MMM-YY dates to ISO 8601, validates all REQUIRED_CSV_COLUMNS, stores
    clean record list in ProcessingContext
  - `steps/step3_metadata_embed.py` — **fully implemented**: Mutagen ID3v2.3 tag
    embedding; all ATW tag mappings (TIT1/2/3, TALB, TPE1, COMM, TCOP, TPUB, TSRC,
    TDAT, TYER, TORY, TRDA, TOFN, TCON, WOAS, WXXX, TEXT, TXXX:ISBJ/IPRD/TLOC/ICRD,
    IPLS); copies originals to output/tmp/ before writing; saves with v2_version=3
  - `steps/step1_csv_prep.py` — **stub**: structure and TODO comments in place
  - `steps/step4_thumbnail_embed.py` — **stub** (Album Art Embedding): structure and TODO comments in place
  - `steps/step5_validation.py` — **stub**: structure and TODO comments in place

  **CLI entry point (`hstl_audio.py`):**
  - `init` — initialise batch; creates full directory tree; registers in BatchRegistry
  - `batches` — list all active batches (--all for archived/completed)
  - `run` — execute steps (--step N / --steps 1-3 / --all / --from N / --continue)
  - `status` — show batch step completion and data directory
  - `validate --dependencies` — checks mutagen, Pillow, PyYAML, colorama, tqdm
  - `batch info/complete/archive/reactivate/remove` — lifecycle management

  **GUI (`ham_gui.py` + `gui/`):**
  - `ham_gui.py` — PyQt6 launcher; ATW icon (copied from audio-tag-writer project);
    Windows AppUserModelID and taskbar icon fix via IconLoader
  - `gui/main_window.py` — 4-tab QMainWindow (Batches / Current Batch / Config / Logs);
    menu bar; status bar with version label; QSettings geometry persistence
  - `gui/widgets/batch_list_widget.py` — sortable batch table with context menu
  - `gui/widgets/step_widget.py` — per-step run buttons with status indicators;
    progress bar; Run All button
  - `gui/widgets/log_widget.py` — timestamped scrolling log pane with Clear button
  - `gui/dialogs/new_batch_dialog.py` — name + folder-picker dialog
  - `gui/dialogs/batch_info_dialog.py` — read-only batch detail dialog

  **ATW icon set** (`gui/resources/icons/`) — copied from `audio-tag-writer` project:
  app.ico, app.icns, app.png, app_16×16 through app_256×256

- **`requirements.txt`** — mutagen>=1.47, Pillow>=10, PyYAML>=6, PyQt6>=6.6,
  colorama>=0.4.6, tqdm>=4.66

### Notes
- Steps 1, 4, and 5 are stubs — implementation planned for subsequent sessions
- Step widget runs steps on the main thread; QThread wrapping planned for next session
- GUI Configuration tab is a placeholder; ConfigWidget implementation planned

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
