"""
Bengali text processing and pattern matching.

Handles normalization, extraction, and fuzzy matching of Bengali text.
"""

import logging
import re
from typing import List

from rapidfuzz import fuzz

from .types import BoundingBox, OCRWord, VoterInfo

logger = logging.getLogger(__name__)

# Regex patterns with bounded quantifiers to prevent ReDoS
NAME_RE = re.compile(r"নাম\s*[:：]\s*(.{1,200}?)(?:\n|$)", re.MULTILINE)
FATHER_RE = re.compile(r"(পিতার নাম|স্বামীর নাম)\s*[:：]\s*(.{1,200}?)(?:\n|$)", re.MULTILINE)


def normalize_bn(text: str) -> str:
    """
    Normalize Bengali text for fuzzy matching.

    Removes diacritics and whitespace to improve matching accuracy
    when dealing with OCR variations.

    Args:
        text: Bengali text to normalize

    Returns:
        Normalized text string

    Example:
        >>> normalize_bn("নাম : রহিম")
        "নামরহিম"
    """
    if not text:
        return ""

    # Use str.translate for better performance
    translation_table = str.maketrans("", "", "ঃ।্ ")
    return text.translate(translation_table).strip()


def extract_voter_blocks(text: str) -> List[VoterInfo]:
    """
    Extract voter name and father's/guardian's name from OCR text.

    Parses electoral roll OCR text looking for Bengali name patterns.
    Expects format:
        নাম : <name>
        পিতার নাম : <father's name>
        OR
        স্বামীর নাম : <husband's name>

    Args:
        text: OCR-extracted text from electoral roll PDF page

    Returns:
        List of VoterInfo dictionaries containing name and father fields

    Example:
        >>> text = "নাম : রহিম\\nপিতার নাম : করিম\\n"
        >>> extract_voter_blocks(text)
        [{'name': 'রহিম', 'father': 'করিম'}]
    """
    voters: List[VoterInfo] = []
    blocks = text.split("\n\n")

    for block in blocks:
        try:
            name_match = NAME_RE.search(block)
            father_match = FATHER_RE.search(block)

            if name_match and father_match:
                voters.append(
                    VoterInfo(
                        name=name_match.group(1).strip(),
                        father=father_match.group(2).strip(),
                    )
                )
        except Exception as e:
            logger.debug(f"Failed to extract voter from block: {e}")
            continue

    return voters


def extract_voter_blocks_with_boxes(text: str, ocr_words: List[OCRWord]) -> List[VoterInfo]:
    """
    Extract voter information with bounding boxes from OCR word data.

    This function processes OCR word data to extract voter names and
    father/guardian names along with their bounding box coordinates.

    Args:
        text: Reconstructed text from OCR words
        ocr_words: List of OCRWord objects with bbox and confidence

    Returns:
        List of VoterInfo with bbox and confidence scores

    Example:
        >>> ocr_words = [
        ...     {'text': 'নাম', 'confidence': 95, 'bbox': {...}},
        ...     {'text': 'রহিম', 'confidence': 92, 'bbox': {...}}
        ... ]
        >>> voters = extract_voter_blocks_with_boxes(text, ocr_words)
    """
    voters: List[VoterInfo] = []

    # First extract text blocks as usual
    text_voters = extract_voter_blocks(text)

    # For each text match, try to find corresponding words in OCR data
    for voter_text in text_voters:
        try:
            # Find name words in OCR data
            name_words = _find_text_words(voter_text["name"], ocr_words)
            father_words = _find_text_words(voter_text["father"], ocr_words)

            # Calculate bounding boxes
            name_bbox = _get_combined_bbox(name_words) if name_words else None
            father_bbox = _get_combined_bbox(father_words) if father_words else None

            # Calculate average confidence
            all_words = name_words + father_words
            avg_conf = (
                sum(w["confidence"] for w in all_words) / len(all_words) if all_words else None
            )

            voter = VoterInfo(
                name=voter_text["name"],
                father=voter_text["father"],
            )

            # Add optional fields
            if name_bbox:
                voter["name_bbox"] = name_bbox
            if father_bbox:
                voter["father_bbox"] = father_bbox
            if avg_conf is not None:
                voter["confidence"] = avg_conf

            voters.append(voter)

        except Exception as e:
            logger.debug(f"Failed to extract bbox for voter: {e}")
            # Fall back to text-only data
            voters.append(
                VoterInfo(
                    name=voter_text["name"],
                    father=voter_text["father"],
                )
            )
            continue

    return voters


def _find_text_words(search_text: str, ocr_words: List[OCRWord]) -> List[OCRWord]:
    """
    Find OCR words that match the search text.

    Uses fuzzy matching to handle OCR variations.

    Args:
        search_text: Text to search for
        ocr_words: List of OCR word objects

    Returns:
        List of matching OCRWord objects
    """
    if not search_text or not ocr_words:
        return []

    matching_words: List[OCRWord] = []
    search_tokens = search_text.split()

    for token in search_tokens:
        # Find best matching OCR word
        best_match = None
        best_score = 0

        for word in ocr_words:
            score = fuzz.ratio(normalize_bn(token), normalize_bn(word["text"]))
            if score > best_score and score >= 70:  # Threshold
                best_score = score
                best_match = word

        if best_match and best_match not in matching_words:
            matching_words.append(best_match)

    return matching_words


def _get_combined_bbox(ocr_words: List[OCRWord]) -> BoundingBox:
    """
    Calculate combined bounding box for OCR words.

    Args:
        ocr_words: List of OCRWord objects

    Returns:
        Combined BoundingBox
    """
    if not ocr_words:
        return BoundingBox(left=0, top=0, width=0, height=0)

    min_left = min(word["bbox"]["left"] for word in ocr_words)
    min_top = min(word["bbox"]["top"] for word in ocr_words)
    max_right = max(word["bbox"]["left"] + word["bbox"]["width"] for word in ocr_words)
    max_bottom = max(word["bbox"]["top"] + word["bbox"]["height"] for word in ocr_words)

    return BoundingBox(
        left=min_left, top=min_top, width=max_right - min_left, height=max_bottom - min_top
    )


def fuzzy_match(a: str, b: str, threshold: int) -> bool:
    """
    Bengali fuzzy matching using RapidFuzz token set ratio.

    Uses normalized text (diacritics removed) for better matching of
    OCR-extracted Bengali text which may have variations.

    Args:
        a: First string to compare
        b: Second string to compare
        threshold: Minimum similarity score (0-100) to consider a match

    Returns:
        True if similarity >= threshold, False otherwise

    Example:
        >>> fuzzy_match("রহিম", "রহীম", 80)
        True
    """
    if not a or not b:
        return False

    try:
        score = fuzz.token_set_ratio(normalize_bn(a), normalize_bn(b))
        return score >= threshold
    except Exception as e:
        logger.warning(f"Fuzzy match failed for '{a}' vs '{b}': {e}")
        return False
