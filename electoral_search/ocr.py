"""
OCR and PDF processing functionality.

Handles PDF to image conversion and Tesseract OCR processing.
"""

import logging
from pathlib import Path
from typing import List, Optional

import pytesseract
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError
from pytesseract import Output

from .config import DPI, MAX_PDF_PAGES, OCR_CONFIG, OCR_LANG, ProcessingStats
from .text_processing import extract_voter_blocks, extract_voter_blocks_with_boxes, fuzzy_match
from .types import BoundingBox, OCRWord, SearchResult
from .validation import validate_pdf_file

logger = logging.getLogger(__name__)


def extract_ocr_data(image, min_confidence: float = 0) -> List[OCRWord]:
    """
    Extract OCR data with bounding boxes and confidence scores.

    Args:
        image: PIL Image object
        min_confidence: Minimum confidence threshold (0-100)

    Returns:
        List of OCRWord dictionaries with text, confidence, and bbox

    Raises:
        RuntimeError: If OCR processing fails
    """
    try:
        # Get detailed OCR data including bounding boxes
        data = pytesseract.image_to_data(
            image, lang=OCR_LANG, config=OCR_CONFIG, output_type=Output.DICT, timeout=30
        )

        ocr_words: List[OCRWord] = []

        # Process each detected word
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])

            # Skip empty text or low confidence
            if not text or conf < min_confidence:
                continue

            bbox = BoundingBox(
                left=int(data["left"][i]),
                top=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
            )

            ocr_words.append(OCRWord(text=text, confidence=conf, bbox=bbox))

        return ocr_words

    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract not found. Install: apt-get install tesseract-ocr tesseract-ocr-ben"
        )
    except Exception as e:
        raise RuntimeError(f"OCR extraction failed: {e}")


def get_text_bounding_box(ocr_words: List[OCRWord]) -> Optional[BoundingBox]:
    """
    Calculate combined bounding box for a list of OCR words.

    Args:
        ocr_words: List of OCRWord objects

    Returns:
        Combined BoundingBox or None if empty list
    """
    if not ocr_words:
        return None

    # Find the extreme coordinates
    min_left = min(word["bbox"]["left"] for word in ocr_words)
    min_top = min(word["bbox"]["top"] for word in ocr_words)
    max_right = max(word["bbox"]["left"] + word["bbox"]["width"] for word in ocr_words)
    max_bottom = max(word["bbox"]["top"] + word["bbox"]["height"] for word in ocr_words)

    return BoundingBox(
        left=min_left, top=min_top, width=max_right - min_left, height=max_bottom - min_top
    )


def process_pdf(
    pdf_path: Path,
    search_names: List[str],
    threshold: int,
    stats: ProcessingStats,
    box_level: bool = False,
    min_confidence: float = 60,
) -> List[SearchResult]:
    """
    Process a PDF file and search for matching names using OCR.

    Args:
        pdf_path: Path to PDF file to process
        search_names: List of names to search for
        threshold: Fuzzy match threshold (0-100)
        stats: ProcessingStats object to track progress
        box_level: Enable bounding box extraction (default: False)
        min_confidence: Minimum OCR confidence threshold (default: 60)

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

        logger.info(f"Processing PDF: {pdf_path.name} (box_level={box_level})")

        # Convert PDF to images with error handling
        try:
            images = convert_from_path(
                str(pdf_path),
                dpi=DPI,
                thread_count=1,
                use_pdftocairo=False,  # Limit resource usage
            )
        except PDFPageCountError:
            raise ValueError(f"Invalid PDF page count: {pdf_path.name}")
        except PDFSyntaxError:
            raise ValueError(f"Corrupted PDF file: {pdf_path.name}")
        except Exception as e:
            raise RuntimeError(f"Failed to convert PDF to images: {e}") from e

        # Check page limit
        if len(images) > MAX_PDF_PAGES:
            logger.warning(f"PDF has {len(images)} pages, limiting to {MAX_PDF_PAGES}")
            images = images[:MAX_PDF_PAGES]

        # Process each page
        for page_no, image in enumerate(images, start=1):
            try:
                if box_level:
                    # Box-level OCR extraction
                    ocr_words = extract_ocr_data(image, min_confidence)
                    # Reconstruct text for pattern matching
                    text = " ".join(word["text"] for word in ocr_words)

                    stats.pages_processed += 1

                    # Extract voter information with bounding boxes
                    voters = extract_voter_blocks_with_boxes(text, ocr_words)
                    logger.debug(f"Page {page_no}: Extracted {len(voters)} voters (box-level)")

                    # Search for matches
                    for voter in voters:
                        for query in search_names:
                            if fuzzy_match(voter["name"], query, threshold):
                                # Get confidence if available
                                avg_conf = voter.get("confidence")
                                result = SearchResult(
                                    file=pdf_path.name,
                                    page=page_no,
                                    name=voter["name"],
                                    father=voter["father"],
                                    bbox=voter.get("name_bbox"),
                                    confidence=avg_conf,
                                )
                                results.append(result)
                                stats.matches_found += 1
                                if avg_conf:
                                    logger.info(
                                        f"Match found: {voter['name']} "
                                        f"on page {page_no} "
                                        f"(confidence: {avg_conf:.1f})"
                                    )
                                else:
                                    logger.info(f"Match found: {voter['name']} on page {page_no}")
                else:
                    # Standard text-only OCR (backward compatible)
                    text = pytesseract.image_to_string(
                        image,
                        lang=OCR_LANG,
                        config=OCR_CONFIG,
                        timeout=30,  # Timeout per page
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
                                logger.info(f"Match found: {voter['name']} on page {page_no}")

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
                        logger.error(f"Failed to close image: {image}")
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
