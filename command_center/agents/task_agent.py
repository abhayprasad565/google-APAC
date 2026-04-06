# ============================================================================
# FILE: agents/task_agent.py
# LAYER: L3 — Task Management Sub-Agent
# ============================================================================
#
# PURPOSE:
#   L3 sub-agent responsible for task management. Owns a custom Cloud SQL
#   task tool (FunctionTool, NOT MCP). Handles creating, updating,
#   prioritising, and tracking tasks. Stores tasks in the Cloud SQL
#   database via task_db_tool → task_repository.
#
# KEY RESPONSIBILITIES:
#   1. Create tasks with inferred priority from user language
#   2. List tasks sorted by priority DESC, due_date ASC
#   3. Update task fields (status, priority, due_date, etc.)
#   4. Mark tasks as completed
#   5. Decompose large tasks into sub-tasks automatically
#
# ============================================================================
#
#
# ── CONSTANT: SYSTEM_INSTRUCTION ────────────────────────────────────────────
#
#   str — system prompt for the task agent
#
#   TEACHES THE MODEL TO:
#     - Use priority scoring: 1=low, 2=medium, 3=high, 4=urgent, 5=critical
#     - Infer priority from user language cues (e.g. "ASAP" → 4 or 5)
#     - Sort listings by: priority DESC, due_date ASC
#     - Break large tasks into sub-tasks automatically
#     - Track task dependencies
#
#
# ── OBJECT: task_agent ──────────────────────────────────────────────────────
#
# task_agent : LlmAgent
#
#   CONFIGURATION:
#     name        : "task_agent"
#     model       : "gemini-2.0-flash"
#     instruction : SYSTEM_INSTRUCTION
#     tools       : load_task_tools()  — from tools/task_db_tool.py
#
#   INPUT (from orchestrator via AgentTool call):
#     Natural language task description
#       e.g. "Create a high-priority task to prepare the Q3 report by June 15"
#
#     Session context:
#       {
#         user_id : str   — for task ownership
#       }
#
#   OUTPUT (returned to orchestrator):
#     Natural language confirmation text +
#     Structured result (varies by operation):
#
#     For task_create:
#       {
#         task_id     : str (UUID)
#         title       : str
#         priority    : int (1-5)
#         status      : str — "pending"
#         due_date    : str (ISO date) | None
#         tags        : list[str]
#       }
#
#     For task_list:
#       list[{
#         id          : str (UUID)
#         title       : str
#         priority    : int
#         status      : str
#         due_date    : str | None
#       }]
#
#     For task_complete:
#       {
#         task_id      : str
#         status       : "completed"
#         completed_at : str (ISO datetime)
#       }
#
#   TOOLS AVAILABLE (FunctionTool — from tools/task_db_tool.py):
#
#     - task_create(title, description, priority, due_date, tags)
#         INPUT:  title: str, description: str, priority: int (1-5),
#                 due_date: str (ISO date), tags: list[str]
#         OUTPUT: {task_id: str, title: str, priority: int}
#
#     - task_list(filter_status, filter_priority, limit)
#         INPUT:  filter_status: str (default "pending"),
#                 filter_priority: int | None, limit: int (default 20)
#         OUTPUT: list[{id, title, priority, due_date}]
#
#     - task_update(task_id, changes)
#         INPUT:  task_id: str, changes: dict (fields to update)
#         OUTPUT: {task_id: str, updated_fields: list[str]}
#
#     - task_complete(task_id)
#         INPUT:  task_id: str
#         OUTPUT: {task_id: str, status: "completed"}
#
#     - task_delete(task_id)
#         INPUT:  task_id: str
#         OUTPUT: {deleted: bool, task_id: str}
#
# ============================================================================
