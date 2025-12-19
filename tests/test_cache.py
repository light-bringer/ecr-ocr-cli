"""Tests for caching module."""

import tempfile
from pathlib import Path
import pytest

from electoral_search.cache import ResultCache


class TestResultCache:
    """Tests for result caching."""

    def test_cache_initialization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=Path(tmpdir))
            assert cache.cache_dir.exists()

    def test_cache_miss(self, tmp_path):
        """Test cache miss."""
        cache_dir = tmp_path / "cache"
        cache = ResultCache(cache_dir=cache_dir)

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-test")

        result = cache.get(pdf_file, ["test"], 80)
        assert result is None

    def test_cache_set_and_get(self, tmp_path):
        """Test setting and getting cache."""
        cache_dir = tmp_path / "cache"
        cache = ResultCache(cache_dir=cache_dir)

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-test")

        results = [{"name": "test", "page": 1}]
        cache.set(pdf_file, ["test"], 80, results)

        cached = cache.get(pdf_file, ["test"], 80)
        assert cached == results

    def test_cache_different_params(self, tmp_path):
        """Test cache with different parameters."""
        cache_dir = tmp_path / "cache"
        cache = ResultCache(cache_dir=cache_dir)

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-test")

        results = [{"name": "test", "page": 1}]
        cache.set(pdf_file, ["test"], 80, results)

        # Different threshold should be cache miss
        cached = cache.get(pdf_file, ["test"], 90)
        assert cached is None

    def test_clear_cache(self, tmp_path):
        """Test clearing cache."""
        cache_dir = tmp_path / "cache"
        cache = ResultCache(cache_dir=cache_dir)

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-test")

        results = [{"name": "test", "page": 1}]
        cache.set(pdf_file, ["test"], 80, results)

        count = cache.clear()
        assert count >= 1

        cached = cache.get(pdf_file, ["test"], 80)
        assert cached is None

    def test_cache_stats(self, tmp_path):
        """Test cache statistics."""
        cache_dir = tmp_path / "cache"
        cache = ResultCache(cache_dir=cache_dir)

        stats = cache.get_stats()
        assert "total_entries" in stats
        assert "total_size_mb" in stats
        assert "cache_dir" in stats
