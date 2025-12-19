"""
Input validation and security functions.

Provides path validation, file validation, and security checks.
"""

from pathlib import Path
from typing import Optional

from .config import MAX_PDF_SIZE_MB


def validate_path_security(path: str, base_dir: Optional[str] = None) -> Path:
    """
    Validate file path to prevent directory traversal attacks.

    Args:
        path: Path to validate
        base_dir: Optional base directory to restrict access to

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path is invalid or outside base_dir
    """
    try:
        resolved_path = Path(path).resolve()

        # Check for path traversal
        if base_dir:
            base_resolved = Path(base_dir).resolve()
            if not str(resolved_path).startswith(str(base_resolved)):
                raise ValueError(f"Path '{path}' is outside allowed directory '{base_dir}'")

        return resolved_path
    except Exception as e:
        raise ValueError(f"Invalid path '{path}': {e}")


def validate_pdf_file(pdf_path: Path) -> None:
    """
    Validate PDF file meets security and resource requirements.

    Args:
        pdf_path: Path to PDF file

    Raises:
        ValueError: If file is invalid or exceeds limits
    """
    if not pdf_path.exists():
        raise ValueError(f"PDF file not found: {pdf_path}")

    if not pdf_path.is_file():
        raise ValueError(f"Path is not a file: {pdf_path}")

    # Check file size
    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_PDF_SIZE_MB:
        raise ValueError(f"PDF file too large: {size_mb:.1f}MB (max: {MAX_PDF_SIZE_MB}MB)")

    # Basic file type check (magic number)
    with open(pdf_path, 'rb') as f:
        header = f.read(5)
        if header != b'%PDF-':
            raise ValueError(f"File is not a valid PDF: {pdf_path}")
