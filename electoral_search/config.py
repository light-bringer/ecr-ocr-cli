"""
Configuration management for electoral search tool.

All configuration values can be overridden via environment variables.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List

# OCR Configuration
DPI = int(os.getenv("OCR_DPI", "350"))  # Image resolution for OCR
OCR_LANG = os.getenv("OCR_LANG", "ben")  # Tesseract language (Bengali)
OCR_CONFIG = "--psm 6"  # Page Segmentation Mode: uniform text block
FUZZY_THRESHOLD_DEFAULT = 82  # Default similarity threshold (0-100)

# Security & Resource Limits
MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "50"))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "100"))
MAX_NAMES_FILE_SIZE_MB = int(os.getenv("MAX_NAMES_FILE_SIZE_MB", "10"))
MAX_SEARCH_NAMES = int(os.getenv("MAX_SEARCH_NAMES", "1000"))

# Logging Configuration
LOG_FILE = "electoral_search.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        verbose: Enable debug logging if True

    Returns:
        Configured logger instance
    """
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    return logger


@dataclass
class ProcessingStats:
    """Statistics for processing session."""

    files_processed: int = 0
    files_failed: int = 0
    pages_processed: int = 0
    matches_found: int = 0
    errors: List[str] = field(default_factory=list)
