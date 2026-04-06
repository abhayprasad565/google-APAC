# ============================================================================
# FILE: nlu/intent_classifier.py
# LAYER: L1 — Natural Language Understanding
# ============================================================================
#
# PURPOSE:
#   Takes a raw user message and returns a classified domain and intent
#   string by making a lightweight Gemini API call with a structured output
#   prompt. This is the FIRST step in L1 — it decides which agent(s) need
#   to be involved.
#
# KEY RESPONSIBILITIES:
#   1. Build a classification prompt with recent conversation history
#   2. Call Gemini with structured JSON output format
#   3. Parse the response to extract domain, intent, and confidence
#   4. Fall back to "compound" domain for low-confidence classifications
#
# ============================================================================
#
#
# ── CONSTANT: CLASSIFICATION_THRESHOLD ──────────────────────────────────────
#
#   float — confidence score below which the classifier returns
#           domain="compound" and intent="multi_step"
#   Default: 0.7
#
#
# ── FUNCTION: classify_intent ───────────────────────────────────────────────
#
# async function classify_intent(message, session_ctx) -> tuple[DomainType, str, float]
#
#   TASK:
#     Sends the user's raw message plus recent session history to Gemini
#     with a prompt that instructs it to return a JSON classification.
#     If confidence is below threshold, returns "compound" domain to
#     trigger multi-agent handling.
#
#   INPUT:
#     message     : str
#       — raw natural-language user input
#       — e.g. "Schedule a meeting with Alice on Friday"
#
#     session_ctx : dict (SessionState)
#       — recent conversation history and user preferences
#       — contains keys:
#           recent_history : list[dict]  — last N turns
#           user_timezone  : str         — e.g. "America/New_York"
#           preferences    : dict        — user's default settings
#
#   OUTPUT:
#     tuple of:
#       domain     : DomainType  — Enum: calendar | task | email | research | compound
#       intent     : str         — specific intent string
#                                  e.g. "create_meeting", "summarize_inbox",
#                                       "research_topic", "multi_step"
#       confidence : float       — 0.0 to 1.0
#
#
# ── FUNCTION: build_classification_prompt ───────────────────────────────────
#
# function build_classification_prompt(message, recent_history) -> str
#
#   TASK:
#     Constructs the prompt string sent to Gemini for intent classification.
#     Includes the user message, recent conversation turns for context, and
#     explicit instructions to return JSON with domain/intent/confidence.
#
#   INPUT:
#     message        : str             — raw user text
#     recent_history : list[dict]      — last N conversation turns
#                                        each: {role: str, content: str}
#
#   OUTPUT:
#     str — the fully constructed prompt string for Gemini
#
# ============================================================================
