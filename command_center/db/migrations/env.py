# ============================================================================
# FILE: db/migrations/env.py
# LAYER: L6 — Alembic Migration Environment
# ============================================================================
#
# PURPOSE:
#   Alembic migration environment configuration. Connects Alembic to the
#   Cloud SQL database using the DATABASE_URL from settings. Imports all
#   ORM models from db/models.py so Alembic can auto-detect schema changes.
#
# KEY RESPONSIBILITIES:
#   1. Load DATABASE_URL from config/settings.py
#   2. Import all ORM models for autogenerate support
#   3. Configure online/offline migration modes
#   4. Run migrations against the Cloud SQL instance
#
# ── FUNCTION: run_migrations_online ─────────────────────────────────────────
#
#   TASK:
#     Runs migrations in "online" mode with a live database connection.
#     Creates an async engine, connects, and runs the migration within
#     a transaction.
#
#   INPUT:  None (reads DATABASE_URL from settings)
#   OUTPUT: None (applies migrations to the database)
#
# ── FUNCTION: run_migrations_offline ────────────────────────────────────────
#
#   TASK:
#     Runs migrations in "offline" mode — generates SQL scripts without
#     connecting to the database. Used for reviewing migration SQL.
#
#   INPUT:  None (reads DATABASE_URL from settings)
#   OUTPUT: None (emits SQL to stdout)
#
# ============================================================================
