"""Tests for text processing module."""

import pytest
from electoral_search.text_processing import normalize_bn, extract_voter_blocks, fuzzy_match


class TestNormalizeBn:
    """Tests for Bengali text normalization."""

    def test_empty_string(self):
        assert normalize_bn("") == ""

    def test_removes_diacritics(self):
        text = "নামঃ রহিম"
        result = normalize_bn(text)
        assert "ঃ" not in result
        assert "নাম" in result

    def test_removes_spaces(self):
        text = "রহিম করিম"
        result = normalize_bn(text)
        assert " " not in result

    def test_removes_danda(self):
        text = "নাম।"
        result = normalize_bn(text)
        assert "।" not in result


class TestExtractVoterBlocks:
    """Tests for voter information extraction."""

    def test_extract_single_voter(self):
        text = """
নাম : রহিম আলী
পিতার নাম : করিম আলী
"""
        voters = extract_voter_blocks(text)
        assert len(voters) == 1
        assert voters[0]["name"] == "রহিম আলী"
        assert voters[0]["father"] == "করিম আলী"

    def test_extract_with_husband_name(self):
        text = """
নাম : ফাতিমা খাতুন
স্বামীর নাম : রহিম আলী
"""
        voters = extract_voter_blocks(text)
        assert len(voters) == 1
        assert voters[0]["name"] == "ফাতিমা খাতুন"

    def test_empty_text(self):
        voters = extract_voter_blocks("")
        assert voters == []


class TestFuzzyMatch:
    """Tests for fuzzy string matching."""

    def test_exact_match(self):
        assert fuzzy_match("রহিম", "রহিম", 100) is True

    def test_no_match(self):
        assert fuzzy_match("রহিম", "করিম", 90) is False

    def test_empty_strings(self):
        assert fuzzy_match("", "", 80) is False
