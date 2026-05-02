# HSTL Audio Framework - Development Plan

## Project Overview

The HSTL Audio Framework is an application that orchestrates all components of the HSTL Audio Metadata Project. It manages the complete process from CSV metadata preparation through final tagged MP3 creation, embedding ID3 metadata and custom thumbnails into the Harry S. Truman Library sound recordings collection.

## Repository Information

- **GitHub Repository**: https://github.com/juren53/HST-Metadata
- **Branch**: `master` (main branch)
- **Local Repository**: `C:\Users\juren\Projects\HST-Metadata`
- **Audio Project Path**: `Audio/`
- **Current Status**: Active testing and development (script version 0.12d; Mutagen adopted for metadata embedding)

## Project Structure (Proposed Framework)

```
C:\Users\juren\Projects\HST-Metadata\Audio\
├── hstl_audio.py                  # Main CLI entry point
├── config/
│   ├── __init__.py
│   ├── config_manager.py          # Configuration management
│   └── settings.py                # Default settings
├── steps/
│   ├── __init__.py
│   ├── base_step.py               # Base class for all steps
│   ├── step1_csv_prep.py          # CSV metadata preparation & validation
│   ├── step2_csv_validation.py    # Date conversion & field validation
│   ├── step3_metadata_embed.py    # Mutagen metadata tag embedding
│   ├── step4_thumbnail_embed.py   # Thumbnail creation & embedding
│   └── step5_validation.py        # Output validation & reporting
├── utils/
│   ├── __init__.py
│   ├── logger.py                  # Logging utilities
│   ├── validator.py               # Validation utilities
│   ├── file_utils.py              # File operation utilities
│   ├── path_manager.py            # Path management utilities
│   └── batch_registry.py         # Multi-batch registry management
├── core/
│   ├── __init__.py
│   └── pipeline.py                # Pipeline orchestration system
├── gui/                           # Future PyQt6 GUI (Phase 2)
│   └── __init__.py
├── assets/
│   └── HST-thumbnail-c.png        # Base thumbnail image
├── requirements.txt               # Python dependencies
├── docs/DEVELOPMENT_PLAN.md       # This file
└── README.md                      # Usage documentation
```

## Architecture & Best Practices

### Core Architecture Patterns

#### Plugin/Extension Architecture

- **Modular Design**: Each step (1-5) is a separate, self-contained module
- **Common Interface**: All step implementations inherit from a base `StepProcessor` class
- **Extensibility**: Easy to add, remove, or replace individual steps without affecting others
- **Isolation**: Each step operates independently with clear input/output contracts

#### Pipeline/Workflow Pattern

- **Data Flow**: Model the 5-step process as a pipeline where data flows through stages
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
- **Status Management**: Track batch lifecycle (active, completed, archived)

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
- **Dependency Check**: Verify mutagen package is installed (Step 3); verify FFmpeg is installed and accessible before Step 4 (thumbnail generation)

#### Quality Assurance

- **File Count Validation**: Ensure expected number of files at each stage
- **Metadata Verification**: Validate embedded metadata against source CSV data
- **Tag Verification**: Read back embedded tags after writing to confirm accuracy
- **Automated Testing**: Unit tests for each step module
- **Integration Testing**: End-to-end workflow validation

## Process Steps Overview

| Step | Process                                        | Validation Required                                                                                      |
| ---- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 1    | Prepare CSV metadata file                      | Confirm required columns exist: title, Accession Number, Date, Restrictions, Description, Place, Speakers, Production and Copyright |
| 2    | Validate & clean CSV data                      | Date format conversion (DD-MMM-YY → ISO 8601), field completeness check, unicode/encoding issues         |
| 3    | Embed metadata tags into MP3 files             | Mutagen write success, MP3 count matches CSV row count, spot-check tags with external tool               |
| 4    | Create & embed custom thumbnails               | Thumbnail generation success, final MP3 count matches input count                                        |
| 5    | Output validation & reporting                  | Tag readback verification, file size sanity checks, summary report                                       |

## Existing Code to Integrate

### Available in root directory:

- **Steps 2-4**: `audio-tags-12d.py` (v0.12d) - Proven prototype combining date conversion, metadata embedding, and thumbnail embedding
  - Date parsing logic (DD-MMM-YY → ISO 8601)
  - ID3 tag field mappings (TIT2, TALB, TPE1, COMM, TCOP, TLOC, TRDA, TCON, etc.) — see table below
  - Thumbnail overlay generation using FFmpeg `drawtext` filter (accession number on base PNG)
  - Two-pass FFmpeg approach for Step 4: pass 1 generates custom thumbnail JPEG, pass 2 embeds it into MP3
  - **Note**: Step 3 metadata embedding will be reimplemented using Mutagen in the framework (replacing FFmpeg for tag writing)

