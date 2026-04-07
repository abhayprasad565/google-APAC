from typing import Any, Optional
from command_center.api.schemas import ParsedCommand
from command_center.config.settings import settings

# Maps an intent to a list of strictly required field names
REQUIRED_ENTITIES: dict[str, list[str]] = {
    "create_meeting": ["date", "attendees"],
    "create_task": ["title"],
    "draft_email": ["recipient", "subject_hint"],
    "research_topic": ["topic"],
}

def build_clarification_question(intent: str, missing: list[str]) -> str:
    missing_str = " and ".join(missing).replace("_", " ")
    return f"I can definitely help with that. But first, could you please provide the {missing_str}?"

def fill_defaults(entities: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    """Return a new dict with defaults filled in for missing fields.
    Does NOT mutate the input dict."""
    filled = dict(entities)
    # Future enhancement: populate defaults based on session preferences or current time
    # e.g., if 'date' is missing for a task, default to "today"
    return filled

def resolve_ambiguity(parsed: ParsedCommand) -> tuple[bool, Optional[str], float]:
    """
    Checks if the parsed command has all required information to execute.
    Returns: (is_resolved, clarification_question, ambiguity_score)

    NOTE: Does NOT mutate the input ParsedCommand.
    """
    required_fields = REQUIRED_ENTITIES.get(parsed.intent, [])

    missing = [f for f in required_fields if f not in parsed.entities]

    if not missing:
        return True, None, 0.0

    ambiguity_score = len(missing) / len(required_fields)

    if ambiguity_score > settings.AMBIGUITY_THRESHOLD:
        question = build_clarification_question(parsed.intent, missing)
        return False, question, ambiguity_score

    # Tolerable ambiguity — return defaults without mutating input
    # Caller should use: parsed.entities = fill_defaults(parsed.entities, missing)
    return True, None, ambiguity_score
