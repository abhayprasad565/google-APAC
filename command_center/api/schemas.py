# ============================================================================
# FILE: api/schemas.py
# LAYER: Cross-cutting — Data Transfer Objects (Contracts)
# ============================================================================
#
# PURPOSE:
#   Single source of truth for ALL typed data contracts exchanged between
#   layers. Every layer imports its input/output types from this file.
#   Contains NO business logic — pure Pydantic model definitions only.
#
# DESIGN PRINCIPLE:
#   No raw dicts cross layer boundaries. Every inter-layer hand-off uses
#   a Pydantic model defined here.
#
# ============================================================================
#
# ── CONTRACT FLOW ───────────────────────────────────────────────────────────
#
#   UserRequest       (L0 → L1)  — raw user input from HTTP
#   ParsedCommand     (L1 → L2)  — classified and entity-extracted command
#   AgentTask         (L2 → L3)  — discrete task dispatched to a sub-agent
#   ToolCall          (L3 → L4)  — request from agent to tool layer
#   RetryConfig       (L3 → L4)  — retry parameters for tool calls
#   ToolResponse      (L4 → L3)  — response from external service via tool
#   AgentResult       (L3 → L2)  — sub-agent's result back to orchestrator
#   ErrorDetail       (L3 → L2)  — structured error info within AgentResult
#   FinalResponse     (L7 → L0)  — synthesised response to user
#   ActionRecord      (L7 → L0)  — single action summary within FinalResponse
#
# ============================================================================
#
#
# ── CLASS: UserRequest ──────────────────────────────────────────────────────
#
#   DIRECTION: L0 → L1
#   TASK: Captures the raw incoming user request from the HTTP layer
#
#   FIELDS:
#     session_id    : str            — client-provided or auto-generated UUID
#     user_id       : str            — authenticated user identifier
#     message       : str            — raw natural-language command text
#     context_hints : list[str]      — optional hints for disambiguation
#                                      (default: empty list)
#     timestamp     : datetime       — auto-set to UTC now() on creation
#
#
# ── ENUM: DomainType ────────────────────────────────────────────────────────
#
#   TASK: Enumerates the possible routing domains for intent classification
#
#   VALUES:
#     calendar  — scheduling, events, invites
#     task      — to-do items, task tracking
#     email     — drafting, sending, summarising emails
#     research  — web search, information gathering
#     compound  — multi-domain request requiring multiple agents
#
#
# ── CLASS: ParsedCommand ────────────────────────────────────────────────────
#
#   DIRECTION: L1 → L2
#   TASK: Carries the classified intent, extracted entities, and ambiguity
#         score from the NLU layer to the orchestrator
#
#   FIELDS:
#     domain          : DomainType   — which agent domain this maps to
#     intent          : str          — specific intent string
#                                      e.g. "create_meeting", "summarize_inbox"
#     entities        : dict         — extracted entities
#                                      e.g. {date: "2025-06-01",
#                                            attendees: ["alice@co.com"],
#                                            topic: "Q3 planning"}
#     priority        : int          — 1 (low) to 5 (critical)
#     ambiguity_score : float        — 0.0 = fully clear, 1.0 = ambiguous
#     session_ctx     : dict         — session state snapshot for context
#
#
# ── CLASS: AgentTask ────────────────────────────────────────────────────────
#
#   DIRECTION: L2 → L3
#   TASK: Represents a single, discrete task dispatched by the orchestrator
#         to a specific sub-agent
#
#   FIELDS:
#     task_id     : UUID             — unique task identifier
#     agent_id    : DomainType       — which sub-agent handles this
#     task_type   : str              — e.g. "create_event", "draft_email"
#     payload     : dict             — all data the sub-agent needs
#     deadline    : datetime | None  — optional soft deadline
#     depends_on  : list[UUID]       — task IDs that must complete first
#                                      (for sequential workflows)
#
#
# ── CLASS: RetryConfig ──────────────────────────────────────────────────────
#
#   DIRECTION: embedded in ToolCall
#   TASK: Specifies retry behaviour for tool calls that may fail transiently
#
#   FIELDS:
#     max_attempts : int   — maximum retry count (default: 3)
#     backoff_ms   : int   — initial backoff in milliseconds (default: 500)
#
#
# ── CLASS: ToolCall ─────────────────────────────────────────────────────────
#
#   DIRECTION: L3 → L4
#   TASK: Represents a request from a sub-agent to invoke a specific tool
#         (MCP tool or FunctionTool)
#
#   FIELDS:
#     tool_name    : str          — name of the tool to invoke
#     params       : dict         — tool-specific parameters
#     auth_token   : str          — OAuth2 bearer token for external APIs
#     timeout_ms   : int          — max wait time in ms (default: 10000)
#     retry_policy : RetryConfig  — retry configuration
#
#
# ── CLASS: ToolResponse ─────────────────────────────────────────────────────
#
#   DIRECTION: L4 → L3
#   TASK: Carries the result of a tool invocation back to the sub-agent
#
#   FIELDS:
#     status     : Enum[success, error, timeout]
#     data       : dict         — tool-specific response payload
#     latency_ms : int          — wall-clock time for the tool call
#     source     : str          — which external service was called
#                                 e.g. "google_calendar", "gmail", "search_api"
#
#
# ── CLASS: ErrorDetail ──────────────────────────────────────────────────────
#
#   DIRECTION: embedded in AgentResult
#   TASK: Carries structured error information when a sub-agent encounters
#         a partial or full failure
#
#   FIELDS:
#     error_code : str   — machine-readable error code
#     message    : str   — human-readable error description
#     tool_name  : str   — which tool caused the error (if applicable)
#     recoverable: bool  — whether the orchestrator can retry
#
#
# ── CLASS: AgentResult ──────────────────────────────────────────────────────
#
#   DIRECTION: L3 → L2
#   TASK: Carries the complete result of a sub-agent's work back to the
#         orchestrator for aggregation
#
#   FIELDS:
#     task_id         : UUID                      — matches the dispatched AgentTask.task_id
#     agent_id        : str                       — which sub-agent produced this
#     status          : Enum[success, partial, failed]
#     data            : dict                      — result payload
#                                                   (structure varies by agent)
#     errors          : list[ErrorDetail]          — any errors encountered
#     tool_calls_made : list[str]                  — names of tools invoked
#
#
# ── CLASS: ActionRecord ─────────────────────────────────────────────────────
#
#   DIRECTION: embedded in FinalResponse
#   TASK: A concise summary of one action taken by one agent, for the user
#
#   FIELDS:
#     agent          : str   — agent name (e.g. "calendar", "email")
#     action         : str   — what was done (e.g. "create_event", "send_email")
#     result_summary : str   — one-line human-readable summary
#     success        : bool  — whether the action succeeded
#
#
# ── CLASS: FinalResponse ────────────────────────────────────────────────────
#
#   DIRECTION: L7 → L0
#   TASK: The fully synthesised response returned to the user via HTTP.
#         Aggregates results from all sub-agents into a coherent narrative.
#
#   FIELDS:
#     session_id    : str                         — echo back the session ID
#     summary       : str                         — human-readable narrative
#     actions_taken : list[ActionRecord]           — per-agent action summaries
#     follow_ups    : list[str]                    — suggested next actions
#     render_format : Enum[json, text, sse]        — how to render the response
#
# ============================================================================
