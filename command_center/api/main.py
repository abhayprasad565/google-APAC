# ============================================================================
# FILE: api/main.py
# LAYER: L0 (User Interface) — FastAPI Application Entry Point
# ============================================================================
#
# PURPOSE:
#   FastAPI application entry point. Defines all HTTP routes, initializes the
#   ADK Runner and SessionService at startup, and wires together L0 (input
#   capture) and L7 (response delivery). This is the ONLY file that starts
#   the server.
#
# KEY RESPONSIBILITIES:
#   1. Register all routes: /run, /stream, /health, /sessions/{id}
#   2. Instantiate root_agent, SessionService, and ADK Runner at startup
#   3. Pass raw user request to the NLU pipeline (L1), then hand the
#      resulting ParsedCommand to the ADK Runner (L2)
#   4. Call synthesizer.build_response() on the Runner event stream to
#      produce a FinalResponse (L7)
#   5. Handle both JSON and SSE (Server-Sent Events) response modes
#
# ============================================================================
#
# ── STARTUP (Lifespan Event) ────────────────────────────────────────────────
#
# function: lifespan(app: FastAPI) -> AsyncContextManager
#
#   TASK:
#     Runs once when the server starts. Loads settings, creates the Cloud SQL
#     connection pool, initialises the ADK SessionService and Runner, and
#     mounts middleware. On shutdown, closes the DB pool and MCP connections.
#
#   INPUT:
#     app : FastAPI
#       The FastAPI application instance (injected by framework)
#
#   OUTPUT:
#     None — mutates app.state to attach:
#       app.state.session_service : CloudSqlSessionService
#       app.state.runner          : Runner
#       app.state.settings        : Settings
#
#   SIDE EFFECTS:
#     - Opens a Cloud SQL connection pool
#     - Creates the ADK Runner wrapping root_agent
#     - Mounts CORSMiddleware, AuthMiddleware, LoggingMiddleware
#
#
# ── ROUTE: POST /run ────────────────────────────────────────────────────────
#
# function: handle_run(request: UserRequest) -> FinalResponse
#
#   TASK:
#     Receives a natural-language user request, pipes it through the full
#     L0→L1→L2→L3→L4→L7 pipeline, and returns the final synthesised answer
#     as a JSON response.
#
#   INPUT:
#     request : UserRequest
#       {
#         session_id    : str            — client-provided or auto-generated
#         user_id       : str            — authenticated user identifier
#         message       : str            — raw natural-language command
#         context_hints : list[str]      — optional disambiguation hints
#         timestamp     : datetime       — auto-set to now()
#       }
#
#   OUTPUT:
#     FinalResponse
#       {
#         session_id    : str
#         summary       : str            — human-readable result narrative
#         actions_taken : list[ActionRecord]
#         follow_ups    : list[str]      — suggested next actions
#         render_format : Enum[json, text, sse]
#       }
#
#   INTERNAL FLOW:
#     1. session = session_service.get_or_create(session_id, user_id)
#     2. parsed  = nlu_pipeline.process(message, session.context)
#     3. events  = runner.run(session_id, parsed.to_adk_message())
#     4. response = synthesizer.build_response(events, session_id)
#     5. return FinalResponse
#
#
# ── ROUTE: GET /stream ──────────────────────────────────────────────────────
#
# function: handle_stream(session_id: str, user_id: str, message: str) -> EventSourceResponse
#
#   TASK:
#     Same pipeline as POST /run but streams intermediate ADK events back
#     to the client as Server-Sent Events (SSE) in real time.
#
#   INPUT:
#     session_id : str   — query parameter
#     user_id    : str   — query parameter
#     message    : str   — query parameter — raw user command
#
#   OUTPUT:
#     EventSourceResponse  — SSE stream where each event is a JSON chunk:
#       {
#         event_type : str     — "text_chunk" | "agent_result" | "done"
#         data       : dict    — varies by event_type
#       }
#
#
# ── ROUTE: GET /sessions/{id} ───────────────────────────────────────────────
#
# function: get_session(session_id: str) -> dict
#
#   TASK:
#     Returns the current state of a session from the SessionService so
#     the client can inspect conversation history and context.
#
#   INPUT:
#     session_id : str — path parameter
#
#   OUTPUT:
#     dict
#       {
#         session_id : str
#         user_id    : str
#         state      : dict    — full ADK session state blob
#         created_at : datetime
#         updated_at : datetime
#       }
#
#
# ── ROUTE: GET /health ──────────────────────────────────────────────────────
#
# function: health_check() -> dict
#
#   TASK:
#     Liveness/readiness probe for Cloud Run. Pings the DB connection pool
#     and verifies that the Runner and agents are loaded.
#
#   INPUT:
#     None
#
#   OUTPUT:
#     dict
#       {
#         status : str   — "ok"
#         agents : int   — number of registered sub-agents (expected: 4)
#         db     : str   — "connected" | "error"
#       }
#
# ============================================================================
