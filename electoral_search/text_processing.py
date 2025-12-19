"""
Bengali text processing and pattern matching.

Handles normalization, extraction, and fuzzy matching of Bengali text.
"""

import re
import logging
from typing import List
from rapidfuzz import fuzz

from .types import VoterInfo

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
        List of VoterInfo dictionaries containing name and father/guardian fields

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
