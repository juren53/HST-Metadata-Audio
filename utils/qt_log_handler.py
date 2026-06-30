"""
Qt logging handler — bridges Python logging into the GUI LogWidget.

Attach to any logger; records are emitted as a Qt signal so they can be
safely appended to the LogWidget from the main thread.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal


class QtLogHandler(QObject, logging.Handler):
    """logging.Handler that emits each record as a Qt signal."""

    log_record = pyqtSignal(str, str)   # (formatted_message, level_name)

    def __init__(self, parent=None, level: int = logging.DEBUG):
        QObject.__init__(self, parent)
        logging.Handler.__init__(self, level)
        self.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.log_record.emit(msg, record.levelname)
        except Exception:
            self.handleError(record)
