"""
L6 — SQLAlchemy ORM Models

Defines the database tables for sessions, tasks, and agent logs.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class SessionRecord(Base):
    """Stores ADK session state for persistence across requests."""
    __tablename__ = "sessions"

    session_id = Column(String(64), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    state = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TaskRecord(Base):
    """Stores user tasks managed by the task_agent."""
    __tablename__ = "tasks"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    priority = Column(Integer, default=3)  # 1=low … 5=critical
    status = Column(
        SAEnum("pending", "in_progress", "completed", "cancelled", name="task_status"),
        default="pending",
        nullable=False,
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AgentLogRecord(Base):
    """Audit log of every agent invocation for debugging and analytics."""
    __tablename__ = "agent_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(64), nullable=False)
    action = Column(String(256), nullable=False)
    status = Column(String(32), nullable=False)  # success | partial | failed
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
