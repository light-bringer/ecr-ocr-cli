"""Tests for configuration module."""

from electoral_search.config import ProcessingStats, setup_logging


class TestProcessingStats:
    """Tests for ProcessingStats dataclass."""

    def test_initialization(self):
        stats = ProcessingStats()
        assert stats.files_processed == 0
        assert stats.files_failed == 0
        assert stats.pages_processed == 0
        assert stats.matches_found == 0
        assert stats.errors == []

    def test_error_tracking(self):
        stats = ProcessingStats()
        stats.errors.append("Error 1")
        stats.errors.append("Error 2")
        assert len(stats.errors) == 2


class TestSetupLogging:
    """Tests for logging setup."""

    def test_setup_logging_returns_logger(self):
        logger = setup_logging(verbose=False)
        assert logger is not None

    def test_verbose_mode(self):
        import logging
        logger = setup_logging(verbose=True)
        assert logger.level == logging.DEBUG
