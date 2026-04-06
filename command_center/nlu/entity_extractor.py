# ============================================================================
# FILE: nlu/entity_extractor.py
# LAYER: L1 — Natural Language Understanding
# ============================================================================
#
# PURPOSE:
#   Extracts structured entities from the user message — dates, times,
#   people names, email addresses, topic keywords, task names. Builds the
#   `entities` dict that gets packed into ParsedCommand.
#
# KEY RESPONSIBILITIES:
#   1. Select the right extraction schema based on the classified intent
#   2. Build a Gemini prompt that extracts entities matching the schema
#   3. Post-process: normalise relative dates, validate email formats
#
# ============================================================================
#
#
# ── CONSTANT: ENTITY_SCHEMAS ────────────────────────────────────────────────
#
#   dict[str, dict]
#   Maps intent strings to their expected entity extraction schemas.
#
#   Examples:
#     "create_meeting" → {
#       date       : str (ISO datetime)
#       time       : str (ISO time)
#       duration   : int (minutes)
#       attendees  : list[str] (email addresses)
#       title      : str
#       location   : str | None
#       description: str | None
#     }
#
#     "draft_email" → {
#       to         : list[str] (email addresses)
#       subject    : str
#       key_points : list[str]
#       tone       : str (formal | casual | friendly)
#       cc         : list[str] | None
#     }
#
#     "create_task" → {
#       title      : str
#       description: str | None
#       priority   : int (1-5)
#       due_date   : str (ISO date) | None
#       tags       : list[str]
#     }
#
#     "research_topic" → {
#       topic      : str
#       depth      : str (quick | deep)
#       focus_areas: list[str] | None
#     }
#
#
# ── FUNCTION: extract_entities ──────────────────────────────────────────────
#
# async function extract_entities(message, intent) -> dict
#
#   TASK:
#     Sends the user message to Gemini with a schema-driven extraction
#     prompt. The prompt is tailored to the intent so that only relevant
#     entities are extracted. Post-processes relative dates (e.g. "next
#     Monday") into ISO datetime strings.
#
#   INPUT:
#     message : str
#       — raw natural-language user text
#       — e.g. "Set up a meeting with bob@corp.com next Friday at 3pm"
#
#     intent  : str
#       — classified intent from intent_classifier
#       — e.g. "create_meeting"
#
#   OUTPUT:
#     dict — key-value pairs matching the schema for the given intent
#     Example for intent "create_meeting":
#       {
#         "date"      : "2025-06-06T15:00:00",
#         "duration"  : 60,
#         "attendees" : ["bob@corp.com"],
#         "title"     : "Meeting",
#         "location"  : None,
#         "description": None
#       }
#
#
# ── FUNCTION: build_extraction_prompt ───────────────────────────────────────
#
# function build_extraction_prompt(message, schema) -> str
#
#   TASK:
#     Constructs the Gemini prompt that instructs the model to extract
#     entities from the message according to the provided schema.
#
#   INPUT:
#     message : str        — raw user text
#     schema  : dict       — expected entity schema for the intent
#
#   OUTPUT:
#     str — fully constructed extraction prompt for Gemini
#
#
# ── FUNCTION: normalize_dates ───────────────────────────────────────────────
#
# function normalize_dates(entities) -> dict
#
#   TASK:
#     Post-processes the extracted entities dict. Converts any relative
#     date/time references into absolute ISO 8601 datetime strings.
#     Uses the user's timezone from session context.
#
#   INPUT:
#     entities : dict — raw extracted entities (may have relative dates)
#       e.g. {"date": "next Friday", "time": "3pm"}
#
#   OUTPUT:
#     dict — same entities with dates normalised
#       e.g. {"date": "2025-06-06T15:00:00+05:30"}
#
# ============================================================================
