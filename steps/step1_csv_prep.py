"""
Step 1 – CSV Preparation & Validation (STUB)

Checks that:
  - A CSV file exists in input/csv/
  - MP3 files exist in input/mp3/
  - MP3 filenames match accession numbers found in the CSV
  - All required columns are present

Incorporates logic from match-audio-files.py.
"""

# TODO: Implement full CSV preparation and MP3/accession-number matching.
#       Reference: match-audio-files.py for file-matching logic.
#       Required columns are defined in config/settings.py (REQUIRED_CSV_COLUMNS).

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult
from config.settings import REQUIRED_CSV_COLUMNS


class Step1_CSVPrep(StepProcessor):
    """CSV metadata preparation & validation."""

    def __init__(self):
        super().__init__(1, "CSV Preparation & Validation")

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        if not context.paths.input_csv_dir.exists():
            result.add_error(f"input/csv/ directory not found: {context.paths.input_csv_dir}")
        if not context.paths.input_mp3_dir.exists():
            result.add_error(f"input/mp3/ directory not found: {context.paths.input_mp3_dir}")
        return result

    def execute(self, context: ProcessingContext) -> StepResult:
        # TODO: implement full logic
        #   1. Find CSV file in input/csv/
        #   2. Parse column headers; verify REQUIRED_CSV_COLUMNS all present
        #   3. Load accession numbers from CSV
        #   4. Match against MP3 filenames in input/mp3/
        #   5. Report unmatched files (CSV rows with no MP3, MP3 files with no CSV row)
        #   6. Store parsed DataFrame in context.shared_data["csv_data"]
        self.logger.warning("Step 1 is a stub – not yet implemented.")
        return StepResult(False, "Step 1 not yet implemented")

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        # TODO: verify csv_data is in context.shared_data
        return ValidationResult()
