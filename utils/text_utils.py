"""
Text cleanup helpers for HAM.

Mojibake is text that was encoded as UTF-8 and then decoded with the
wrong code page (usually Windows-1252), e.g. a non-breaking space
(U+00A0, UTF-8 bytes C2 A0) that comes back as "Â" + non-breaking space.
Once the CSV has been saved that way, the wrong characters are real text
and get embedded in every tag that uses the field.

Detection uses ftfy.fix_encoding(), which only undoes wrong-code-page
decoding. Unlike ftfy.fix_text() it leaves curly quotes, full-width CJK
punctuation and other legitimate characters alone.
"""

from typing import Optional


def fix_mojibake(text: str) -> Optional[str]:
    """Return the repaired text if `text` contains mojibake, else None."""
    if text.isascii():
        return None
    import ftfy
    fixed = ftfy.fix_encoding(text)
    return fixed if fixed != text else None


def snippet(text: str, other: str, width: int = 30) -> str:
    """The part of `text` around its first difference from `other`, with
    non-ASCII characters escaped so a report shows exactly what changed."""
    i = next((n for n, (a, b) in enumerate(zip(text, other)) if a != b),
             min(len(text), len(other)))
    start = max(0, i - width // 2)
    part = text[start:start + width].encode("ascii", "backslashreplace").decode("ascii")
    return ("…" if start else "") + part + ("…" if start + width < len(text) else "")
