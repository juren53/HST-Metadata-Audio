"""
Step 4 – Thumbnail Creation & Embedding (STUB)

Uses Pillow to overlay the accession number on HST-thumbnail-c.png,
generates a JPEG in memory (BytesIO), then uses Mutagen to embed it
as an APIC frame in each tagged MP3.

Single-pass, pure-Python – no FFmpeg dependency.
"""

# TODO: Implement thumbnail generation and embedding.
#       Reference: FFmpeg drawtext parameters in audio-tags-12d.py for positioning/font/colour.
#       Font: Arial Bold; default font size 24; font colour yellow; x=10 y=10.
#       Input:  output/tmp/  (Mutagen-tagged MP3s from Step 3)
#       Output: output/processed/  (final MP3s with album art embedded)

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult


class Step4_ThumbnailEmbed(StepProcessor):
    """Create accession-number thumbnails and embed as album art (APIC)."""

    def __init__(self):
        super().__init__(4, "Thumbnail Creation & Embedding")

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        try:
            import PIL  # noqa: F401
        except ImportError:
            result.add_error("Pillow is not installed. Run: pip install Pillow")
        try:
            import mutagen  # noqa: F401
        except ImportError:
            result.add_error("mutagen is not installed. Run: pip install mutagen")
        if not context.paths.working_dir.exists():
            result.add_error(f"output/tmp/ not found — run Step 3 first")
        if not context.paths.thumbnail_base.exists():
            result.add_error(f"Base thumbnail not found: {context.paths.thumbnail_base}")
        return result

    def execute(self, context: ProcessingContext) -> StepResult:
        # TODO: implement
        #   For each MP3 in output/tmp/:
        #     1. Open HST-thumbnail-c.png with Pillow
        #     2. Draw accession number text with ImageDraw/ImageFont (Arial Bold, yellow, x=10 y=10)
        #     3. Save to BytesIO as JPEG
        #     4. Open MP3 with mutagen ID3; add APIC frame with BytesIO data
        #     5. Save to output/processed/
        self.logger.warning("Step 4 is a stub – not yet implemented.")
        return StepResult(False, "Step 4 not yet implemented")

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        # TODO: verify output/processed/ count matches input count
        return ValidationResult()
