# ============================================================================
# FILE: db/models.py
# LAYER: L6 — Database ORM Models
# ============================================================================
#
# PURPOSE:
#   SQLAlchemy ORM model definitions for all Cloud SQL tables. Four tables
#   back the L6 memory layer. This file contains NO business logic — only
#   table/column definitions.
#
# ============================================================================
#
#
# ── TABLE: sessions ─────────────────────────────────────────────────────────
#
#   TASK:
#     Stores ADK session state. Each session represents a conversation
#     between a user and the command center. The state_json field holds
#     the full ADK session state blob (conversation history, context).
#
#   COLUMNS:
#     id          : UUID       — Primary Key, auto-generated
#     user_id     : str        — Indexed, the owning user
#     state_json  : JSONB      — ADK session state blob
#                                (conversation history, agent context)
#     created_at  : datetime   — auto-set on insert
#     updated_at  : datetime   — auto-set on insert and update
#
#   INDEXES:
#     - idx_sessions_user_id ON user_id
#
#
# ── TABLE: tasks ────────────────────────────────────────────────────────────
#
#   TASK:
#     Stores user tasks managed by the task_agent. Supports full CRUD
#     operations via task_repository.py.
#
#   COLUMNS:
#     id           : UUID                                    — Primary Key
#     user_id      : str                                     — Indexed
#     session_id   : UUID                                    — Foreign Key → sessions.id
#     title        : str                                     — task title
#     description  : text                                    — detailed description
#     priority     : int (1-5)                               — 1=low, 5=critical
#     status       : Enum[pending, in_progress, completed, cancelled]
#     due_date     : datetime | null                         — optional deadline
#     tags         : ARRAY[str]                              — categorisation tags
#     created_at   : datetime                                — auto-set on insert
#     completed_at : datetime | null                         — set when completed
#
#   INDEXES:
#     - idx_tasks_user_id ON user_id
#     - idx_tasks_status ON status
#     - idx_tasks_priority ON priority
#
#   FOREIGN KEYS:
#     - session_id → sessions.id (ON DELETE CASCADE)
#
#
# ── TABLE: agent_logs ───────────────────────────────────────────────────────
#
#   TASK:
#     Audit trail for every tool call made by every agent. Used for
#     debugging, performance monitoring, and usage analytics.
#
#   COLUMNS:
#     id          : UUID        — Primary Key
#     session_id  : UUID        — Foreign Key → sessions.id
#     agent_id    : str         — which agent made the call
#                                 (e.g. "calendar_agent", "task_agent")
#     task_id     : UUID | null — the AgentTask this was part of (if any)
#     tool_name   : str         — which tool was invoked
#                                 (e.g. "gcal_create_event", "task_create")
#     input_json  : JSONB       — the tool call parameters
#     output_json : JSONB       — the tool call response
#     latency_ms  : int         — wall-clock time for the tool call
#     status      : str         — "success", "error", "timeout"
#     created_at  : datetime    — auto-set on insert
#
#   INDEXES:
#     - idx_agent_logs_session_id ON session_id
#     - idx_agent_logs_agent_id ON agent_id
#
#   FOREIGN KEYS:
#     - session_id → sessions.id (ON DELETE CASCADE)
#
#
# ── TABLE: user_preferences ─────────────────────────────────────────────────
#
#   TASK:
#     Stores per-user preferences that agents reference when making
#     decisions (timezone, default calendar, email tone, notifications).
#
#   COLUMNS:
#     user_id             : str          — Primary Key
#     timezone            : str          — e.g. "Asia/Kolkata", "America/New_York"
#     default_calendar_id : str          — Google Calendar ID (default: "primary")
#     email_tone          : Enum[formal, casual, friendly]  — default email tone
#     notification_prefs  : JSONB        — notification configuration
#                                          e.g. {email: true, sms: false,
#                                                summary_frequency: "daily"}
#
# ============================================================================