- **Step 1 utility**: `match-audio-files.py` - Matches MP3 files in working directory against accession numbers from CSV; reports counts and unmatched files. Useful as a pre-flight check before Step 3.

### Key Reference Files:

- `LIST_HSTL-Audio-Files.csv` - Master list of 3,757 audio files (full production dataset)
- `audio.csv` - Full metadata export (127 KB)
- `short.csv` - 8-record test subset
- `two.csv` - 2-record minimal test set

## Development Phases

### Phase 1: Core Framework & CLI (Current Priority)

1. **Framework Architecture**

   - Main CLI entry point with argparse
   - Configuration management system
   - Project initialization and tracking
   - Data directory management
   - Logging and reporting system
   - Multi-batch registry system

2. **Step Integration** (Priority Order)

   - Step 2: CSV validation & date conversion (extract from `audio-tags-12d.py`)
   - Step 3: Metadata embedding (reimplement using Mutagen; reference `audio-tags-12d.py` for tag mappings)
   - Step 4: Thumbnail creation & embedding (extract FFmpeg thumbnail logic from `audio-tags-12d.py`)
   - Step 1: CSV preparation & structural validation (incorporate `match-audio-files.py` logic; new implementation)
   - Step 5: Output validation & reporting (new implementation)

3. **Validation & Quality Assurance**

   - CSV field validation
   - Mutagen package availability check (Step 3)
   - FFmpeg dependency verification (Step 4 only)
   - Tag readback verification utilities
   - Summary report generation

### Phase 2: GUI Implementation (Future)

- PyQt6 interface development
- Visual progress tracking
- Interactive configuration
- Integrated file browser
- Real-time validation feedback

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
hstl_audio.py validate --dependencies   # Check mutagen package and FFmpeg (thumbnail) dependencies
```

### Configuration Options

```bash
# Step-specific configurations
hstl_audio.py config --step 4 --set thumbnail_font_size 32
hstl_audio.py config --step 4 --set thumbnail_font_color yellow
hstl_audio.py config --step 3 --set id3v2_version 3

# Global settings
hstl_audio.py config --set log_level DEBUG
hstl_audio.py config --set ffmpeg_path /usr/bin/ffmpeg    # used by Step 4 only
```

## Data Directory Structure

```
Project Data Directory/ (Per Batch)
├── input/
│   ├── mp3/                   # Original MP3 files (source)
│   └── csv/                   # CSV metadata file
├── output/
│   ├── tmp/                   # Intermediate Mutagen output (Step 3); FFmpeg thumbnail staging (Step 4)
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

| ID3 Tag        | Description              | Source / Value                                                        |
| -------------- | ------------------------ | --------------------------------------------------------------------- |
| TIT2           | Title                    | title (CSV)                                                           |
| TIT1           | Grouping                 | (static) NARA-HST-SRC Sound Recordings Collection                    |
| TIT3           | Subtitle/Description     | Description + Date (CSV)                                              |
| COMM           | Comment                  | Description + Date (CSV)                                              |
| ISBJ           | Subject                  | Description + Date (CSV)                                              |
| dc:description | XMP Description          | Description + Date (CSV)                                              |
| xmpDM:logComment | XMP Log Comment        | Description + Date (CSV)                                              |
| ©cmt           | iTunes Comment           | Description + Date (CSV)                                              |
| TALB           | Album / Accession No.    | Accession Number (CSV)                                                |
| IPRD           | Product / Accession      | Accession Number (CSV)                                                |
| TPE1           | Artist                   | (static) Harry S. Truman Library                                      |
| IPLS           | Involved People          | Speakers (CSV) — **known issue in prototype: hardcoded; fix in HAM**  |
| TCOP           | Copyright / Restrictions | Restrictions (CSV)                                                    |
| TPUB           | Publisher                | Production and Copyright (CSV)                                        |
| ©pub           | iTunes Publisher         | Production and Copyright (CSV)                                        |
| dc:publisher   | XMP Publisher            | Production and Copyright (CSV)                                        |
| ISRC           | Source                   | (static) Harry S. Truman Library                                      |
| TLOC           | Location                 | Place (CSV)                                                           |
| ICRD           | Creation Date (raw)      | Date original string (CSV)                                            |
| TDAT           | Date DDMM                | Date converted to DDMM                                                |
| TYER           | Year                     | Date converted year (YYYY)                                            |
| TORY           | Original Year            | Date converted year (YYYY)                                            |
| TRDA           | Recording Date           | Date ISO 8601 (YYYY-MM-DD)                                            |
| TOFN           | Original Filename        | Accession Number + .mp3                                               |
| TCON           | Genre                    | (static) speech                                                       |
| WOAS           | Source URL               | (static) https://www.trumanlibrary.gov/library/sound-recordings-collection |
| WXXX           | External URL             | (static) https://catalog.archives.gov/                                |
| TEXT           | Processing Note          | (static) script/tool version string                                   |

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

