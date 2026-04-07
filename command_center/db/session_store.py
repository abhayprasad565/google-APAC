"""
L6 — ADK Session Store backed by Cloud SQL

Provides get/save session operations for the ADK Runner,
persisting session state to the sessions table.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from command_center.config.settings import settings
from command_center.db.models import SessionRecord, Base

# Async engine and session factory — initialised lazily
_engine = None
_async_session_factory = None


async def init_db() -> None:
    """Initialise the async engine, session factory, and create tables if needed."""
    global _engine, _async_session_factory
    _engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=5)
    _async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    # Create tables (in production, use Alembic migrations instead)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine and connection pool."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


def get_db_session() -> AsyncSession:
    """Returns a new async DB session. Caller must use `async with` or close it."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _async_session_factory()


async def get_or_create_session(
    session_id: str, user_id: str
) -> dict[str, Any]:
    """
    Retrieve an existing session or create a new one.
    Returns a dict with session_id, user_id, state, created_at, updated_at.
    """
    async with get_db_session() as db:
        stmt = select(SessionRecord).where(SessionRecord.session_id == session_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            return _record_to_dict(record)

        # Create new session
        record = SessionRecord(
            session_id=session_id,
            user_id=user_id,
            state={},
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return _record_to_dict(record)


async def save_session_state(session_id: str, state: dict[str, Any]) -> None:
    """Persist updated session state to the database."""
    async with get_db_session() as db:
        stmt = select(SessionRecord).where(SessionRecord.session_id == session_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            record.state = state
            record.updated_at = datetime.now(timezone.utc)
            await db.commit()


async def get_session(session_id: str) -> Optional[dict[str, Any]]:
    """Retrieve a session by ID. Returns None if not found."""
    async with get_db_session() as db:
        stmt = select(SessionRecord).where(SessionRecord.session_id == session_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            return _record_to_dict(record)
        return None


def _record_to_dict(record: SessionRecord) -> dict[str, Any]:
    """Convert a SessionRecord ORM object to a plain dict."""
    return {
        "session_id": record.session_id,
        "user_id": record.user_id,
        "state": record.state or {},
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
