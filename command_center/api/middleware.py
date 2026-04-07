"""
L0 — Cross-cutting HTTP Middleware

FastAPI middleware stack for authentication, structured request logging,
and CORS policy. Applied to every incoming HTTP request.
"""

import json
import time
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from command_center.config.settings import settings

logger = logging.getLogger("command_center.api")


# ── Auth Middleware ──────────────────────────────────────────────────────────

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Validates Bearer token or API key on every request.
    Skips auth for /health and /docs endpoints.
    In development mode (no API keys configured), auth is bypassed.
    """

    # Paths that never require authentication
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Development mode: if no API keys are configured, skip auth
        if not settings.GOOGLE_API_KEY:
            request.state.user_id = "dev_user"
            return await call_next(request)

        # Try Bearer token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            if token:
                request.state.user_id = _extract_user_from_token(token)
                return await call_next(request)

        # Try API key from the configured header
        api_key = request.headers.get(settings.API_KEY_HEADER, "")
        if api_key:
            request.state.user_id = f"apikey_{api_key[:8]}"
            return await call_next(request)

        # No valid credentials found
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing authentication"},
        )


def _extract_user_from_token(token: str) -> str:
    """
    Extract user identity from a Bearer token.
    In production this would validate against Cloud IAM or decode a JWT.
    For now, we use a placeholder extraction.
    """
    # TODO: Implement proper JWT / Cloud IAM validation
    return f"user_{token[:12]}"


# ── Logging Middleware ───────────────────────────────────────────────────────

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Captures structured telemetry for every request.
    Emits JSON log entries suitable for Cloud Logging.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.monotonic()

        # Attempt to extract session_id from query params or body
        session_id = request.query_params.get("session_id")

        response = await call_next(request)

        latency_ms = int((time.monotonic() - start_time) * 1000)

        log_entry = {
            "method": request.method,
            "path": request.url.path,
            "session_id": session_id,
            "status": response.status_code,
            "latency_ms": latency_ms,
        }

        # Use appropriate log level based on status code
        if response.status_code >= 500:
            logger.error(json.dumps(log_entry))
        elif response.status_code >= 400:
            logger.warning(json.dumps(log_entry))
        else:
            logger.info(json.dumps(log_entry))

        return response


# ── CORS Setup ───────────────────────────────────────────────────────────────

def setup_cors(app: FastAPI, allowed_origins: Optional[list[str]] = None) -> None:
    """
    Adds CORSMiddleware to the FastAPI app with the configured allowed origins.
    Falls back to settings.ALLOWED_ORIGINS if none provided.
    """
    origins = allowed_origins or settings.ALLOWED_ORIGINS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ── Middleware Stack Setup ───────────────────────────────────────────────────

def setup_middleware(app: FastAPI) -> None:
    """
    Mounts all middleware in the correct order.
    Order matters: outermost middleware runs first.
    CORS → Logging → Auth
    """
    # Auth runs closest to the route handlers
    app.add_middleware(AuthMiddleware)

    # Logging wraps auth so we capture latency for 401s too
    app.add_middleware(LoggingMiddleware)

    # CORS runs outermost to handle preflight requests
    setup_cors(app)
