#!/usr/bin/env python3
"""
Electoral Roll OCR Search - Production Entry Point

A production-ready tool for searching scanned Bengali electoral roll PDFs
using OCR and fuzzy matching.

Usage:
    python run.py search /path/to/pdfs --names-file names.txt [options]

Options:
    -n, --names-file PATH   File with Bengali names (UTF-8) [required]
    -t, --threshold INT     Fuzzy match threshold 0-100 (default: 82)
    -v, --verbose           Enable debug logging
    -o, --output-json PATH  Save results to JSON file
    --help                  Show help message

Examples:
    # Basic search
    python run.py search ./pdfs --names-file names.txt

    # With custom threshold and JSON export
    python run.py search ./pdfs -n names.txt -t 85 -o results.json

    # Verbose mode for debugging
    python run.py search ./pdfs -n names.txt -v

Requirements:
    - Python 3.14+
    - Tesseract OCR with Bengali language support
    - Poppler utilities (for PDF processing)

    Install system dependencies:
        Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-ben poppler-utils
        macOS: brew install tesseract tesseract-lang poppler

    Install Python dependencies:
        pip install -r requirements.txt
"""

from electoral_search.cli import main

if __name__ == "__main__":
    main()
