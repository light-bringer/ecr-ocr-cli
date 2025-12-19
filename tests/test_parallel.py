"""Tests for parallel processing module."""

import multiprocessing as mp
from pathlib import Path
from unittest.mock import Mock
import pytest

from electoral_search.parallel import get_optimal_workers, process_pdfs_parallel


# Module-level mock function for pickling compatibility
def _mock_process_pdf(pdf_path):
    """Mock function for testing parallel processing."""
    return [{"name": "test", "page": 1, "file": str(pdf_path)}]


class TestGetOptimalWorkers:
    """Tests for optimal worker calculation."""

    def test_auto_detect(self):
        workers = get_optimal_workers()
        cpu_count = mp.cpu_count()
        expected = max(1, cpu_count - 1)
        assert workers == expected

    def test_max_workers_limit(self):
        workers = get_optimal_workers(max_workers=2)
        assert workers == 2

    def test_max_workers_exceeds_cpu(self):
        workers = get_optimal_workers(max_workers=999)
        assert workers == mp.cpu_count()

    def test_zero_workers(self):
        workers = get_optimal_workers(max_workers=0)
        assert workers == 1


class TestProcessPdfsParallel:
    """Tests for parallel PDF processing."""

    def test_empty_list(self):
        results = process_pdfs_parallel([], lambda x: [])
        assert results == []

    def test_single_file(self, tmp_path):
        """Test processing a single file."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-test")

        results = process_pdfs_parallel([pdf_file], _mock_process_pdf, max_workers=1)
        assert len(results) == 1
        assert results[0]["name"] == "test"
