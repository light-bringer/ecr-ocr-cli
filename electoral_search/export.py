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

    Automatically includes bbox and confidence fields if present.

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
        raise OSError(f"Failed to export JSON: {e}")


def export_to_csv(results: List[SearchResult], output_path: Path) -> None:
    """
    Export results to CSV file.

    Automatically includes bbox columns if bbox data is present:
    - bbox_left, bbox_top, bbox_width, bbox_height, confidence

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
                writer = csv.DictWriter(f, fieldnames=["file", "page", "name", "father"])
                writer.writeheader()
                logger.info(f"Exported 0 results to CSV: {output_path}")
                return

            # Determine if we have bbox data
            has_bbox = any("bbox" in result for result in results)
            has_confidence = any("confidence" in result for result in results)

            # Prepare fieldnames
            fieldnames = ["file", "page", "name", "father"]
            if has_bbox:
                fieldnames.extend(["bbox_left", "bbox_top", "bbox_width", "bbox_height"])
            if has_confidence:
                fieldnames.append("confidence")

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Write rows with bbox data expanded
            for result in results:
                row = {
                    "file": result["file"],
                    "page": result["page"],
                    "name": result["name"],
                    "father": result["father"],
                }

                # Add bbox columns if present
                if has_bbox and "bbox" in result and result["bbox"]:
                    bbox = result["bbox"]
                    row["bbox_left"] = bbox["left"]
                    row["bbox_top"] = bbox["top"]
                    row["bbox_width"] = bbox["width"]
                    row["bbox_height"] = bbox["height"]
                elif has_bbox:
                    # Empty bbox data
                    row["bbox_left"] = ""
                    row["bbox_top"] = ""
                    row["bbox_width"] = ""
                    row["bbox_height"] = ""

                # Add confidence if present
                if has_confidence:
                    row["confidence"] = (
                        f"{result['confidence']:.2f}" if "confidence" in result else ""
                    )

                writer.writerow(row)

        logger.info(f"Exported {len(results)} results to CSV: {output_path}")

    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        raise OSError(f"Failed to export CSV: {e}")


def export_results(results: List[SearchResult], output_path: Path, format: str = "auto") -> None:
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
        raise ValueError(f"Unsupported export format: {format}. Use 'json' or 'csv'.")
