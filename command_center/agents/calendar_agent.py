from command_center.config.settings import settings

try:
    from google.adk.agents import LlmAgent
except ImportError:
    class LlmAgent:
        def __init__(self, **kwargs):
            self.config = kwargs

try:
    from command_center.tools.calendar_mcp import load_calendar_tools
except ImportError:
    def load_calendar_tools():
        return []

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
    tools=load_calendar_tools()
)
