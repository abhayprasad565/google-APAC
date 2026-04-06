# ============================================================================
# FILE: api/middleware.py
# LAYER: L0 — Cross-cutting HTTP Middleware
# ============================================================================
#
# PURPOSE:
#   FastAPI middleware stack. Handles cross-cutting concerns that apply to
#   EVERY request: authentication header validation, CORS policy, and
#   structured request/response logging for Cloud Logging.
#
# KEY RESPONSIBILITIES:
#   1. Validate Bearer token or API key on every request
#   2. Attach authenticated user_id to request.state
#   3. Configure CORS for allowed origins
#   4. Emit structured JSON logs (method, path, status, latency)
#
# ============================================================================
#
#
# ── CLASS: AuthMiddleware ───────────────────────────────────────────────────
#
# class AuthMiddleware(BaseHTTPMiddleware)
#
#   TASK:
#     Intercepts every incoming HTTP request. Extracts the Bearer token
#     from the Authorization header (or an API key from X-API-Key header).
#     Validates the token against Cloud IAM or an internal API key store.
#     If invalid, returns 401 Unauthorized immediately. If valid, attaches
#     the authenticated user_id to request.state for downstream use.
#
#   INPUT:
#     request : Request
#       — FastAPI Request object. Reads headers:
#         Authorization : str  — "Bearer <token>"
#         X-API-Key     : str  — alternative API key auth
#
#   OUTPUT:
#     On success:
#       Mutates request.state.user_id = <authenticated_user_id>
#       Passes request to next middleware/route handler
#
#     On failure:
#       Returns JSONResponse with status 401
#       {
#         detail : str — "Invalid or missing authentication"
#       }
#
#
# ── CLASS: LoggingMiddleware ────────────────────────────────────────────────
#
# class LoggingMiddleware(BaseHTTPMiddleware)
#
#   TASK:
#     Captures structured telemetry for every request. Records start time,
#     HTTP method, path, session_id (if present), and after the response is
#     generated, records status code and total latency. Emits a structured
#     JSON log line to stdout (captured by Cloud Logging in Cloud Run).
#
#   INPUT:
#     request : Request — incoming HTTP request
#
#   OUTPUT:
#     None (pass-through to next handler)
#
#   SIDE EFFECTS:
#     Emits a JSON log entry to stdout:
#       {
#         method     : str      — e.g. "POST"
#         path       : str      — e.g. "/run"
#         session_id : str|None — extracted from body or query params
#         status     : int      — HTTP status code
#         latency_ms : int      — wall-clock request duration
#         timestamp  : str      — ISO 8601 timestamp
#       }
#
#
# ── FUNCTION: setup_cors ────────────────────────────────────────────────────
#
# function setup_cors(app: FastAPI, allowed_origins: list[str]) -> None
#
#   TASK:
#     Adds CORSMiddleware to the FastAPI app with the configured allowed
#     origins from settings.ALLOWED_ORIGINS. Allows all methods and headers
#     for development; production should restrict to specific origins.
#
#   INPUT:
#     app             : FastAPI    — the app instance
#     allowed_origins : list[str]  — e.g. ["https://myapp.com"] or ["*"]
#
#   OUTPUT:
#     None — mutates the app's middleware stack
#
# ============================================================================
