# ============================================================================
# FILE: db/task_repository.py
# LAYER: L6 — Task Data Access Layer
# ============================================================================
#
# PURPOSE:
#   Data access layer for the `tasks` table. ALL SQL queries for task
#   operations live here. Called by tools/task_db_tool.py. Keeps SQL out
#   of tool and agent files (separation of concerns).
#
# KEY RESPONSIBILITIES:
#   1. CRUD operations for the tasks table
#   2. Filtering by status, priority, user
#   3. Sorting by priority DESC, due_date ASC
#   4. Return ORM Task objects to callers
#
# ============================================================================
#
#
# ── FUNCTION: create ────────────────────────────────────────────────────────
#
# async function create(task_data: dict) -> Task
#
#   TASK:
#     Inserts a new task record into the tasks table.
#
#   INPUT:
#     task_data : dict
#       {
#         user_id     : str          — the owning user
#         title       : str          — task title
#         description : str          — detailed description
#         priority    : int          — 1-5
#         due_date    : datetime     — parsed deadline
#         tags        : list[str]   — categorisation tags
#         status      : str          — "pending" (always for new tasks)
#       }
#
#   OUTPUT:
#     Task — SQLAlchemy ORM Task object with all fields populated,
#            including the auto-generated id and created_at
#
#
# ── FUNCTION: list ──────────────────────────────────────────────────────────
#
# async function list(user_id, filter_status, filter_priority, limit) -> list[Task]
#
#   TASK:
#     Queries tasks for a specific user with optional filters. Results
#     are always sorted by priority DESC, due_date ASC.
#
#   INPUT:
#     user_id         : str       — filter to this user's tasks
#     filter_status   : str|None  — status to filter on
#                                   (e.g. "pending", "completed")
#     filter_priority : int|None  — minimum priority (inclusive)
#     limit           : int       — max results to return
#
#   OUTPUT:
#     list[Task] — list of ORM Task objects, sorted by:
#                  priority DESC, due_date ASC
#
#
# ── FUNCTION: get ───────────────────────────────────────────────────────────
#
# async function get(task_id: str) -> Task | None
#
#   TASK:
#     Retrieves a single task by its UUID.
#
#   INPUT:
#     task_id : str — UUID of the task
#
#   OUTPUT:
#     Task | None — the Task object if found, None otherwise
#
#
# ── FUNCTION: update ────────────────────────────────────────────────────────
#
# async function update(task_id, changes: dict) -> Task
#
#   TASK:
#     Updates specific fields of an existing task. Only the keys
#     present in the changes dict are modified.
#
#   INPUT:
#     task_id : str    — UUID of the task to update
#     changes : dict   — key-value pairs to update
#                        Valid keys: title, description, priority,
#                                    due_date, tags, status, completed_at
#
#   OUTPUT:
#     Task — the updated ORM Task object
#
#   SIDE EFFECTS:
#     - Commits the transaction
#
#
# ── FUNCTION: delete ────────────────────────────────────────────────────────
#
# async function delete(task_id: str) -> bool
#
#   TASK:
#     Permanently removes a task from the database.
#
#   INPUT:
#     task_id : str — UUID of the task to delete
#
#   OUTPUT:
#     bool — True if the task was found and deleted, False if not found
#
#   SIDE EFFECTS:
#     - Commits the transaction
#
# ============================================================================
