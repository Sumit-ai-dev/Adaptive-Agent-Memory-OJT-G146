"""
Unit tests for scripts/fetch_arxiv_literature.py
Verifies BibTeX key generation, citation formatting, and filename sanitization.
"""

from datetime import datetime
from unittest.mock import MagicMock
import pytest

from scripts.fetch_arxiv_literature import (
    sanitize_filename,
    generate_bibtex_key,
    format_bibtex,
)


def test_sanitize_filename():
    raw = "Adaptive Agent Memory: Towards Reliable Multi-Agent RAG! (2026)"
    sanitized = sanitize_filename(raw, max_len=40)
    assert "!" not in sanitized
    assert ":" not in sanitized
    assert len(sanitized) <= 40
    assert sanitized.startswith("Adaptive_Agent_Memory")


def test_generate_bibtex_key():
    mock_result = MagicMock()
    mock_author_1 = MagicMock()
    mock_author_1.name = "Zhiruo Wang"
    mock_author_2 = MagicMock()
    mock_author_2.name = "Graham Neubig"
    mock_result.authors = [mock_author_1, mock_author_2]
    mock_result.published = datetime(2024, 9, 15)
    mock_result.title = "Agent Workflow Memory: Inducing Procedural Runbooks"

    key = generate_bibtex_key(mock_result)
    assert key == "wang2024agent"


def test_format_bibtex():
    mock_result = MagicMock()
    mock_author = MagicMock()
    mock_author.name = "Noah Shinn"
    mock_result.authors = [mock_author]
    mock_result.published = datetime(2023, 10, 1)
    mock_result.title = "Reflexion: Language Agents with Verbal Reinforcement"
    mock_result.get_short_id.return_value = "2303.11366v2"
    mock_result.primary_category = "cs.AI"

    bib = format_bibtex(mock_result)
    assert bib.startswith("@article{shinn2023reflexion,")
    assert "title={{Reflexion: Language Agents with Verbal Reinforcement}}" in bib
    assert "author={Noah Shinn}" in bib
    assert "journal={arXiv preprint arXiv:2303.11366v2}" in bib
    assert "eprint={2303.11366v2}" in bib
    assert "primaryClass={cs.AI}" in bib
