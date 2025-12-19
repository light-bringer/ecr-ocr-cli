"""
Command-line interface for electoral search tool.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.table import Table

from .cache import ResultCache
from .config import (
    FUZZY_THRESHOLD_DEFAULT,
    MAX_NAMES_FILE_SIZE_MB,
    MAX_SEARCH_NAMES,
    ProcessingStats,
    setup_logging,
)
from .export import export_results
from .ocr import process_pdf
from .parallel import get_optimal_workers
from .types import SearchResult
from .validation import validate_path_security

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer(help="Search Bengali Electoral Roll PDFs")


# Module-level worker function for multiprocessing (must be picklable)
def _process_pdf_worker(
    args: Tuple[Path, List[str], int, Optional[str], bool, bool, float],
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
    (pdf_path, search_names, threshold, cache_dir, use_cache, box_level, min_confidence) = args

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
        pdf_path, search_names, threshold, worker_stats, box_level, min_confidence
    )

    # Cache results
    if cache:
        cache.set(pdf_path, search_names, threshold, results)

    return results


def _validate_inputs(directory: str, names_file: str) -> Tuple[Path, Path]:
    """Validate input paths for security and existence."""
    # Validate directory
    try:
        dir_path = validate_path_security(directory)
        if not dir_path.exists():
            console.print(f"[red]Directory not found: {directory}[/red]")
            raise typer.Exit(1)
        if not dir_path.is_dir():
            console.print(f"[red]Path is not a directory: {directory}[/red]")
            raise typer.Exit(1) from None
    except ValueError as e:
        console.print(f"[red]Invalid directory: {e}[/red]")
        raise typer.Exit(1) from None

    # Validate names file
    try:
        names_path = validate_path_security(names_file)
        if not names_path.exists():
            console.print(f"[red]Names file not found: {names_file}[/red]")
            raise typer.Exit(1) from None
    except ValueError as e:
        console.print(f"[red]Invalid names file: {e}[/red]")
        raise typer.Exit(1) from None

    return dir_path, names_path


def _load_search_names(names_path: Path) -> List[str]:
    """Load and validate search names from file."""
    # Check file size
    size_mb = names_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_NAMES_FILE_SIZE_MB:
        console.print(
            f"[red]Names file too large: {size_mb:.1f}MB "
            f"(max: {MAX_NAMES_FILE_SIZE_MB}MB)[/red]"
        )
        raise typer.Exit(1) from None

    try:
        with open(names_path, encoding="utf-8") as f:
            search_names = [line.strip() for line in f if line.strip()]
    except UnicodeDecodeError:
        console.print("[red]Names file must be UTF-8 encoded[/red]")
        raise typer.Exit(1) from None

    if not search_names:
        console.print("[red]No names provided in file[/red]")
        raise typer.Exit(1) from None

    if len(search_names) > MAX_SEARCH_NAMES:
        console.print(
            f"[yellow]Warning: {len(search_names)} names provided, "
            f"limiting to {MAX_SEARCH_NAMES}[/yellow]"
        )
        search_names = search_names[:MAX_SEARCH_NAMES]

    logger.info(f"Loaded {len(search_names)} names to search")
    return search_names


def _find_targets(directory: Path) -> List[Path]:
    """Find all PDF files in the directory."""
    pdf_files: List[Path] = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(Path(root) / file)

    if not pdf_files:
        console.print(f"[yellow]No PDF files found in {directory}[/yellow]")
        raise typer.Exit(0)

    logger.info(f"Found {len(pdf_files)} PDF files to process")
    return pdf_files


def _process_sequential(
    pdf_files: List[Path],
    search_names: List[str],
    threshold: int,
    stats: ProcessingStats,
    cache: Optional[ResultCache],
    box_level: bool,
    min_confidence: float,
) -> List[SearchResult]:
    """Process PDFs sequentially."""
    all_results: List[SearchResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Processing {len(pdf_files)} PDFs...", total=len(pdf_files))

        for pdf_path in pdf_files:
            progress.update(task, description=f"Processing {pdf_path.name}...")

            try:
                # Try cache first
                if cache:
                    cached = cache.get(pdf_path, search_names, threshold)
                    if cached is not None:
                        stats.files_processed += 1
                        all_results.extend(cached)
                        progress.advance(task)
                        continue

                # Process PDF
                results = process_pdf(
                    pdf_path, search_names, threshold, stats, box_level, min_confidence
                )
                all_results.extend(results)

                # Cache results
                if cache:
                    cache.set(pdf_path, search_names, threshold, results)

            except (ValueError, RuntimeError) as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"Failed to process {pdf_path.name}: {e}")
            except Exception as e:
                console.print(f"[red]Unexpected error: {e}[/red]")
                logger.error(f"Unexpected error on {pdf_path.name}: {e}")
            finally:
                progress.advance(task)

    return all_results


def _process_parallel(
    pdf_files: List[Path],
    search_names: List[str],
    threshold: int,
    stats: ProcessingStats,
    workers: Optional[int],
    cache_dir: Optional[str],
    use_cache: bool,
    box_level: bool,
    min_confidence: float,
) -> List[SearchResult]:
    """Process PDFs in parallel."""
    # Local import to avoid circular dependency issues
    from concurrent.futures import ProcessPoolExecutor, as_completed

    num_workers = get_optimal_workers(workers)
    console.print(
        f"[cyan]Processing {len(pdf_files)} PDFs with "
        f"{num_workers} workers (parallel mode)[/cyan]"
    )

    all_results: List[SearchResult] = []
    worker_args = [
        (pdf, search_names, threshold, cache_dir, use_cache, box_level, min_confidence)
        for pdf in pdf_files
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Processing {len(pdf_files)} PDFs...", total=len(pdf_files))

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_pdf = {
                executor.submit(_process_pdf_worker, args): args[0] for args in worker_args
            }

            for future in as_completed(future_to_pdf):
                pdf_path = future_to_pdf[future]
                progress.update(task, description=f"Processing {pdf_path.name}...")

                try:
                    results = future.result()
                    all_results.extend(results)
                    stats.files_processed += 1
                    stats.matches_found += len(results)
                except (ValueError, RuntimeError) as e:
                    logger.error(f"Failed to process {pdf_path.name}: {e}")
                    stats.files_failed += 1
                    stats.errors.append(f"{pdf_path.name}: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error on {pdf_path.name}: {e}")
                    stats.files_failed += 1
                    stats.errors.append(f"{pdf_path.name}: {str(e)}")
                finally:
                    progress.advance(task)

    return all_results


def _execute_processing(
    pdf_files: List[Path],
    search_names: List[str],
    threshold: int,
    stats: ProcessingStats,
    parallel: bool,
    workers: Optional[int],
    cache: Optional[ResultCache],
    cache_dir: Optional[str],
    use_cache: bool,
    box_level: bool,
    min_confidence: float,
) -> List[SearchResult]:
    """Execute the appropriate processing strategy."""
    if parallel and len(pdf_files) > 1:
        return _process_parallel(
            pdf_files,
            search_names,
            threshold,
            stats,
            workers,
            cache_dir,
            use_cache,
            box_level,
            min_confidence,
        )
    else:
        if not parallel:
            console.print(f"[cyan]Processing {len(pdf_files)} PDFs (sequential mode)[/cyan]")
        return _process_sequential(
            pdf_files, search_names, threshold, stats, cache, box_level, min_confidence
        )


def _display_results(
    all_results: List[SearchResult],
    stats: ProcessingStats,
    box_level: bool,
    output: Optional[str],
    output_format: str,
    cache: Optional[ResultCache] = None,
    use_cache: bool = False,
) -> None:
    """Display final table, stats, and export results."""
    # 1. Results Table
    if all_results:
        table = Table(title=f"Electoral Roll Matches ({len(all_results)} found)")
        table.add_column("PDF File", style="cyan")
        table.add_column("Page", justify="right", style="magenta")
        table.add_column("Name", style="green")
        table.add_column("Father / Guardian", style="yellow")

        if box_level:
            table.add_column("Confidence", justify="right", style="blue")

        for result in all_results:
            row_data = [result["file"], str(result["page"]), result["name"], result["father"]]
            if box_level:
                conf = result.get("confidence")
                # Handle possible None confidence or missing key
                row_data.append(f"{conf:.1f}%" if conf is not None else "N/A")
            table.add_row(*row_data)

        console.print(table)

        # Export results if requested
        if output:
            try:
                output_path = Path(output)
                export_results(all_results, output_path, output_format)
                console.print(f"[green]Results saved to {output}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to export results: {e}[/red]")
                logger.error(f"Export failed: {e}")

    else:
        console.print("[yellow]No matches found[/yellow]")

    # 2. Print statistics
    _print_stats(stats, cache, use_cache)


def _print_stats(
    stats: ProcessingStats,
    cache: Optional[ResultCache] = None,
    use_cache: bool = False,
) -> None:
    """Print processing and cache statistics."""
    console.print("\n[bold]Processing Statistics:[/bold]")
    console.print(f"  Files processed: {stats.files_processed}")
    console.print(f"  Files failed: {stats.files_failed}")
    console.print(f"  Pages processed: {stats.pages_processed}")
    console.print(f"  Matches found: {stats.matches_found}")

    if cache and use_cache:
        cache_stats = cache.get_stats()
        console.print("\n[bold]Cache Statistics:[/bold]")
        console.print(f"  Cache entries: {cache_stats['total_entries']}")
        console.print(f"  Cache size: {cache_stats['total_size_mb']:.2f}MB")
        console.print(f"  Cache location: {cache_stats['cache_dir']}")

    if stats.errors:
        console.print(f"\n[yellow]Errors ({len(stats.errors)}):[/yellow]")
        for error in stats.errors[:10]:
            console.print(f"  - {error}")
        if len(stats.errors) > 10:
            console.print(f"  ... and {len(stats.errors) - 10} more")


@app.command()
def search(
    directory: str = typer.Argument(..., help="Directory containing PDFs"),
    names_file: str = typer.Option(
        ..., "--names-file", "-n", help="File with Bengali names (UTF-8)"
    ),
    threshold: int = typer.Option(
        FUZZY_THRESHOLD_DEFAULT,
        "--threshold",
        "-t",
        help="Fuzzy match threshold (0-100)",
        min=0,
        max=100,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
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
    clear_cache: bool = typer.Option(False, "--clear-cache", help="Clear cache before processing"),
    box_level: bool = typer.Option(
        False, "--box-level", help="Enable box-level OCR with bounding boxes"
    ),
    min_confidence: float = typer.Option(
        60.0, "--min-confidence", help="Minimum OCR confidence threshold (0-100)", min=0, max=100
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
        # 1. Validation and Loading
        dir_path, names_path = _validate_inputs(directory, names_file)
        search_names = _load_search_names(names_path)

        # 2. Cache Initialization
        cache = None
        if use_cache:
            cache_path = Path(cache_dir) if cache_dir else None
            cache = ResultCache(cache_dir=cache_path)
            if clear_cache:
                cleared = cache.clear()
                console.print(f"[yellow]Cleared {cleared} cache entries[/yellow]")
                logger.info(f"Cleared {cleared} cache entries")

            # Log initial cache stats
            c_stats = cache.get_stats()
            logger.info(f"Cache: {c_stats['total_entries']} entries")

        # 3. Discovery
        pdf_files = _find_targets(dir_path)

        # 4. Processing
        all_results = _execute_processing(
            pdf_files,
            search_names,
            threshold,
            stats,
            parallel,
            workers,
            cache,
            cache_dir,
            use_cache,
            box_level,
            min_confidence,
        )

        # 5. Display and Export
        _display_results(all_results, stats, box_level, output, output_format, cache, use_cache)

        logger.info("Search complete")

    except KeyboardInterrupt:
        console.print("\n[yellow]Search interrupted by user[/yellow]")
        logger.info("Search interrupted")
        raise typer.Exit(130) from None
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        logger.exception("Fatal error during search")
        raise typer.Exit(1) from None


def main():
    """Entry point for the CLI application."""
    app()
