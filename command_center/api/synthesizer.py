"""
L7 — Response Synthesiser

Takes the raw ADK event stream from the Runner (which may contain results
from multiple sub-agents) and merges them into a single, coherent
FinalResponse. Handles tone normalisation and multi-agent result collation.
"""

import re
import logging
from typing import Any, AsyncIterator

from command_center.api.schemas import (
    FinalResponse,
    ActionRecord,
    AgentResult,
    AgentResultStatus,
    RenderFormat,
)

logger = logging.getLogger("command_center.synthesizer")


# ── Main Entry Point ────────────────────────────────────────────────────────

async def build_response(
    events: AsyncIterator[Any],
    session_id: str,
) -> FinalResponse:
    """
    Consumes the complete async event stream from the ADK Runner.
    Collects all AgentResult objects and text chunks, then assembles
    them into a single FinalResponse.

    Args:
        events: Async iterator of ADK Event objects from runner.run_async()
        session_id: The session this response belongs to

    Returns:
        FinalResponse with summary, actions, and follow-up suggestions.
    """
    agent_results: list[AgentResult] = []
    text_parts: list[str] = []

    async for event in events:
        # ADK events have different shapes — extract what we can
        if _is_agent_result(event):
            try:
                result = _parse_agent_result(event)
                agent_results.append(result)
            except Exception as e:
                logger.warning(f"Failed to parse agent result: {e}")

        # Collect text chunks from agent responses
        text = _extract_text(event)
        if text:
            text_parts.append(text)

    # Build the final response
    summary = normalize_tone(" ".join(text_parts)) if text_parts else "Request processed."
    actions = [map_result_to_action(r) for r in agent_results]
    follow_ups = generate_follow_ups(agent_results)

    return FinalResponse(
        session_id=session_id,
        summary=summary,
        actions_taken=actions,
        follow_ups=follow_ups,
        render_format=RenderFormat.json,
    )


# ── Result-to-Action Mapping ────────────────────────────────────────────────

def map_result_to_action(result: AgentResult) -> ActionRecord:
    """
    Converts a single AgentResult into a concise ActionRecord
    for the user-facing response.
    """
    # Derive a human-readable action name from tool calls or agent id
    action = result.tool_calls_made[0] if result.tool_calls_made else "process_request"

    # Build a one-line summary from the result data
    result_summary = _summarise_result_data(result)

    return ActionRecord(
        agent=result.agent_id,
        action=action,
        result_summary=result_summary,
        success=result.status == AgentResultStatus.success,
    )


# ── Tone Normalisation ──────────────────────────────────────────────────────

