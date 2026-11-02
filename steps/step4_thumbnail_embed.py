"""
Step 4 – Album Art Embedding

For each tagged MP3 in output/tmp/ (Step 3 output):
  1. Open the batch's album art with Pillow — the image chosen in the
     GUI's Step 4 dialog (step_configurations.step4.thumbnail_base_image),
     shrunk to fit 300x300 if larger
  2. Draw the accession number in Arial Bold 32 / yellow / x=10,y=10
     with a semi-transparent black background box for legibility
  3. Encode the result as JPEG (BytesIO, quality=90)
  4. Copy the MP3 to output/processed/, then open the copy with Mutagen
     ID3 (translate=False, keeping the v2.3 date frames); add / replace
     the APIC front-cover frame
  5. Save as ID3v2.3 and check the output's audio length matches the
     source; a failed file is removed from output/processed/

No FFmpeg required — pure Pillow + Mutagen.
"""

import shutil
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
_MAX_SIZE   = 300              # album art is shrunk to fit this square


def _resolve_base_image(context: ProcessingContext) -> Path:
    """The batch's chosen album art. Relative config values name a bundled
    image under the app folder; if that image is missing (e.g. an older
    batch config's default), fall back to the blank HST template."""
    value = context.config.get("step_configurations.step4.thumbnail_base_image")
    if not value:
        return context.paths.thumbnail_base
    path = Path(value)
    if path.is_absolute():
        return path
    path = context.paths.framework_root / path
    return path if path.exists() else context.paths.thumbnail_base


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
    img.thumbnail((_MAX_SIZE, _MAX_SIZE))  # a large custom image would bloat every MP3
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
        base_image = _resolve_base_image(context)
        if not base_image.exists():
            result.add_error(
                f"Album art not found: {base_image}\n"
                f"Choose another image in the Step 4 dialog."
            )
        return result

    # ── execute ───────────────────────────────────────────────────────────

    def execute(self, context: ProcessingContext) -> StepResult:
        from mutagen.id3 import ID3, ID3NoHeaderError, APIC
        from mutagen.id3._util import ID3NoHeaderError  # noqa: F811

        processed_dir = context.paths.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)

        thumbnail_base = _resolve_base_image(context)
        self.logger.info(f"Album art: {thumbnail_base}")
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
                # Copy the whole MP3 first, then tag the copy: saving an ID3
                # object to a path that doesn't exist yet writes a tag-only
                # file with no audio.
                shutil.copy2(src, dst)
                try:
                    tags = ID3(str(dst), translate=False)  # translate=False keeps v2.3 date frames (TRDA/TDAT) as-is
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

                # Confirm the output still holds the audio, not just a tag
                from mutagen.mp3 import MP3
                out_len = MP3(str(dst)).info.length
                in_len = MP3(str(src)).info.length
                if abs(out_len - in_len) > 1:
                    raise ValueError(f"audio length {out_len:.0f}s, expected {in_len:.0f}s")

                ok.append(dst)
                self.logger.info(f"Album art embedded: {an}")

            except Exception as e:
                self.logger.error(f"APIC embed failed for {an}: {e}")
                failed.append(src.name)
                dst.unlink(missing_ok=True)  # don't leave a broken file in processed/

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
                    tags = ID3(str(path), translate=False)
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
