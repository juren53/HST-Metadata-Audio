"""
Centralized Logging Manager for HAM (HSTL Audio Metadata Framework).

Ported from HPM's utils/log_manager.py
(Photos/Version-2/Framework/utils/log_manager.py), including HPM's
LogRecord/GUILogHandler pair (previously deferred — see CHANGELOG v0.2.8),
adapted to HAM's specifics:

- LogRecord's level filter/dropdown includes HAM's custom SUCCESS level
  (25, between INFO and WARNING) and CRITICAL, which HPM's own filter
  dropdown omits.
- ContextFilter (new, no HPM equivalent) — per-step-run loggers
  (utils.logger.get_logger(), wired in gui/widgets/step_widget.py) aren't
  children of the shared "ham" logger, and step implementations
  (steps/*.py) log via plain self.logger.info(...) without `extra=`. This
  filter, attached directly to each per-run logger, stamps batch_id/step
  onto every record that reaches it, so LogViewerDialog's batch/step
  filtering actually has something to filter on without editing every
  step module.
- Per-step execution keeps its own uniquely-named, per-run logger and log
  file (utils.logger.get_logger(), wired in gui/widgets/step_widget.py) —
  that mechanism is unchanged by this port and still gives one isolated
  file per step invocation. What's new here is a *consolidated* per-batch
  log file: step_widget.py additionally attaches LogManager's batch handler
  (via get_batch_handler()) to each per-run logger so step messages also
  land in one place per batch, alongside application-level events (batch
  selection, etc.) that are logged directly through LogManager.

Provides:
- Session-level logging (whole app run) to a rotating file
- Per-batch logging to a rotating file
- A singleton GUI handler emitting structured LogRecords, for real-time,
  filterable display in the Logs tab and pop-out LogViewerDialog
- Verbosity level control
"""

import logging
import threading
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import QObject, pyqtSignal

from utils.logger import SUCCESS_LEVEL

# Verbosity level mappings (mirrors HPM's utils/log_manager.py)
VERBOSITY_LEVELS = {
    "minimal": logging.WARNING,   # Errors and warnings only
    "normal": logging.INFO,       # Key actions (default)
    "detailed": logging.DEBUG,    # All operations including debug
    "success": SUCCESS_LEVEL,     # Custom success level
}

# Level filter priority — used by LogRecord.matches_filter(). Includes
# HAM's SUCCESS level and CRITICAL, both of which HPM's dropdown omits.
LEVEL_PRIORITY = {
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": SUCCESS_LEVEL,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


@dataclass
class LogRecord:
    """Enhanced log record with metadata for GUI filtering/display."""

    timestamp: datetime
    level: str
    level_no: int
    source: str
    message: str
    batch_id: Optional[str] = None
    step: Optional[int] = None

    def matches_filter(
        self,
        level_filter: str = "ALL",
        batch_filter: Optional[str] = None,
        step_filter: Optional[int] = None,
        search_text: str = "",
    ) -> bool:
        """Check if this record matches the given filter settings."""
        if level_filter != "ALL":
            if LEVEL_PRIORITY.get(self.level, 0) < LEVEL_PRIORITY.get(level_filter, 0):
                return False
        if batch_filter and self.batch_id != batch_filter:
            return False
        if step_filter is not None and self.step != step_filter:
            return False
        if search_text and search_text.lower() not in self.message.lower():
            return False
        return True

    def format_display(self) -> str:
        """Format for display in the log viewer."""
        ts = self.timestamp.strftime("%H:%M:%S")
        parts = [f"[{ts}]", f"[{self.level}]"]
        if self.batch_id:
            parts.append(f"[{self.batch_id[:8]}]")
        if self.step is not None:
            parts.append(f"[Step {self.step}]")
        parts.append(self.message)
        return " ".join(parts)


class GUILogHandler(logging.Handler, QObject):
    """Thread-safe logging handler that emits a LogRecord via a Qt signal.

    Qt auto-queues signal emissions from a worker thread onto the GUI
    thread, so this is safe to attach to loggers used from StepRunner's
    background thread (gui/workers.py).
    """

    log_emitted = pyqtSignal(object)  # Emits LogRecord

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord):
        try:
            log_record = LogRecord(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                level_no=record.levelno,
                source=record.name,
                message=self.format(record),
                batch_id=getattr(record, "batch_id", None),
                step=getattr(record, "step", None),
            )
            self.log_emitted.emit(log_record)
        except Exception:
            self.handleError(record)


class ContextFilter(logging.Filter):
    """Stamps batch_id/step onto every record from a per-run step logger.

    Step implementations (steps/*.py) log via plain self.logger.info(...)
    without passing `extra=`, so without this filter their records would
    reach LogViewerDialog with batch_id=step=None, making batch/step
    filtering useless for the most common log source. No HPM equivalent
    — HPM's step logic all runs through the single shared "hstl_framework"
    logger LogManager itself tags via extra=, so this problem doesn't
    arise there.
    """

    def __init__(self, batch_id: Optional[str], step: Optional[int]):
        super().__init__()
        self.batch_id = batch_id
        self.step = step

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "batch_id", None) is None:
            record.batch_id = self.batch_id
        if getattr(record, "step", None) is None:
            record.step = self.step
        return True


class BatchFileHandler(RotatingFileHandler):
    """Rotating file handler for a single batch's consolidated log."""

    def __init__(
        self,
        batch_dir: Path,
        batch_id: str,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 3,
    ):
        log_dir = Path(batch_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"batch_{batch_id}.log"
        super().__init__(
            str(log_file), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        self.batch_id = batch_id
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))


