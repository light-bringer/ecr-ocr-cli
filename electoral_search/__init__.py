"""
Electoral Roll OCR Search Package

A production-ready tool for searching scanned Bengali electoral roll PDFs
using OCR and fuzzy matching.
"""

from .config import (
    DPI,
    OCR_LANG,
    OCR_CONFIG,
    FUZZY_THRESHOLD_DEFAULT,
    MAX_PDF_SIZE_MB,
    MAX_PDF_PAGES,
    MAX_NAMES_FILE_SIZE_MB,
    MAX_SEARCH_NAMES,
    ProcessingStats,
    setup_logging,
)
from .types import VoterInfo, SearchResult
from .validation import validate_path_security, validate_pdf_file
from .text_processing import normalize_bn, extract_voter_blocks, fuzzy_match
from .ocr import process_pdf
from .parallel import process_pdfs_parallel, get_optimal_workers
from .cache import ResultCache
from .export import export_to_json, export_to_csv, export_results
from .cli import app, main

__version__ = "2.1.0"
__all__ = [
    # Config
    "DPI",
    "OCR_LANG",
    "OCR_CONFIG",
    "FUZZY_THRESHOLD_DEFAULT",
    "MAX_PDF_SIZE_MB",
    "MAX_PDF_PAGES",
    "MAX_NAMES_FILE_SIZE_MB",
    "MAX_SEARCH_NAMES",
    "ProcessingStats",
    "setup_logging",
    # Types
    "VoterInfo",
    "SearchResult",
    # Validation
    "validate_path_security",
    "validate_pdf_file",
    # Text Processing
    "normalize_bn",
    "extract_voter_blocks",
    "fuzzy_match",
    # OCR
    "process_pdf",
    # Parallel Processing
    "process_pdfs_parallel",
    "get_optimal_workers",
    # Cache
    "ResultCache",
    # Export
    "export_to_json",
    "export_to_csv",
    "export_results",
    # CLI
    "app",
    "main",
]
