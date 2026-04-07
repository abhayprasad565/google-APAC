from command_center.config.settings import settings

try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import AgentTool
except ImportError:
    # Stubs if google-adk is not installed
    class LlmAgent:
        def __init__(self, **kwargs):
            self.config = kwargs

    class AgentTool:
        def __init__(self, agent):
            self.agent = agent

from command_center.agents.calendar_agent import calendar_agent
from command_center.agents.task_agent import task_agent
from command_center.agents.email_agent import email_agent
from command_center.agents.research_agent import research_agent

SYSTEM_INSTRUCTION = """
You are the primary orchestrator for a personal command center.
You have access to 4 specialized agents as tools:
  - calendar_agent: for scheduling, events, invites
  - task_agent: for creating, tracking, prioritizing tasks
  - email_agent: for drafting, sending, summarizing emails
  - research_agent: for web searches and information gathering

Rules:
1. Analyze the user request and identify all required actions.
2. For compound requests, call multiple agents in logical order.
3. Pass the output of one agent as context to the next when they are sequential.
4. If a calendar slot is unavailable, call calendar_agent to find the next free slot.
5. Always confirm actions before executing irreversible ones (send email, delete task).
6. Summarize all actions taken at the end.
"""

root_agent = LlmAgent(
    name="command_center_root",
    model=settings.GEMINI_MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        AgentTool(calendar_agent),
        AgentTool(task_agent),
        AgentTool(email_agent),
        AgentTool(research_agent),
    ]
)