class LogManager:
    """Singleton log manager for centralized logging control.

    Usage:
        log_manager = LogManager.instance()
        log_manager.setup_session_logging(log_dir)
        log_manager.info("Application started")
    """

    _instance: Optional["LogManager"] = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> "LogManager":
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (mainly for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
            cls._instance = None

    def __init__(self):
        self._logger = logging.getLogger("ham")
        self._batch_handlers: Dict[str, BatchFileHandler] = {}
        self._gui_handler: Optional[GUILogHandler] = None
        self._session_handler: Optional[RotatingFileHandler] = None
        self._verbosity = "normal"
        self._session_log_path: Optional[Path] = None

    def setup_session_logging(self, log_dir: Path, verbosity: str = "normal"):
        """Initialize session-level logging (one rotating file per app run)."""
        if self._session_handler is not None:
            return  # already set up for this process

        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_log_path = log_dir / f"session_{timestamp}.log"

        self._session_handler = RotatingFileHandler(
            str(self._session_log_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        self._session_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self._logger.addHandler(self._session_handler)
        self.set_verbosity(verbosity)

        self.info(f"Session logging initialized: {self._session_log_path}")

    def get_gui_handler(self) -> GUILogHandler:
        """Get or create the singleton GUI log handler."""
        if self._gui_handler is None:
            self._gui_handler = GUILogHandler()
            self._gui_handler.setLevel(VERBOSITY_LEVELS.get(self._verbosity, logging.INFO))
            self._logger.addHandler(self._gui_handler)
        return self._gui_handler

    def setup_batch_logging(self, batch_id: str, batch_dir: Path):
        """Create the consolidated per-batch log file handler."""
        if batch_id in self._batch_handlers:
            return  # already set up

        handler = BatchFileHandler(batch_dir, batch_id)
        handler.setLevel(logging.DEBUG)  # Capture everything in the batch file

        self._batch_handlers[batch_id] = handler
        self._logger.addHandler(handler)

        self.info(f"Batch logging initialized for: {batch_id}", batch_id=batch_id)

    def get_batch_handler(self, batch_id: str) -> Optional[BatchFileHandler]:
        """Return the active batch handler, if any.

        Per-step-run loggers (utils.logger.get_logger()) aren't children of
        the shared "ham" logger, so they don't inherit this handler
        automatically — callers that want step output in the consolidated
        batch log must attach it explicitly (see step_widget.py._run_step()).
        """
        return self._batch_handlers.get(batch_id)

    def remove_batch_logging(self, batch_id: str):
        """Remove and close the per-batch log file handler."""
        handler = self._batch_handlers.pop(batch_id, None)
        if handler is not None:
            self._logger.removeHandler(handler)
            handler.close()

    def set_verbosity(self, level: str):
        """Set the verbosity level for the logger and its handlers."""
        self._verbosity = level
        log_level = VERBOSITY_LEVELS.get(level, logging.INFO)

        self._logger.setLevel(log_level)
        if self._session_handler:
            self._session_handler.setLevel(log_level)
        if self._gui_handler:
            self._gui_handler.setLevel(log_level)

    @property
    def verbosity(self) -> str:
        return self._verbosity

    @property
    def session_log_path(self) -> Optional[Path]:
        return self._session_log_path

    # ------------------------------------------------------------------
    # Convenience logging methods
    # ------------------------------------------------------------------

    def log(
        self,
        level: int,
        message: str,
        batch_id: Optional[str] = None,
        step: Optional[int] = None,
        exc_info: bool = False,
    ):
        """Log a message with optional batch and step context."""
        extra = {"batch_id": batch_id, "step": step}
        self._logger.log(level, message, extra=extra, exc_info=exc_info)

    def debug(self, message: str, batch_id: Optional[str] = None, step: Optional[int] = None):
        self.log(logging.DEBUG, message, batch_id, step)

    def info(self, message: str, batch_id: Optional[str] = None, step: Optional[int] = None):
        self.log(logging.INFO, message, batch_id, step)

    def warning(self, message: str, batch_id: Optional[str] = None, step: Optional[int] = None):
        self.log(logging.WARNING, message, batch_id, step)

    def error(
        self,
        message: str,
        batch_id: Optional[str] = None,
        step: Optional[int] = None,
        exc_info: bool = False,
    ):
        self.log(logging.ERROR, message, batch_id, step, exc_info=exc_info)

    def success(self, message: str, batch_id: Optional[str] = None, step: Optional[int] = None):
        self.log(SUCCESS_LEVEL, message, batch_id, step)

    def critical(
        self,
        message: str,
        batch_id: Optional[str] = None,
        step: Optional[int] = None,
        exc_info: bool = False,
    ):
        self.log(logging.CRITICAL, message, batch_id, step, exc_info=exc_info)

    def step_start(self, step: int, step_name: str, batch_id: Optional[str] = None):
        self.info(f"Starting Step {step}: {step_name}", batch_id, step)

    def step_complete(self, step: int, step_name: str, batch_id: Optional[str] = None):
        self.success(f"Completed Step {step}: {step_name}", batch_id, step)

    def step_error(
        self, step: int, error: str, batch_id: Optional[str] = None, exc_info: bool = False
    ):
        self.error(f"Step {step} failed: {error}", batch_id, step, exc_info=exc_info)

    def shutdown(self):
        """Close all handlers and clean up."""
        for handler in list(self._batch_handlers.values()):
            self._logger.removeHandler(handler)
            handler.close()
        self._batch_handlers.clear()

        if self._session_handler:
            self._logger.removeHandler(self._session_handler)
            self._session_handler.close()
            self._session_handler = None

        if self._gui_handler:
            self._logger.removeHandler(self._gui_handler)
            self._gui_handler = None


def get_log_manager() -> LogManager:
    """Convenience function to get the LogManager singleton."""
    return LogManager.instance()
