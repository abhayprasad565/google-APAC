# ============================================================================
# FILE: config/settings.py
# LAYER: Cross-cutting — Centralised Configuration
# ============================================================================
#
# PURPOSE:
#   Single configuration object using Pydantic BaseSettings. Reads all
#   environment variables (injected by Cloud Run from Secret Manager).
#   Every other module imports from here — NO direct os.getenv() calls
#   elsewhere in the codebase.
#
# KEY RESPONSIBILITIES:
#   1. Define all required and optional environment variables
#   2. Provide sensible defaults for non-secret settings
#   3. Support .env file for local development
#   4. Export a singleton Settings instance
#
# ============================================================================
#
#
# ── CLASS: Settings ─────────────────────────────────────────────────────────
#
# class Settings(BaseSettings)
#
#   TASK:
#     Loads all configuration from environment variables. In Cloud Run,
#     these are injected from Secret Manager at deploy time. Locally,
#     they are loaded from a .env file.
#
#   FIELDS:
#
#     # ── ADK / Gemini ──────────────────────────────────────────────────
#     GOOGLE_API_KEY   : str          — Gemini API key for all agents
#     GEMINI_MODEL     : str          — model name (default: "gemini-2.0-flash")
#
#     # ── OAuth for Google APIs ─────────────────────────────────────────
#     GOOGLE_CLIENT_ID        : str   — OAuth2 client ID
#     GOOGLE_CLIENT_SECRET    : str   — OAuth2 client secret
#     CALENDAR_REFRESH_TOKEN  : str   — Google Calendar OAuth refresh token
#     GMAIL_REFRESH_TOKEN     : str   — Gmail OAuth refresh token
#
#     # ── Search ────────────────────────────────────────────────────────
#     SEARCH_API_KEY   : str          — Google Custom Search API key
#     SEARCH_API_URL   : str          — Search endpoint URL
#                                       (default: "https://customsearch.googleapis.com/customsearch/v1")
#
#     # ── Database ──────────────────────────────────────────────────────
#     DATABASE_URL     : str          — Postgres connection string
#                                       e.g. "postgresql+asyncpg://user:pass@host/db"
#
#     # ── API ───────────────────────────────────────────────────────────
#     ALLOWED_ORIGINS  : list[str]    — CORS allowed origins
#                                       (default: ["*"])
#     API_KEY_HEADER   : str          — header name for API key auth
#                                       (default: "X-API-Key")
#
#     # ── Thresholds ────────────────────────────────────────────────────
#     AMBIGUITY_THRESHOLD : float     — NLU ambiguity cutoff
#                                       (default: 0.6)
#     TOOL_TIMEOUT_MS     : int       — default tool call timeout in ms
#                                       (default: 10000)
#
#   INNER CLASS Config:
#     env_file : str — ".env" (for local development)
#
#
# ── SINGLETON: settings ─────────────────────────────────────────────────────
#
#   settings : Settings
#   Module-level singleton instance. All other modules import this object:
#     from command_center.config.settings import settings
#
# ============================================================================
