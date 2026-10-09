"""
Search and Fact Retrieval Tool for Open-Domain Multi-Hop Queries.
Provides online search using DuckDuckGo with resilient fallback for offline execution.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import warnings

logger = logging.getLogger("ai_service.tools.search")

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


class SearchTool:
    """
    Search tool providing factual context snippets for reasoning tasks.
    Uses DDGS (duckduckgo_search) for live web search with graceful offline fallback.
    """

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    def _sync_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """
        Synchronous search execution intended to be dispatched via asyncio.to_thread.
        """
        if DDGS is None:
            raise RuntimeError("duckduckgo_search package is not installed.")

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            with DDGS(timeout=self.timeout) as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))

        formatted: List[Dict[str, str]] = []
        for r in raw_results:
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            href = r.get("href", "").strip()
            if body:
                formatted.append({
                    "title": title or "Web Result",
                    "snippet": body,
                    "url": href,
                })
        return formatted

    async def execute(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """
        Execute search query and return formatted snippets.
        Non-blocking async wrapper around the search engine.
        """
        clean_query = query.strip()
        if not clean_query:
            return {
                "tool": "duckduckgo_search",
                "query": "",
                "status": "empty_query",
                "results": [],
                "output": "No search query provided.",
            }

        try:
            results = await asyncio.to_thread(self._sync_search, clean_query, max_results)
            if results:
                formatted_output = "\n\n".join(
                    f"[{r['title']}]: {r['snippet']}" + (f" (Source: {r['url']})" if r.get("url") else "")
                    for r in results
                )
                return {
                    "tool": "duckduckgo_search",
                    "query": clean_query,
                    "status": "success",
                    "results": results,
                    "output": formatted_output,
                }
        except Exception as e:
            logger.warning("DuckDuckGo search error: %s. Using graceful fallback.", e)

        # Resilient fallback snippet when offline, rate-limited, or library unavailable
        return {
            "tool": "duckduckgo_search",
            "query": clean_query,
            "status": "fallback",
            "results": [
                {
                    "title": clean_query,
                    "snippet": f"Web search temporarily unreachable for '{clean_query}'. Relying on internal parametric reasoning.",
                    "url": "",
                }
            ],
            "output": f"Search context unavailable for '{clean_query}'. Relying on internal parametric reasoning.",
        }


# Global singleton search tool
search_tool = SearchTool()

