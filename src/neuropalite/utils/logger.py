"""Centralized logging configuration for Neuropalite.

Uses coloredlogs for console output and RotatingFileHandler for persistent logs.
All modules should use ``logging.getLogger(__name__)`` to inherit this configuration.
"""

import logging
import logging.handlers
from pathlib import Path

import coloredlogs

# Project root (3 levels up from this file: utils/ -> neuropalite/ -> src/ -> project root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = PROJECT_ROOT / "logs"


def setup_logging(level: str = "INFO", log_file: str = "neuropalite.log") -> None:
    """Configure logging for the entire application.

    Parameters
    ----------
    level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    log_file : str
        Name of the log file written to ``logs/``.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger("neuropalite")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console — coloredlogs
    coloredlogs.install(
        level=level.upper(),
        logger=root_logger,
        fmt="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # File — rotating (5 MB, 3 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(file_handler)

    root_logger.info("Logging initialized (level=%s, file=%s)", level, log_file)
