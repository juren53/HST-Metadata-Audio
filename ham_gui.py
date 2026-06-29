#!/usr/bin/env python3
"""
ham_gui.py — HAM (HSTL Audio Metadata) GUI launcher.

Uses the ATW (Audio Tag Writer) application icon.

Usage:
    python ham_gui.py
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Add Icon_Manager_Module to path
_IMM = Path.home() / "Projects" / "Icon_Manager_Module"
if _IMM.exists() and str(_IMM) not in sys.path:
    sys.path.insert(0, str(_IMM))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from __init__ import __app_name__, __version__

APP_ID = "HSTL.AudioMetadata.HAM"

# Icons live in gui/resources/icons/ (ATW icons copied here)
_ICON_DIR = _ROOT / "gui" / "resources" / "icons"


def main():
    # Windows: set AppUserModelID before creating QApplication
    if sys.platform.startswith("win"):
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("HSTL")
    app.setStyle("Fusion")

    # Capture base font size before any zoom is applied
    from gui.zoom_manager import ZoomManager
    ZoomManager.instance().initialize_base_font(app)

    # Load icon via IconLoader if available, fall back to direct QIcon
    try:
        from icon_loader import IconLoader
        loader = IconLoader(_ICON_DIR)
        icon = loader.app_icon()
    except ImportError:
        from PyQt6.QtGui import QIcon
        ico = _ICON_DIR / "app.ico"
        icon = QIcon(str(ico)) if ico.exists() else QIcon()

    app.setWindowIcon(icon)

    from gui.main_window import MainWindow
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()

    # Windows: fix taskbar icon
    if sys.platform.startswith("win"):
        try:
            from icon_loader import IconLoader
            loader = IconLoader(_ICON_DIR)
            loader.set_taskbar_icon(window, APP_ID)
        except (ImportError, Exception):
            pass

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
