# ============================================================================
# FILE: agents/research_agent.py
# LAYER: L3 — Research Domain Sub-Agent
# ============================================================================
#
# PURPOSE:
#   L3 sub-agent responsible for web research. Uses Google Search as a
#   FunctionTool and can make multiple search calls to cross-reference
#   information. Summarises findings and cites sources. Can optionally
#   persist research summaries to L6 memory for future reference.
#
# KEY RESPONSIBILITIES:
#   1. Decompose research topics into 2-3 specific search queries
#   2. Run each query and collect top results
#   3. Deep-read highly relevant pages via fetch_page_content
#   4. Synthesise structured summaries with cited sources
#   5. Optionally store research to session memory for reuse
#
# ============================================================================
#
#
# ── CONSTANT: SYSTEM_INSTRUCTION ────────────────────────────────────────────
#
#   str — system prompt for the research agent
#
#   TEACHES THE MODEL TO:
#     - Decompose topics into 2-3 specific search queries
#     - Run each query, collect top results
#     - If a result is highly relevant, call fetch_page_content
#     - Synthesise findings into structured summary:
#         • Key finding 1, 2, 3 (bullet points)
#         • Conflicting information (if any)
#         • Source list with URLs
#     - For deep research, store summary to session memory
#     - Always cite sources — never present without URL attribution
#
#
# ── OBJECT: research_agent ──────────────────────────────────────────────────
#
# research_agent : LlmAgent
#
#   CONFIGURATION:
#     name        : "research_agent"
#     model       : "gemini-2.0-flash"
#     instruction : SYSTEM_INSTRUCTION
#     tools       : load_research_tools()  — from tools/search_tool.py
#
#   INPUT (from orchestrator via AgentTool call):
#     Natural language research request:
#       e.g. "Research the latest trends in AI agent frameworks"
#
#     Optional depth parameter (extracted from entities):
#       depth : str   — "quick" (default) | "deep"
#
#   OUTPUT (returned to orchestrator):
#     Natural language summary text +
#     Structured result:
#       {
#         topic        : str           — what was researched
#         key_findings : list[str]     — bullet-point findings
#         conflicts    : list[str]     — conflicting information found
#         sources      : list[{
#           title : str
#           url   : str
#           snippet : str
#         }]
#         cached       : bool          — whether stored to session memory
#       }
#
#   TOOLS AVAILABLE (FunctionTool — from tools/search_tool.py):
#
#     - google_search(query, num_results)
#         INPUT:  query: str, num_results: int (default 5)
#         OUTPUT: list[{title: str, url: str, snippet: str}]
#
#     - fetch_page_content(url)
#         INPUT:  url: str
#         OUTPUT: {url: str, content: str}  — content capped at 4000 chars
#
#     - session_store_research(topic, summary)
#         INPUT:  topic: str, summary: str
#         OUTPUT: {stored: bool, topic: str}
#
# ============================================================================
