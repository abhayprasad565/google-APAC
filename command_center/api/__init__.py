# ============================================================================
# MODULE: api (L0 + L7 — FastAPI Entrypoint & Response Synthesis)
# ============================================================================
#
# This package contains the HTTP-facing layer (L0) and the response
# synthesis layer (L7). It is the boundary between the outside world
# and the internal agent pipeline.
#
# Files in this package:
#   - main.py        → FastAPI app, route definitions, ADK Runner bootstrap
#   - schemas.py     → All Pydantic DTOs (data contracts between layers)
#   - synthesizer.py → Aggregates multi-agent results into FinalResponse
#   - middleware.py  → Auth, CORS, structured request logging middleware
# ============================================================================
