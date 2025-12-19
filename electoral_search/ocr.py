"""
OCR and PDF processing functionality.

Handles PDF to image conversion and Tesseract OCR processing.
"""

import logging
from pathlib import Path
from typing import List

import pytesseract
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError

from .config import DPI, OCR_LANG, OCR_CONFIG, MAX_PDF_PAGES, ProcessingStats
from .types import SearchResult
from .validation import validate_pdf_file
from .text_processing import extract_voter_blocks, fuzzy_match

logger = logging.getLogger(__name__)


def process_pdf(
    pdf_path: Path,
    search_names: List[str],
    threshold: int,
    stats: ProcessingStats
) -> List[SearchResult]:
    """
    Process a PDF file and search for matching names using OCR.

    Args:
        pdf_path: Path to PDF file to process
        search_names: List of names to search for
        threshold: Fuzzy match threshold (0-100)
        stats: ProcessingStats object to track progress

    Returns:
        List of SearchResult dictionaries containing matches

    Raises:
        ValueError: If file validation fails
        RuntimeError: If OCR processing fails critically
    """
    results: List[SearchResult] = []

    try:
        # Validate PDF file
        validate_pdf_file(pdf_path)

        logger.info(f"Processing PDF: {pdf_path.name}")

        # Convert PDF to images with error handling
        try:
            images = convert_from_path(
                str(pdf_path),
                dpi=DPI,
                thread_count=1,  # Limit resource usage
                use_pdftocairo=False
            )
        except PDFPageCountError:
            raise ValueError(f"Invalid PDF page count: {pdf_path.name}")
        except PDFSyntaxError:
            raise ValueError(f"Corrupted PDF file: {pdf_path.name}")
        except Exception as e:
            raise RuntimeError(f"Failed to convert PDF to images: {e}")

        # Check page limit
        if len(images) > MAX_PDF_PAGES:
            logger.warning(
                f"PDF has {len(images)} pages, limiting to {MAX_PDF_PAGES}"
            )
            images = images[:MAX_PDF_PAGES]

        # Process each page
        for page_no, image in enumerate(images, start=1):
            try:
                # Perform OCR
                text = pytesseract.image_to_string(
                    image,
                    lang=OCR_LANG,
                    config=OCR_CONFIG,
                    timeout=30  # Timeout per page
                )

                stats.pages_processed += 1

                # Extract voter information
                voters = extract_voter_blocks(text)
                logger.debug(f"Page {page_no}: Extracted {len(voters)} voters")

                # Search for matches
                for voter in voters:
                    for query in search_names:
                        if fuzzy_match(voter["name"], query, threshold):
                            result = SearchResult(
                                file=pdf_path.name,
                                page=page_no,
                                name=voter["name"],
                                father=voter["father"],
                            )
                            results.append(result)
                            stats.matches_found += 1
                            logger.info(
                                f"Match found: {voter['name']} on page {page_no}"
                            )

            except pytesseract.TesseractNotFoundError:
                raise RuntimeError(
                    "Tesseract not found. Install: apt-get install tesseract-ocr tesseract-ocr-ben"
                )
            except RuntimeError as e:
                if "timeout" in str(e).lower():
                    logger.warning(f"OCR timeout on page {page_no}, skipping")
                    continue
                raise
            except Exception as e:
                logger.error(f"Error processing page {page_no}: {e}")
                continue
            finally:
                # Cleanup image to free memory
                if image:
                    try:
                        image.close()
                    except Exception:
                        pass

        stats.files_processed += 1
        return results

    except (ValueError, RuntimeError) as e:
        # Re-raise validation and critical errors
        stats.files_failed += 1
        stats.errors.append(f"{pdf_path.name}: {str(e)}")
        raise
    except Exception as e:
        # Log unexpected errors but don't crash
        error_msg = f"Unexpected error processing {pdf_path.name}: {e}"
        logger.error(error_msg)
        stats.files_failed += 1
        stats.errors.append(error_msg)
        return results
