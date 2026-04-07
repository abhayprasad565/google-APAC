from typing import Dict, Any, Type
from google import genai
from pydantic import BaseModel
from command_center.config.settings import settings

class CalendarEntities(BaseModel):
    date: str | None = None
    time: str | None = None
    attendees: list[str] | None = None
    title: str | None = None

class TaskEntities(BaseModel):
    title: str | None = None
    due_date: str | None = None
    priority_hint: str | None = None

class EmailEntities(BaseModel):
    recipient: str | None = None
    subject_hint: str | None = None
    key_points: list[str] | None = None
    tone: str | None = None

class ResearchEntities(BaseModel):
    topic: str | None = None
    depth: str | None = None

class DefaultEntities(BaseModel):
    extracted_keywords: list[str] | None = None

# Maps a specific intent string to its corresponding Pydantic schema
ENTITY_SCHEMAS: dict[str, Type[BaseModel]] = {
    "create_meeting": CalendarEntities,
    "create_task": TaskEntities,
    "draft_email": EmailEntities,
    "research_topic": ResearchEntities,
}

def build_extraction_prompt(message: str, intent: str) -> str:
    return f"""
You are the Entity Extractor.
Extract structured information from the user message for a '{intent}' intent.
If a piece of information is missing, do not hallucinate it; leave it null/omitted.

User message: "{message}"
"""

async def extract_entities(message: str, intent: str) -> dict[str, Any]:
    schema_cls = ENTITY_SCHEMAS.get(intent, DefaultEntities)
    prompt = build_extraction_prompt(message, intent)

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    response = await client.aio.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema_cls,
            temperature=0.0
        )
    )

    # Parse and validate the JSON string into the Pydantic model
    parsed = schema_cls.model_validate_json(response.text)

    # Return as clean dict, stripping out purely None fields
    entities = {k: v for k, v in parsed.model_dump().items() if v is not None}

    return entities
