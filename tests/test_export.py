"""Tests for export module."""

import csv
import json
from pathlib import Path
import pytest

from electoral_search.export import export_to_json, export_to_csv, export_results


class TestExportToJson:
    """Tests for JSON export."""

    def test_export_json(self, tmp_path):
        """Test exporting to JSON."""
        results = [
            {"file": "test.pdf", "page": 1, "name": "রহিম", "father": "করিম"}
        ]

        output_file = tmp_path / "results.json"
        export_to_json(results, output_file)

        assert output_file.exists()

        with open(output_file, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == results

    def test_export_empty_json(self, tmp_path):
        """Test exporting empty results to JSON."""
        output_file = tmp_path / "empty.json"
        export_to_json([], output_file)

        assert output_file.exists()

        with open(output_file, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == []


class TestExportToCsv:
    """Tests for CSV export."""

    def test_export_csv(self, tmp_path):
        """Test exporting to CSV."""
        results = [
            {"file": "test.pdf", "page": 1, "name": "রহিম", "father": "করিম"}
        ]

        output_file = tmp_path / "results.csv"
        export_to_csv(results, output_file)

        assert output_file.exists()

        with open(output_file, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["name"] == "রহিম"

    def test_export_empty_csv(self, tmp_path):
        """Test exporting empty results to CSV."""
        output_file = tmp_path / "empty.csv"
        export_to_csv([], output_file)

        assert output_file.exists()

        # Should have header but no data
        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        assert "file,page,name,father" in content


class TestExportResults:
    """Tests for auto-format export."""

    def test_auto_detect_json(self, tmp_path):
        """Test auto-detecting JSON format."""
        results = [{"file": "test.pdf", "page": 1, "name": "test", "father": "test"}]
        output_file = tmp_path / "results.json"

        export_results(results, output_file, format="auto")

        assert output_file.exists()
        with open(output_file) as f:
            loaded = json.load(f)
        assert loaded == results

    def test_auto_detect_csv(self, tmp_path):
        """Test auto-detecting CSV format."""
        results = [{"file": "test.pdf", "page": 1, "name": "test", "father": "test"}]
        output_file = tmp_path / "results.csv"

        export_results(results, output_file, format="auto")

        assert output_file.exists()

    def test_unsupported_format(self, tmp_path):
        """Test unsupported format raises error."""
        results = [{"file": "test.pdf", "page": 1, "name": "test", "father": "test"}]
        output_file = tmp_path / "results.xml"

        with pytest.raises(ValueError, match="Cannot auto-detect"):
            export_results(results, output_file, format="auto")

    def test_explicit_format(self, tmp_path):
        """Test explicit format specification."""
        results = [{"file": "test.pdf", "page": 1, "name": "test", "father": "test"}]
        output_file = tmp_path / "results.txt"

        export_results(results, output_file, format="json")

        assert output_file.exists()
