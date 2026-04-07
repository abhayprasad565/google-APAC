"""
L4 — Google Calendar MCP Wrapper

Wraps the Google Calendar MCP server connection and exposes
load_calendar_tools() for the calendar_agent.
"""

from command_center.tools import auth_manager, mcp_gateway


async def load_calendar_tools() -> list:
    """
    Fetches a fresh OAuth2 access token for Google Calendar,
    connects to the Calendar MCP server, and returns the tool list.

    Tools typically returned by the Calendar MCP server:
      - calendar.events.insert   → create a new event
      - calendar.events.list     → list events in a date range
      - calendar.events.patch    → update specific event fields
      - calendar.events.delete   → delete an event
      - calendar.freebusy.query  → check availability
    """
    token = await auth_manager.get_token("google_calendar")
    toolset = await mcp_gateway.get_toolset("google_calendar", token)
    tools = await toolset.list_tools()
    return tools