def normalize_tone(text: str) -> str:
    """
    Ensures a consistent, professional tone across outputs from
    multiple sub-agents. Strips duplicate sentences, internal tool
    names, and jargon from user-facing text.
    """
    if not text:
        return text

    # Remove internal tool/function names that agents might mention
    tool_patterns = [
        r"gcal_\w+",
        r"gmail_\w+",
        r"task_\w+",
        r"google_search",
        r"fetch_page_content",
        r"session_store_research",
    ]
    for pattern in tool_patterns:
        text = re.sub(
            rf"\b{pattern}\b",
            "",
            text,
            flags=re.IGNORECASE,
        )

    # Remove duplicate sentences
    text = _remove_duplicate_sentences(text)

    # Clean up extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Remove leftover "I called ..." or "Using tool ..." fragments
    text = re.sub(
        r"(?:I called|Using tool|Calling|Invoked)\s*[.,]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


# ── Follow-Up Generation ────────────────────────────────────────────────────

def generate_follow_ups(results: list[AgentResult]) -> list[str]:
    """
    Inspects each AgentResult's data to identify logical next actions.
    Returns 0 to 3 human-readable suggestion strings.
    """
    suggestions: list[str] = []
    agents_involved = {r.agent_id for r in results}

    for result in results:
        data = result.data

        # Calendar event created but no email sent → suggest emailing
        if result.agent_id == "calendar_agent" and "email_agent" not in agents_involved:
            if result.status == AgentResultStatus.success:
                suggestions.append(
                    "Would you like me to email the attendees about this event?"
                )

        # Task created with no due date → suggest setting one
        if result.agent_id == "task_agent" and result.status == AgentResultStatus.success:
            if not data.get("due_date"):
                suggestions.append(
                    "Would you like to set a due date for this task?"
                )

        # Research completed → suggest creating a task
        if result.agent_id == "research_agent" and result.status == AgentResultStatus.success:
            if "task_agent" not in agents_involved:
                suggestions.append(
                    "Would you like to create a task to act on these findings?"
                )

        # Email drafted but not sent → suggest sending
        if result.agent_id == "email_agent" and result.status == AgentResultStatus.success:
            if data.get("draft_id") and not data.get("sent"):
                suggestions.append(
                    "The email draft is ready. Would you like me to send it?"
                )

        # Limit to 3 suggestions
        if len(suggestions) >= 3:
            break

    return suggestions[:3]


# ── Helper: Build SSE Event ─────────────────────────────────────────────────

def format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """
    Formats a dict as a Server-Sent Event string.
    Used by the /stream endpoint in main.py.
    """
    import json
    payload = json.dumps({"event_type": event_type, "data": data})
    return f"event: {event_type}\ndata: {payload}\n\n"


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _is_agent_result(event: Any) -> bool:
    """Check if an ADK event represents a completed agent result."""
    # ADK events may have different attributes depending on version
    if hasattr(event, "agent_id") and hasattr(event, "status"):
        return True
    if isinstance(event, dict) and "agent_id" in event and "status" in event:
        return True
    return False


def _parse_agent_result(event: Any) -> AgentResult:
    """Parse an ADK event into our AgentResult schema."""
    if isinstance(event, AgentResult):
        return event

    if isinstance(event, dict):
        return AgentResult(**event)

    # Try attribute-based extraction for ADK event objects
    from uuid import uuid4
    return AgentResult(
        task_id=getattr(event, "task_id", uuid4()),
        agent_id=getattr(event, "agent_id", "unknown"),
        status=getattr(event, "status", "success"),
        data=getattr(event, "data", {}),
        errors=getattr(event, "errors", []),
        tool_calls_made=getattr(event, "tool_calls_made", []),
    )


def _extract_text(event: Any) -> str | None:
    """Extract text content from an ADK event, if present."""
    # ADK text chunk events
    if hasattr(event, "text"):
        return event.text

    # Content from agent response parts
    if hasattr(event, "content") and hasattr(event.content, "parts"):
        texts = []
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                texts.append(part.text)
        return " ".join(texts) if texts else None

    # Dict-based events
    if isinstance(event, dict):
        return event.get("text") or event.get("content")

    return None


def _summarise_result_data(result: AgentResult) -> str:
    """Build a concise one-line summary from an AgentResult."""
    data = result.data

    if result.status == AgentResultStatus.failed:
        error_msg = result.errors[0].message if result.errors else "Unknown error"
        return f"Failed: {error_msg}"

    # Agent-specific summaries
    if result.agent_id == "calendar_agent":
        title = data.get("title", "event")
        start = data.get("start", "")
        return f"Scheduled '{title}' at {start}" if start else f"Calendar action on '{title}'"

    if result.agent_id == "task_agent":
        title = data.get("title", "task")
        return f"Task '{title}' (priority {data.get('priority', '?')})"

    if result.agent_id == "email_agent":
        to = data.get("to", "recipient")
        return f"Email to {to}"

    if result.agent_id == "research_agent":
        topic = data.get("topic", "topic")
        count = len(data.get("sources", []))
        return f"Research on '{topic}' ({count} sources)"

    # Generic fallback
    return f"{result.agent_id}: completed"


def _remove_duplicate_sentences(text: str) -> str:
    """Remove exact duplicate sentences while preserving order."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    seen: set[str] = set()
    unique: list[str] = []

    for sentence in sentences:
        normalised = sentence.strip().lower()
        if normalised and normalised not in seen:
            seen.add(normalised)
            unique.append(sentence)

    return " ".join(unique)
