"""
Type definitions for electoral search.
"""

from typing import NotRequired, Optional, TypedDict


class BoundingBox(TypedDict):
    """Bounding box coordinates for text."""

    left: int
    top: int
    width: int
    height: int


class OCRWord(TypedDict):
    """OCR word-level data with bounding box and confidence."""

    text: str
    confidence: float
    bbox: BoundingBox


class VoterInfo(TypedDict):
    """Structured voter information extracted from OCR."""

    name: str
    father: str
    name_bbox: NotRequired[Optional[BoundingBox]]
    father_bbox: NotRequired[Optional[BoundingBox]]
    confidence: NotRequired[Optional[float]]


class SearchResult(TypedDict):
    """Search result with match information."""

    file: str
    page: int
    name: str
    father: str
    bbox: NotRequired[Optional[BoundingBox]]
    confidence: NotRequired[Optional[float]]
