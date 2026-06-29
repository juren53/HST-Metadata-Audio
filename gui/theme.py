"""
ThemeManager integration for HAM GUI.

Adds ~/Projects/ThemeManager to sys.path and re-exports the helpers
the app needs. Pattern mirrors the QR Code Generator theme.py.
"""

from __future__ import annotations
import os
import sys

_TM_PATH = os.path.expanduser("~/Projects/ThemeManager")
if os.path.isdir(_TM_PATH) and _TM_PATH not in sys.path:
    sys.path.insert(0, _TM_PATH)

from theme_manager import get_theme_registry, get_fusion_palette, detect_system_theme  # noqa: F401

DEFAULT_THEME = "light"

_DARK_THEMES = {"dark", "solarized_dark", "dracula"}


def is_dark_theme(theme_name: str) -> bool:
    return theme_name in _DARK_THEMES
