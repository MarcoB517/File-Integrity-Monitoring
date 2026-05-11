"""
logger.py — Centralized Logging Configuration

Sets up logging for the FIM system. All modules import get_logger()
from here so that log format and output are consistent across the project.

Logs are written to both the terminal and a file called fim.log.

Usage:
    from logger import get_logger
    logger = get_logger(__name__)

    logger.info("Scan started")
    logger.warning("File skipped: permission denied")
    logger.error("Database connection failed")

Author: Marco Buritica
Course: CISC 4900
"""

import logging
import sys
from pathlib import Path

LOG_FILE = "fim.log"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a logger for the given module name.

    Logs are sent to two places:
        - Terminal (stdout): WARNING level and above
        - fim.log file: DEBUG level and above (everything)

    Args:
        name: The module name, typically passed as __name__.

    Returns:
        A configured logging.Logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting scan")
        2026-04-12 10:00:00 [INFO] scanner: Starting scan
    """
    logger = logging.getLogger(name)

    # Only add handlers if none exist (prevents duplicate logs)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Terminal handler — shows WARNING and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    # File handler — logs everything (DEBUG and above)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
