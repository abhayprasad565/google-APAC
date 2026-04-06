# ============================================================================
# FILE: tools/search_tool.py
# LAYER: L4 — Google Search FunctionTool
# ============================================================================
#
# PURPOSE:
#   Wraps the Google Custom Search API (or Serper API) as ADK FunctionTools.
#   Also provides a fetch_page_content tool for the research agent to read
#   full web pages, and a session_store_research tool to persist findings.
#   Does NOT use MCP — uses direct HTTP calls wrapped in FunctionTool.
#
# KEY RESPONSIBILITIES:
#   1. Execute web searches via Google Custom Search API
#   2. Fetch and extract main content from web pages
#   3. Persist research summaries to session memory
#   4. Expose all tools via load_research_tools()
#
# ============================================================================
#
#
# ── FUNCTION (FunctionTool): google_search ──────────────────────────────────
#
# async function google_search(query, num_results) -> list[dict]
#
#   TASK:
#     Performs a web search using the Google Custom Search API. Returns
#     the top results with title, URL, and snippet.
#
#   INPUT:
#     query       : str   — the search query string
#                           e.g. "latest AI agent framework trends 2025"
#     num_results : int   — number of results to return (default: 5)
#
#   OUTPUT:
#     list[dict] — each dict contains:
#       {
#         title   : str   — page title
#         url     : str   — full URL
#         snippet : str   — search result snippet
#       }
#
#   DEPENDENCIES:
#     - settings.SEARCH_API_KEY  — Google Custom Search API key
#     - settings.SEARCH_API_URL  — API endpoint URL
#
#
# ── FUNCTION (FunctionTool): fetch_page_content ─────────────────────────────
#
# async function fetch_page_content(url) -> dict
#
#   TASK:
#     Fetches a web page and extracts its main text content, stripping
#     navigation, ads, and boilerplate HTML. Content is capped at 4000
#     characters to stay within LLM context limits.
#
#   INPUT:
#     url : str — full URL of the page to fetch
#                 e.g. "https://example.com/article"
#
#   OUTPUT:
#     dict
#       {
#         url     : str   — echo back the URL
#         content : str   — extracted main text, max 4000 chars
#       }
#
#   ERROR HANDLING:
#     - HTTP timeout (10s) returns {url, content: "Error: timeout"}
#     - 4xx/5xx returns {url, content: "Error: HTTP <status_code>"}
#
#
# ── FUNCTION (FunctionTool): session_store_research ─────────────────────────
#
# async function session_store_research(topic, summary) -> dict
#
#   TASK:
#     Persists a research summary to the ADK session state under the
#     key "research_cache[topic]". This allows the orchestrator or
#     other agents to retrieve prior research without re-searching.
#
#   INPUT:
#     topic   : str   — the research topic (used as cache key)
#     summary : str   — the research summary to store
#
#   OUTPUT:
#     dict
#       {
#         stored : bool   — True on success
#         topic  : str    — echo back the topic key
#       }
#
#
# ── FUNCTION: load_research_tools ───────────────────────────────────────────
#
# function load_research_tools() -> list[FunctionTool]
#
#   TASK:
#     Returns the list of all research-related FunctionTools for the
#     research_agent to register.
#
#   INPUT:
#     None
#
#   OUTPUT:
#     list[FunctionTool] — [google_search, fetch_page_content, session_store_research]
#
# ============================================================================
