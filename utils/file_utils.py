"""
File operation utilities for HAM.
"""

import shutil
from pathlib import Path
from typing import List, Optional, Tuple


def safe_copy(src: Path, dst: Path, overwrite: bool = True) -> bool:
    """Copy a file, creating parent dirs as needed. Returns True on success."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not overwrite:
            return False
        shutil.copy2(src, dst)
        return True
    except OSError as e:
        print(f"[file_utils] copy failed {src} -> {dst}: {e}")
        return False


def read_csv_text(path: Path) -> Tuple[str, str]:
    """Read a CSV's text, tolerating non-UTF-8 exports.

    Tries UTF-8 (with or without BOM) first, then Windows-1252 — what Excel
    and most Windows database exports write (e.g. byte 0xA0 is a
    non-breaking space there, but an invalid start byte in UTF-8). Latin-1
    is the last resort since it decodes any byte. Returns (text, encoding).
    """
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise AssertionError("unreachable: latin-1 decodes every byte")


def count_mp3s(directory: Path) -> int:
    return len(list(directory.glob("*.mp3"))) if directory.exists() else 0


def count_csvs(directory: Path) -> int:
    return len(list(directory.glob("*.csv"))) if directory.exists() else 0


def find_csv(directory: Path) -> Optional[Path]:
    files = sorted(directory.glob("*.csv"))
    return files[0] if files else None


def list_mp3s(directory: Path) -> List[Path]:
    return sorted(directory.glob("*.mp3")) if directory.exists() else []


def open_in_explorer(path: Path):
    """Open a directory in Windows Explorer."""
    import subprocess, os
    if os.name == "nt":
        subprocess.Popen(["explorer", str(path)])
