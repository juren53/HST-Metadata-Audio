"""
Logging utilities for HAM.

Provides a colourised console logger and optional file handler.
Import the module-level `get_logger()` factory anywhere in the framework.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    _HAS_COLOR = True
except ImportError:
    _HAS_COLOR = False


# Custom SUCCESS level (between INFO and WARNING)
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


class HAMLogger(logging.Logger):
    def success(self, msg, *args, **kwargs):
        if self.isEnabledFor(SUCCESS_LEVEL):
            self._log(SUCCESS_LEVEL, msg, args, **kwargs)


logging.setLoggerClass(HAMLogger)


class _ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\033[36m",   # cyan
        logging.INFO:     "\033[37m",   # white
        SUCCESS_LEVEL:    "\033[32m",   # green
        logging.WARNING:  "\033[33m",   # yellow
        logging.ERROR:    "\033[31m",   # red
        logging.CRITICAL: "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        msg = super().format(record)
        return f"{color}{msg}{self.RESET}" if _HAS_COLOR else msg


def get_logger(
    name: str = "ham",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> HAMLogger:
    """Return a configured HAMLogger instance."""
    logger: HAMLogger = logging.getLogger(name)  # type: ignore[assignment]
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(_ColorFormatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    # Optional file handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)

    return logger
