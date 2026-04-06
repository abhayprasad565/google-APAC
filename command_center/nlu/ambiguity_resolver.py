# ============================================================================
# FILE: nlu/ambiguity_resolver.py
# LAYER: L1 — Natural Language Understanding
# ============================================================================
#
# PURPOSE:
#   Checks whether the extracted ParsedCommand has enough information to
#   execute. If the ambiguity_score is above a threshold, returns a
#   clarifying question to bounce back to L0 instead of proceeding to L2.
#   Acts as a quality gate between NLU and the orchestrator.
#
# KEY RESPONSIBILITIES:
#   1. Check extracted entities against required fields for the intent
#   2. Calculate an ambiguity score based on missing fields
#   3. If ambiguity is tolerable, fill defaults for missing fields
#   4. If ambiguity is too high, generate a clarification question
#
# ============================================================================
#
#
# ── CONSTANT: REQUIRED_ENTITIES ─────────────────────────────────────────────
#
#   dict[str, list[str]]
#   Maps each intent string to the list of entity fields that MUST be
#   present for execution.
#
#   Examples:
#     "create_meeting"  → ["date", "attendees", "title"]
#     "draft_email"     → ["to", "subject"]
#     "create_task"     → ["title"]
#     "research_topic"  → ["topic"]
#     "summarize_inbox" → []  (no required entities)
#     "list_events"     → ["date"]
#
#
# ── CONSTANT: AMBIGUITY_THRESHOLD ───────────────────────────────────────────
#
#   float — from settings.AMBIGUITY_THRESHOLD (default: 0.6)
#   If the ratio of missing fields to required fields exceeds this,
#   a clarification question is generated.
#
#
# ── FUNCTION: resolve_ambiguity ─────────────────────────────────────────────
#
# function resolve_ambiguity(parsed: ParsedCommand) -> tuple[bool, str | None, float]
#
#   TASK:
#     Validates that the ParsedCommand has all required entities for its
#     intent. Calculates an ambiguity score as:
#       ambiguity_score = len(missing_fields) / len(required_fields)
#
#     If score is 0 → proceed (fully resolved).
#     If score > 0 but ≤ threshold → fill defaults, proceed.
#     If score > threshold → generate clarification question, halt pipeline.
#
#   INPUT:
#     parsed : ParsedCommand
#       {
#         domain          : DomainType
#         intent          : str
#         entities        : dict    — what was extracted so far
#         priority        : int
#         ambiguity_score : float   — will be updated by this function
#         session_ctx     : dict
#       }
#
#   OUTPUT:
#     tuple of:
#       resolved               : bool       — True = proceed to L2;
#                                              False = ask user for more info
#       clarification_question : str | None  — human-readable question
#                                              (None if resolved)
#       ambiguity_score        : float       — computed score (0.0 to 1.0)
#
#
# ── FUNCTION: build_clarification_question ──────────────────────────────────
#
# function build_clarification_question(intent, missing_fields) -> str
#
#   TASK:
#     Generates a natural-language clarification question asking the user
#     to provide the missing entity fields. The question is contextual
#     based on the intent type.
#
#   INPUT:
#     intent         : str        — the classified intent
#     missing_fields : list[str]  — entity field names that are missing
#
#   OUTPUT:
#     str — a human-readable question
#     Example: "I'd like to schedule the meeting, but I need a few details:
#               Who should I invite, and what date/time works best?"
#
#
# ── FUNCTION: fill_defaults ─────────────────────────────────────────────────
#
# function fill_defaults(entities, missing_fields) -> dict
#
#   TASK:
#     For missing fields that have sensible defaults, fills them
#     automatically rather than asking the user. Used when ambiguity
#     is tolerable (below threshold).
#
#   INPUT:
#     entities       : dict       — current extracted entities
#     missing_fields : list[str]  — fields that are missing
#
#   OUTPUT:
#     dict — entities with defaults filled
#
#   DEFAULT VALUES:
#     duration   → 30 (minutes)
#     priority   → 3 (medium)
#     tone       → "professional"
#     depth      → "quick"
#     location   → None
#     tags       → []
#
# ============================================================================
