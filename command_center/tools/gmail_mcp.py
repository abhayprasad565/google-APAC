# ============================================================================
# FILE: tools/gmail_mcp.py
# LAYER: L4 — Gmail MCP Wrapper
# ============================================================================
#
# PURPOSE:
#   Same pattern as calendar_mcp.py but for the Gmail MCP server.
#   Exposes load_gmail_tools() for agents/email_agent.py to call at startup.
#
# KEY RESPONSIBILITIES:
#   1. Fetch a valid OAuth token for Gmail
#   2. Connect to the Gmail MCP server via mcp_gateway
#   3. Return the list of ADK-compatible tools from the server
#
# ============================================================================
#
#
# ── CONSTANT: GMAIL_MCP_URL ─────────────────────────────────────────────────
#
#   str — "https://gmail.googleapis.com/mcp/v1/sse"
#   The Gmail MCP server endpoint (SSE transport).
#
#
# ── FUNCTION: load_gmail_tools ──────────────────────────────────────────────
#
# async function load_gmail_tools() -> list[MCPTool]
#
#   TASK:
#     Fetches a fresh OAuth2 access token for Gmail via auth_manager,
#     then connects to the Gmail MCP server via the mcp_gateway, and
#     returns the full list of MCP tools exposed by the server.
#
#   INPUT:
#     None (tokens are fetched internally from auth_manager)
#
#   OUTPUT:
#     list[MCPTool] — ADK-compatible tool list, typically including:
#       - gmail_messages_send       → send an email message
#       - gmail_messages_list       → list/search messages
#       - gmail_threads_get         → get full conversation thread
#       - gmail_drafts_create       → create an email draft
#       - gmail_drafts_send         → send an existing draft
#       - gmail_users_labels_list   → list email labels
#
#     Each MCPTool is a wrapper that, when called, sends a JSON-RPC
#     request to the MCP server and returns the result.
#
#   DEPENDENCIES:
#     - auth_manager.get_token("gmail")
#     - mcp_gateway.get_toolset("gmail", token)
#
#   AUTH REQUIREMENT:
#     OAuth2 scope: https://www.googleapis.com/auth/gmail.modify
#
# ============================================================================
