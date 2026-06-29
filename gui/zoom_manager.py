"""Zoom Manager for HSTL Audio Metadata (HAM).

Provides centralized zoom/font scaling management.
Singleton pattern; mirrors gui/zoom_manager.py in HPM.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


class ZoomManager(QObject):
    """Singleton zoom manager for application-wide font scaling.

    Font-only scaling lets Qt layouts resize buttons, tables, trees,
    and menus automatically without per-widget dimension code.
    """

    zoom_changed = pyqtSignal(float)

    ZOOM_LEVELS = [0.75, 0.85, 1.0, 1.15, 1.3, 1.5, 1.75, 2.0]
    DEFAULT_ZOOM = 1.0
    MIN_ZOOM = 0.75
    MAX_ZOOM = 2.0
    MIN_FONT_SIZE = 8
    MAX_FONT_SIZE = 24
    SETTINGS_KEY = "ui/zoom_level"

    _instance = None

    def __init__(self):
        if ZoomManager._instance is not None:
            raise RuntimeError("Use ZoomManager.instance() instead")
        super().__init__()
        self._current_zoom = self.DEFAULT_ZOOM
        self._base_font_size = None

    @classmethod
    def instance(cls) -> "ZoomManager":
        if cls._instance is None:
            cls._instance = ZoomManager()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """For testing only — resets singleton state."""
        cls._instance = None

    def initialize_base_font(self, app: QApplication):
        """Capture the app's default font size. Call once at startup before any zoom."""
        if self._base_font_size is None:
            self._base_font_size = app.font().pointSize()

    def apply_saved_zoom(self, app: QApplication):
        """Load zoom level from QSettings and apply it."""
        settings = QSettings("HSTL", "AudioMetadata")
        zoom_level = settings.value(self.SETTINGS_KEY, self.DEFAULT_ZOOM, type=float)
        zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom_level))
        self.set_zoom_level(app, zoom_level)

    def save_zoom_preference(self):
        """Persist current zoom level to QSettings."""
        settings = QSettings("HSTL", "AudioMetadata")
        settings.setValue(self.SETTINGS_KEY, self._current_zoom)

    def set_zoom_level(self, app: QApplication, factor: float):
        """Set an absolute zoom factor (0.75–2.0)."""
        factor = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
        if factor == self._current_zoom:
            return
        self._current_zoom = factor
        self._apply_font_scaling(app)
        self.zoom_changed.emit(factor)

    def zoom_in(self, app: QApplication):
        """Step to the next higher zoom level."""
        idx = self._nearest_index()
        if idx < len(self.ZOOM_LEVELS) - 1:
            self.set_zoom_level(app, self.ZOOM_LEVELS[idx + 1])

    def zoom_out(self, app: QApplication):
        """Step to the next lower zoom level."""
        idx = self._nearest_index()
        if idx > 0:
            self.set_zoom_level(app, self.ZOOM_LEVELS[idx - 1])

    def reset_zoom(self, app: QApplication):
        """Reset to 100% (factor = 1.0)."""
        self.set_zoom_level(app, self.DEFAULT_ZOOM)

    def get_current_zoom(self) -> float:
        return self._current_zoom

    def get_zoom_percentage(self) -> int:
        return int(self._current_zoom * 100)

    # ── private ──────────────────────────────────────────────────────────────

    def _nearest_index(self) -> int:
        return min(
            range(len(self.ZOOM_LEVELS)),
            key=lambda i: abs(self.ZOOM_LEVELS[i] - self._current_zoom),
        )

    def _apply_font_scaling(self, app: QApplication):
        if self._base_font_size is None:
            self._base_font_size = app.font().pointSize()
        new_size = int(self._base_font_size * self._current_zoom)
        new_size = max(self.MIN_FONT_SIZE, min(self.MAX_FONT_SIZE, new_size))
        font = QFont()
        font.setPointSize(new_size)
        app.setFont(font)
        for widget in app.allWidgets():
            widget.setFont(font)
