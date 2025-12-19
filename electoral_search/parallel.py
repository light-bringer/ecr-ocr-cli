"""
Parallel processing utilities for multi-core PDF processing.

Provides safe parallel execution with proper resource management.
"""

import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Callable, Any, Optional

from .config import ProcessingStats
from .types import SearchResult

logger = logging.getLogger(__name__)


def get_optimal_workers(max_workers: Optional[int] = None) -> int:
    """
    Calculate optimal number of worker processes.

    Args:
        max_workers: Maximum workers to use (None = auto-detect)

    Returns:
        Optimal number of workers (at least 1, at most CPU count)
    """
    if max_workers is not None:
        return max(1, min(max_workers, mp.cpu_count()))

    # Use CPU count - 1 to leave one core for system
    cpu_count = mp.cpu_count()
    optimal = max(1, cpu_count - 1)

    logger.info(f"Auto-detected {cpu_count} CPUs, using {optimal} workers")
    return optimal


def process_pdfs_parallel(
    pdf_files: List[Path],
    process_func: Callable[[Path], List[SearchResult]],
    max_workers: Optional[int] = None,
    stats: Optional[ProcessingStats] = None
) -> List[SearchResult]:
    """
    Process multiple PDFs in parallel using multiprocessing.

    Args:
        pdf_files: List of PDF file paths to process
        process_func: Function to process a single PDF
        max_workers: Maximum parallel workers (None = auto-detect)
        stats: Optional ProcessingStats for tracking

    Returns:
        Combined list of all search results

    Example:
        >>> def process_one(pdf_path):
        ...     return process_pdf(pdf_path, names, threshold, stats)
        >>> results = process_pdfs_parallel(pdf_files, process_one)
    """
    if not pdf_files:
        logger.warning("No PDF files to process")
        return []

    workers = get_optimal_workers(max_workers)
    all_results: List[SearchResult] = []

    logger.info(f"Processing {len(pdf_files)} PDFs with {workers} workers")

    # Use ProcessPoolExecutor for parallel processing
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_pdf = {
            executor.submit(process_func, pdf_path): pdf_path
            for pdf_path in pdf_files
        }

        # Process completed tasks as they finish
        for future in as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]

            try:
                results = future.result()
                all_results.extend(results)

                logger.info(
                    f"Completed {pdf_path.name}: {len(results)} matches"
                )

            except Exception as e:
                logger.error(f"Failed to process {pdf_path.name}: {e}")
                if stats:
                    stats.files_failed += 1
                    stats.errors.append(f"{pdf_path.name}: {str(e)}")

    logger.info(
        f"Parallel processing complete: {len(all_results)} total matches"
    )

    return all_results


def process_single_pdf_wrapper(args: tuple) -> List[SearchResult]:
    """
    Wrapper function for multiprocessing with multiple arguments.

    This is needed because ProcessPoolExecutor.map() requires a single argument.

    Args:
        args: Tuple of (pdf_path, search_names, threshold, stats)

    Returns:
        List of search results
    """
    from .ocr import process_pdf

    pdf_path, search_names, threshold, stats = args

    try:
        return process_pdf(pdf_path, search_names, threshold, stats)
    except Exception as e:
        logger.error(f"Error in wrapper for {pdf_path}: {e}")
        return []
