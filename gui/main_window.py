"""
Main Window for HAM (HSTL Audio Metadata) GUI.

Modeled after HPM (HSTL Photo Metadata Framework) main_window.py.
Four-tab layout: Batches | Current Batch | Configuration | Logs
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QScrollArea, QStatusBar, QLabel, QMessageBox,
    QFileDialog, QApplication,
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QAction

_GUI_DIR = Path(__file__).parent
_ROOT = _GUI_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from __init__ import __version__, __commit_date__, __app_name__, __short_name__
from utils.batch_registry import BatchRegistry
from config.config_manager import ConfigManager
from utils.path_manager import PathManager
from utils.logger import get_logger

from gui.widgets.batch_list_widget import BatchListWidget
from gui.widgets.step_widget import StepWidget
from gui.widgets.log_widget import LogWidget
from gui.dialogs.new_batch_dialog import NewBatchDialog
from gui.theme import DEFAULT_THEME, get_theme_registry, get_fusion_palette, is_dark_theme
from gui.zoom_manager import ZoomManager


_logger = get_logger("ham-gui")


class MainWindow(QMainWindow):
    """Primary application window for HAM."""

    batch_changed = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()
        self.registry = BatchRegistry(_ROOT)
        self.current_batch_id: str = ""
        self.current_config: ConfigManager = None
        self.settings = QSettings("HSTL", "AudioMetadata")

        saved = self.settings.value("theme/current", DEFAULT_THEME)
        self.current_theme = saved if get_theme_registry().get_theme(saved) else DEFAULT_THEME

        self.zoom_manager = ZoomManager.instance()
        self.zoom_manager.zoom_changed.connect(self._on_zoom_changed)

        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()
        self._load_window_state()
        self._refresh_batch_list()
        self.apply_theme()

    # ──────────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(800, 600)
        self.resize(1100, 750)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._create_batches_tab()
        self._create_current_batch_tab()
        self._create_config_tab()
        self._create_logs_tab()

        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _create_batches_tab(self):
        self.batch_list_widget = BatchListWidget(self.registry)
        self.batch_list_widget.batch_selected.connect(self._on_batch_selected)
        self.batch_list_widget.batch_action_requested.connect(self._handle_batch_action)
        self.tabs.addTab(self.batch_list_widget, "Batches")

    def _create_current_batch_tab(self):
        self.step_widget = StepWidget()
        self.step_widget.step_executed.connect(self._on_step_executed)
        scroll = QScrollArea()
        scroll.setWidget(self.step_widget)
        scroll.setWidgetResizable(True)
        self.tabs.addTab(scroll, "Current Batch")

    def _create_config_tab(self):
        # TODO: implement ConfigWidget (stub placeholder)
        placeholder = QLabel("Configuration editor — coming soon")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabs.addTab(placeholder, "Configuration")

    def _create_logs_tab(self):
        self.log_widget = LogWidget()
        self.tabs.addTab(self.log_widget, "Logs")

    # ──────────────────────────────────────────────────────────────────────
    # Menu bar
    # ──────────────────────────────────────────────────────────────────────

    def _create_menu_bar(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "&New Batch…", self._new_batch, "Ctrl+N")
        self._add_action(file_menu, "&Open Config…", self._open_config, "Ctrl+O")
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", self.close, "Ctrl+Q")

        # Edit
        edit_menu = mb.addMenu("&Edit")
        self._add_action(edit_menu, "&Theme Selection…", self._show_theme_dialog)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "&Settings…", self._show_settings)

        # View
        view_menu = mb.addMenu("&View")
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.setStatusTip("Increase zoom level")
        zoom_in_action.triggered.connect(self._zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_in_alt = QAction(self)
        zoom_in_alt.setShortcut("Ctrl+=")
        zoom_in_alt.triggered.connect(self._zoom_in)
        self.addAction(zoom_in_alt)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.setStatusTip("Decrease zoom level")
        zoom_out_action.triggered.connect(self._zoom_out)
        view_menu.addAction(zoom_out_action)

        view_menu.addSeparator()
        zoom_reset_action = QAction("&Reset Zoom", self)
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.setStatusTip("Reset zoom to 100%")
        zoom_reset_action.triggered.connect(self._reset_zoom)
        view_menu.addAction(zoom_reset_action)

        # Batch
        batch_menu = mb.addMenu("&Batch")
        self._add_action(batch_menu, "&Refresh Batches", self._refresh_batch_list, "F5")
        batch_menu.addSeparator()
        self._add_action(batch_menu, "Mark as &Complete",
                         lambda: self._batch_action("complete"))
        self._add_action(batch_menu, "&Archive",
                         lambda: self._batch_action("archive"))
        self._add_action(batch_menu, "&Reactivate",
                         lambda: self._batch_action("reactivate"))

        # Tools
        tools_menu = mb.addMenu("&Tools")
        self._add_action(tools_menu, "&Validate Dependencies",
                         self._validate_dependencies)
        self._add_action(tools_menu, "&Browse Data Directory…",
                         self._browse_data_dir, "Ctrl+B")

        # Help
        help_menu = mb.addMenu("&Help")
        self._add_action(help_menu, "&User Guide", self._show_user_guide, "F1")
        self._add_action(help_menu, "&Change Log", self._show_changelog)
        help_menu.addSeparator()
        self._add_action(help_menu, "HAM &Issue Tracker", self._show_issue_tracker)
        help_menu.addSeparator()
        self._add_action(help_menu, "&About", self._show_about)

    def _add_action(self, menu, label, slot, shortcut=None):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    # ──────────────────────────────────────────────────────────────────────
    # Status bar
    # ──────────────────────────────────────────────────────────────────────

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        ver_label = QLabel(f"v{__version__} | {__commit_date__}")
        ver_label.setStyleSheet("color: gray;")
        self.status_bar.addPermanentWidget(ver_label)

    # ──────────────────────────────────────────────────────────────────────
    # Batch management
    # ──────────────────────────────────────────────────────────────────────

    def _new_batch(self):
        dialog = NewBatchDialog(self)
        if dialog.exec():
            name, data_dir = dialog.get_values()
            paths = PathManager(Path(data_dir), _ROOT)
            paths.create_batch_dirs()
            config = ConfigManager()
            config.set("project.name", name)
            config.set("project.data_directory", str(data_dir))
            config.save_config(config.config_data, paths.config_path)
            batch_id = self.registry.register_batch(name, str(data_dir), str(paths.config_path))
            if batch_id:
                self.status_bar.showMessage(f"Created batch: {name}", 3000)
                self._refresh_batch_list()
            else:
                QMessageBox.warning(self, "Error", "Failed to register batch")

    def _open_config(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration", "", "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        if fname:
            config_path = Path(fname)
            result = self.registry.find_batch_by_config(fname)
            if result:
                batch_id, batch_info = result
                self._on_batch_selected(batch_id, batch_info)
            else:
                QMessageBox.information(self, "Not Registered",
                                        "This config is not in the batch registry.\n"
                                        "Use File → New Batch to create one.")

    def _refresh_batch_list(self):
        self.registry.reload()
        self.batch_list_widget.refresh()

    def _on_batch_selected(self, batch_id: str, batch_info: dict):
        self.current_batch_id = batch_id
        config_path = Path(batch_info["config_path"])
        self.current_config = ConfigManager(config_path)

        self.registry.update_last_accessed(batch_id)
        self.step_widget.set_batch(self.current_config, batch_id, batch_info)

        self.log_widget.append(f"Selected batch: {batch_info['name']}")
        self.status_bar.showMessage(f"Current batch: {batch_info['name']}")
        self.tabs.setCurrentIndex(1)

    def _handle_batch_action(self, action: str, batch_id: str):
        batch = self.registry.get_batch(batch_id)
        if not batch:
            return
        if action == "complete":
            self.registry.update_batch_status(batch_id, "completed")
        elif action == "archive":
            self.registry.update_batch_status(batch_id, "archived")
        elif action == "reactivate":
            self.registry.update_batch_status(batch_id, "active")
        elif action == "remove":
            reply = QMessageBox.question(
                self, "Confirm Remove",
                f"Remove '{batch['name']}' from registry?\n\nFiles will NOT be deleted.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.registry.unregister_batch(batch_id)
        elif action == "info":
            from gui.dialogs.batch_info_dialog import BatchInfoDialog
            BatchInfoDialog(batch_id, self.registry, self).exec()
        self._refresh_batch_list()

    def _batch_action(self, action: str):
        if not self.current_batch_id:
            QMessageBox.information(self, "No Batch", "Please select a batch first")
            return
        self._handle_batch_action(action, self.current_batch_id)

    def _on_step_executed(self, step_num: int, success: bool):
        verb = "completed" if success else "failed"
        self.status_bar.showMessage(f"Step {step_num} {verb}", 3000)
        self._refresh_batch_list()

    def _on_tab_changed(self, index: int):
        names = ["Batches", "Current Batch", "Configuration", "Logs"]
        if index < len(names):
            self.status_bar.showMessage(f"Viewing: {names[index]}", 2000)

    # ──────────────────────────────────────────────────────────────────────
    # Tools / Help
    # ──────────────────────────────────────────────────────────────────────

    def _validate_dependencies(self):
        deps = {"mutagen": False, "Pillow": False, "PyYAML": False}
        for pkg, key in [("mutagen", "mutagen"), ("Pillow", "PIL"), ("PyYAML", "yaml")]:
            try:
                import importlib
                importlib.import_module(key)
                deps[pkg] = True
            except ImportError:
                pass
        lines = [f"{'[OK]' if ok else '[X]'}  {pkg}" for pkg, ok in deps.items()]
        QMessageBox.information(self, "Dependency Check", "\n".join(lines))

    def _browse_data_dir(self):
        if not self.current_batch_id:
            QMessageBox.information(self, "No Batch", "Select a batch first")
            return
        batch = self.registry.get_batch(self.current_batch_id)
        data_dir = Path(batch.get("data_directory", "")) if batch else None
        if data_dir and data_dir.exists():
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir)))
        else:
            QMessageBox.warning(self, "Not Found", "Data directory not found")

    def _show_theme_dialog(self):
        registry = get_theme_registry()
        themes = [
            (registry.get_theme(n).display_name, n)
            for n in registry.get_theme_names()
            if registry.get_theme(n) is not None
        ]
        display_names = [d for d, _ in themes]
        current_display = next(
            (d for d, k in themes if k == self.current_theme), display_names[0]
        )
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(
            self, "Select Theme", "Theme:", display_names,
            display_names.index(current_display), editable=False,
        )
        if ok and name:
            self.current_theme = next(k for d, k in themes if d == name)
            self.apply_theme()
            self.status_bar.showMessage(f"Applied {name} theme.", 2000)

    def apply_theme(self):
        QApplication.instance().setPalette(get_fusion_palette(self.current_theme))
        self.settings.setValue("theme/current", self.current_theme)

    def _show_settings(self):
        # TODO: implement SettingsDialog
        QMessageBox.information(self, "Settings", "Settings dialog — coming soon")

    # ──────────────────────────────────────────────────────────────────────
    # Zoom
    # ──────────────────────────────────────────────────────────────────────

    def _zoom_in(self):
        self.zoom_manager.zoom_in(QApplication.instance())

    def _zoom_out(self):
        self.zoom_manager.zoom_out(QApplication.instance())

    def _reset_zoom(self):
        self.zoom_manager.reset_zoom(QApplication.instance())

    def _on_zoom_changed(self, factor: float):
        self.status_bar.showMessage(f"Zoom: {self.zoom_manager.get_zoom_percentage()}%", 2000)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            app = QApplication.instance()
            if event.angleDelta().y() > 0:
                self.zoom_manager.zoom_in(app)
            else:
                self.zoom_manager.zoom_out(app)
            event.accept()
        else:
            super().wheelEvent(event)

    def _show_user_guide(self):
        import os
        guide = _ROOT / "docs" / "HSTL_Audio_Framework-Development_Plan.md"
        fallback = "https://github.com/juren53/HST-Metadata/tree/master/Audio/docs"
        if guide.exists():
            try:
                os.startfile(str(guide)) if os.name == "nt" else None
                self.status_bar.showMessage("Opening User Guide…", 2000)
                return
            except Exception:
                pass
        self._open_url(fallback, "User Guide")

    def _show_changelog(self):
        import os
        log = _ROOT / "CHANGELOG.md"
        fallback = "https://github.com/juren53/HST-Metadata/tree/master/Audio"
        if log.exists():
            try:
                os.startfile(str(log)) if os.name == "nt" else None
                self.status_bar.showMessage("Opening Change Log…", 2000)
                return
            except Exception:
                pass
        self._open_url(fallback, "Change Log")

    def _show_issue_tracker(self):
        self._open_url("https://github.com/juren53/HST-Metadata/issues", "Issue Tracker")

    def _open_url(self, url: str, label: str):
        import webbrowser
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        try:
            if QDesktopServices.openUrl(QUrl(url)):
                self.status_bar.showMessage(f"Opening {label}…", 2000)
                return
        except Exception:
            pass
        try:
            webbrowser.open(url)
            self.status_bar.showMessage(f"Opening {label}…", 2000)
        except Exception as e:
            QMessageBox.warning(self, f"Cannot Open {label}",
                                f"Could not open {label} in browser.\n\n"
                                f"URL: {url}\n\nError: {e}")

    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {__short_name__}",
            f"<b>{__app_name__}</b> v{__version__}<br>"
            f"Build date: {__commit_date__}<br><br>"
            "An end-to-end framework for embedding metadata into HSTL sound recordings.<br>"
            "Processes CSV metadata through 5 steps to produce tagged MP3 files<br>"
            "with custom album art thumbnails.<br><br>"
            "Harry S. Truman Presidential Library &amp; Museum",
        )

    # ──────────────────────────────────────────────────────────────────────
    # Window state
    # ──────────────────────────────────────────────────────────────────────

    def _load_window_state(self):
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
        last = self.settings.value("lastBatch")
        if last:
            batch = self.registry.get_batch(last)
            if batch:
                self._on_batch_selected(last, batch)

        self.zoom_manager.apply_saved_zoom(QApplication.instance())

    def _save_window_state(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        if self.current_batch_id:
            self.settings.setValue("lastBatch", self.current_batch_id)

    def closeEvent(self, event):
        self._save_window_state()
        self.zoom_manager.save_zoom_preference()
        event.accept()
