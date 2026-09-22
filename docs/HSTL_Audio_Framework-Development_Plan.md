# HSTL Audio Metadata Framework - Development Plan

Updated: 2026-09-21 2330 CDT

## Project Overview

The HSTL Audio Framework (HAM) is an application that orchestrates all components of the HSTL Audio Metadata Project. It manages the complete process from CSV metadata preparation through final tagged MP3 creation, embedding audio metadata and custom album art thumbnails into the Harry S. Truman Library sound recordings collection.

HAM is the second application in the HSTL metadata framework family. It follows **HPM (HSTL Photo Metadata)** — a PyQt6 desktop application that is delivered and working in production for the customer, orchestrating an 8-step photo processing pipeline. HAM is deliberately **not** a from-scratch design: wherever HAM's problem shape matches HPM's, HAM adopts HPM's already-proven architecture, module layout, and GUI patterns rather than inventing new ones. See [Relationship to HPM](#relationship-to-hpm-predecessor-framework) below.

## Repository Information

- **GitHub Repository**: https://github.com/juren53/HST-Metadata-Audio
- **Branch**: `master` (main branch)
- **Local Repository**: `C:\Users\juren\Projects\HST-Metadata`
- **Audio Project Path**: `Audio/`
- **Predecessor Reference**: `C:\Users\juren\Projects\HST-Metadata\Photos\Version-2\Framework` (HPM — delivered, in production; the canonical reference implementation for framework and GUI patterns)
- **Current Status**: Active development, v0.2.3. Core pipeline (CLI + 5 steps), config/path/batch-registry infrastructure, and a PyQt6 GUI (4-tab `MainWindow` mirroring HPM's layout) are implemented. Several HPM-proven GUI/infrastructure components have not yet been ported — see [GUI Architecture](#gui-architecture-from-hpm) and [Next Steps](#next-steps).

## Relationship to HPM (Predecessor Framework)

HPM (`Photos/Version-2/Framework`) already solved the general problem HAM faces: *ingest a metadata spreadsheet, walk a numbered pipeline of validation/transform/embed steps against a batch of source files, track multi-batch progress, and expose it all through both a CLI and a PyQt6 GUI.* It is delivered to the customer and has a 296-test regression suite (`Photos/Version-2/Framework/tests/`) and a `docs/SOFTWARE_ARCHITECTURE.md` documenting its component design and design patterns (Singleton, Template Method, Observer/Signals-Slots, Context Object, Strategy).

HAM reuses HPM's design **directly**, adapted to audio/MP3 instead of photo/TIFF:

| HPM Component (proven)                         | HAM Equivalent                              | Status                                                             |
| ------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------- |
| `steps/base_step.py` — `StepProcessor` (ABC, Template Method), `ProcessingContext`, `StepResult` | `steps/base_step.py`                         | Ported — same Template Method (`validate_inputs` → `execute` → `validate_outputs`) |
| `core/pipeline.py` — `Pipeline` orchestrator      | `core/pipeline.py`                           | Ported                                                               |
| `config/config_manager.py` — dot-notation YAML config | `config/config_manager.py`                   | Ported                                                               |
| `utils/path_manager.py` — `PathManager`           | `utils/path_manager.py`                      | Ported                                                               |
| `utils/batch_registry.py` — `BatchRegistry`, batch lifecycle (active/completed/archived) | `utils/batch_registry.py`                    | Ported                                                               |
| `utils/validator.py` — `Validator`, `ValidationResult` (Strategy pattern) | `utils/validator.py`                         | Ported                                                               |
| `utils/file_utils.py`                             | `utils/file_utils.py`                        | Ported                                                               |
| `gui/main_window.py` — 4-tab `QMainWindow` (Batches / Current Batch / Configuration / Logs) | `gui/main_window.py`                         | Ported — same tab structure, all four tabs now backed by real widgets |
| `gui/widgets/step_widget.py`, `batch_list_widget.py`, `log_widget.py` | `gui/widgets/` (same filenames + `batch_info_panel.py`) | Ported                                                               |
| `gui/dialogs/new_batch_dialog.py`, `batch_info_dialog.py` | `gui/dialogs/` (same filenames)              | Ported                                                               |
| `gui/zoom_manager.py` — `ZoomManager` Singleton (font-scale, `QSettings`) | `gui/zoom_manager.py`                        | Ported — explicitly mirrors HPM's implementation                     |
| `gui/theme_manager.py` — `ThemeManager` Singleton | `gui/theme.py` (thin wrapper)                | **Adapted, not duplicated** — HPM's theme system was extracted into the standalone `~/Projects/ThemeManager` package; HAM consumes that shared package instead of re-implementing it in-repo |
| (n/a in HPM directly — single-instance guard was factored out separately) | `gui/single_instance.py`                     | Uses the shared `single-instance-guard` package (`github.com/juren53/single-instance-guard`); silent raise-existing-window UX preference is documented in [[feedback_single_instance_ux]] |
| `gui/widgets/config_widget.py` — `ConfigWidget`   | `gui/widgets/config_widget.py`               | **Ported** — read-only tree view of the current batch's `project_config.yaml` (HPM's version is view-only too, despite the docstring; a `config_changed` signal was declared in HPM but never emitted anywhere, so it wasn't ported) |
| `gui/dialogs/settings_dialog.py` — `SettingsDialog` | *(none yet)*                                 | **Not ported**                                                       |
| `gui/dialogs/log_viewer_dialog.py`                | *(none yet)*                                 | **Not ported**                                                       |
| `utils/log_manager.py` — `LogManager` Singleton (session + per-batch + GUI-signal logging, verbosity control) | `utils/log_manager.py` — `LogManager` Singleton | **Ported** — session logging to `~/.hstl_audio_framework/logs/` (mirrors HPM's `~/.hstl_photo_framework/logs/`), a consolidated per-batch `batch_<id>.log` created on batch selection, and a singleton GUI handler now owned by `LogManager` instead of created ad hoc in `main_window.py`. Adapted rather than copied 1:1: reuses HAM's existing `QtLogHandler` (`(message, level)` signal, matching `LogWidget.append()`) instead of porting HPM's richer `LogRecord`/`GUILogHandler` dataclass — that belongs with a future `LogViewerDialog` port. Per-step-run log files (`step{N}_<timestamp>.log`, unchanged since v0.2.3) now additionally feed the batch's consolidated log via `LogManager.get_batch_handler()`. |
| `step_widget.py` step execution on a `QThread` (keeps GUI responsive) | `gui/workers.py` — `StepRunner(QThread)`, used by `gui/widgets/step_widget.py._run_step()` | **Ported** — steps run on a background thread; `finished`/`error` signals drive `_on_step_finished`/`_on_step_error`; controls are disabled while a step runs (steps share the batch's `tmp/` working files) and "Run All" chains steps via the same signals instead of a blocking loop |
| `tests/` — `unit/`, `integration/`, `gui/`, `conftest.py` fixtures | *(none yet)*                                 | **Not ported** — no `tests/` directory in HAM yet                    |
| `utils/github_version_checker.py`, `git_updater.py` | *(none yet)*                                 | Not ported; lower priority — evaluate need before porting            |
| `core/delivery_service.py`                        | *(none yet — no HAM equivalent workflow yet)* | Evaluate once Step 5 delivery/output requirements are finalized      |

**Working rule for HAM development**: before designing a new piece of framework or GUI infrastructure, check whether HPM already has a working, delivered version of it (`Photos/Version-2/Framework/`). Port and adapt rather than redesign. Where HPM later factored a component into a standalone shared package (ThemeManager, single-instance-guard, Icon_Manager_Module), prefer consuming the shared package over re-vendoring the code, as HAM already does for theming, single-instance behavior, and icon loading.

## Project Structure (Current)

```
C:\Users\juren\Projects\HST-Metadata\Audio\
├── hstl_audio.py                  # CLI entry point
├── ham_gui.py                     # GUI launcher entry point
├── config/
│   ├── __init__.py
│   ├── config_manager.py          # Configuration management (dot-notation YAML)
│   ├── settings.py                # Default settings
│   ├── batch_registry.yaml        # Central batch registry (runtime data)
│   └── project_config.yaml        # Example/default project config
├── steps/
│   ├── __init__.py
│   ├── base_step.py               # StepProcessor (ABC), ProcessingContext, StepResult
│   ├── step1_csv_prep.py          # CSV metadata preparation & validation
│   ├── step2_csv_validation.py    # Date conversion & field validation
│   ├── step3_metadata_embed.py    # Mutagen metadata tag embedding
│   ├── step4_thumbnail_embed.py   # Thumbnail creation & embedding
│   └── step5_validation.py        # Output validation & reporting
├── utils/
│   ├── __init__.py
│   ├── logger.py                  # Logging utilities
│   ├── qt_log_handler.py          # QtLogHandler — bridges logging records to Qt signals (GUI)
│   ├── log_manager.py             # LogManager Singleton — session/batch/GUI logging (mirrors HPM)
│   ├── validator.py               # Validation utilities
│   ├── file_utils.py              # File operation utilities
│   ├── path_manager.py            # Path management utilities
│   └── batch_registry.py          # Multi-batch registry management
├── core/
│   ├── __init__.py
│   └── pipeline.py                # Pipeline orchestration system
├── gui/                            # PyQt6 GUI
│   ├── __init__.py
│   ├── main_window.py             # MainWindow — 4-tab layout (mirrors HPM)
│   ├── theme.py                   # Thin wrapper around the shared ThemeManager package
│   ├── zoom_manager.py            # ZoomManager Singleton (mirrors HPM)
│   ├── single_instance.py         # SingleInstanceGuard (shared single-instance-guard package)
│   ├── workers.py                 # StepRunner(QThread) — background step execution (mirrors HPM)
│   ├── resources/icons/           # App icons
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── batch_list_widget.py
│   │   ├── batch_info_panel.py
│   │   ├── step_widget.py
│   │   ├── config_widget.py        # Read-only config tree view (mirrors HPM)
│   │   └── log_widget.py
│   └── dialogs/
│       ├── __init__.py
│       ├── new_batch_dialog.py
│       └── batch_info_dialog.py
├── assets/
│   └── HST-thumbnail-c.png        # Base thumbnail image
├── tests/                         # (planned — not yet present; see HPM's tests/ for the target shape)
├── requirements.txt                # Python dependencies
├── run.ps1                         # venv bootstrap + launcher (GUI)
├── HAM.spec                        # PyInstaller build spec
├── version_info.txt                # Windows executable version resource
├── docs/HSTL_Audio_Framework-Development_Plan.md  # This file
├── CHANGELOG.md
└── README.md                       # Usage documentation
```

## Architecture & Best Practices

### Core Architecture Patterns

These patterns are adopted directly from HPM's `docs/SOFTWARE_ARCHITECTURE.md` §8 (Design Patterns), applied to the audio domain.

#### Plugin/Extension Architecture

- **Modular Design**: Each step (1-5) is a separate, self-contained module
- **Common Interface**: All step implementations inherit from a base `StepProcessor` class
- **Extensibility**: Easy to add, remove, or replace individual steps without affecting others
- **Isolation**: Each step operates independently with clear input/output contracts

#### Pipeline/Workflow Pattern (Template Method)

- **Data Flow**: Model the 5-step process as a pipeline where data flows through stages
- **Template Method**: `StepProcessor.run()` orchestrates `validate_inputs()` → `execute()` → `validate_outputs()` for every step, identically to HPM's `steps/base_step.py`
- **Stage Validation**: Each stage validates its inputs before execution
- **Checkpoints**: Validation points between stages
- **State Tracking**: Maintain processing state throughout the pipeline

#### Configuration-Driven Design

- **External Configuration**: Store all settings in YAML config files
- **Path Management**: Keep data directory paths separate from code
- **Step Parameters**: Configurable validation rules and processing parameters
- **Environment Flexibility**: Easy deployment across different environments

#### Multi-Batch Registry Pattern

- **Centralized Tracking**: Single registry tracks all batch projects across the framework
- **Batch Isolation**: Each batch has independent configuration and data directories
- **Progress Visibility**: View status and progress of all batches from any location
- **Automatic Registration**: Batches auto-register on creation, no manual tracking needed
- **Status Management**: Track batch lifecycle (active, completed, archived) — same three states as HPM

### Key Technical Practices

#### State Management

- **Progress Tracking**: Track completion status of each step for each audio collection batch
- **Resume Capability**: Store processing state to resume interrupted workflows
- **History Logging**: Maintain detailed logs of processing history, timestamps, and errors
- **Rollback Support**: Ability to revert to previous states when needed

#### Path Management System

```python
class PathManager:
    - framework_root: Framework installation directory
    - input_mp3_dir: Source MP3 file directory
    - output_mp3_dir: Processed MP3 output directory
    - working_dir: Temporary processing directory (tmp/)
    - logs_dir: Log file storage location
    - config_dir: Configuration file directory
    - reports_dir: Validation and summary reports
    - assets_dir: Thumbnail and other shared assets
```

#### Batch Registry System

```python
class BatchRegistry:
    """Centralized registry for tracking multiple batch projects"""
    - registry_path: Path to central batch_registry.yaml
    - batches: Dictionary of all registered batches

    # Core Operations
    def register_batch(name, data_dir, config_path) -> bool
    def unregister_batch(batch_id) -> bool
    def get_batch_summary(batch_id) -> Dict  # Includes step completion status
    def list_batches_summary() -> List[Dict]  # All batches with progress

    # Query Operations
    def get_active_batches() -> Dict
    def find_batch_by_name(name) -> Tuple[batch_id, info]
    def find_batch_by_config(config_path) -> Tuple[batch_id, info]

    # Lifecycle Management
    def update_batch_status(batch_id, status) -> bool  # status: active/completed/archived
    def update_last_accessed(batch_id) -> bool
```

**Batch Status Values:**
- `active` - Currently being processed (default)
- `completed` - All processing finished
- `archived` - Long-term storage

**Registry Storage**: `config/batch_registry.yaml`
- Persists across framework sessions
- Stores batch metadata (name, paths, creation time, status)
- Automatically updated on batch operations

#### Context Object Pattern

- **Pipeline Context**: Pass a context object through all processing stages
- **Shared Resources**: Contains paths, configuration, and shared utilities
- **Error Handling**: Centralized error collection and reporting
- **Progress Reporting**: Real-time status updates throughout the pipeline

#### Validation & Error Handling

- **Pre-flight Checks**: Validate inputs and environment before each step
- **Clear Error Messages**: Actionable guidance for error resolution
- **Summary Reports**: Detailed reports after each step completion
- **Dry-run Mode**: Validation without making changes (--dry-run flag)
- **Graceful Degradation**: Continue processing when non-critical errors occur
- **Dependency Check**: Verify mutagen package is installed (Step 3); verify Pillow package is installed before Step 4 (thumbnail generation)

#### Quality Assurance

- **File Count Validation**: Ensure expected number of files at each stage
- **Metadata Verification**: Validate embedded metadata against source CSV data
- **Tag Verification**: Read back embedded tags after writing to confirm accuracy
- **Automated Testing**: Unit tests for each step module (HPM's `tests/unit/`, `tests/integration/`, `tests/gui/` split is the target shape — see [Relationship to HPM](#relationship-to-hpm-predecessor-framework))
- **Integration Testing**: End-to-end workflow validation

## GUI Architecture (from HPM)

HAM's GUI is a direct port of HPM's PyQt6 GUI structure, not a fresh design:

- **`MainWindow`** — `QMainWindow` with a `QTabWidget` holding four tabs, same order as HPM: **Batches**, **Current Batch**, **Configuration**, **Logs**.
- **Widgets** (`gui/widgets/`) — one reusable widget per tab concern (`batch_list_widget.py`, `step_widget.py`, `log_widget.py`), same split as HPM's `gui/widgets/`.
- **Dialogs** (`gui/dialogs/`) — modal dialogs for batch creation/inspection (`new_batch_dialog.py`, `batch_info_dialog.py`), same pattern as HPM's `gui/dialogs/`. HPM additionally has one dialog per step (`step1_dialog.py`…`step8_dialog.py`); HAM does not yet use per-step dialogs — evaluate whether Step 1-5 parameter configuration needs this pattern as the GUI matures.
- **Singleton managers** — `ZoomManager` (ported directly) and theming (consumed via the shared `ThemeManager` package) follow HPM's Singleton pattern for app-wide, cross-widget state (`instance()` classmethod, `QSettings`-backed persistence, `pyqtSignal` change notifications).
- **Observer pattern (Signals/Slots)** — widgets emit signals (e.g. `step_executed`, `batch_selected`) that `MainWindow` and sibling widgets subscribe to, decoupling GUI components exactly as HPM's SAD §8.3 describes.
- **Gaps vs. HPM** (see table above for detail): no `SettingsDialog`/`LogViewerDialog` yet. Step execution is ported to a `QThread` worker (`gui/workers.py`), logging is consolidated in a `LogManager` singleton (`utils/log_manager.py`), and the Configuration tab is a real `ConfigWidget` (`gui/widgets/config_widget.py`) instead of a placeholder.

## Process Steps Overview

| Step | Process                                        | Validation Required                                                                                      |
| ---- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 1    | Prepare metadata file                           | Confirm required columns exist: title, Accession Number, Date, Restrictions, Description, Place, Speakers, Production and Copyright |
| 2    | Validate & clean metadata to create CSV data    | Date format conversion (DD-MMM-YY → ISO 8601), field completeness check, unicode/encoding issues         |
| 3    | Embed metadata tags into MP3 files              | Mutagen write success, MP3 count matches CSV row count, spot-check tags with external tool                 |
| 4    | Create & embed custom album art                 | Thumbnail generation success, final MP3 count matches input count                                          |
| 5    | Output validation & reporting                   | Tag readback verification, file size sanity checks, summary report                                         |

## Existing Code to Integrate

### Available in root directory:

- **Steps 2-4**: `audio-tags-12d.py` (v0.12d) - Proven prototype combining date conversion, metadata embedding, and thumbnail embedding
  - Date parsing logic (DD-MMM-YY → ISO 8601)
  - ID3 tag field mappings (TIT2, TALB, TPE1, COMM, TCOP, TLOC, TRDA, TCON, etc.) — see table below
  - Thumbnail overlay generation using FFmpeg `drawtext` filter (accession number on base PNG) — **replaced by Pillow in the framework**
  - Two-pass FFmpeg approach for Step 4 (prototype only): pass 1 generates custom thumbnail JPEG, pass 2 embeds it into MP3
  - **Note**: Step 3 metadata embedding will be reimplemented using Mutagen in the framework (replacing FFmpeg for tag writing)
  - **Note**: Step 4 thumbnail generation will be reimplemented using Pillow in the framework (replacing FFmpeg entirely; single-pass, no subprocess)

- **Step 1 utility**: `match-audio-files.py` - Matches MP3 files in working directory against accession numbers from CSV; reports counts and unmatched files. Useful as a pre-flight check before Step 3.

### Key Reference Files:

- `LIST_HSTL-Audio-Files.csv` - Master list of 3,757 audio files (full production dataset)
- `audio.csv` - Full metadata export (127 KB)
- `short.csv` - 8-record test subset
- `two.csv` - 2-record minimal test set

## Development Phases

### Phase 1: Core Framework & CLI — Complete

1. **Framework Architecture** — done
   - CLI entry point (`hstl_audio.py`) with argparse
   - Configuration management system (`config/config_manager.py`)
   - Data directory management (`utils/path_manager.py`)
   - Logging system (`utils/logger.py`, `utils/qt_log_handler.py`)
   - Multi-batch registry system (`utils/batch_registry.py`)

2. **Step Integration** — all five steps implemented in `steps/`

3. **Validation & Quality Assurance** — Mutagen/Pillow pre-flight checks, tag readback verification in place per step

### Phase 2: GUI Implementation — In Progress (v0.2.3)

The GUI is no longer a future phase — a PyQt6 `MainWindow` with the four HPM-pattern tabs is implemented and in active use. Remaining work, in priority order, ports specific HPM components rather than designing new ones:

1. ~~**Background step execution**~~ — done: `gui/workers.py` (`StepRunner`) runs steps on a `QThread`, ported from HPM's `MetadataEmbeddingThread` pattern (`gui/dialogs/step5_dialog.py`)
2. ~~**`LogManager` singleton**~~ — done: `utils/log_manager.py`, ported from HPM's `utils/log_manager.py`; session logging, per-batch consolidated log files, and a singleton GUI handler now live in `LogManager` instead of ad hoc `main_window.py` wiring
3. ~~**Configuration tab**~~ — done: `gui/widgets/config_widget.py`, ported from HPM's `gui/widgets/config_widget.py`
4. **`SettingsDialog`** — port HPM's `gui/dialogs/settings_dialog.py` for app-level settings (theme, zoom, logging verbosity).
5. **`LogViewerDialog`** — port HPM's `gui/dialogs/log_viewer_dialog.py` for browsing historical batch logs.
6. **Per-step dialogs (evaluate)** — decide whether Step 1-5 parameter configuration warrants HPM's per-step-dialog pattern (`step1_dialog.py`…`step8_dialog.py`) or is adequately served by the current step widget.

### Phase 3: Testing & Packaging (Next)

- Stand up a `tests/` directory mirroring HPM's `unit/` / `integration/` / `gui/` split and `conftest.py` fixture pattern
- Unit tests for each step module; integration tests using `two.csv` / `short.csv` / `audio.csv`
- GUI smoke tests for `MainWindow` tab flows
- `HAM.spec` (PyInstaller) build already exists — verify it stays in sync with HPM's `build_exe.ps1` / `HPM.spec` release process as the app grows

## Framework Implementation Architecture

### Core Classes Structure

```python
class StepProcessor(ABC):
    """Base class for all step implementations"""
    @abstractmethod
    def validate_inputs(self, context: ProcessingContext) -> ValidationResult
    @abstractmethod
    def execute(self, context: ProcessingContext) -> StepResult
    @abstractmethod
    def validate_outputs(self, context: ProcessingContext) -> ValidationResult

class ProcessingContext:
    """Shared context passed through the pipeline"""
    paths: PathManager
    config: ConfigManager
    logger: Logger
    state: StateManager
    current_step: int

class Pipeline:
    """Main pipeline orchestrator"""
    def __init__(self, steps: List[StepProcessor], context: ProcessingContext)
    def run(self, start_step: int = 1, end_step: int = 5) -> PipelineResult
    def validate_all(self) -> ValidationReport
    def resume_from_checkpoint(self) -> PipelineResult
```

### Step Implementation Pattern

```python
class Step3_MetadataEmbed(StepProcessor):
    """Metadata embedding step using Mutagen"""

    def validate_inputs(self, context):
        # Check MP3 files exist in input directory
        # Verify CSV file is present and parsed
        # Verify mutagen package is importable
        return ValidationResult()

    def execute(self, context):
        # Copy MP3 to tmp/ to preserve originals
        # Open each MP3 with mutagen.id3.ID3
        # Write all tag frames (TIT2, TALB, TRDA, etc.) per CSV row
        # Save file, generate processing report
        return StepResult()

    def validate_outputs(self, context):
        # Verify output MP3 count matches CSV row count
        # Read back tags with mutagen to confirm accuracy
        # Spot-check metadata on first/last file
        return ValidationResult()
```

## CLI Interface Design

### Core Commands

```bash
# Project Management
hstl_audio.py init --data-dir "C:\path\to\mp3s" --project-name "MyBatch"
hstl_audio.py config --list
hstl_audio.py config --set data_dir "C:\new\path"

# Multi-Batch Management
hstl_audio.py batches                  # List all active batches
hstl_audio.py batches --all            # List all batches (including archived)

# Batch Lifecycle Management
hstl_audio.py batch info <batch_id>              # Show detailed batch information
hstl_audio.py batch complete <batch_id>          # Mark batch as completed
hstl_audio.py batch archive <batch_id>           # Archive a batch
hstl_audio.py batch reactivate <batch_id>        # Reactivate archived/completed batch
hstl_audio.py batch remove <batch_id> --confirm  # Remove from registry (preserves files)

# Step Execution
hstl_audio.py run --step 1              # Run single step
hstl_audio.py run --steps 1-3           # Run range of steps
hstl_audio.py run --steps 2,4           # Run specific steps
hstl_audio.py run --all                 # Run all steps
hstl_audio.py run --from 3              # Run from step 3 onwards
hstl_audio.py run --continue            # Continue from last completed step

# Status and Validation
hstl_audio.py status                    # Show project status
hstl_audio.py status --verbose          # Detailed status
hstl_audio.py validate --step 3         # Validate specific step
hstl_audio.py validate --all            # Validate all completed steps

# Reporting
hstl_audio.py report --step 3           # Generate step report
hstl_audio.py report --summary          # Overall project summary
hstl_audio.py report --export csv       # Export report to CSV

# Pipeline Management
hstl_audio.py pipeline --dry-run        # Validate entire pipeline without execution
hstl_audio.py pipeline --resume         # Resume from last checkpoint
hstl_audio.py state --checkpoint         # Create manual checkpoint
hstl_audio.py state --history           # Show processing history

# Advanced Validation
hstl_audio.py validate --pre-flight     # Check all requirements before starting
hstl_audio.py validate --paths          # Validate all directory paths
hstl_audio.py validate --dependencies   # Check mutagen (Step 3) and Pillow (Step 4) package dependencies
```

> **Note**: `hstl_audio.py` (313 lines) implements the core of this surface today (`init`, `batches`, `run`, `status`, `validate --dependencies`). Treat the remaining subcommands above as the target CLI surface, not all as already implemented — verify against the current `argparse` wiring before documenting a command as available in user-facing docs.

### Configuration Options

```bash
# Step-specific configurations
hstl_audio.py config --step 4 --set thumbnail_font_size 32
hstl_audio.py config --step 4 --set thumbnail_font_color yellow
hstl_audio.py config --step 3 --set id3v2_version 3

# Global settings
hstl_audio.py config --set log_level DEBUG
```

## Data Directory Structure

```
Project Data Directory/ (Per Batch)
├── input/
│   ├── mp3/                   # Original MP3 files (source)
│   └── csv/                   # CSV metadata file
├── output/
│   ├── tmp/                   # Intermediate Mutagen output (Step 3); Pillow thumbnail staging (Step 4)
│   └── processed/             # Final tagged MP3 files (Step 4)
├── reports/                   # Step reports and summaries
├── logs/                      # Processing logs
└── config/                    # Project-specific configuration
    └── project_config.yaml    # Batch configuration file

Framework Directory/ (Shared)
├── assets/
│   └── HST-thumbnail-c.png    # Base thumbnail image
└── config/
    └── batch_registry.yaml    # Central registry of all batches
```

### Configuration File (project_config.yaml)

```yaml
project:
  name: "HSTL_Audio_Batch_2024"
  created: "2024-10-06T14:00:00Z"
  data_directory: "C:\\Data\\HSTL_Audio\\Batch_2024"

steps_completed:
  step1: false
  step2: true
  step3: true
  step4: false
  step5: false

step_configurations:
  step4:
    thumbnail_font_size: 32
    thumbnail_font_color: yellow
    thumbnail_base_image: "assets/HST-thumbnail-c.png"
  step3:
    id3v2_version: 3

validation:
  strict_mode: true
  auto_backup: true
```

## Audio Metadata Tag Field Mappings

The following metadata fields are embedded into each MP3 file using Mutagen. This table reflects the current mapping from ATW:

| ID3 Tag / Frame    | Description              | Source / Value                                                        | Mutagen Notes                          |
| ------------------ | ------------------------- | ----------------------------------------------------------------------- | ----------------------------------------- |
| TIT2               | Title                     | title (CSV)                                                             | Native frame                              |
| TIT1               | Grouping                  | (static) NARA-HST-SRC Sound Recordings Collection                       | Native frame                              |
| TIT3               | Subtitle/Description      | Description + Date (CSV)                                                | Native frame                              |
| COMM               | Comment                   | Description + Date (CSV)                                                | Native frame                              |
| TXXX:ISBJ          | Subject                   | Description + Date (CSV)                                                | No native ID3 frame; write as TXXX        |
| TALB               | Album / Accession No.     | Accession Number (CSV)                                                  | Native frame                              |
| TXXX:IPRD          | Product / Accession       | Accession Number (CSV)                                                  | No native ID3 frame; write as TXXX        |
| TPE1               | Artist                    | (static) Harry S. Truman Library                                        | Native frame                              |
| IPLS               | Involved People           | Speakers (CSV) — **known issue in prototype: hardcoded; fix in HAM**    | ID3v2.3 only; requires `v2_version=3`     |
| TCOP               | Copyright / Restrictions  | Restrictions (CSV)                                                      | Native frame                              |
| TPUB               | Publisher                 | Production and Copyright (CSV)                                          | Native frame                              |
| TSRC               | ISRC / Source             | (static) Harry S. Truman Library                                        | Native frame (prototype used key ISRC)    |
| TLOC               | Location                  | Place (CSV)                                                             | Non-standard; write as TXXX:TLOC          |
| ICRD               | Creation Date (raw)       | Date original string (CSV)                                              | Write as TXXX:ICRD (RIFF/INFO key)        |
| TDAT               | Date DDMM                 | Date converted to DDMM                                                  | ID3v2.3 only; requires `v2_version=3`     |
| TYER               | Year                      | Date converted year (YYYY)                                              | ID3v2.3 only; requires `v2_version=3`     |
| TORY               | Original Year             | Date converted year (YYYY)                                              | ID3v2.3 only; requires `v2_version=3`     |
| TRDA               | Recording Date            | Date ISO 8601 (YYYY-MM-DD)                                              | ID3v2.3 only; requires `v2_version=3`     |
| TOFN               | Original Filename         | Accession Number + .mp3                                                 | Native frame                              |
| TCON               | Genre                     | (static) speech                                                         | Native frame                              |
| WOAS               | Source URL                | (static) https://www.trumanlibrary.gov/library/sound-recordings-collection | Native frame                           |
| WXXX               | External URL              | (static) https://catalog.archives.gov/                                  | Native frame                              |
| TEXT               | Processing Note           | (static) script/tool version string                                     | Native frame                              |

> **Note:** Tags `dc:description`, `xmpDM:logComment`, `©cmt`, `©pub`, and `dc:publisher` from the ATW prototype are **not supported by Mutagen for MP3 files** (XMP and iTunes © tags are MP4-only in Mutagen). These were experimental additions in v0.12d and are excluded from the HAM framework tag set.

## Multi-Batch Workflow

### Use Case: Managing Multiple Concurrent Batches

The framework handles multiple batch projects simultaneously — useful when processing different series of sound recordings (e.g., SR59, SR60, SR65) in parallel or at different stages of completion.

### Workflow Example

```bash
# Initialize multiple batches
python hstl_audio.py init --data-dir "C:\Data\Audio_SR59" --project-name "SR59_Series"
python hstl_audio.py init --data-dir "C:\Data\Audio_SR60" --project-name "SR60_Series"

# View all batches at a glance
python hstl_audio.py batches
# Output shows:
# - Batch names and IDs
# - Progress: X/5 steps (percentage)
# - Status: active/completed/archived
# - Data directory locations

# Work on specific batch
python hstl_audio.py --config "C:\Data\Audio_SR59\config\project_config.yaml" run --step 3

# Check status of specific batch
python hstl_audio.py --config "C:\Data\Audio_SR59\config\project_config.yaml" status

# Return to overview
python hstl_audio.py batches
```

### Batch Lifecycle States

- **active**: Currently being processed (default state)
- **completed**: All 5 steps finished, ready for delivery
- **archived**: Long-term storage, not actively worked on

## Implementation Strategy

### Development Order

1. ~~**Core Framework Setup**~~ — Complete
   - Project structure, CLI, config management, logging, batch registry, path management

2. ~~**Step Modules**~~ — Complete
   - Steps 1-5 implemented, referencing `audio-tags-12d.py` for tag mappings and `match-audio-files.py` for Step 1 pre-flight matching

3. **GUI Port from HPM** (Current) — see [Phase 2](#phase-2-gui-implementation--in-progress-v023) above: `QThread` step execution, `LogManager`, `ConfigWidget`, `SettingsDialog`, `LogViewerDialog`

4. **Integration Testing**

   - Stand up `tests/` (unit/integration/gui) mirroring HPM's suite
   - End-to-end workflow with `two.csv` (2 records)
   - Expand to `short.csv` (8 records)
   - Full run with `audio.csv` (full dataset)
   - Error handling and recovery testing

5. **Documentation & Polish**

   - User documentation (consider mirroring HPM's `USER_GUIDE.md` / `GUI_QUICKSTART.md` / `GLOSSARY.md` split)
   - Developer documentation (consider an HAM `SOFTWARE_ARCHITECTURE.md` once the GUI port settles, mirroring HPM's)
   - Error message improvements
   - CLI help system enhancement

### Key Design Principles

- **Modularity**: Each step is independent and can be run separately
- **Configurability**: All settings can be customized per project
- **Multi-Batch Support**: Concurrent management of multiple audio batches with centralized tracking
- **Reliability**: Comprehensive validation and error handling
- **Transparency**: Detailed logging and reporting at each step
- **Extensibility**: Easy to add new steps or modify existing ones
- **Data Safety**: Non-destructive operations; originals never modified
- **Lifecycle Safety**: Batch status changes never delete files; manual deletion required
- **Pipeline Flow**: Sequential data processing with validation checkpoints
- **Context-Aware**: Centralized resource and state management throughout processing
- **Resume-able**: Ability to restart from any step without losing progress
- **Batch Isolation**: Each batch maintains independent configuration and data directories
- **Reuse Proven Design**: When HAM's problem shape matches HPM's, port HPM's already-delivered solution rather than designing a new one (see [Relationship to HPM](#relationship-to-hpm-predecessor-framework))

## Dependencies

- Python 3.8+
- **mutagen** — ID3 metadata tag reading/writing (Step 3)
- **Pillow** — album art thumbnail generation and text overlay (Step 4; replaces FFmpeg)
- PyYAML (configuration)
- colorama (CLI colors)
- tqdm (progress bars)
- pathlib (path handling)
- csv, datetime, io (standard library)
- PyQt6 (GUI)
- Shared HSTL packages consumed at runtime (same pattern as HPM): `ThemeManager` (`~/Projects/ThemeManager`), `single-instance-guard`, `Icon_Manager_Module`

## Testing Strategy

- Unit tests for date conversion logic (DD-MMM-YY → ISO 8601, edge cases)
- Unit tests for CSV field validation
- Integration tests using `two.csv` (2-record minimal dataset)
- Integration tests using `short.csv` (8-record subset)
- Full-scale test with `audio.csv`
- Mutagen tag-write validation (dry-run mode: build tag dict, verify keys/values without writing)
- Tag readback verification after embedding (re-read with mutagen.id3.ID3 and compare to CSV)
- Target shape: HPM's `tests/unit/`, `tests/integration/`, `tests/gui/`, `conftest.py` fixture split — HAM has no `tests/` directory yet (see Phase 3)

## Risk Mitigation

- **Mutagen Not Installed**: Pre-flight `import mutagen` check; fail with `pip install mutagen` instructions
- **ID3v2.3 Frame Loss**: Mutagen defaults to ID3v2.4; TDAT, TRDA, TORY, TYER, IPLS are silently dropped unless saved with `v2_version=3` — always pass this parameter in Step 3
- **Pillow Not Installed**: Pre-flight `import PIL` check before Step 4; fail with `pip install Pillow` instructions
- **CSV Format Changes**: Validate column names on load; fail fast with actionable error
- **Invalid Dates**: Validate all date strings before any tag embedding begins
- **MP3 File Missing**: Log missing files, skip with warning, continue batch
- **Data Loss Prevention**: Copy to tmp/ before writing tags; originals never modified in place
- **Performance**: Mutagen tag writes are fast (no audio re-encoding); progress bars for large batches (3,757 files)
- **GUI Unresponsiveness**: Mitigated — step execution runs on a background `QThread` (`gui/workers.py`, ported from HPM's `MetadataEmbeddingThread` pattern), so large batches no longer block the UI

---

## Next Steps

### Current Focus

1. ~~Port HPM's `QThread` step-execution pattern into `StepWidget._run_step()`~~ — done (`gui/workers.py`)
2. ~~Consolidate logging into a `LogManager` singleton~~ — done (`utils/log_manager.py`)
3. ~~Implement the Configuration tab (`ConfigWidget`)~~ — done (`gui/widgets/config_widget.py`)
4. Implement `SettingsDialog` (ported from HPM's `gui/dialogs/settings_dialog.py`)
5. Implement `LogViewerDialog` (ported from HPM's `gui/dialogs/log_viewer_dialog.py`) — will want `LogManager`'s GUI handler upgraded to HPM's `LogRecord`/`GUILogHandler` dataclass at that point, to support level/batch/step filtering

### Upcoming

1. Stand up `tests/` (`unit/`, `integration/`, `gui/`, `conftest.py`) mirroring HPM's test suite structure
2. Fix IPLS tag: map to Speakers CSV column (currently hardcoded in prototype)
3. Decide whether per-step dialogs (HPM's `step1_dialog.py`…`step8_dialog.py` pattern) are warranted for Steps 1-5
4. Evaluate `github_version_checker.py` / `git_updater.py` for update-check parity with HPM, once HAM has its own release cadence established
5. Complete documentation (consider an HAM `SOFTWARE_ARCHITECTURE.md` mirroring HPM's, once the GUI port from this plan settles)

## Notes

- `audio-tags-12d.py` (v0.12d) is the proven prototype for the audio-specific logic (dates, tag mappings) — extract logic into modules, don't rewrite
- `match-audio-files.py` is a useful pre-flight utility integrated into Step 1
- **HPM** (`Photos/Version-2/Framework`, delivered, in production) is the proven reference for everything *not* audio-specific — framework infrastructure, multi-batch registry, and GUI. Check it first before designing new HAM infrastructure; see [Relationship to HPM](#relationship-to-hpm-predecessor-framework)
- Shared, previously-extracted HSTL packages (`ThemeManager`, `single-instance-guard`, `Icon_Manager_Module`) are consumed directly by HAM rather than re-implemented — the same packages HPM's own GUI patterns were factored out into
- **Mutagen** handles all metadata tag writing (Step 3); no audio re-encoding, fast
- **Pillow** handles Step 4 thumbnail generation (overlays accession number on base PNG using `ImageDraw`/`ImageFont`); no FFmpeg dependency
- Step 4 is a single-pass pure-Python operation: Pillow generates JPEG in memory (`BytesIO`), Mutagen embeds it as `APIC` frame
- Use `two.csv` (2 records) for rapid iteration during development
- Full production dataset: 3,757 MP3 files in `LIST_HSTL-Audio-Files.csv`
- Windows PowerShell/bash environment
- Data directories separate from framework code location
- GUI-first in practice: `run.ps1` launches `ham_gui.py` directly; the CLI (`hstl_audio.py`) remains available for scripting/automation, following HPM's dual-interface approach

Updated: 2026-09-21 2330 CDT (Ported HPM's ConfigWidget — see `gui/widgets/config_widget.py` — the third item worked off the HPM component-mapping table below; earlier revisions ported the LogManager singleton and QThread step-execution pattern, and documented HAM's dependence on HPM's proven design patterns)
