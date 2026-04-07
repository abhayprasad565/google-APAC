from command_center.config.settings import settings

try:
    from google.adk.agents import LlmAgent
except ImportError:
    class LlmAgent:
        def __init__(self, **kwargs):
            self.config = kwargs

try:
    from command_center.tools.task_db_tool import load_task_tools
except ImportError:
    def load_task_tools():
        return []

SYSTEM_INSTRUCTION = """
You are the Task Agent. You manage a task list stored in the database.
Priority scoring: 1=low, 2=medium, 3=high, 4=urgent, 5=critical.
When creating tasks, infer priority from the user's language cues.
When listing tasks, sort by: priority DESC, due_date ASC.
For task decomposition: break large tasks into sub-tasks automatically.
"""

task_agent = LlmAgent(
    name="task_agent",
    model=settings.GEMINI_MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=load_task_tools()
)
