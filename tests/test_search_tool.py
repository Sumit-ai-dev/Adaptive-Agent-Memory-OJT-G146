"""
Unit Tests for SearchTool and DuckDuckGo Integration.
"""

from unittest.mock import MagicMock, patch
import pytest

from ai_service.tools.search import SearchTool, search_tool


@pytest.mark.asyncio
async def test_search_tool_empty_query():
    tool = SearchTool()
    res = await tool.execute("")
    assert res["status"] == "empty_query"
    assert res["results"] == []
    assert res["tool"] == "duckduckgo_search"


@pytest.mark.asyncio
async def test_search_tool_mocked_success():
    tool = SearchTool()
    mock_results = [
        {"title": "Test Title 1", "body": "Snippet 1 text", "href": "https://example.com/1"},
        {"title": "Test Title 2", "body": "Snippet 2 text", "href": "https://example.com/2"},
    ]
    with patch.object(tool, "_sync_search", return_value=[
        {"title": "Test Title 1", "snippet": "Snippet 1 text", "url": "https://example.com/1"},
        {"title": "Test Title 2", "snippet": "Snippet 2 text", "url": "https://example.com/2"},
    ]):
        res = await tool.execute("test query", max_results=2)
        assert res["status"] == "success"
        assert len(res["results"]) == 2
        assert "Snippet 1 text" in res["output"]
        assert "Test Title 1" in res["output"]
        assert res["tool"] == "duckduckgo_search"


@pytest.mark.asyncio
async def test_search_tool_graceful_fallback_on_exception():
    tool = SearchTool()
    with patch.object(tool, "_sync_search", side_effect=RuntimeError("Rate limit / Network down")):
        res = await tool.execute("test failing query")
        assert res["status"] == "fallback"
        assert res["tool"] == "duckduckgo_search"
        assert "Search context unavailable" in res["output"]
        assert len(res["results"]) == 1


@pytest.mark.asyncio
async def test_singleton_search_tool_instance():
    assert isinstance(search_tool, SearchTool)


@pytest.mark.asyncio
async def test_search_tool_live_execution():
    tool = SearchTool()
    res = await tool.execute("Nobel Prize physics", max_results=2)
    assert res["tool"] == "duckduckgo_search"
    assert res["status"] in ("success", "fallback")
    assert len(res["results"]) >= 1
    assert "Nobel" in res["output"] or "Search context unavailable" in res["output"]

