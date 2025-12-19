"""
Type definitions for electoral search.
"""

from typing import TypedDict


class VoterInfo(TypedDict):
    """Structured voter information extracted from OCR."""
    name: str
    father: str


class SearchResult(TypedDict):
    """Search result with match information."""
    file: str
    page: int
    name: str
    father: str
