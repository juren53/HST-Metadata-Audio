"""
Step 5 – Output Validation & Reporting (STUB)

Reads back tags from all files in output/processed/ and verifies them
against the source CSV data. Generates a summary report in reports/.
"""

# TODO: Implement tag-readback verification and report generation.
#       1. For each MP3 in output/processed/, open with mutagen.id3.ID3
#       2. Compare key fields (TIT2, TALB, TRDA) against csv_records
#       3. Check file sizes are reasonable (not zero, not suspiciously large)
#       4. Write summary report to reports/step5_report_<timestamp>.txt
#       5. Print pass/fail summary to console

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult


class Step5_Validation(StepProcessor):
    """Output validation and summary reporting."""

    def __init__(self):
        super().__init__(5, "Output Validation & Reporting")

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        if not context.paths.processed_dir.exists():
            result.add_error("output/processed/ not found — run Step 4 first")
        return result

    def execute(self, context: ProcessingContext) -> StepResult:
        # TODO: implement full validation and reporting
        self.logger.warning("Step 5 is a stub – not yet implemented.")
        return StepResult(False, "Step 5 not yet implemented")

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        return ValidationResult()
