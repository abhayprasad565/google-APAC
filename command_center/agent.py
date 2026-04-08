# =============================================================================
# agent.py — ADK Entry Point
#
# The ADK CLI (adk web, adk run) looks for a `root_agent` variable in this
# file. We simply re-export it from the agents package so that both:
#   - `adk web`  (uses this file)
#   - `uvicorn command_center.api.main:app`  (imports directly from agents/)
# can coexist without duplication.
# =============================================================================

# Register Gemma 4 in the ADK model registry before importing agents,
# since agents instantiate LlmAgent at module level.
try:
    from google.adk.models.registry import LLMRegistry
    from google.adk.models.gemma_llm import Gemma
    LLMRegistry._register(r'gemma-4.*', Gemma)
except Exception:
    pass

from command_center.agents.root_agent import root_agent  # noqa: F401

__all__ = ["root_agent"]
