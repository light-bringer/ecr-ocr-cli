"""Tests for validation module."""

import tempfile
from pathlib import Path
import pytest
from electoral_search.validation import validate_path_security, validate_pdf_file


class TestValidatePathSecurity:
    """Tests for path validation."""

    def test_valid_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = validate_path_security(tmpdir)
            assert isinstance(path, Path)
            assert path.exists()

    def test_path_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="outside allowed directory"):
                validate_path_security("../../../etc/passwd", base_dir=tmpdir)


class TestValidatePdfFile:
    """Tests for PDF file validation."""

    def test_nonexistent_file(self):
        with pytest.raises(ValueError, match="not found"):
            validate_pdf_file(Path("/nonexistent/file.pdf"))

    def test_directory_not_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="not a file"):
                validate_pdf_file(Path(tmpdir))

    def test_invalid_pdf_magic_number(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"NOT A PDF")
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="not a valid PDF"):
                validate_pdf_file(temp_path)
        finally:
            temp_path.unlink()

    def test_valid_pdf_header(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4\ntest")
            f.flush()
            temp_path = Path(f.name)

        try:
            validate_pdf_file(temp_path)  # Should not raise
        finally:
            temp_path.unlink()
