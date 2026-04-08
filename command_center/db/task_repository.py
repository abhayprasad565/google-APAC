"""
L6 — Task Repository

Task CRUD operations backed by SQLAlchemy async sessions.
Used by tools/task_db_tool.py — keeps SQL out of agent/tool files.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from command_center.db.models import TaskRecord


async def create_task(
    db: AsyncSession,
    user_id: str,
    title: str,
    description: str = "",
    priority: int = 3,
    due_date: Optional[datetime] = None,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Create a new task and return its summary."""
    task = TaskRecord(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        description=description,
        priority=max(1, min(5, priority)),  # Clamp to 1-5
        due_date=due_date,
        tags=tags or [],
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {
        "task_id": str(task.id),
        "title": task.title,
        "priority": task.priority,
    }


async def list_tasks(
    db: AsyncSession,
    user_id: str,
    filter_status: str = "pending",
    filter_priority: Optional[int] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List tasks sorted by priority DESC, due_date ASC."""
    stmt = (
        select(TaskRecord)
        .where(TaskRecord.user_id == user_id)
        .where(TaskRecord.status == filter_status)
    )
    if filter_priority is not None:
        stmt = stmt.where(TaskRecord.priority >= filter_priority)

    stmt = stmt.order_by(
        TaskRecord.priority.desc(),
        TaskRecord.due_date.asc().nulls_last(),
    ).limit(limit)

    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        }
        for t in tasks
    ]


async def update_task(
    db: AsyncSession,
    task_id: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    """Update specific fields of a task."""
    allowed_fields = {"title", "description", "priority", "due_date", "tags", "status"}
    valid_changes = {k: v for k, v in changes.items() if k in allowed_fields}

    if "priority" in valid_changes:
        valid_changes["priority"] = max(1, min(5, valid_changes["priority"]))

    stmt = (
        update(TaskRecord)
        .where(TaskRecord.id == task_id)
        .values(**valid_changes, updated_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)
    await db.commit()
    return {"task_id": task_id, "updated_fields": list(valid_changes.keys())}


async def complete_task(db: AsyncSession, task_id: str) -> dict[str, Any]:
    """Mark a task as completed."""
    now = datetime.now(timezone.utc)
    stmt = (
        update(TaskRecord)
        .where(TaskRecord.id == task_id)
        .values(status="completed", completed_at=now, updated_at=now)
    )
    await db.execute(stmt)
    await db.commit()
    return {"task_id": task_id, "status": "completed"}


async def delete_task(db: AsyncSession, task_id: str) -> dict[str, Any]:
    """Permanently delete a task."""
    stmt = delete(TaskRecord).where(TaskRecord.id == task_id)
    result = await db.execute(stmt)
    await db.commit()
    return {"deleted": result.rowcount > 0, "task_id": task_id}
