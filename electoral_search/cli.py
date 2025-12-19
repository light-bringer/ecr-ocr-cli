"""
Command-line interface for electoral search tool.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeRemainingColumn
)

from .config import (
    FUZZY_THRESHOLD_DEFAULT,
    MAX_NAMES_FILE_SIZE_MB,
    MAX_SEARCH_NAMES,
    ProcessingStats,
    setup_logging
)
from .types import SearchResult
from .validation import validate_path_security
from .ocr import process_pdf
from .parallel import get_optimal_workers
from .cache import ResultCache
from .export import export_results

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer(help="Search Bengali Electoral Roll PDFs")


# Module-level worker function for multiprocessing (must be picklable)
def _process_pdf_worker(
    args: Tuple[Path, List[str], int, Optional[str], bool, bool, float]
) -> List[SearchResult]:
    """
    Worker function for parallel PDF processing.

    This function is defined at module level to be picklable for
    multiprocessing. Each worker process creates its own cache instance.

    Args:
        args: Tuple of (pdf_path, search_names, threshold, cache_dir,
              use_cache, box_level, min_confidence)

    Returns:
        List of search results
    """
    (
        pdf_path, search_names, threshold, cache_dir,
        use_cache, box_level, min_confidence
    ) = args

    # Create cache instance in worker process if needed
    cache = None
    if use_cache:
        cache_path = Path(cache_dir) if cache_dir else None
        cache = ResultCache(cache_dir=cache_path)

    # Try cache first
    if cache:
        cached_results = cache.get(pdf_path, search_names, threshold)
        if cached_results is not None:
            return cached_results

    # Create a local stats object for this worker
    worker_stats = ProcessingStats()

    # Process PDF
    results = process_pdf(
        pdf_path, search_names, threshold, worker_stats,
        box_level, min_confidence
    )

    # Cache results
    if cache:
        cache.set(pdf_path, search_names, threshold, results)

    return results


@app.command()
def search(
    directory: str = typer.Argument(..., help="Directory containing PDFs"),
    names_file: str = typer.Option(
        ..., "--names-file", "-n", help="File with Bengali names (UTF-8)"
    ),
    threshold: int = typer.Option(
        FUZZY_THRESHOLD_DEFAULT,
        "--threshold", "-t",
        help="Fuzzy match threshold (0-100)",
        min=0,
        max=100
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Save results to file (JSON or CSV based on extension)"
    ),
    output_format: Optional[str] = typer.Option(
        "auto", "--format", "-f", help="Output format: json, csv, or auto (default: auto)"
    ),
    parallel: bool = typer.Option(
        True, "--parallel/--no-parallel", help="Enable parallel processing (default: True)"
    ),
    workers: Optional[int] = typer.Option(
        None, "--workers", "-w", help="Number of parallel workers (default: auto)"
    ),
    use_cache: bool = typer.Option(
        True, "--cache/--no-cache", help="Enable result caching (default: True)"
    ),
    cache_dir: Optional[str] = typer.Option(
        None, "--cache-dir", help="Cache directory (default: ~/.electoral_search_cache)"
    ),
    clear_cache: bool = typer.Option(
        False,
        "--clear-cache",
        help="Clear cache before processing"
    ),
    box_level: bool = typer.Option(
        False,
        "--box-level",
        help="Enable box-level OCR with bounding boxes"
    ),
    min_confidence: float = typer.Option(
        60.0,
        "--min-confidence",
        help="Minimum OCR confidence threshold (0-100)",
        min=0,
        max=100
    ),
):
    """
    Search scanned electoral roll PDFs for Bengali names using OCR.

    Processes PDF files in the specified directory, performs OCR with Tesseract,
    and uses fuzzy matching to find names from the search list.

    Features:
        - Multi-core parallel processing for faster execution
        - Result caching to avoid reprocessing
        - CSV and JSON export formats
        - Progress bars and statistics

    Examples:
        # Basic search
        electoral_search search /path/to/pdfs --names-file names.txt

        # Parallel processing with 4 workers
        electoral_search search /path/to/pdfs -n names.txt --workers 4

        # Export to CSV
        electoral_search search /path/to/pdfs -n names.txt -o results.csv

        # Disable cache for fresh results
        electoral_search search /path/to/pdfs -n names.txt --no-cache

    Requirements:
        - Tesseract OCR (tesseract-ocr)
        - Bengali language pack (tesseract-ocr-ben)
        - Poppler utils (for pdf2image)

    Box-Level OCR:
        Use --box-level to extract bounding box coordinates
        and OCR confidence scores for each match. This
        enables spatial analysis and filtering by confidence.
    """
    # Setup logging
    global logger
    logger = setup_logging(verbose)

    logger.info("Starting electoral roll search")

    stats = ProcessingStats()

    try:
        # Validate and resolve directory path
        try:
            dir_path = validate_path_security(directory)
            if not dir_path.exists():
                console.print(f"[red]Directory not found: {directory}[/red]")
                raise typer.Exit(1)
            if not dir_path.is_dir():
                console.print(f"[red]Path is not a directory: {directory}[/red]")
                raise typer.Exit(1)
        except ValueError as e:
            console.print(f"[red]Invalid directory: {e}[/red]")
            raise typer.Exit(1)

        # Validate and load names file
        try:
            names_path = validate_path_security(names_file)
            if not names_path.exists():
                console.print(f"[red]Names file not found: {names_file}[/red]")
                raise typer.Exit(1)

            # Check file size
            size_mb = names_path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_NAMES_FILE_SIZE_MB:
                console.print(
                    f"[red]Names file too large: {size_mb:.1f}MB "
                    f"(max: {MAX_NAMES_FILE_SIZE_MB}MB)[/red]"
                )
                raise typer.Exit(1)

            with open(names_path, encoding="utf-8") as f:
                search_names = [line.strip() for line in f if line.strip()]

        except UnicodeDecodeError:
            console.print("[red]Names file must be UTF-8 encoded[/red]")
            raise typer.Exit(1)
        except ValueError as e:
            console.print(f"[red]Invalid names file: {e}[/red]")
            raise typer.Exit(1)

        if not search_names:
            console.print("[red]No names provided in file[/red]")
            raise typer.Exit(1)

        if len(search_names) > MAX_SEARCH_NAMES:
            console.print(
                f"[yellow]Warning: {len(search_names)} names provided, "
                f"limiting to {MAX_SEARCH_NAMES}[/yellow]"
            )
            search_names = search_names[:MAX_SEARCH_NAMES]

        logger.info(f"Loaded {len(search_names)} names to search")

        # Initialize cache if enabled
        cache = None
        if use_cache:
            cache_path = Path(cache_dir) if cache_dir else None
            cache = ResultCache(cache_dir=cache_path)

            if clear_cache:
                cleared = cache.clear()
                console.print(f"[yellow]Cleared {cleared} cache entries[/yellow]")
                logger.info(f"Cleared {cleared} cache entries")

            # Show cache stats
            cache_stats = cache.get_stats()
            logger.info(
                f"Cache: {cache_stats['total_entries']} entries, "
                f"{cache_stats['total_size_mb']:.2f}MB"
            )

        # Collect PDF files
        pdf_files: List[Path] = []
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(Path(root) / file)

        if not pdf_files:
            console.print(f"[yellow]No PDF files found in {directory}[/yellow]")
            raise typer.Exit(0)

        logger.info(f"Found {len(pdf_files)} PDF files to process")

        # Display processing mode
        if parallel:
            num_workers = get_optimal_workers(workers)
            console.print(
                f"[cyan]Processing {len(pdf_files)} PDFs with "
                f"{num_workers} workers (parallel mode)[/cyan]"
            )
        else:
            console.print(
                f"[cyan]Processing {len(pdf_files)} PDFs (sequential mode)[/cyan]"
            )

        # Process PDFs with progress bar
        all_results: List[SearchResult] = []

        # Define local wrapper for sequential processing
        def process_with_cache(pdf_path: Path) -> List[SearchResult]:
            """Process PDF with optional caching (sequential mode only)."""
            # Try cache first
            if cache:
                cached_results = cache.get(pdf_path, search_names, threshold)
                if cached_results is not None:
                    stats.files_processed += 1
                    return cached_results

            # Process PDF
            results = process_pdf(
                pdf_path, search_names, threshold, stats,
                box_level, min_confidence
            )

            # Cache results
            if cache:
                cache.set(pdf_path, search_names, threshold, results)

            return results

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Processing {len(pdf_files)} PDFs...",
                total=len(pdf_files)
            )

            if parallel and len(pdf_files) > 1:
                # Parallel processing using module-level worker
                from concurrent.futures import ProcessPoolExecutor, as_completed

                num_workers = get_optimal_workers(workers)

                # Prepare arguments for each worker
                worker_args = [
                    (
                        pdf, search_names, threshold, cache_dir,
                        use_cache, box_level, min_confidence
                    )
                    for pdf in pdf_files
                ]

                with ProcessPoolExecutor(max_workers=num_workers) as executor:
                    future_to_pdf = {
                        executor.submit(_process_pdf_worker, args): args[0]
                        for args in worker_args
                    }

                    for future in as_completed(future_to_pdf):
                        pdf_path = future_to_pdf[future]
                        progress.update(
                            task,
                            description=f"Processing {pdf_path.name}..."
                        )

                        try:
                            results = future.result()
                            all_results.extend(results)
                            stats.files_processed += 1
                            stats.matches_found += len(results)

                        except (ValueError, RuntimeError) as e:
                            logger.error(
                                f"Failed to process {pdf_path.name}: {e}"
                            )
                            stats.files_failed += 1
                            stats.errors.append(f"{pdf_path.name}: {str(e)}")

                        except Exception as e:
                            logger.error(f"Unexpected error on {pdf_path.name}: {e}")
                            stats.files_failed += 1
                            stats.errors.append(f"{pdf_path.name}: {str(e)}")

                        finally:
                            progress.advance(task)

            else:
                # Sequential processing
                for pdf_path in pdf_files:
                    progress.update(
                        task,
                        description=f"Processing {pdf_path.name}..."
                    )

                    try:
                        results = process_with_cache(pdf_path)
                        all_results.extend(results)

                    except (ValueError, RuntimeError) as e:
                        console.print(f"[red]Error: {e}[/red]")
                        logger.error(f"Failed to process {pdf_path.name}: {e}")
                        continue

                    except Exception as e:
                        console.print(f"[red]Unexpected error: {e}[/red]")
                        logger.error(f"Unexpected error on {pdf_path.name}: {e}")
                        continue

                    finally:
                        progress.advance(task)

        # Display results
        if all_results:
            table = Table(
                title=f"Electoral Roll Matches ({len(all_results)} found)"
            )
            table.add_column("PDF File", style="cyan")
            table.add_column("Page", justify="right", style="magenta")
            table.add_column("Name", style="green")
            table.add_column("Father / Guardian", style="yellow")

            # Add confidence column if box-level mode
            if box_level:
                table.add_column(
                    "Confidence",
                    justify="right",
                    style="blue"
                )

            for result in all_results:
                row_data = [
                    result["file"],
                    str(result["page"]),
                    result["name"],
                    result["father"]
                ]

                # Add confidence if box-level mode
                if box_level and "confidence" in result:
                    conf = result["confidence"]
                    row_data.append(f"{conf:.1f}%" if conf else "N/A")
                elif box_level:
                    row_data.append("N/A")

                table.add_row(*row_data)

            console.print(table)

            # Export results if requested
            if output:
                try:
                    output_path = Path(output)
                    export_results(
                        all_results, output_path, output_format
                    )
                    console.print(f"[green]Results saved to {output}[/green]")
                except Exception as e:
                    console.print(
                        f"[red]Failed to export results: {e}[/red]"
                    )
                    logger.error(f"Export failed: {e}")

        else:
            console.print("[yellow]No matches found[/yellow]")

        # Display statistics
        console.print("\n[bold]Processing Statistics:[/bold]")
        console.print(f"  Files processed: {stats.files_processed}")
        console.print(f"  Files failed: {stats.files_failed}")
        console.print(f"  Pages processed: {stats.pages_processed}")
        console.print(f"  Matches found: {stats.matches_found}")

        if cache and use_cache:
            cache_stats = cache.get_stats()
            console.print(f"\n[bold]Cache Statistics:[/bold]")
            console.print(f"  Cache entries: {cache_stats['total_entries']}")
            console.print(f"  Cache size: {cache_stats['total_size_mb']:.2f}MB")
            console.print(f"  Cache location: {cache_stats['cache_dir']}")

        if stats.errors:
            console.print(f"\n[yellow]Errors ({len(stats.errors)}):[/yellow]")
            for error in stats.errors[:10]:  # Show first 10 errors
                console.print(f"  - {error}")
            if len(stats.errors) > 10:
                console.print(f"  ... and {len(stats.errors) - 10} more")

        logger.info("Search complete")

    except KeyboardInterrupt:
        console.print("\n[yellow]Search interrupted by user[/yellow]")
        logger.info("Search interrupted")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        logger.exception("Fatal error during search")
        raise typer.Exit(1)


def main():
    """Entry point for the CLI application."""
    app()