1. **Core Framework Setup** (Priority 1)

   - Project structure creation
   - Basic CLI interface (argparse with subcommands)
   - Configuration management (YAML-based with dot notation)
   - Logging system
   - Multi-batch registry system
   - Path management utilities

2. **Step Modules (Incremental)**

   - Step 2: CSV validation & date conversion (refactor from `audio-tags-12d.py`)
   - Step 3: Metadata embedding (implement with Mutagen; reference `audio-tags-12d.py` for tag mappings)
   - Step 4: Thumbnail creation & embedding (refactor FFmpeg thumbnail logic from `audio-tags-12d.py`)
   - Step 1: CSV preparation & structural validation (incorporate `match-audio-files.py` logic)
   - Step 5: Output validation & reporting (new)

3. **Integration Testing**

   - End-to-end workflow with `two.csv` (2 records)
   - Expand to `short.csv` (8 records)
   - Full run with `audio.csv` (full dataset)
   - Error handling and recovery testing

4. **Documentation & Polish**

   - User documentation
   - Developer documentation
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

## Dependencies

- Python 3.8+
- **mutagen** — ID3 metadata tag reading/writing (Step 3; replaces FFmpeg for tag embedding)
- **FFmpeg** (external, must be installed and on PATH) — thumbnail image generation only (Step 4)
- PyYAML (configuration)
- colorama (CLI colors)
- tqdm (progress bars)
- pathlib (path handling)
- csv, datetime, subprocess (standard library)
- PyQt6 (Phase 2 only)

## Testing Strategy

- Unit tests for date conversion logic (DD-MMM-YY → ISO 8601, edge cases)
- Unit tests for CSV field validation
- Integration tests using `two.csv` (2-record minimal dataset)
- Integration tests using `short.csv` (8-record subset)
- Full-scale test with `audio.csv`
- Mutagen tag-write validation (dry-run mode: build tag dict, verify keys/values without writing)
- Tag readback verification after embedding (re-read with mutagen.id3.ID3 and compare to CSV)

## Risk Mitigation

- **Mutagen Not Installed**: Pre-flight `import mutagen` check; fail with `pip install mutagen` instructions
- **FFmpeg Not Found**: Pre-flight check before Step 4 only; clear installation instructions
- **CSV Format Changes**: Validate column names on load; fail fast with actionable error
- **Invalid Dates**: Validate all date strings before any tag embedding begins
- **MP3 File Missing**: Log missing files, skip with warning, continue batch
- **Data Loss Prevention**: Copy to tmp/ before writing tags; originals never modified in place
- **Performance**: Mutagen tag writes are fast (no audio re-encoding); progress bars for large batches (3,757 files)

---

## Next Steps

### Current Focus

1. Create basic project structure
2. Implement core CLI framework
3. Add configuration management (YAML with dot notation)
4. Implement logging system
5. Build multi-batch registry system
6. Create path management utilities

### Upcoming

1. Refactor Step 2: CSV validation & date conversion from `audio-tags-12d.py`
2. Implement Step 3: Metadata embedding using Mutagen (tag mappings from `audio-tags-12d.py`)
3. Refactor Step 4: Thumbnail creation & embedding (FFmpeg drawtext logic from `audio-tags-12d.py`)
4. Implement Step 1: CSV preparation & structural validation (incorporating `match-audio-files.py`)
5. Implement Step 5: Output validation & reporting
6. Build pipeline orchestration
7. Add comprehensive error handling
8. Fix IPLS tag: map to Speakers CSV column (currently hardcoded in prototype)
9. Complete documentation

## Notes

- `audio-tags-12d.py` (v0.12d) is the proven prototype — extract logic into modules, don't rewrite
- `match-audio-files.py` is a useful pre-flight utility to integrate into Step 1
- **Mutagen** replaces FFmpeg for all metadata tag writing (Step 3); no audio re-encoding, fast
- FFmpeg is still required for Step 4 thumbnail generation (drawtext filter overlays accession number on base PNG)
- Step 4 remains a two-pass operation: pass 1 generates custom JPEG thumbnail, pass 2 embeds it into MP3
- Use `two.csv` (2 records) for rapid iteration during development
- Full production dataset: 3,757 MP3 files in `LIST_HSTL-Audio-Files.csv`
- Windows PowerShell/bash environment
- Data directories separate from framework code location
- CLI implementation first, GUI in Phase 2

Updated: 2026-05-02
