# ============================================================================
# FILE: agents/calendar_agent.py
# LAYER: L3 — Calendar Domain Sub-Agent
# ============================================================================
#
# PURPOSE:
#   L3 sub-agent responsible for all calendar operations. Owns the Google
#   Calendar MCP toolset. Can schedule events, check availability, resolve
#   conflicts, and send invites.
#
# KEY RESPONSIBILITIES:
#   1. Check free/busy status before creating events
#   2. Handle scheduling conflicts by finding alternative slots
#   3. Create, update, and delete calendar events
#   4. Return structured event details with calendar links
#   5. Respect user timezone from session context
#
# ============================================================================
#
#
# ── CONSTANT: SYSTEM_INSTRUCTION ────────────────────────────────────────────
#
#   str — system prompt for the calendar agent
#
#   TEACHES THE MODEL TO:
#     - Check free/busy status for all attendees before scheduling
#     - If conflicts exist, find the next available slot
#     - Create events with all required fields
#     - Return event details including a calendar link
#     - Never double-book
#     - Always confirm timezone from session context
#
#
# ── OBJECT: calendar_agent ──────────────────────────────────────────────────
#
# calendar_agent : LlmAgent
#
#   CONFIGURATION:
#     name        : "calendar_agent"
#     model       : "gemini-2.0-flash"
#     instruction : SYSTEM_INSTRUCTION
#     tools       : load_calendar_tools()  — from tools/calendar_mcp.py
#
#   INPUT (from orchestrator via AgentTool call):
#     Natural language task description
#       e.g. "Schedule a 1-hour meeting with Alice on Friday at 2pm"
#
#     Session context (from ADK session state):
#       {
#         user_timezone       : str   — e.g. "Asia/Kolkata"
#         default_calendar_id : str   — e.g. "primary"
#       }
#
#   OUTPUT (returned to orchestrator):
#     Natural language confirmation text +
#     Structured result:
#       {
#         event_id    : str           — Google Calendar event ID
#         title       : str           — event title
#         start       : str           — ISO datetime of start
#         end         : str           — ISO datetime of end
#         attendees   : list[str]     — email addresses of attendees
#         invite_sent : bool          — whether calendar invites were sent
#         link        : str           — Google Calendar event URL
#       }
#
#   TOOLS AVAILABLE (from Google Calendar MCP):
#     - gcal_create_event(title, start, end, attendees, description)
#         INPUT:  title: str, start: str (ISO), end: str (ISO),
#                 attendees: list[str], description: str
#         OUTPUT: {event_id: str, link: str, status: str}
#
#     - gcal_list_events(start_date, end_date)
#         INPUT:  start_date: str (ISO), end_date: str (ISO)
#         OUTPUT: list[{event_id, title, start, end, attendees}]
#
#     - gcal_check_free_busy(emails, start, end)
#         INPUT:  emails: list[str], start: str (ISO), end: str (ISO)
#         OUTPUT: {email: [{busy_start, busy_end}]} — busy periods per email
#
#     - gcal_update_event(event_id, changes)
#         INPUT:  event_id: str, changes: dict (fields to update)
#         OUTPUT: {event_id: str, updated_fields: list[str]}
#
#     - gcal_delete_event(event_id)
#         INPUT:  event_id: str
#         OUTPUT: {deleted: bool, event_id: str}
#
# ============================================================================
