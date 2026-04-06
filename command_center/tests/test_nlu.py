# ============================================================================
# FILE: tests/test_nlu.py
# ============================================================================
#
# PURPOSE:
#   Tests for the NLU Layer (L1): intent classification, entity extraction,
#   and ambiguity resolution.
#
# ============================================================================
#
#
# ── TEST: test_classify_calendar_intent ─────────────────────────────────────
#   TASK: Verify that "Schedule a meeting" classifies to domain=calendar,
#         intent=create_meeting with high confidence
#   INPUT:  message="Schedule a meeting with Alice on Friday", session_ctx={}
#   EXPECTED: domain=calendar, intent="create_meeting", confidence > 0.8
#
#
# ── TEST: test_classify_compound_intent ─────────────────────────────────────
#   TASK: Verify that a multi-domain request classifies to domain=compound
#   INPUT:  message="Schedule a meeting and email the agenda", session_ctx={}
#   EXPECTED: domain=compound, intent="multi_step"
#
#
# ── TEST: test_extract_calendar_entities ────────────────────────────────────
#   TASK: Verify entity extraction for a calendar intent
#   INPUT:  message="Meeting with bob@co.com Friday 3pm", intent="create_meeting"
#   EXPECTED: entities contains date (ISO), attendees=["bob@co.com"]
#
#
# ── TEST: test_extract_task_entities ────────────────────────────────────────
#   TASK: Verify entity extraction for a task intent
#   INPUT:  message="Create urgent task: prepare Q3 report by June 15",
#           intent="create_task"
#   EXPECTED: entities contains title, priority >= 4, due_date
#
#
# ── TEST: test_ambiguity_resolved ───────────────────────────────────────────
#   TASK: Verify that a fully specified command passes ambiguity check
#   INPUT:  ParsedCommand with all required entities present
#   EXPECTED: resolved=True, ambiguity_score=0.0
#
#
# ── TEST: test_ambiguity_needs_clarification ────────────────────────────────
#   TASK: Verify that a vague command triggers clarification
#   INPUT:  ParsedCommand with intent="create_meeting", entities={}
#   EXPECTED: resolved=False, clarification_question is not None
#
#
# ── TEST: test_ambiguity_fills_defaults ─────────────────────────────────────
#   TASK: Verify that tolerable ambiguity fills defaults
#   INPUT:  ParsedCommand with intent="create_meeting",
#           entities={date: ..., attendees: ...} but missing duration
#   EXPECTED: resolved=True, entities.duration filled with default (30)
#
# ============================================================================
