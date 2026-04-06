# ============================================================================
# FILE: agents/root_agent.py
# LAYER: L2 — Orchestrator Agent
# ============================================================================
#
# PURPOSE:
#   Defines the primary ADK LlmAgent that acts as the central orchestrator.
#   Registers all four sub-agents as AgentTool instances so Gemini can
#   decide which to call. Contains the system instruction that teaches the
#   orchestrator how to plan multi-step workflows, sequence dependent tasks,
#   and resolve scheduling conflicts.
#
# KEY RESPONSIBILITIES:
#   1. Define the SYSTEM_INSTRUCTION for orchestration logic
#   2. Register calendar_agent, task_agent, email_agent, research_agent
#      as AgentTool instances
#   3. Handle compound requests by calling multiple agents in sequence
#   4. Pass output from one agent as context to the next agent
#   5. Summarise all actions taken at the end of the workflow
#
# ============================================================================
#
#
# ── CONSTANT: SYSTEM_INSTRUCTION ────────────────────────────────────────────
#
#   str — the system prompt that defines the orchestrator's behaviour
#
#   TEACHES THE MODEL TO:
#     - Analyse user requests and identify all required actions
#     - Route single-domain requests to the correct sub-agent
#     - For compound requests, call multiple agents in logical order
#     - Pass output of one agent as context to the next (chaining)
#     - If a calendar slot is unavailable, ask calendar_agent for alternatives
#     - Always confirm before executing irreversible actions (send, delete)
#     - Summarise all actions taken at the end
#
#
# ── OBJECT: root_agent ──────────────────────────────────────────────────────
#
# root_agent : LlmAgent
#
#   TASK:
#     The top-level agent that the ADK Runner invokes. Receives the
#     ParsedCommand as its initial user message and uses Gemini to decide
#     which sub-agent(s) to call and in what order.
#
#   CONFIGURATION:
#     name        : "command_center_root"
#     model       : "gemini-2.0-flash"
#     instruction : SYSTEM_INSTRUCTION
#     tools       : [
#                     AgentTool(calendar_agent),
#                     AgentTool(task_agent),
#                     AgentTool(email_agent),
#                     AgentTool(research_agent),
#                   ]
#
#   INPUT (via ADK Runner):
#     ParsedCommand — arrives as the user message in ADK's message format
#       {
#         domain          : DomainType
#         intent          : str
#         entities        : dict
#         priority        : int
#         ambiguity_score : float
#         session_ctx     : dict
#       }
#
#   OUTPUT (via ADK event stream):
#     - One or more AgentResult objects (from sub-agents)
#     - Natural language summary text (streamed as TextChunks)
#     - The event stream is consumed by synthesizer.build_response()
#
#   DELEGATION FLOW:
#     1. Gemini reads ParsedCommand
#     2. Decides: single agent or multi-agent?
#     3. For single: calls the relevant AgentTool
#     4. For compound: calls agents in sequence, passing intermediate results
#     5. Generates a summary of all actions
#
# ============================================================================
