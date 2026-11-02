"""
Step 4 Dialog — Album Art Selection, for HAM GUI.

Shown before Step 4 runs (as Step1Dialog is before Step 1) so the user
can pick the base image the accession number is drawn onto. Three
choices, each shown as a thumbnail tile:

  1. assets/TrumanSpeakingAlbumArt_ArialYellow.png  (bundled)
  2. assets/TrumanLibraryAlbumArt_ArialYellow.png   (bundled)
  3. Any image file chosen from the file system

The choice is saved in the batch config as
step_configurations.step4.thumbnail_base_image — a path relative to the
app folder for the bundled images (the exe's _MEIPASS folder changes on
every launch, so an absolute path to it would go stale) or an absolute
path for a custom file.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QButtonGroup,
    QDialogButtonBox, QFileDialog, QMessageBox, QStyle,
)
from PyQt6.QtCore import Qt, QSize, QSettings
from PyQt6.QtGui import QIcon, QPixmap

CONFIG_KEY = "step_configurations.step4.thumbnail_base_image"

# (config value, tile caption) — config values are relative to the app folder
PRESET_IMAGES = [
    ("assets/TrumanSpeakingAlbumArt_ArialYellow.png", "Truman Speaking"),
    ("assets/TrumanLibraryAlbumArt_ArialYellow.png", "Truman Library"),
]

_TILE_ICON_SIZE = 160
_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff);;All Files (*)"


class Step4Dialog(QDialog):
    """Dialog for Step 4: choose the album art for the current batch."""

    def __init__(self, paths, parent=None, config=None):
        super().__init__(parent)
        self.paths = paths
        # The batch's ConfigManager — the chosen image is recorded in it
        self.config = config
        self.settings = QSettings("HSTL", "AudioMetadata")
        self._custom_path: Path = None
        self._last_checked_id = 0

        self.setWindowTitle("Step 4: Album Art Selection")
        self.setMinimumWidth(620)

        self._init_ui()
        self._load_current_choice()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h2>Step 4: Album Art Selection</h2>"))

        desc = QLabel(
            "<p>Choose the album art for this batch. Each MP3's accession number "
            "is drawn in the top-left corner of the chosen image, which is then "
            "embedded as the file's front cover.</p>"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(8)

        tiles = QHBoxLayout()
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, (rel_path, caption) in enumerate(PRESET_IMAGES):
            pixmap = QPixmap(str(self.paths.framework_root / rel_path))
            icon = QIcon(pixmap) if not pixmap.isNull() else self._file_icon()
            tiles.addWidget(self._make_tile(i, icon, caption))

        self._custom_id = len(PRESET_IMAGES)
        self._custom_tile = self._make_tile(self._custom_id, self._file_icon(), "Choose File…")
        tiles.addWidget(self._custom_tile)

        self._group.idClicked.connect(self._on_tile_clicked)
        layout.addLayout(tiles)

        self.selection_label = QLabel()
        self.selection_label.setWordWrap(True)
        self.selection_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.selection_label)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setText("Continue")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _make_tile(self, tile_id: int, icon: QIcon, caption: str) -> QToolButton:
        tile = QToolButton()
        tile.setCheckable(True)
        tile.setIcon(icon)
        tile.setIconSize(QSize(_TILE_ICON_SIZE, _TILE_ICON_SIZE))
        tile.setText(caption)
        tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        tile.setMinimumWidth(_TILE_ICON_SIZE + 24)
        self._group.addButton(tile, tile_id)
        return tile

    def _file_icon(self) -> QIcon:
        return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    # ------------------------------------------------------------------
    # Current choice
    # ------------------------------------------------------------------

    def _load_current_choice(self):
        """Pre-select the batch's saved choice; default to the first preset."""
        saved = self.config.get(CONFIG_KEY) if self.config is not None else None
        tile_id = 0
        if saved:
            presets = [rel for rel, _ in PRESET_IMAGES]
            if saved in presets:
                tile_id = presets.index(saved)
            elif Path(saved).is_absolute() and Path(saved).is_file():
                self._set_custom(Path(saved))
                tile_id = self._custom_id
        self._group.button(tile_id).setChecked(True)
        self._last_checked_id = tile_id
        self._refresh_selection_label()

    def _set_custom(self, path: Path):
        self._custom_path = path
        self._custom_tile.setText(path.name)
        self._custom_tile.setToolTip(str(path))
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            self._custom_tile.setIcon(QIcon(pixmap))

    def _selected_value(self) -> str:
        """The config value for the checked tile."""
        tile_id = self._group.checkedId()
        if tile_id == self._custom_id:
            return str(self._custom_path)
        return PRESET_IMAGES[tile_id][0]

    def _refresh_selection_label(self):
        tile_id = self._group.checkedId()
        if tile_id == self._custom_id:
            self.selection_label.setText(f"Selected: {self._custom_path}")
        else:
            self.selection_label.setText(f"Selected: {PRESET_IMAGES[tile_id][1]} (built-in)")

    # ------------------------------------------------------------------
    # Tile clicks
    # ------------------------------------------------------------------

    def _on_tile_clicked(self, tile_id: int):
        if tile_id == self._custom_id and not self._browse_custom():
            # Cancelled or unreadable — go back to the previous tile
            self._group.button(self._last_checked_id).setChecked(True)
            return
        self._last_checked_id = tile_id
        self._refresh_selection_label()

    def _browse_custom(self) -> bool:
        """Pick an image file; returns False if cancelled or unreadable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Album Art Image", self._start_dir(), _IMAGE_FILTER
        )
        if not file_path:
            return False
        path = Path(file_path)
        self.settings.setValue("step4/last_image_dir", str(path.parent))

        try:
            from PIL import Image
            with Image.open(path) as img:
                img.verify()
        except Exception as e:
            QMessageBox.warning(self, "Cannot Read Image",
                                f"Could not open the selected file as an image:\n{e}")
            return False

        self._set_custom(path)
        return True

    def _start_dir(self) -> str:
        """Last folder used for this picker, falling back to Pictures."""
        last = self.settings.value("step4/last_image_dir", "", type=str)
        if last and Path(last).is_dir():
            return last
        pictures = Path.home() / "Pictures"
        return str(pictures) if pictures.is_dir() else ""

    # ------------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------------

    def _on_accept(self):
        """Save the choice in the batch config, then close."""
        if self.config is not None and self.config.config_path:
            self.config.set(CONFIG_KEY, self._selected_value())
            self.config.save_config(self.config.config_data, self.config.config_path)
        self.accept()
