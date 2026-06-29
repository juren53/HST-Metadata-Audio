"""
File operation utilities for HAM.
"""

import shutil
from pathlib import Path
from typing import List, Optional


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
