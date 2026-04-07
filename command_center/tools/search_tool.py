"""
L4 — Google Search & Web Research FunctionTools

Wraps Google Custom Search API and page fetching as ADK FunctionTools.
Does NOT use MCP — uses direct HTTP calls.
"""

import httpx
from typing import Any

try:
    from google.adk.tools import FunctionTool
except ImportError:
    # Stub: treat FunctionTool as a passthrough decorator
    def FunctionTool(func):
        return func

from command_center.config.settings import settings


async def google_search(query: str, num_results: int = 5) -> list[dict[str, str]]:
    """Search the web for current information on a topic.

    Args:
        query: The search query string.
        num_results: Number of results to return (default 5).

    Returns:
        A list of dicts, each with 'title', 'url', and 'snippet'.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            settings.SEARCH_API_URL,
            params={
                "q": query,
                "num": num_results,
                "key": settings.SEARCH_API_KEY,
            },
            timeout=10.0,
        )

    if response.status_code != 200:
        return [{"title": "Error", "url": "", "snippet": f"Search API returned HTTP {response.status_code}"}]

    data = response.json()
    items = data.get("items", [])
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in items[:num_results]
    ]


async def fetch_page_content(url: str) -> dict[str, str]:
    """Fetch and return the main text content of a webpage.

    Args:
        url: Full URL of the page to fetch.

    Returns:
        A dict with 'url' and 'content' (max 4000 chars).
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=10.0)

        if response.status_code >= 400:
            return {"url": url, "content": f"Error: HTTP {response.status_code}"}

        # Basic content extraction: strip HTML tags
        text = _extract_text(response.text)
        return {"url": url, "content": text[:4000]}

    except httpx.TimeoutException:
        return {"url": url, "content": "Error: timeout"}
    except Exception as e:
        return {"url": url, "content": f"Error: {str(e)}"}


async def session_store_research(topic: str, summary: str) -> dict[str, Any]:
    """Persist a research summary to session memory for future reference.

    Args:
        topic: The research topic (used as cache key).
        summary: The research summary to store.

    Returns:
        A dict with 'stored' (bool) and 'topic' (str).
    """
    # NOTE: Actual session persistence will be wired in main.py
    # via the ADK SessionService. For now, return success.
    return {"stored": True, "topic": topic}


def _extract_text(html: str) -> str:
    """Very basic HTML-to-text extraction. Strips tags and collapses whitespace."""
    import re
    # Remove script and style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_research_tools() -> list:
    """Returns the list of all research-related tools for the research_agent."""
    return [google_search, fetch_page_content, session_store_research]
