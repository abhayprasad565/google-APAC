# ============================================================================
# FILE: tools/calendar_mcp.py
# LAYER: L4 — Google Calendar MCP Wrapper
# ============================================================================
#
# PURPOSE:
#   Wraps the Google Calendar MCP server connection and exposes a
#   load_calendar_tools() function that agents/calendar_agent.py calls
#   at startup. Handles fetching a fresh OAuth token from auth_manager
#   before connecting.
#
# KEY RESPONSIBILITIES:
#   1. Fetch a valid OAuth token for Google Calendar
#   2. Connect to the Calendar MCP server via mcp_gateway
#   3. Return the list of ADK-compatible tools from the server
#
# ============================================================================
#
#
# ── CONSTANT: CALENDAR_MCP_URL ──────────────────────────────────────────────
#
#   str — "https://calendar.googleapis.com/mcp/v1/sse"
#   The Google Calendar MCP server endpoint (SSE transport).
#
#
# ── FUNCTION: load_calendar_tools ───────────────────────────────────────────
#
# async function load_calendar_tools() -> list[MCPTool]
#
#   TASK:
#     Fetches a fresh OAuth2 access token for Google Calendar via
#     auth_manager, then connects to the Calendar MCP server via the
#     mcp_gateway, and returns the full list of MCP tools exposed by
#     the server.
#
#   INPUT:
#     None (tokens are fetched internally from auth_manager)
#
#   OUTPUT:
#     list[MCPTool] — ADK-compatible tool list, typically including:
#       - calendar_events_insert    → create a new event
#       - calendar_events_list      → list events in a date range
#       - calendar_events_patch     → update specific event fields
#       - calendar_events_delete    → delete an event
#       - calendar_freebusy_query   → check availability for calendars
#
#     Each MCPTool is a wrapper that, when called, sends a JSON-RPC
#     request to the MCP server and returns the result.
#
#   DEPENDENCIES:
#     - auth_manager.get_token("google_calendar")
#     - mcp_gateway.get_toolset("google_calendar", token)
#
#   AUTH REQUIREMENT:
#     OAuth2 scope: https://www.googleapis.com/auth/calendar
#
# ============================================================================
