# ============================================================================
# FILE: agents/email_agent.py
# LAYER: L3 — Email Domain Sub-Agent
# ============================================================================
#
# PURPOSE:
#   L3 sub-agent responsible for email operations. Owns the Gmail MCP
#   toolset. Can draft emails from natural language descriptions, summarise
#   inbox threads, send replies, and manage labels.
#
# KEY RESPONSIBILITIES:
#   1. Draft emails matching the requested tone (formal, casual, assertive)
#   2. Present drafts for review before sending
#   3. Send emails only with explicit confirmation from orchestrator
#   4. Summarise threads extracting decisions, action items, deadlines
#   5. Manage email labels
#
# ============================================================================
#
#
# ── CONSTANT: SYSTEM_INSTRUCTION ────────────────────────────────────────────
#
#   str — system prompt for the email agent
#
#   TEACHES THE MODEL TO:
#     - Match the requested tone: formal, casual, assertive, friendly
#     - When drafting: produce email body first, then ask whether to send
#     - Never send an email without explicit orchestrator confirmation
#     - When summarising threads: extract key decisions, action items,
#       and deadlines
#     - Include context from other agents (e.g. meeting details from
#       calendar_agent) when drafting
#
#
# ── OBJECT: email_agent ─────────────────────────────────────────────────────
#
# email_agent : LlmAgent
#
#   CONFIGURATION:
#     name        : "email_agent"
#     model       : "gemini-2.0-flash"
#     instruction : SYSTEM_INSTRUCTION
#     tools       : load_gmail_tools()  — from tools/gmail_mcp.py
#
#   INPUT (from orchestrator via AgentTool call):
#     Natural language email intent:
#       e.g. "Email alice@co.com with the agenda for our Friday 2pm meeting"
#
#     Optional context from other agents:
#       {
#         calendar_event : dict   — event details from calendar_agent
#         research_data  : dict   — research findings from research_agent
#       }
#
#     Session context:
#       {
#         email_tone : str   — user's default tone preference
#       }
#
#   OUTPUT (returned to orchestrator):
#     Natural language confirmation text +
#     Structured result (varies by operation):
#
#     For gmail_draft:
#       {
#         draft_id : str      — Gmail draft ID
#         to       : list[str]
#         subject  : str
#         body     : str      — full drafted email text
#         status   : str      — "draft_created"
#       }
#
#     For gmail_send / gmail_send_direct:
#       {
#         message_id : str    — Gmail message ID
#         to         : list[str]
#         subject    : str
#         status     : str    — "sent"
#       }
#
#     For gmail_list_threads (summarise):
#       list[{
#         thread_id  : str
#         subject    : str
#         summary    : str
#         decisions  : list[str]
#         action_items: list[str]
#         deadlines  : list[str]
#       }]
#
#   TOOLS AVAILABLE (from Gmail MCP):
#
#     - gmail_draft(to, subject, body, cc, attachments)
#         INPUT:  to: list[str], subject: str, body: str,
#                 cc: list[str] | None, attachments: list[str] | None
#         OUTPUT: {draft_id: str, message_id: str}
#
#     - gmail_send(draft_id)
#         INPUT:  draft_id: str
#         OUTPUT: {message_id: str, status: "sent"}
#
#     - gmail_send_direct(to, subject, body)
#         INPUT:  to: list[str], subject: str, body: str
#         OUTPUT: {message_id: str, status: "sent"}
#
#     - gmail_list_threads(query, max_results)
#         INPUT:  query: str (Gmail search syntax), max_results: int
#         OUTPUT: list[{thread_id, subject, snippet, date}]
#
#     - gmail_get_thread(thread_id)
#         INPUT:  thread_id: str
#         OUTPUT: {thread_id, subject, messages: list[{from, to, body, date}]}
#
#     - gmail_reply(thread_id, body)
#         INPUT:  thread_id: str, body: str
#         OUTPUT: {message_id: str, status: "sent"}
#
# ============================================================================
