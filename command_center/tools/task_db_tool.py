"""
L4 — Cloud SQL Task CRUD FunctionTools

Wraps task_repository operations as functions callable by the task_agent.
Delegates all SQL to db/task_repository.py.
"""

from typing import Any, Optional
from datetime import datetime

from command_center.db import session_store, task_repository


async def task_create(
    title: str,
    description: str = "",
    priority: int = 3,
    due_date: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Create a new task in the database.

    Args:
        title: Task title, e.g. "Prepare Q3 report".
        description: Detailed task description.
        priority: 1 (low) to 5 (critical).
        due_date: ISO date string, e.g. "2025-06-15".
        tags: Categorisation tags, e.g. ["work", "report"].

    Returns:
        Dict with task_id, title, and priority.
    """
    parsed_due = datetime.fromisoformat(due_date) if due_date else None
    async with session_store.get_db_session() as db:
        return await task_repository.create_task(
            db=db,
            user_id="current_user",  # Will be injected from session context at runtime
            title=title,
            description=description,
            priority=priority,
            due_date=parsed_due,
            tags=tags,
        )


async def task_list(
    filter_status: str = "pending",
    filter_priority: Optional[int] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List tasks sorted by priority DESC, due_date ASC.

    Args:
        filter_status: Filter by status ("pending", "in_progress", "completed", "cancelled").
        filter_priority: Minimum priority threshold (inclusive).
        limit: Max number of tasks to return.

    Returns:
        List of task dicts with id, title, priority, due_date.
    """
    async with session_store.get_db_session() as db:
        return await task_repository.list_tasks(
            db=db,
            user_id="current_user",
            filter_status=filter_status,
            filter_priority=filter_priority,
            limit=limit,
        )


async def task_update(task_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    """Update one or more fields of an existing task.

    Args:
        task_id: UUID of the task to update.
        changes: Key-value pairs of fields to update (title, description, priority, due_date, tags, status).

    Returns:
        Dict with task_id and updated_fields.
    """
    async with session_store.get_db_session() as db:
        return await task_repository.update_task(db=db, task_id=task_id, changes=changes)


async def task_complete(task_id: str) -> dict[str, Any]:
    """Mark a task as completed.

    Args:
        task_id: UUID of the task to complete.

    Returns:
        Dict with task_id and status "completed".
    """
    async with session_store.get_db_session() as db:
        return await task_repository.complete_task(db=db, task_id=task_id)


async def task_delete(task_id: str) -> dict[str, Any]:
    """Permanently delete a task.

    Args:
        task_id: UUID of the task to delete.

    Returns:
        Dict with deleted (bool) and task_id.
    """
    async with session_store.get_db_session() as db:
        return await task_repository.delete_task(db=db, task_id=task_id)


def load_task_tools() -> list:
    """Returns the list of all task-related tools for the task_agent."""
    return [task_create, task_list, task_update, task_complete, task_delete]
