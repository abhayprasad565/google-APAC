# ============================================================================
# PACKAGE: command_center
# ============================================================================
#
# ADK Command Center — Multi-Agent AI System
#
# A primary orchestrator agent receives user requests, classifies intent,
# and delegates to one or more specialised sub-agents. Each sub-agent owns
# a narrow domain (calendar, tasks, email, research) and operates its own
# set of tools via MCP or ADK FunctionTools.
#
# Stack: Google ADK · FastAPI · Gemini 2.0 Flash · Cloud SQL · Cloud Run · MCP
# Pattern: Layered monolith · Primary agent + 4 sub-agents · REST + SSE API
#
# ============================================================================
