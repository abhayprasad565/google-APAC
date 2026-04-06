# ============================================================================
# MODULE: tools (L4 — Tool Wrappers & MCP Gateway)
# ============================================================================
#
# This package contains all tool wrappers and the MCP connection gateway.
# Sub-agents never call external APIs directly — they go through tools here.
#
# Files in this package:
#   - mcp_gateway.py   → Central MCP connection manager (SSE + Stdio)
#   - calendar_mcp.py  → Google Calendar MCP toolset wrapper
#   - gmail_mcp.py     → Gmail MCP toolset wrapper
#   - search_tool.py   → Google Search FunctionTool + page fetcher
#   - task_db_tool.py  → Cloud SQL task CRUD as FunctionTools
#   - auth_manager.py  → OAuth2 token refresh & Secret Manager binding
# ============================================================================
