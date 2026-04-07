from command_center.config.settings import settings

try:
    from google.adk.agents import LlmAgent
except ImportError:
    class LlmAgent:
        def __init__(self, **kwargs):
            self.config = kwargs

try:
    from command_center.tools.search_tool import load_research_tools
except ImportError:
    def load_research_tools():
        return []

SYSTEM_INSTRUCTION = """
You are the Research Agent. You gather information from the web.
Steps:
1. Decompose the topic into 2-3 specific search queries.
2. Run each query, collect top results.
3. If a result looks highly relevant, call fetch_page_content for the full text.
4. Synthesize findings into a structured summary with:
   - Key finding 1, 2, 3 (bullet points)
   - Conflicting information (if any)
   - Source list with URLs
5. If the orchestrator requested deep research, store the summary to session memory.
Always cite sources. Never present information without a URL attribution.
"""

research_agent = LlmAgent(
    name="research_agent",
    model=settings.GEMINI_MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=load_research_tools()
)
