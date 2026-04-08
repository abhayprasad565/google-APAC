from command_center.config.settings import settings

try:
    from google.adk.agents import LlmAgent
except ImportError:
    class LlmAgent:
        def __init__(self, **kwargs):
            self.config = kwargs

# NOTE: gmail_mcp.load_gmail_tools() is async and cannot be called
# at module import time. Start with empty tools.

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
    tools=[]  # MCP tools loaded asynchronously at startup
)
