from command_center.config.settings import settings

try:
    from google.adk.agents import LlmAgent
except ImportError:
    class LlmAgent:
        def __init__(self, **kwargs):
            self.config = kwargs

# NOTE: calendar_mcp.load_calendar_tools() is async and cannot be called
# at module import time. The tools are loaded later via the agent factory
# in api/main.py. For now we start with an empty tools list.
# When ADK supports async tool loading, refactor this.

SYSTEM_INSTRUCTION = """
You are the Calendar Agent. You handle all scheduling tasks.
You have access to Google Calendar tools.
Steps for creating a meeting:
1. Call gcal_check_free_busy for all attendees at the requested time.
2. If there is a conflict, find the next available 30-minute slot.
3. Call gcal_create_event with confirmed slot.
4. Return the event details including a calendar link.
Never double-book. Always confirm timezone from session context.
"""

calendar_agent = LlmAgent(
    name="calendar_agent",
    model=settings.GEMINI_MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=[]  # MCP tools loaded asynchronously at startup
)
