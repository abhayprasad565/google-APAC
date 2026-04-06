# ============================================================================
# MODULE: db (L6 — Database Models, Session Service, Migrations)
# ============================================================================
#
# This package contains the database layer — ORM models, the custom
# ADK SessionService backed by Cloud SQL, and the task repository.
#
# Files in this package:
#   - models.py          → SQLAlchemy ORM models (sessions, tasks, agent_logs,
#                           user_preferences)
#   - session_store.py   → ADK SessionService backed by Cloud SQL
#   - task_repository.py → Task CRUD data access layer
#   - migrations/        → Alembic migration scripts
# ============================================================================
