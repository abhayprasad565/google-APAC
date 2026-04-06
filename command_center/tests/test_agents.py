# ============================================================================
# FILE: tests/test_agents.py
# ============================================================================
#
# PURPOSE:
#   Tests for the Agent Layer (L2 + L3): root agent delegation and
#   sub-agent behaviour.
#
# ============================================================================
#
#
# ── TEST: test_root_agent_routes_to_calendar ────────────────────────────────
#   TASK: Verify root_agent delegates a calendar request to calendar_agent
#   INPUT:  ParsedCommand(domain=calendar, intent="create_meeting", ...)
#   EXPECTED: calendar_agent is invoked via AgentTool
#
#
# ── TEST: test_root_agent_routes_to_task ────────────────────────────────────
#   TASK: Verify root_agent delegates a task request to task_agent
#   INPUT:  ParsedCommand(domain=task, intent="create_task", ...)
#   EXPECTED: task_agent is invoked via AgentTool
#
#
# ── TEST: test_root_agent_compound_request ──────────────────────────────────
#   TASK: Verify root_agent calls multiple sub-agents in sequence for
#         a compound request
#   INPUT:  ParsedCommand(domain=compound, intent="multi_step", ...)
#           e.g. "Schedule meeting and email agenda"
#   EXPECTED: calendar_agent called first, then email_agent with calendar
#             result as context
#
#
# ── TEST: test_calendar_agent_checks_availability ───────────────────────────
#   TASK: Verify calendar_agent calls gcal_check_free_busy before creating
#   INPUT:  "Schedule meeting with alice@co.com Friday 2pm"
#   EXPECTED: gcal_check_free_busy called, then gcal_create_event
#
#
# ── TEST: test_task_agent_creates_task ──────────────────────────────────────
#   TASK: Verify task_agent calls task_create with correct parameters
#   INPUT:  "Create task: prepare Q3 report, priority 4, due June 15"
#   EXPECTED: task_create called with title, priority=4, due_date
#
#
# ── TEST: test_email_agent_drafts_before_send ───────────────────────────────
#   TASK: Verify email_agent creates a draft first and confirms before send
#   INPUT:  "Email alice@co.com about the meeting"
#   EXPECTED: gmail_draft called (not gmail_send_direct)
#
#
# ── TEST: test_research_agent_multiple_queries ──────────────────────────────
#   TASK: Verify research_agent decomposes topic into multiple searches
#   INPUT:  "Research AI agent frameworks"
#   EXPECTED: google_search called 2-3 times with different queries
#
# ============================================================================
