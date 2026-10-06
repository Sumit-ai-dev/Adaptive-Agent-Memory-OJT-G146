"""
Unit tests for scripts/fetch_semanticscholar_literature.py
Verifies API key loading, header synthesis, and BibTeX extraction.
"""

from unittest.mock import patch
import pytest

from scripts.fetch_semanticscholar_literature import (
    load_api_key,
    get_headers,
    format_clean_bibtex,
)


def test_load_api_key_explicit():
    assert load_api_key("test_key_123") == "test_key_123"


def test_get_headers_with_key():
    headers = get_headers(api_key="custom_s2_key")
    assert headers["x-api-key"] == "custom_s2_key"
    assert "User-Agent" in headers


def test_format_clean_bibtex_with_styles():
    paper = {
        "title": "Voyager: An Open-Ended Embodied Agent",
        "citationStyles": {
            "bibtex": "@article{wang2023voyager, title={Voyager}, author={Wang et al.}}"
        }
    }
    bib = format_clean_bibtex(paper)
    assert bib == "@article{wang2023voyager, title={Voyager}, author={Wang et al.}}"


def test_format_clean_bibtex_fallback():
    paper = {
        "title": "Reflexion: Language Agents with Verbal Reinforcement Learning",
        "authors": [{"name": "Noah Shinn"}, {"name": "Ashwin Gopinath"}],
        "year": 2023,
        "venue": "NeurIPS"
    }
    bib = format_clean_bibtex(paper)
    assert bib.startswith("@article{shinn2023reflexion,")
    assert "title={{Reflexion: Language Agents with Verbal Reinforcement Learning}}" in bib
    assert "author={Noah Shinn and Ashwin Gopinath}" in bib
    assert "journal={NeurIPS}" in bib
    assert "year={2023}" in bib
