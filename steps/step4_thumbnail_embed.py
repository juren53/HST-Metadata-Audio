"""
Step 4 – Album Art Embedding

For each tagged MP3 in output/tmp/ (Step 3 output):
  1. Open assets/HST-thumbnail-c.png with Pillow
  2. Draw the accession number in Arial Bold 32 / yellow / x=10,y=10
     with a semi-transparent black background box for legibility
  3. Encode the result as JPEG (BytesIO, quality=90)
  4. Open the MP3 with Mutagen ID3; add / replace APIC front-cover frame
  5. Save to output/processed/ as ID3v2.3

No FFmpeg required — pure Pillow + Mutagen.
"""

from io import BytesIO
from pathlib import Path

from steps.base_step import StepProcessor, ProcessingContext, StepResult
from utils.validator import ValidationResult


# ── font search order (Windows paths first, then generic names) ───────────────
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",   # Arial Bold — Windows
    r"C:\Windows\Fonts\arial.ttf",     # Arial Regular — Windows fallback
    "/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf",  # Linux with MS fonts
    "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
    "arialbd.ttf",                     # cwd or PATH
    "arial.ttf",
]

_FONT_SIZE  = 32
_TEXT_COLOR = "yellow"
_BOX_COLOR  = (0, 0, 0, 128)   # semi-transparent black
_TEXT_X     = 10
_TEXT_Y     = 10


def _load_font(size: int):
    from PIL import ImageFont
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _make_thumbnail(base_image_path: Path, accession_number: str) -> bytes:
    """Overlay accession number on base thumbnail; return JPEG bytes."""
    from PIL import Image, ImageDraw

    img = Image.open(base_image_path).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    font = _load_font(_FONT_SIZE)

    # Measure text bounding box for background rectangle
    bbox = draw.textbbox((_TEXT_X, _TEXT_Y), accession_number, font=font)
    pad = 3
    box_rect = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
    draw.rectangle(box_rect, fill=_BOX_COLOR)
    draw.text((_TEXT_X, _TEXT_Y), accession_number, fill=_TEXT_COLOR, font=font)

    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class Step4_ThumbnailEmbed(StepProcessor):
    """Embed accession-number album art into each tagged MP3."""

    def __init__(self):
        super().__init__(4, "Album Art Embedding")

    # ── validate_inputs ───────────────────────────────────────────────────

    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        try:
            import PIL  # noqa: F401
        except ImportError:
            result.add_error("Pillow is not installed — run: pip install Pillow")
        try:
            import mutagen  # noqa: F401
        except ImportError:
            result.add_error("mutagen is not installed — run: pip install mutagen")
        if not context.paths.working_dir.exists():
            result.add_error("output/tmp/ not found — run Step 3 first")
        elif not any(context.paths.working_dir.glob("*.mp3")):
            result.add_error("No MP3 files in output/tmp/ — run Step 3 first")
        if not context.paths.thumbnail_base.exists():
            result.add_error(
                f"Base album art not found: {context.paths.thumbnail_base}\n"
                f"Place HST-blank-album-art.jpg in the assets/ directory."
            )
        return result

    # ── execute ───────────────────────────────────────────────────────────

    def execute(self, context: ProcessingContext) -> StepResult:
        from mutagen.id3 import ID3, ID3NoHeaderError, APIC
        from mutagen.id3._util import ID3NoHeaderError  # noqa: F811

        processed_dir = context.paths.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)

        thumbnail_base = context.paths.thumbnail_base
        mp3_files = sorted(context.paths.working_dir.glob("*.mp3"))

        ok, failed = [], []

        for src in mp3_files:
            an = src.stem
            dst = processed_dir / src.name

            try:
                jpeg_bytes = _make_thumbnail(thumbnail_base, an)
            except Exception as e:
                self.logger.error(f"Thumbnail generation failed for {an}: {e}")
                failed.append(src.name)
                continue

            try:
                try:
                    tags = ID3(str(src))
                except ID3NoHeaderError:
                    tags = ID3()

                tags.delall("APIC")
                tags["APIC"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,       # front cover
                    desc="Cover",
                    data=jpeg_bytes,
                )
                tags.save(str(dst), v2_version=3)
                ok.append(dst)
                self.logger.info(f"Album art embedded: {an}")

            except Exception as e:
                self.logger.error(f"APIC embed failed for {an}: {e}")
                failed.append(src.name)

        msg = f"Embedded album art in {len(ok)} files; failed {len(failed)}"
        self.logger.info(msg)
        context.set_data("processed_mp3s", ok)

        if not ok:
            return StepResult(False, msg)
        return StepResult(True, msg, files_processed=ok)

    # ── validate_outputs ──────────────────────────────────────────────────

    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        result = ValidationResult()
        processed = context.get_data("processed_mp3s") or []
        if not processed:
            result.add_error("No files written to output/processed/")
        else:
            missing_apic = []
            for path in processed:
                try:
                    from mutagen.id3 import ID3
                    tags = ID3(str(path))
                    if "APIC:" not in tags and not any(k.startswith("APIC") for k in tags):
                        missing_apic.append(path.name)
                except Exception:
                    missing_apic.append(path.name)
            if missing_apic:
                result.add_warning(
                    f"APIC frame missing in {len(missing_apic)} file(s): "
                    + ", ".join(missing_apic[:5])
                )
        return result
