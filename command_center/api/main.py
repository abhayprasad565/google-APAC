"""
L0 — FastAPI Application Entry Point

Defines HTTP routes, initialises the ADK Runner and SessionService at
startup, and wires together L0 (input capture) and L7 (response delivery).
This is the ONLY file that starts the server.
"""

import logging
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from command_center.config.settings import settings
from command_center.api.schemas import (
    UserRequest,
    ParsedCommand,
    FinalResponse,
)
from command_center.api.middleware import setup_middleware
from command_center.api.synthesizer import build_response, format_sse_event
from command_center.nlu.intent_classifier import classify_intent
from command_center.nlu.entity_extractor import extract_entities
from command_center.nlu.ambiguity_resolver import resolve_ambiguity, fill_defaults
from command_center.db.session_store import (
    init_db,
    close_db,
    get_or_create_session,
    get_session,
    save_session_state,
)

# ── ADK imports — graceful fallback if not installed ────────────────────────

try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import AgentTool
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

    class LlmAgent:
        def __init__(self, **kwargs):
            self.config = kwargs
            self.name = kwargs.get("name", "stub_agent")

    class AgentTool:
        def __init__(self, agent):
            self.agent = agent

    class InMemorySessionService:
        """Stub session service when ADK is not installed."""
        async def get_session(self, **kwargs):
            return None
        async def create_session(self, **kwargs):
            return type("Session", (), {"id": kwargs.get("session_id", "stub"), "state": {}})()

    class Runner:
        """Stub runner when ADK is not installed."""
        def __init__(self, **kwargs):
            self.agent = kwargs.get("agent")
            self.app_name = kwargs.get("app_name", "command_center")

        async def run_async(self, **kwargs):
            """Yield a stub response event."""
            content = kwargs.get("new_message", "")
            yield _make_stub_event(
                f"[Stub Mode] Received: {content}. "
                f"ADK is not installed — agents are not running. "
                f"Install google-adk to enable full agent functionality."
            )


logger = logging.getLogger("command_center.api")


# ── Agent Factory ───────────────────────────────────────────────────────────

async def create_agents() -> dict[str, Any]:
    """
    Creates all agents with their tools loaded asynchronously.
    Returns a dict with the root_agent and runner.

    This factory pattern avoids calling async tool loaders at module
    import time — the issue flagged in the code review.
    """
    # Import agent modules — these create LlmAgent instances at module level
    # The current agents use sync stubs for tool loading, which works for now.
    # When we switch to real async MCP connections, we'll refactor the tool
    # loading into this factory.
    from command_center.agents.root_agent import root_agent

    # Create the ADK session service and runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="command_center",
        session_service=session_service,
    )

    return {
        "root_agent": root_agent,
        "session_service": session_service,
        "runner": runner,
    }


# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler. Initialises all services on startup
    and tears them down on shutdown.
    """
    logger.info("Starting ADK Command Center...")

    # Initialise Cloud SQL connection pool
    try:
        await init_db()
        app.state.db_connected = True
        logger.info("Database initialised")
    except Exception as e:
        logger.warning(f"Database init failed (will run without persistence): {e}")
        app.state.db_connected = False

    # Create agents and runner
    try:
        components = await create_agents()
        app.state.root_agent = components["root_agent"]
        app.state.session_service = components["session_service"]
        app.state.runner = components["runner"]
        logger.info(f"Agents loaded (ADK available: {ADK_AVAILABLE})")
    except Exception as e:
        logger.error(f"Failed to create agents: {e}")
        raise

    logger.info("ADK Command Center is ready")

    yield  # ── Server is running ──

    # Shutdown
    logger.info("Shutting down ADK Command Center...")

    # Close MCP connections
    try:
        from command_center.tools.mcp_gateway import close_all
        await close_all()
    except Exception:
        pass

    # Close database
    await close_db()
    logger.info("Shutdown complete")


# ── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="ADK Command Center",
    description="Multi-agent AI command center powered by Google ADK & Gemini",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount middleware stack
setup_middleware(app)


# ── NLU Pipeline ────────────────────────────────────────────────────────────

async def run_nlu_pipeline(
    message: str, session_state: dict[str, Any]
) -> tuple[ParsedCommand, str | None]:
    """
    Runs the full L1 NLU pipeline: classify → extract → resolve.

    Returns:
        (ParsedCommand, clarification_question)
        If clarification is needed, the question is non-None and the
        caller should return it to the user instead of proceeding.
    """
    # Step 1: Classify intent
    domain, intent, confidence = await classify_intent(message, session_state)

    # Step 2: Extract entities
    entities = await extract_entities(message, intent)

    # Step 3: Build preliminary ParsedCommand
    parsed = ParsedCommand(
        domain=domain,
        intent=intent,
        entities=entities,
        priority=3,  # Default; agent can re-assess
        ambiguity_score=0.0,
        session_ctx=session_state,
    )

    # Step 4: Resolve ambiguity
    resolved, clarification, ambiguity_score = resolve_ambiguity(parsed)
    parsed.ambiguity_score = ambiguity_score

    if not resolved:
        return parsed, clarification

    # Fill defaults for tolerably ambiguous commands
    if ambiguity_score > 0:
        required_fields_map = {
            "create_meeting": ["date", "attendees"],
            "create_task": ["title"],
            "draft_email": ["recipient", "subject_hint"],
            "research_topic": ["topic"],
        }
        required = required_fields_map.get(parsed.intent, [])
        missing = [f for f in required if f not in parsed.entities]
        if missing:
            parsed.entities = fill_defaults(parsed.entities, missing)

    return parsed, None


# ── Routes ──────────────────────────────────────────────────────────────────

@app.post("/run", response_model=FinalResponse)
async def handle_run(request: UserRequest, raw_request: Request) -> FinalResponse:
    """
    Receives a natural-language user request, pipes it through the
    NLU → Agent → Synthesiser pipeline, and returns a FinalResponse.
    """
    runner: Runner = raw_request.app.state.runner
    session_service = raw_request.app.state.session_service

    # Get or create session in our DB-backed store
    try:
        session_data = await get_or_create_session(request.session_id, request.user_id)
        session_state = session_data.get("state", {})
    except Exception:
        session_state = {}

    # Run NLU pipeline
    parsed, clarification = await run_nlu_pipeline(request.message, session_state)

    if clarification:
        return FinalResponse(
            session_id=request.session_id,
            summary=clarification,
            actions_taken=[],
            follow_ups=[],
        )

    # Prepare session for ADK Runner
    try:
        session = await session_service.get_session(
            app_name="command_center",
            user_id=request.user_id,
            session_id=request.session_id,
        )
        if session is None:
            session = await session_service.create_session(
                app_name="command_center",
                user_id=request.user_id,
                session_id=request.session_id,
            )
    except Exception:
        session = await session_service.create_session(
            app_name="command_center",
            user_id=request.user_id,
            session_id=request.session_id,
        )

    # Build the message for the ADK Runner
    # Include parsed context so the orchestrator has structured information
    adk_message = (
        f"{request.message}\n\n"
        f"[System Context — do not repeat to user]\n"
        f"Domain: {parsed.domain.value}\n"
        f"Intent: {parsed.intent}\n"
        f"Entities: {json.dumps(parsed.entities)}\n"
        f"Priority: {parsed.priority}"
    )

    # Run the agent pipeline
    events = runner.run_async(
        session_id=session.id if hasattr(session, "id") else request.session_id,
        user_id=request.user_id,
        new_message=adk_message,
    )

    # Synthesise the response
    response = await build_response(events, request.session_id)

    # Persist updated session state
    try:
        updated_state = session_state.copy()
        recent_history = updated_state.get("recent_history", [])
        recent_history.append({"role": "user", "content": request.message})
        recent_history.append({"role": "assistant", "content": response.summary})
        updated_state["recent_history"] = recent_history[-20:]  # Keep last 20 turns
        await save_session_state(request.session_id, updated_state)
    except Exception as e:
        logger.warning(f"Failed to persist session state: {e}")

    return response


@app.get("/stream")
async def handle_stream(
    session_id: str,
    user_id: str,
    message: str,
    raw_request: Request = None,
):
    """
    Same pipeline as POST /run, but streams intermediate ADK events
    back to the client as Server-Sent Events in real time.
    """
    runner: Runner = raw_request.app.state.runner
    session_service = raw_request.app.state.session_service

    async def event_generator() -> AsyncIterator[str]:
        # Get session state
        try:
            session_data = await get_or_create_session(session_id, user_id)
            session_state = session_data.get("state", {})
        except Exception:
            session_state = {}

        # NLU pipeline
        parsed, clarification = await run_nlu_pipeline(message, session_state)

        if clarification:
            yield format_sse_event("clarification", {"question": clarification})
            yield format_sse_event("done", {"session_id": session_id})
            return

        # Prepare ADK session
        try:
            session = await session_service.get_session(
                app_name="command_center",
                user_id=user_id,
                session_id=session_id,
            )
            if session is None:
                session = await session_service.create_session(
                    app_name="command_center",
                    user_id=user_id,
                    session_id=session_id,
                )
        except Exception:
            session = await session_service.create_session(
                app_name="command_center",
                user_id=user_id,
                session_id=session_id,
            )

        adk_message = (
            f"{message}\n\n"
            f"[System Context]\n"
            f"Domain: {parsed.domain.value}\n"
            f"Intent: {parsed.intent}\n"
            f"Entities: {json.dumps(parsed.entities)}"
        )

        # Stream events from the runner
        events = runner.run_async(
            session_id=session.id if hasattr(session, "id") else session_id,
            user_id=user_id,
            new_message=adk_message,
        )

        async for event in events:
            # Extract text to stream
            text = None
            if hasattr(event, "text"):
                text = event.text
            elif hasattr(event, "content") and hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        text = part.text
                        break

            if text:
                yield format_sse_event("text_chunk", {"text": text})

        yield format_sse_event("done", {"session_id": session_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/sessions/{session_id}")
async def get_session_state(session_id: str):
    """
    Returns the current state of a session from the DB-backed store.
    """
    try:
        session_data = await get_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if session_data is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return session_data


@app.get("/health")
async def health_check(raw_request: Request):
    """
    Liveness/readiness probe for Cloud Run.
    Checks DB connectivity and agent availability.
    """
    db_status = "connected" if getattr(raw_request.app.state, "db_connected", False) else "disconnected"

    # Count sub-agents
    agent_count = 0
    root = getattr(raw_request.app.state, "root_agent", None)
    if root:
        tools = getattr(root, "tools", None) or root.config.get("tools", [])
        agent_count = len(tools) if tools else 0

    return {
        "status": "ok",
        "adk_available": ADK_AVAILABLE,
        "agents": agent_count,
        "db": db_status,
    }


# ── Stub Helpers ────────────────────────────────────────────────────────────

def _make_stub_event(text: str):
    """Creates a simple stub event object with a .text attribute."""
    return type("StubEvent", (), {"text": text})()
