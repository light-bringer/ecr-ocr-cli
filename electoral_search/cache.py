"""
Result caching system for OCR operations.

Caches OCR results based on PDF file hash to avoid reprocessing.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from .types import SearchResult

logger = logging.getLogger(__name__)

# Default cache directory
CACHE_DIR = Path.home() / ".electoral_search_cache"
CACHE_VERSION = "1.0"


class ResultCache:
    """
    File-based cache for OCR results.

    Caches results by PDF file hash to avoid reprocessing identical files.
    """

    def __init__(self, cache_dir: Optional[Path] = None, ttl_days: int = 30):
        """
        Initialize the result cache.

        Args:
            cache_dir: Directory to store cache files (default: ~/.electoral_search_cache)
            ttl_days: Time to live for cache entries in days (default: 30)
        """
        self.cache_dir = cache_dir or CACHE_DIR
        self.ttl_days = ttl_days
        self.ttl = timedelta(days=ttl_days)

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache directory: {self.cache_dir}")

    def _compute_file_hash(self, file_path: Path) -> str:
        """
        Compute SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def _get_cache_key(
        self, pdf_path: Path, search_names: List[str], threshold: int
    ) -> str:
        """
        Generate cache key based on PDF hash and search parameters.

        Args:
            pdf_path: Path to PDF file
            search_names: List of search names
            threshold: Fuzzy match threshold

        Returns:
            Cache key string
        """
        file_hash = self._compute_file_hash(pdf_path)
        names_hash = hashlib.sha256(
            "|".join(sorted(search_names)).encode()
        ).hexdigest()[:16]

        return f"{file_hash}_{names_hash}_{threshold}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Get path to cache file for a given key.

        Args:
            cache_key: Cache key

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{cache_key}.json"

    def get(
        self, pdf_path: Path, search_names: List[str], threshold: int
    ) -> Optional[List[SearchResult]]:
        """
        Retrieve cached results if available and not expired.

        Args:
            pdf_path: Path to PDF file
            search_names: List of search names
            threshold: Fuzzy match threshold

        Returns:
            Cached results or None if not found/expired
        """
        cache_key = self._get_cache_key(pdf_path, search_names, threshold)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {pdf_path.name}")
            return None

        try:
            # Check if cache is expired
            cache_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            if datetime.now() - cache_mtime > self.ttl:
                logger.info(f"Cache expired for {pdf_path.name}, removing")
                cache_path.unlink()
                return None

            # Load cached results
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Verify cache version
            if cache_data.get("version") != CACHE_VERSION:
                logger.warning(f"Cache version mismatch for {pdf_path.name}")
                cache_path.unlink()
                return None

            results = cache_data.get("results", [])
            logger.info(
                f"Cache hit: {pdf_path.name} ({len(results)} results)"
            )

            return results

        except Exception as e:
            logger.error(f"Error reading cache for {pdf_path.name}: {e}")
            # Remove corrupted cache file
            try:
                cache_path.unlink()
            except Exception:
                pass
            return None

    def set(
        self,
        pdf_path: Path,
        search_names: List[str],
        threshold: int,
        results: List[SearchResult],
    ) -> None:
        """
        Store results in cache.

        Args:
            pdf_path: Path to PDF file
            search_names: List of search names
            threshold: Fuzzy match threshold
            results: Search results to cache
        """
        cache_key = self._get_cache_key(pdf_path, search_names, threshold)
        cache_path = self._get_cache_path(cache_key)

        try:
            cache_data = {
                "version": CACHE_VERSION,
                "timestamp": datetime.now().isoformat(),
                "pdf_path": str(pdf_path),
                "pdf_name": pdf_path.name,
                "threshold": threshold,
                "num_names": len(search_names),
                "results": results,
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            logger.info(
                f"Cached {len(results)} results for {pdf_path.name}"
            )

        except Exception as e:
            logger.error(f"Error writing cache for {pdf_path.name}: {e}")

    def clear(self) -> int:
        """
        Clear all cache files.

        Returns:
            Number of cache files removed
        """
        count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1

            logger.info(f"Cleared {count} cache files")
            return count

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return count

    def clear_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of expired entries removed
        """
        count = 0
        try:
            now = datetime.now()

            for cache_file in self.cache_dir.glob("*.json"):
                cache_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if now - cache_mtime > self.ttl:
                    cache_file.unlink()
                    count += 1

            logger.info(f"Removed {count} expired cache entries")
            return count

        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
            return count

    def get_stats(self) -> Dict[str, any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "cache_dir": str(self.cache_dir),
                "total_entries": len(cache_files),
                "total_size_mb": total_size / (1024 * 1024),
                "ttl_days": self.ttl_days,
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
