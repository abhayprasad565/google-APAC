from typing import Dict, Any, List
from google import genai
from command_center.config.settings import settings
from command_center.api.schemas import DomainType
from pydantic import BaseModel

CLASSIFICATION_THRESHOLD = 0.7

class IntentClassification(BaseModel):
    domain: DomainType
    intent: str
    confidence: float

def build_classification_prompt(message: str, recent_history: list[dict[str, str]]) -> str:
    history_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_history])
    prompt = f"""
You are the Intent Classifier for a personal command center.
Classify the following user message into one of the known domains and intents.

Domains:
- calendar: for scheduling, events, availability
- task: for to-do items, reminders
- email: for drafting, sending, reading emails
- research: for web searching, finding information
- compound: for multi-step tasks crossing domains

History:
{history_str}

User message: "{message}"
"""
    return prompt

async def classify_intent(message: str, session_ctx: dict[str, Any]) -> tuple[DomainType, str, float]:
    recent_history = session_ctx.get("recent_history", [])
    prompt = build_classification_prompt(message, recent_history)

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    response = await client.aio.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=IntentClassification,
            temperature=0.0
        )
    )

    parsed = IntentClassification.model_validate_json(response.text)

    if parsed.confidence < CLASSIFICATION_THRESHOLD:
        return (DomainType.compound, "multi_step", parsed.confidence)

    return (parsed.domain, parsed.intent, parsed.confidence)
