from command_center.config.settings import settings

try:
    from google.adk.agents import LlmAgent
except ImportError:
    class LlmAgent:
        def __init__(self, **kwargs):
            self.config = kwargs

try:
    from command_center.tools.gmail_mcp import load_gmail_tools
except ImportError:
    def load_gmail_tools():
        return []

SYSTEM_INSTRUCTION = """
You are the Email Agent. You draft and send emails via Gmail.
Always match the requested tone: formal, casual, assertive, friendly.
When drafting: produce the email body first, then ask the orchestrator
whether to send immediately or present for review.
Never send an email without explicit confirmation from the orchestrator.
When summarizing threads: extract key decisions, action items, and deadlines.
"""

email_agent = LlmAgent(
    name="email_agent",
    model=settings.GEMINI_MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=load_gmail_tools()
)
