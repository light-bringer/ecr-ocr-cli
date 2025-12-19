"""
Export utilities for search results.

Supports multiple export formats: JSON, CSV.
"""

import csv
import json
import logging
from pathlib import Path
from typing import List

from .types import SearchResult

logger = logging.getLogger(__name__)


def export_to_json(results: List[SearchResult], output_path: Path) -> None:
    """
    Export results to JSON file.

    Args:
        results: List of search results
        output_path: Path to output JSON file

    Raises:
        IOError: If file cannot be written
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {len(results)} results to JSON: {output_path}")

    except Exception as e:
        logger.error(f"Failed to export JSON: {e}")
        raise IOError(f"Failed to export JSON: {e}")


def export_to_csv(results: List[SearchResult], output_path: Path) -> None:
    """
    Export results to CSV file.

    Args:
        results: List of search results
        output_path: Path to output CSV file

    Raises:
        IOError: If file cannot be written
    """
    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            if not results:
                # Write header only for empty results
                writer = csv.DictWriter(
                    f, fieldnames=["file", "page", "name", "father"]
                )
                writer.writeheader()
                logger.info(f"Exported 0 results to CSV: {output_path}")
                return

            # Write header and rows
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(results)

        logger.info(f"Exported {len(results)} results to CSV: {output_path}")

    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        raise IOError(f"Failed to export CSV: {e}")


def export_results(
    results: List[SearchResult], output_path: Path, format: str = "auto"
) -> None:
    """
    Export results to file with auto-detection of format.

    Args:
        results: List of search results
        output_path: Path to output file
        format: Export format ('json', 'csv', or 'auto')

    Raises:
        ValueError: If format is unsupported
        IOError: If file cannot be written
    """
    # Auto-detect format from extension
    if format == "auto":
        suffix = output_path.suffix.lower()
        if suffix == ".json":
            format = "json"
        elif suffix == ".csv":
            format = "csv"
        else:
            raise ValueError(
                f"Cannot auto-detect format from extension '{suffix}'. "
                f"Use .json or .csv, or specify format explicitly."
            )

    # Export based on format
    if format == "json":
        export_to_json(results, output_path)
    elif format == "csv":
        export_to_csv(results, output_path)
    else:
        raise ValueError(
            f"Unsupported export format: {format}. Use 'json' or 'csv'."
        )
