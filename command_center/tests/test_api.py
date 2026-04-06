# ============================================================================
# FILE: tests/test_api.py
# ============================================================================
#
# PURPOSE:
#   Tests for the API Layer (L0 + L7): FastAPI routes, middleware,
#   and response synthesis.
#
# ============================================================================
#
#
# ── TEST: test_health_endpoint ──────────────────────────────────────────────
#   TASK: Verify GET /health returns 200 with status "ok"
#   INPUT:  GET /health
#   EXPECTED: status=200, body={status: "ok", agents: 4, db: "connected"}
#
#
# ── TEST: test_run_endpoint_returns_final_response ──────────────────────────
#   TASK: Verify POST /run returns a valid FinalResponse
#   INPUT:  UserRequest{session_id: "test", user_id: "u1",
#                       message: "List my tasks"}
#   EXPECTED: status=200, body matches FinalResponse schema
#
#
# ── TEST: test_run_endpoint_invalid_body ────────────────────────────────────
#   TASK: Verify POST /run returns 422 for invalid request body
#   INPUT:  Invalid JSON (missing required fields)
#   EXPECTED: status=422
#
#
# ── TEST: test_auth_middleware_rejects_missing_token ─────────────────────────
#   TASK: Verify requests without auth header are rejected
#   INPUT:  POST /run without Authorization header
#   EXPECTED: status=401
#
#
# ── TEST: test_session_endpoint ─────────────────────────────────────────────
#   TASK: Verify GET /sessions/{id} returns session state
#   INPUT:  GET /sessions/test-session-id (after creating via /run)
#   EXPECTED: status=200, body contains session_id, state dict
#
#
# ── TEST: test_synthesizer_merges_results ───────────────────────────────────
#   TASK: Verify synthesizer.build_response merges multiple AgentResults
#   INPUT:  Mock event stream with 2 AgentResults + TextChunks
#   EXPECTED: FinalResponse with 2 ActionRecords and merged summary
#
#
# ── TEST: test_synthesizer_generates_follow_ups ─────────────────────────────
#   TASK: Verify synthesizer generates relevant follow-up suggestions
#   INPUT:  AgentResult from calendar_agent (event created, no email)
#   EXPECTED: follow_ups contain suggestion to email attendees
#
#
# ── TEST: test_stream_endpoint_returns_sse ──────────────────────────────────
#   TASK: Verify GET /stream returns Server-Sent Events
#   INPUT:  GET /stream?session_id=test&user_id=u1&message=hello
#   EXPECTED: Content-Type="text/event-stream", body contains SSE events
#
# ============================================================================
