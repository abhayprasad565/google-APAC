# ADK Command Center — Detailed Architecture Report

> **Stack:** Google Agent Development Kit (ADK) · FastAPI · Gemini 2.0 Flash · Cloud SQL (Postgres) · Cloud Run · MCP Tools
> **Pattern:** Layered monolith · Primary agent + 4 sub-agents · REST + SSE API

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Layer Architecture Summary](#2-layer-architecture-summary)
3. [Full File Structure](#3-full-file-structure)
4. [File Definitions & Pseudocode](#4-file-definitions--pseudocode)
   - [4.1 API Layer (L0 / L7)](#41-api-layer-l0--l7)
   - [4.2 NLU Layer (L1)](#42-nlu-layer-l1)
   - [4.3 Agents Layer (L2 + L3)](#43-agents-layer-l2--l3)
   - [4.4 Tools & MCP Gateway (L4)](#44-tools--mcp-gateway-l4)
   - [4.5 Database / Memory Layer (L6)](#45-database--memory-layer-l6)
   - [4.6 Config & Infrastructure](#46-config--infrastructure)
5. [Data Transfer Objects (Contracts)](#5-data-transfer-objects-contracts)
6. [MCP Implementation Guide](#6-mcp-implementation-guide)
   - [6.1 What is MCP in ADK](#61-what-is-mcp-in-adk)
   - [6.2 Option A — Google Calendar MCP (Remote)](#62-option-a--google-calendar-mcp-remote)
   - [6.3 Option B — Gmail MCP (Remote)](#63-option-b--gmail-mcp-remote)
   - [6.4 Option C — Local MCP Server (Custom)](#64-option-c--local-mcp-server-custom)
   - [6.5 Option D — Stdio MCP (Subprocess)](#65-option-d--stdio-mcp-subprocess)
   - [6.6 MCP vs FunctionTool Decision Matrix](#66-mcp-vs-functiontool-decision-matrix)
   - [6.7 Auth & Token Management for MCP](#67-auth--token-management-for-mcp)
7. [End-to-End Workflow Example](#7-end-to-end-workflow-example)
8. [Deployment Notes](#8-deployment-notes)

---

## 1. Project Overview

The ADK Command Center is a **multi-agent AI system** where a primary orchestrator agent receives user requests, classifies intent, and delegates to one or more specialized sub-agents. Each sub-agent owns a narrow domain (calendar, tasks, email, research) and operates its own set of tools via MCP or ADK FunctionTools. All agents run in a single Python process deployed as a Cloud Run monolith.

**Key design principles:**

- Every layer communicates only through typed data contracts (Pydantic models)
- No layer calls external APIs directly — all external calls go through the Tool & MCP Gateway (L4)
- All state is persisted in Cloud SQL and exposed to agents via ADK's SessionService
- The primary agent uses ADK's `AgentTool` delegation — sub-agents are treated as tools

---

## 2. Layer Architecture Summary

| Layer | Name | Responsibility |
|-------|------|----------------|
| L0 | User Interface | FastAPI endpoints — capture requests, stream responses |
| L1 | Ingestion & NLU | Intent classification, entity extraction, ambiguity resolution |
| L2 | Orchestration | Primary ADK LlmAgent — route, plan, sequence, conflict-resolve |
| L3 | Sub-Agents | Calendar, Task, Email, Research — each an ADK LlmAgent |
| L4 | Tool & MCP Gateway | MCP protocol adapter, OAuth tokens, retry, rate-limit |
| L5 | External Services | Google APIs, Gemini, Cloud SQL (called only by L4) |
| L6 | Memory & State | ADK SessionService + Cloud SQL persistence |
| L7 | Response Synthesizer | Aggregate AgentResults, format, stream back to L0 |

---

## 3. Full File Structure

```
command_center/
│
├── api/                          # L0 + L7 — FastAPI entrypoint & response synthesis
│   ├── main.py                   # FastAPI app, route definitions, ADK Runner setup
│   ├── schemas.py                # All Pydantic DTOs (UserRequest, FinalResponse, etc.)
│   ├── synthesizer.py            # L7 — aggregates AgentResults into FinalResponse
│   └── middleware.py             # Auth, CORS, request logging middleware
│
├── nlu/                          # L1 — Natural Language Understanding
│   ├── intent_classifier.py      # Classify domain from raw message
│   ├── entity_extractor.py       # Extract dates, names, topics from message
│   └── ambiguity_resolver.py     # Detect and resolve underspecified commands
│
├── agents/                       # L2 + L3 — All ADK LlmAgent definitions
│   ├── root_agent.py             # L2 — Primary orchestrator (registers sub-agents as AgentTools)
│   ├── calendar_agent.py         # L3 — Calendar domain agent
│   ├── task_agent.py             # L3 — Task management agent
│   ├── email_agent.py            # L3 — Email drafting & sending agent
│   └── research_agent.py         # L3 — Web research & summarization agent
│
├── tools/                        # L4 — Tool wrappers & MCP gateway
│   ├── mcp_gateway.py            # Central MCP connection manager (SSE + Stdio)
│   ├── calendar_mcp.py           # Google Calendar MCP toolset wrapper
│   ├── gmail_mcp.py              # Gmail MCP toolset wrapper
│   ├── search_tool.py            # Google Search as ADK FunctionTool
│   ├── task_db_tool.py           # Cloud SQL task CRUD as ADK FunctionTool
│   └── auth_manager.py           # OAuth2 token refresh and Secret Manager binding
│
├── db/                           # L6 — Database models, session service, migrations
│   ├── models.py                 # SQLAlchemy ORM models (sessions, tasks, agent_logs)
│   ├── session_store.py          # ADK SessionService backed by Cloud SQL
│   ├── task_repository.py        # Task CRUD operations (used by task_db_tool)
│   └── migrations/               # Alembic migration scripts
│       ├── env.py
│       └── versions/
│
├── config/
│   └── settings.py               # Pydantic Settings — env vars, Secret Manager bindings
│
├── tests/
│   ├── test_nlu.py
│   ├── test_agents.py
│   ├── test_tools.py
│   └── test_api.py
│
├── Dockerfile                    # Single-stage build, all layers in one image
├── pyproject.toml                # Dependencies: google-adk, fastapi, sqlalchemy, etc.
├── cloudbuild.yaml               # Cloud Build CI/CD pipeline
└── alembic.ini                   # Alembic config pointing to DATABASE_URL
```

---

## 4. File Definitions & Pseudocode

---

### 4.1 API Layer (L0 / L7)

---

#### `api/main.py`

**Purpose:** FastAPI application entry point. Defines HTTP routes, initializes the ADK Runner and SessionService, wires together L0 (input capture) and L7 (response delivery). The only file that starts the server.

**Key responsibilities:**
- Register all routes (`/run`, `/stream`, `/health`, `/sessions/{id}`)
- Instantiate `root_agent`, `InMemorySessionService`, and `Runner` at startup
- Pass raw request to NLU pipeline (L1), then hand ParsedCommand to the ADK Runner
- Call `synthesizer.build_response()` on the event stream to produce FinalResponse

**Inputs:**
- HTTP POST body: raw JSON matching `UserRequest` schema
- HTTP GET params: `session_id` for session retrieval

**Outputs:**
- HTTP response: JSON `FinalResponse` or Server-Sent Events stream

**Pseudocode:**

```
STARTUP:
  load settings from config/settings.py
  init Cloud SQL connection pool
  init session_service = InMemorySessionService()
  init runner = Runner(agent=root_agent, session_service=session_service)
  mount CORS and auth middleware

POST /run:
  receive UserRequest (session_id, user_id, message, context_hints)
  session = session_service.get_or_create(session_id, user_id)
  parsed = nlu_pipeline.process(message, session.context)   # L1
  events = runner.run(session_id, parsed.to_adk_message())  # L2 onwards
  response = synthesizer.build_response(events, session_id) # L7
  return FinalResponse as JSON

GET /stream:
  same as /run but yield events as SSE chunks

GET /sessions/{id}:
  return session state from session_service

GET /health:
  ping DB connection, return {"status": "ok", "agents": 4}
```

---

#### `api/schemas.py`

**Purpose:** Single source of truth for all typed data contracts exchanged between layers. Every layer imports its input/output types from here. No business logic.

**Inputs:** None (pure type definitions)

**Outputs:** Pydantic model classes consumed by all other modules

**Pseudocode:**

```
# --- L0 → L1 ---
class UserRequest:
  session_id: str
  user_id: str
  message: str
  context_hints: list[str] = []
  timestamp: datetime = now()

# --- L1 → L2 ---
class ParsedCommand:
  domain: Enum[calendar, task, email, research, compound]
  intent: str
  entities: dict            # e.g. {date: "2025-06-01", attendees: ["alice"]}
  priority: int             # 1 (low) to 5 (critical)
  ambiguity_score: float    # 0.0 = clear, 1.0 = completely ambiguous
  session_ctx: SessionState

# --- L2 → L3 ---
class AgentTask:
  task_id: UUID
  agent_id: Enum[calendar, task, email, research]
  task_type: str            # e.g. "create_event", "draft_email"
  payload: dict
  deadline: datetime | None
  depends_on: list[UUID]    # for sequential workflows

# --- L3 → L4 ---
class ToolCall:
  tool_name: str
  params: dict
  auth_token: str
  timeout_ms: int = 10000
  retry_policy: RetryConfig

class RetryConfig:
  max_attempts: int = 3
  backoff_ms: int = 500

# --- L4 → L3 (return) ---
class ToolResponse:
  status: Enum[success, error, timeout]
  data: dict
  latency_ms: int
  source: str               # which external service was called

# --- L3 → L2 (return) ---
class AgentResult:
  task_id: UUID
  agent_id: str
  status: Enum[success, partial, failed]
  data: dict
  errors: list[ErrorDetail]
  tool_calls_made: list[str]

# --- L7 → L0 ---
class FinalResponse:
  session_id: str
  summary: str
  actions_taken: list[ActionRecord]
  follow_ups: list[str]
  render_format: Enum[json, text, sse]

class ActionRecord:
  agent: str
  action: str
  result_summary: str
  success: bool
```

---

#### `api/synthesizer.py`

**Purpose:** L7 — Takes the raw ADK event stream from the Runner (which may contain results from multiple sub-agents) and merges them into a single, coherent `FinalResponse`. Handles tone normalization and multi-agent result collation.

**Inputs:**
- `events`: async iterator of ADK Event objects from `runner.run()`
- `session_id`: str

**Outputs:**
- `FinalResponse` object

**Pseudocode:**

```
function build_response(events, session_id):
  agent_results = []
  text_parts = []

  for event in events:
    if event is AgentResult:
      agent_results.append(event)
    if event is TextChunk:
      text_parts.append(event.text)

  summary = join(text_parts)
  actions = [map_result_to_action(r) for r in agent_results]
  follow_ups = generate_follow_ups(agent_results)

  return FinalResponse(
    session_id = session_id,
    summary = normalize_tone(summary),
    actions_taken = actions,
    follow_ups = follow_ups,
    render_format = "json"
  )

function normalize_tone(text):
  # ensure consistent, professional tone across multi-agent outputs
  # strip duplicate information from multiple agents
  return cleaned_text

function generate_follow_ups(results):
  # inspect each AgentResult.data for incomplete items
  # e.g. if calendar event created but no email sent → suggest emailing attendees
  return list_of_suggestion_strings
```

---

#### `api/middleware.py`

**Purpose:** FastAPI middleware stack. Handles cross-cutting concerns: authentication header validation, CORS, structured request/response logging for Cloud Logging.

**Inputs:** Every incoming HTTP request

**Outputs:** Augmented request context; structured log entries

**Pseudocode:**

```
AuthMiddleware:
  extract Bearer token from Authorization header
  validate token against Cloud IAM or API key store
  if invalid → return 401
  attach user_id to request.state

LoggingMiddleware:
  before request: record start_time, method, path, session_id
  after response: record status_code, latency_ms
  emit structured JSON log to stdout (captured by Cloud Logging)

CORSMiddleware:
  allow configured origins from settings.ALLOWED_ORIGINS
```

---

### 4.2 NLU Layer (L1)

---

#### `nlu/intent_classifier.py`

**Purpose:** Takes a raw user message and returns a classified domain and intent string by making a lightweight Gemini API call with a structured output prompt. This is the first step in L1 — it decides which agent(s) need to be involved.

**Inputs:**
- `message: str` — raw user text
- `session_ctx: SessionState` — recent conversation history for context

**Outputs:**
- `domain: Enum[calendar, task, email, research, compound]`
- `intent: str` — e.g. `"create_meeting"`, `"summarize_inbox"`, `"research_topic"`
- `confidence: float`

**Pseudocode:**

```
function classify_intent(message, session_ctx):
  prompt = build_classification_prompt(message, session_ctx.recent_history)
  # prompt instructs Gemini to return JSON: {domain, intent, confidence}

  response = gemini.generate(prompt, response_format="json")
  parsed = parse_json(response)

  if parsed.confidence < THRESHOLD:
    return domain="compound", intent="multi_step", confidence=parsed.confidence

  return parsed.domain, parsed.intent, parsed.confidence
```

---

#### `nlu/entity_extractor.py`

**Purpose:** Extracts structured entities from the user message — dates, times, people names, email addresses, topic keywords, task names. Builds the `entities` dict that gets packed into `ParsedCommand`.

**Inputs:**
- `message: str`
- `intent: str` — from classifier, used to focus extraction

**Outputs:**
- `entities: dict` — e.g. `{date: "2025-06-01T14:00", attendees: ["alice@co.com"], topic: "Q3 planning"}`

**Pseudocode:**

```
function extract_entities(message, intent):
  # select extraction schema based on intent domain
  schema = ENTITY_SCHEMAS[intent]   # e.g. calendar schema: {date, time, attendees, title}

  prompt = build_extraction_prompt(message, schema)
  response = gemini.generate(prompt, response_format="json")
  entities = parse_json(response)

  # post-process: parse relative dates ("next Monday" → ISO datetime)
  entities = normalize_dates(entities)

  return entities
```

---

#### `nlu/ambiguity_resolver.py`

**Purpose:** Checks whether the extracted ParsedCommand has enough information to execute. If `ambiguity_score` is above a threshold, returns a clarifying question to bounce back to L0 instead of proceeding to L2.

**Inputs:**
- `parsed: ParsedCommand` (partial — domain, intent, entities populated)

**Outputs:**
- `resolved: bool` — whether to proceed or ask for clarification
- `clarification_question: str | None`
- `ambiguity_score: float`

**Pseudocode:**

```
function resolve_ambiguity(parsed):
  required_fields = REQUIRED_ENTITIES[parsed.intent]
  missing = [f for f in required_fields if f not in parsed.entities]

  if len(missing) == 0:
    return resolved=True, ambiguity_score=0.0

  ambiguity_score = len(missing) / len(required_fields)

  if ambiguity_score > AMBIGUITY_THRESHOLD:
    question = build_clarification_question(parsed.intent, missing)
    return resolved=False, clarification_question=question, ambiguity_score=ambiguity_score

  # tolerable ambiguity — proceed with defaults for missing fields
  parsed.entities = fill_defaults(parsed.entities, missing)
  return resolved=True, ambiguity_score=ambiguity_score
```

---

### 4.3 Agents Layer (L2 + L3)

---

#### `agents/root_agent.py`

**Purpose:** L2 — Defines the primary ADK `LlmAgent` that acts as orchestrator. Registers all four sub-agents as `AgentTool` instances so Gemini can decide to call them. Contains the system instruction that teaches the orchestrator how to plan multi-step workflows, sequence dependent tasks, and resolve scheduling conflicts.

**Inputs:**
- Receives `ParsedCommand` via the ADK Runner as the initial user message
- Reads session history from `SessionService`

**Outputs:**
- Issues `AgentTask` objects to sub-agents (via ADK's internal tool-call mechanism)
- Returns aggregated natural language response text to the Runner event stream

**Pseudocode:**

```
SYSTEM_INSTRUCTION = """
  You are the primary orchestrator for a personal command center.
  You have access to 4 specialized agents as tools:
    - calendar_agent: for scheduling, events, invites
    - task_agent: for creating, tracking, prioritizing tasks
    - email_agent: for drafting, sending, summarizing emails
    - research_agent: for web searches and information gathering

  Rules:
  1. Analyze the user request and identify all required actions.
  2. For compound requests, call multiple agents in logical order.
  3. Pass the output of one agent as context to the next when they are sequential.
  4. If a calendar slot is unavailable, call calendar_agent to find the next free slot.
  5. Always confirm actions before executing irreversible ones (send email, delete task).
  6. Summarize all actions taken at the end.
"""

root_agent = LlmAgent(
  name = "command_center_root",
  model = "gemini-2.0-flash",
  instruction = SYSTEM_INSTRUCTION,
  tools = [
    AgentTool(calendar_agent),
    AgentTool(task_agent),
    AgentTool(email_agent),
    AgentTool(research_agent),
  ]
)
```

---

#### `agents/calendar_agent.py`

**Purpose:** L3 sub-agent responsible for all calendar operations. Owns the Google Calendar MCP toolset. Can schedule events, check availability, resolve conflicts, and send invites.

**Inputs:**
- Natural language task description from orchestrator (e.g. "Schedule a 1-hour meeting with Alice on Friday at 2pm")
- Session context: user timezone, calendar ID

**Outputs:**
- Natural language confirmation with event details
- Structured result: `{event_id, title, start, end, attendees, invite_sent: bool}`

**Tools available:**
- `gcal_create_event(title, start, end, attendees, description)`
- `gcal_list_events(start_date, end_date)`
- `gcal_check_free_busy(emails, start, end)`
- `gcal_update_event(event_id, changes)`
- `gcal_delete_event(event_id)`

**Pseudocode:**

```
SYSTEM_INSTRUCTION = """
  You are the Calendar Agent. You handle all scheduling tasks.
  You have access to Google Calendar tools.
  Steps for creating a meeting:
  1. Call gcal_check_free_busy for all attendees at the requested time.
  2. If there is a conflict, find the next available 30-minute slot.
  3. Call gcal_create_event with confirmed slot.
  4. Return the event details including a calendar link.
  Never double-book. Always confirm timezone from session context.
"""

calendar_agent = LlmAgent(
  name = "calendar_agent",
  model = "gemini-2.0-flash",
  instruction = SYSTEM_INSTRUCTION,
  tools = load_calendar_tools()   # from tools/calendar_mcp.py
)
```

---

#### `agents/task_agent.py`

**Purpose:** L3 sub-agent responsible for task management. Owns a custom Cloud SQL task tool. Handles creating, updating, prioritizing, and tracking tasks. Does not use MCP — uses a direct `FunctionTool` wrapping the task_repository.

**Inputs:**
- Task description, due date, priority level from orchestrator
- Session context: user_id for task ownership

**Outputs:**
- Task ID, title, priority score, status, due date
- Ranked task list when listing

**Tools available:**
- `task_create(title, description, priority, due_date, tags)`
- `task_list(filter_status, filter_priority, limit)`
- `task_update(task_id, changes)`
- `task_complete(task_id)`
- `task_delete(task_id)`

**Pseudocode:**

```
SYSTEM_INSTRUCTION = """
  You are the Task Agent. You manage a task list stored in the database.
  Priority scoring: 1=low, 2=medium, 3=high, 4=urgent, 5=critical.
  When creating tasks, infer priority from the user's language cues.
  When listing tasks, sort by: priority DESC, due_date ASC.
  For task decomposition: break large tasks into sub-tasks automatically.
"""

task_agent = LlmAgent(
  name = "task_agent",
  model = "gemini-2.0-flash",
  instruction = SYSTEM_INSTRUCTION,
  tools = load_task_tools()   # from tools/task_db_tool.py
)
```

---

#### `agents/email_agent.py`

**Purpose:** L3 sub-agent responsible for email operations. Owns the Gmail MCP toolset. Can draft emails from natural language descriptions, summarize inbox threads, send replies, and manage labels.

**Inputs:**
- Email intent from orchestrator: recipient(s), subject hint, tone, key points to include
- Optionally: output from calendar_agent (e.g. meeting details to include in email body)

**Outputs:**
- Drafted email text (for review before sending)
- Confirmation of send with message ID
- Thread summary as structured list

**Tools available:**
- `gmail_draft(to, subject, body, cc, attachments)`
- `gmail_send(draft_id)` or `gmail_send_direct(to, subject, body)`
- `gmail_list_threads(query, max_results)`
- `gmail_get_thread(thread_id)`
- `gmail_reply(thread_id, body)`

**Pseudocode:**

```
SYSTEM_INSTRUCTION = """
  You are the Email Agent. You draft and send emails via Gmail.
  Always match the requested tone: formal, casual, assertive, friendly.
  When drafting: produce the email body first, then ask the orchestrator
    whether to send immediately or present for review.
  Never send an email without explicit confirmation from the orchestrator.
  When summarizing threads: extract key decisions, action items, and deadlines.
"""

email_agent = LlmAgent(
  name = "email_agent",
  model = "gemini-2.0-flash",
  instruction = SYSTEM_INSTRUCTION,
  tools = load_gmail_tools()   # from tools/gmail_mcp.py
)
```

---

#### `agents/research_agent.py`

**Purpose:** L3 sub-agent responsible for web research. Uses Google Search as a FunctionTool and can make multiple search calls to cross-reference information. Summarizes findings and cites sources. Can optionally persist research summaries to L6 memory for future reference.

**Inputs:**
- Research topic or question from orchestrator
- Optional: `depth` parameter (quick summary vs deep research)

**Outputs:**
- Structured research summary with key findings
- List of source URLs with titles
- Optionally stored to session context as `research_cache[topic]`

**Tools available:**
- `google_search(query, num_results)`
- `fetch_page_content(url)` — for deeper reads of specific pages
- `session_store_research(topic, summary)` — persist to L6

**Pseudocode:**

```
SYSTEM_INSTRUCTION = """
  You are the Research Agent. You gather information from the web.
  Steps:
  1. Decompose the topic into 2-3 specific search queries.
  2. Run each query, collect top results.
  3. If a result looks highly relevant, call fetch_page_content for the full text.
  4. Synthesize findings into a structured summary with:
     - Key finding 1, 2, 3 (bullet points)
     - Conflicting information (if any)
     - Source list with URLs
  5. If the orchestrator requested deep research, store the summary to session memory.
  Always cite sources. Never present information without a URL attribution.
"""

research_agent = LlmAgent(
  name = "research_agent",
  model = "gemini-2.0-flash",
  instruction = SYSTEM_INSTRUCTION,
  tools = load_research_tools()   # from tools/search_tool.py
)
```

---

### 4.4 Tools & MCP Gateway (L4)

---

#### `tools/mcp_gateway.py`

**Purpose:** Central connection manager for all MCP server connections. Maintains persistent SSE connections to remote MCP servers, handles reconnection on failure, and provides a unified `get_toolset(server_name)` interface for agent files to call.

**Inputs:**
- `server_name: str` — which MCP server to connect to
- `auth_token: str` — OAuth token for the server

**Outputs:**
- `ADK MCPToolset` instance with all tools from that server ready to use

**Pseudocode:**

```
connection_pool = {}   # server_name → MCPToolset instance

async function get_toolset(server_name, auth_token):
  if server_name in connection_pool and connection_pool[server_name].is_alive():
    return connection_pool[server_name]

  server_config = MCP_SERVER_CONFIGS[server_name]
  # server_config has: url, auth_scheme (oauth | api_key | none)

  toolset = MCPToolset(
    connection_params = SseServerParams(
      url = server_config.url,
      headers = {"Authorization": f"Bearer {auth_token}"}
    )
  )
  await toolset.connect()
  connection_pool[server_name] = toolset
  return toolset

async function close_all():
  for toolset in connection_pool.values():
    await toolset.close()
```

---

#### `tools/calendar_mcp.py`

**Purpose:** Wraps the Google Calendar MCP server connection and exposes a `load_calendar_tools()` function that `agents/calendar_agent.py` calls at startup. Handles fetching a fresh OAuth token from `auth_manager` before connecting.

**Inputs:** None at module level (tokens fetched from auth_manager at runtime)

**Outputs:**
- `list[MCPTool]` — ADK-compatible tool list from the Google Calendar MCP server

**Pseudocode:**

```
CALENDAR_MCP_URL = "https://calendar.googleapis.com/mcp/v1/sse"

async function load_calendar_tools():
  token = await auth_manager.get_token("google_calendar")
  toolset = await mcp_gateway.get_toolset("google_calendar", token)
  tools = await toolset.list_tools()
  return tools

# Tools returned by the Calendar MCP server include:
#   calendar.events.insert
#   calendar.events.list
#   calendar.events.patch
#   calendar.events.delete
#   calendar.freebusy.query
```

---

#### `tools/gmail_mcp.py`

**Purpose:** Same pattern as `calendar_mcp.py` but for the Gmail MCP server. Exposes `load_gmail_tools()` for the email_agent.

**Inputs:** None at module level

**Outputs:**
- `list[MCPTool]` — ADK-compatible Gmail tool list

**Pseudocode:**

```
GMAIL_MCP_URL = "https://gmail.googleapis.com/mcp/v1/sse"

async function load_gmail_tools():
  token = await auth_manager.get_token("gmail")
  toolset = await mcp_gateway.get_toolset("gmail", token)
  tools = await toolset.list_tools()
  return tools

# Tools returned by the Gmail MCP server include:
#   gmail.messages.send
#   gmail.messages.list
#   gmail.threads.get
#   gmail.drafts.create
#   gmail.drafts.send
#   gmail.users.labels.list
```

---

#### `tools/search_tool.py`

**Purpose:** Wraps the Google Custom Search API (or Serper API) as an ADK `FunctionTool`. Also provides a `fetch_page_content` tool for the research agent to read specific web pages. Does not use MCP — uses a direct HTTP call wrapped in the FunctionTool pattern.

**Inputs:**
- `query: str` — search query
- `num_results: int` — default 5

**Outputs:**
- `list[SearchResult]` — each has `{title, url, snippet}`

**Pseudocode:**

```
@FunctionTool
async function google_search(query: str, num_results: int = 5):
  """Search the web for current information on a topic."""
  api_key = settings.SEARCH_API_KEY
  response = await http_get(SEARCH_API_URL, params={q: query, num: num_results, key: api_key})
  results = parse_search_response(response)
  return [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results]

@FunctionTool
async function fetch_page_content(url: str):
  """Fetch and return the main text content of a webpage."""
  html = await http_get(url, timeout=10)
  text = extract_main_content(html)   # strip nav, ads, boilerplate
  return {"url": url, "content": text[:4000]}   # cap at 4000 chars

function load_research_tools():
  return [google_search, fetch_page_content, session_store_research]
```

---

#### `tools/task_db_tool.py`

**Purpose:** Wraps Cloud SQL task operations as ADK `FunctionTool` instances. The task_agent calls these tools. Internally calls `db/task_repository.py` for the actual SQL operations.

**Inputs/Outputs:** Vary per function (see pseudocode)

**Pseudocode:**

```
@FunctionTool
async function task_create(title: str, description: str, priority: int, due_date: str, tags: list[str]):
  """Create a new task and store it in the database."""
  task = await task_repository.create({
    user_id: current_user_id(),
    title, description, priority,
    due_date: parse_date(due_date),
    tags, status: "pending"
  })
  return {"task_id": task.id, "title": task.title, "priority": task.priority}

@FunctionTool
async function task_list(filter_status: str = "pending", filter_priority: int = None, limit: int = 20):
  """List tasks for the current user, sorted by priority and due date."""
  tasks = await task_repository.list(user_id, filter_status, filter_priority, limit)
  return [{"id": t.id, "title": t.title, "priority": t.priority, "due_date": t.due_date} for t in tasks]

@FunctionTool
async function task_complete(task_id: str):
  """Mark a task as completed."""
  updated = await task_repository.update(task_id, {status: "completed", completed_at: now()})
  return {"task_id": task_id, "status": "completed"}

function load_task_tools():
  return [task_create, task_list, task_update, task_complete, task_delete]
```

---

#### `tools/auth_manager.py`

**Purpose:** Manages OAuth2 access tokens for all external services. Fetches tokens from Google Cloud Secret Manager, caches them in memory, and refreshes them before they expire. The only file that talks to Secret Manager.

**Inputs:**
- `service_name: str` — e.g. `"google_calendar"`, `"gmail"`

**Outputs:**
- `access_token: str` — valid, non-expired OAuth2 bearer token

**Pseudocode:**

```
token_cache = {}   # service_name → {token, expires_at}

async function get_token(service_name):
  if service_name in token_cache:
    cached = token_cache[service_name]
    if cached.expires_at > now() + 60_seconds_buffer:
      return cached.token

  # fetch refresh token from Secret Manager
  refresh_token = await secret_manager.get_secret(f"{service_name}_refresh_token")
  client_id = settings.GOOGLE_CLIENT_ID
  client_secret = settings.GOOGLE_CLIENT_SECRET

  # exchange refresh token for new access token
  response = await oauth2.refresh(refresh_token, client_id, client_secret)
  token_cache[service_name] = {
    token: response.access_token,
    expires_at: now() + response.expires_in
  }
  return response.access_token
```

---

### 4.5 Database / Memory Layer (L6)

---

#### `db/models.py`

**Purpose:** SQLAlchemy ORM model definitions for all Cloud SQL tables. Three tables back the L6 memory layer.

**Tables defined:**

```
Table: sessions
  id: UUID (PK)
  user_id: str (indexed)
  state_json: JSONB          -- ADK session state blob
  created_at: datetime
  updated_at: datetime

Table: tasks
  id: UUID (PK)
  user_id: str (indexed)
  session_id: UUID (FK → sessions)
  title: str
  description: text
  priority: int (1–5)
  status: Enum[pending, in_progress, completed, cancelled]
  due_date: datetime | null
  tags: ARRAY[str]
  created_at: datetime
  completed_at: datetime | null

Table: agent_logs
  id: UUID (PK)
  session_id: UUID (FK → sessions)
  agent_id: str
  task_id: UUID | null
  tool_name: str
  input_json: JSONB
  output_json: JSONB
  latency_ms: int
  status: str
  created_at: datetime

Table: user_preferences
  user_id: str (PK)
  timezone: str
  default_calendar_id: str
  email_tone: Enum[formal, casual, friendly]
  notification_prefs: JSONB
```

---

#### `db/session_store.py`

**Purpose:** Custom ADK `BaseSessionService` implementation that persists session state to Cloud SQL in addition to keeping it in memory. Allows sessions to survive Cloud Run instance restarts.

**Inputs:**
- `session_id: str`, `user_id: str`
- `state_update: dict` — key-value pairs to merge into session state

**Outputs:**
- `Session` object with full state loaded

**Pseudocode:**

```
class CloudSqlSessionService extends InMemorySessionService:

  async function get_or_create(session_id, user_id):
    # check in-memory first
    if session_id in memory_store:
      return memory_store[session_id]

    # check Cloud SQL
    row = await db.query(sessions).where(id=session_id).first()
    if row:
      session = deserialize(row.state_json)
      memory_store[session_id] = session
      return session

    # create new
    session = Session(id=session_id, user_id=user_id, state={})
    await db.insert(sessions, session)
    memory_store[session_id] = session
    return session

  async function update_state(session_id, state_update):
    session = memory_store[session_id]
    session.state.merge(state_update)
    # async write-through to Cloud SQL (non-blocking)
    asyncio.create_task(db.update(sessions, session_id, state_json=serialize(session.state)))
```

---

#### `db/task_repository.py`

**Purpose:** Data access layer for the `tasks` table. All SQL queries for task operations live here. Called by `tools/task_db_tool.py`. Keeps SQL out of tool and agent files.

**Inputs/Outputs:** Vary per function (pass dicts, return ORM Task objects)

**Pseudocode:**

```
async function create(task_data: dict) → Task:
  task = Task(**task_data)
  session.add(task)
  await session.commit()
  return task

async function list(user_id, filter_status, filter_priority, limit) → list[Task]:
  query = select(Task).where(Task.user_id == user_id)
  if filter_status: query = query.where(Task.status == filter_status)
  if filter_priority: query = query.where(Task.priority >= filter_priority)
  query = query.order_by(Task.priority.desc(), Task.due_date.asc()).limit(limit)
  return await session.execute(query).scalars().all()

async function update(task_id, changes: dict) → Task:
  await session.execute(update(Task).where(Task.id == task_id).values(**changes))
  await session.commit()
  return await get(task_id)

async function delete(task_id) → bool:
  await session.execute(delete(Task).where(Task.id == task_id))
  await session.commit()
  return True
```

---

### 4.6 Config & Infrastructure

---

#### `config/settings.py`

**Purpose:** Single configuration object using Pydantic `BaseSettings`. Reads all environment variables (injected by Cloud Run from Secret Manager). Every other module imports from here — no direct `os.getenv()` calls elsewhere.

**Inputs:** Environment variables / Cloud Run secrets

**Outputs:** `Settings` singleton object

**Pseudocode:**

```
class Settings(BaseSettings):
  # ADK / Gemini
  GOOGLE_API_KEY: str
  GEMINI_MODEL: str = "gemini-2.0-flash"

  # OAuth for Google APIs
  GOOGLE_CLIENT_ID: str
  GOOGLE_CLIENT_SECRET: str
  CALENDAR_REFRESH_TOKEN: str
  GMAIL_REFRESH_TOKEN: str

  # Search
  SEARCH_API_KEY: str
  SEARCH_API_URL: str = "https://customsearch.googleapis.com/customsearch/v1"

  # Database
  DATABASE_URL: str     # postgres://user:pass@host/db (Cloud SQL proxy URL)

  # API
  ALLOWED_ORIGINS: list[str] = ["*"]
  API_KEY_HEADER: str = "X-API-Key"

  # Thresholds
  AMBIGUITY_THRESHOLD: float = 0.6
  TOOL_TIMEOUT_MS: int = 10000

  class Config:
    env_file = ".env"

settings = Settings()
```

---

#### `Dockerfile`

**Purpose:** Single-stage Docker build that produces the Cloud Run container image. All eight layers run in this one container.

**Pseudocode:**

```
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install .

COPY command_center/ ./command_center/

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "command_center.api.main:app",
     "--host", "0.0.0.0",
     "--port", "8080",
     "--workers", "1"]
```

---

#### `cloudbuild.yaml`

**Purpose:** Cloud Build CI/CD pipeline. Triggered on git push to main. Builds image, pushes to Artifact Registry, runs DB migrations, deploys to Cloud Run.

**Pseudocode:**

```
steps:
  1. BUILD:  docker build -t $IMAGE .
  2. PUSH:   docker push $IMAGE to Artifact Registry
  3. MIGRATE: run "alembic upgrade head" in Cloud SQL
  4. DEPLOY:  gcloud run deploy command-center
                --image $IMAGE
                --region us-central1
                --set-secrets (all from Secret Manager)
                --concurrency 80
                --min-instances 1
  5. SMOKE TEST: curl /health → expect 200
  6. TRAFFIC: shift 100% traffic to new revision
```

---

## 5. Data Transfer Objects (Contracts)

Every inter-layer boundary has one and only one contract type. The flow is:

```
UserRequest
    ↓ (L0 → L1)
ParsedCommand
    ↓ (L1 → L2)
AgentTask          ← dispatched to one or more sub-agents
    ↓ (L2 → L3)
ToolCall           ← issued by sub-agents to tools
    ↓ (L3 → L4)
ExternalRequest    ← normalized by gateway before hitting APIs
    ↓ (L4 → L5)
ToolResponse       ← returned from external service
    ↑ (L5 → L4 → L3)
AgentResult        ← returned from sub-agent to orchestrator
    ↑ (L3 → L2)
FinalResponse      ← synthesized from all AgentResults
    ↑ (L7 → L0)
```

All contracts are defined in `api/schemas.py` as Pydantic models. No raw dicts cross layer boundaries.

---

## 6. MCP Implementation Guide

### 6.1 What is MCP in ADK

**Model Context Protocol (MCP)** is an open standard for connecting AI agents to external tools and data sources. In ADK, the `MCPToolset` class handles:

- Opening a persistent connection (SSE) or subprocess (Stdio) to an MCP server
- Fetching the list of available tools from the server (`tools/list`)
- Wrapping each MCP tool as an ADK-compatible `Tool` object that Gemini can call
- Handling the JSON-RPC message exchange on each tool invocation

In this project MCP is used in **L4 (Tool & MCP Gateway)** as the mechanism by which sub-agents call Google Calendar and Gmail. The gateway abstracts MCP connection management so sub-agents never deal with protocol details.

---

### 6.2 Option A — Google Calendar MCP (Remote SSE)

**What it is:** Google hosts an official MCP server for Calendar that exposes Calendar API operations as MCP tools. Connection is via Server-Sent Events (SSE) over HTTPS.

**When to use:** Production use for all Calendar operations. Best option — maintained by Google, includes all Calendar API methods.

**Implementation:**

```python
# tools/calendar_mcp.py

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams

async def load_calendar_tools(access_token: str):
    toolset = MCPToolset(
        connection_params=SseServerParams(
            url="https://calendar.googleapis.com/mcp/v1/sse",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
    )
    async with toolset:
        tools = await toolset.load_tools()
        return tools

# Tools exposed by this MCP server:
#   calendar_events_insert   → create event
#   calendar_events_list     → list events in range
#   calendar_events_patch    → update event fields
#   calendar_events_delete   → delete event
#   calendar_freebusy_query  → check availability for multiple calendars
```

**Auth:** Requires a valid Google OAuth2 access token with scope `https://www.googleapis.com/auth/calendar`. Token is fetched by `auth_manager.py` using the stored refresh token.

**Pros:** Full Calendar API surface, maintained, no infrastructure to run
**Cons:** Requires internet from Cloud Run; slight latency on each tool call

---

### 6.3 Option B — Gmail MCP (Remote SSE)

**What it is:** Google's official Gmail MCP server, exposes Gmail API as MCP tools.

**When to use:** Production use for all email operations.

**Implementation:**

```python
# tools/gmail_mcp.py

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams

async def load_gmail_tools(access_token: str):
    toolset = MCPToolset(
        connection_params=SseServerParams(
            url="https://gmail.googleapis.com/mcp/v1/sse",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    )
    async with toolset:
        tools = await toolset.load_tools()
        return tools

# Tools exposed:
#   gmail_messages_send      → send email
#   gmail_messages_list      → list/search messages
#   gmail_threads_get        → get full thread
#   gmail_drafts_create      → create draft
#   gmail_drafts_send        → send existing draft
#   gmail_users_labels_list  → list labels
```

**Auth:** Requires OAuth2 token with scope `https://www.googleapis.com/auth/gmail.modify`.

**Pros:** Same as Calendar MCP — full API, maintained by Google
**Cons:** Same constraints; email sending requires explicit user confirmation in agent instruction

---

### 6.4 Option C — Local MCP Server (Custom FastMCP)

**What it is:** You run your own MCP server alongside the main app (in the same container or as a sidecar). Built with the `fastmcp` Python library. Useful for custom tools not covered by official MCP servers, like the task database operations.

**When to use:** When you need to expose internal data (Cloud SQL, internal APIs) as MCP tools. Can also be used to wrap third-party APIs (Notion, Trello, Slack) that don't have official MCP servers.

**Implementation:**

```python
# tools/custom_mcp_server.py — runs as a sidecar or thread

from fastmcp import FastMCP

mcp = FastMCP("command-center-tools")

@mcp.tool()
async def task_create(title: str, priority: int, due_date: str) -> dict:
    """Create a task in the Cloud SQL tasks table."""
    task = await task_repository.create({title, priority, due_date})
    return {"task_id": str(task.id), "title": task.title}

@mcp.tool()
async def task_list(status: str = "pending") -> list:
    """List pending tasks for the current user."""
    tasks = await task_repository.list(current_user_id(), status)
    return [{"id": str(t.id), "title": t.title, "priority": t.priority} for t in tasks]

# Serve via SSE on localhost:8001
if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8001)

# ----
# In task_agent.py, connect to this local server:
toolset = MCPToolset(
    connection_params=SseServerParams(
        url="http://127.0.0.1:8001/sse"
        # no auth needed — local loopback
    )
)
```

**Pros:** Full control over tool definitions, can access any internal resource, no external network
**Cons:** You own the MCP server code and its reliability; adds a process to manage

---

### 6.5 Option D — Stdio MCP (Subprocess)

**What it is:** Instead of an SSE server, the MCP server runs as a subprocess that communicates over stdin/stdout. ADK's `StdioServerParameters` handles spawning and communicating with the subprocess.

**When to use:** Local development, testing, or when the MCP tool is packaged as a CLI (e.g. the official `@modelcontextprotocol/server-filesystem` npm package for file access).

**Implementation:**

```python
# For a Node.js MCP server run as subprocess
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command="node",
        args=["path/to/mcp-server/index.js"],
        env={"API_KEY": settings.SOME_KEY}
    )
)

# For a Python MCP server run as subprocess
toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=["-m", "my_mcp_server"],
        env={"DATABASE_URL": settings.DATABASE_URL}
    )
)
```

**Pros:** Simple for development; works with any language's MCP implementation
**Cons:** Not suitable for production Cloud Run (process management is complex); higher latency per call

---

### 6.6 MCP vs FunctionTool Decision Matrix

| Scenario | Recommended Approach |
|----------|---------------------|
| Google Calendar operations | MCP (Option A) — official server |
| Gmail operations | MCP (Option B) — official server |
| Cloud SQL task CRUD | FunctionTool wrapping task_repository — simpler, in-process |
| Google Search | FunctionTool wrapping Search REST API — no MCP server needed |
| Notion / Trello / Slack | Custom MCP server (Option C) using their REST APIs |
| File system access (dev only) | Stdio MCP (Option D) with filesystem MCP server |
| Internal microservice calls | FunctionTool wrapping the service's HTTP client |
| Third-party with official MCP | Remote SSE MCP (Option A/B pattern) |

**Rule of thumb:**
- Official Google MCP servers exist → use them (Options A/B)
- Tool accesses internal data → use FunctionTool (stays in-process, faster)
- Complex third-party API with many endpoints → build a custom MCP server (Option C)
- Development/testing only → Stdio MCP (Option D)

---

### 6.7 Auth & Token Management for MCP

All MCP connections that talk to Google APIs require a valid OAuth2 access token. The flow is:

```
1. At startup (or on first tool call):
   auth_manager.get_token("google_calendar")
       ↓
   Reads CALENDAR_REFRESH_TOKEN from Secret Manager
       ↓
   POST to https://oauth2.googleapis.com/token
     {grant_type: "refresh_token", refresh_token, client_id, client_secret}
       ↓
   Returns {access_token, expires_in: 3600}
       ↓
   Cached in memory with expiry

2. On each MCP connection:
   SseServerParams(headers={"Authorization": f"Bearer {access_token}"})

3. Token refresh:
   auth_manager checks cache before each call
   If expires_at < now + 60s → refresh automatically
   This is transparent to the sub-agents

4. For Cloud Run:
   CALENDAR_REFRESH_TOKEN stored in Google Cloud Secret Manager
   Injected into container as env var at deploy time
   Never appears in code or source control
```

**Required OAuth scopes:**

| Service | Scope |
|---------|-------|
| Google Calendar | `https://www.googleapis.com/auth/calendar` |
| Gmail (read+send) | `https://www.googleapis.com/auth/gmail.modify` |
| Google Search | API Key (no OAuth needed) |

---

## 7. End-to-End Workflow Example

**User input:** `"Schedule a 1-hour meeting with alice@co.com on Friday at 2pm and email her the agenda"`

```
L0  POST /run  →  UserRequest{message: "Schedule..."}

L1  intent_classifier  →  domain=compound, intent=schedule_and_email
    entity_extractor   →  {date: "2025-06-06T14:00", duration: 60,
                           attendees: ["alice@co.com"], topic: "meeting"}
    ambiguity_resolver →  resolved=True (all required fields present)
    →  ParsedCommand{domain=compound}

L2  root_agent (orchestrator):
    STEP 1: call calendar_agent("Schedule 1hr meeting with alice@co.com Friday 2pm")
      L3 calendar_agent:
        → gcal_check_free_busy(["alice@co.com"], Friday 2-3pm)
        → slot is free
        → gcal_create_event(title="Meeting", start=Friday 2pm, end=3pm, attendees=["alice@co.com"])
        → returns AgentResult{data: {event_id: "abc123", link: "https://cal.google.com/..."}}
    STEP 2: call email_agent("Email alice@co.com with agenda for our Friday 2pm meeting")
      (orchestrator passes event link from STEP 1 as context)
      L3 email_agent:
        → gmail_draft(to="alice@co.com", subject="Friday Meeting Agenda",
                      body="Hi Alice, here are the agenda items for our 2pm meeting on Friday...")
        → confirm send (orchestrator instruction: always confirm before sending)
        → gmail_send(draft_id)
        → returns AgentResult{data: {message_id: "xyz789"}}

L7  synthesizer:
    merge [calendar_result, email_result]
    → FinalResponse{
        summary: "Done! I've scheduled a 1-hour meeting with Alice for Friday at 2pm
                  and emailed her the agenda.",
        actions_taken: [
          {agent: "calendar", action: "create_event", success: true},
          {agent: "email",    action: "send_email",   success: true}
        ],
        follow_ups: ["Would you like to add this to a task for meeting prep?"]
      }

L0  return JSON to client
```

---

## 8. Deployment Notes

### Cloud Run Configuration

```yaml
service: command-center
image: us-central1-docker.pkg.dev/{project}/adk/command-center:latest
region: us-central1
memory: 4Gi
cpu: 2
min-instances: 1          # always warm — no cold starts
max-instances: 10
concurrency: 80
timeout: 300s             # 5 min for long research tasks
```

### Cloud SQL

```sql
-- Three application tables (see db/models.py for full schema)
CREATE TABLE sessions (id UUID PK, user_id TEXT, state_json JSONB, ...);
CREATE TABLE tasks (id UUID PK, user_id TEXT, session_id UUID FK, priority INT, ...);
CREATE TABLE agent_logs (id UUID PK, session_id UUID FK, agent_id TEXT, latency_ms INT, ...);
```

### Environment Variables (Secret Manager)

| Variable | Source | Used By |
|----------|--------|---------|
| `GOOGLE_API_KEY` | Secret Manager | all agents (Gemini) |
| `GOOGLE_CLIENT_ID` | Secret Manager | auth_manager |
| `GOOGLE_CLIENT_SECRET` | Secret Manager | auth_manager |
| `CALENDAR_REFRESH_TOKEN` | Secret Manager | auth_manager |
| `GMAIL_REFRESH_TOKEN` | Secret Manager | auth_manager |
| `SEARCH_API_KEY` | Secret Manager | search_tool |
| `DATABASE_URL` | Cloud Run env | session_store, task_repository |

### Key Dependencies (`pyproject.toml`)

```toml
[tool.poetry.dependencies]
python = "^3.12"
google-adk = "^1.0"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.30"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.29"         # async Postgres driver
pydantic-settings = "^2.0"
google-auth = "^2.0"
httpx = "^0.27"           # async HTTP for search_tool
alembic = "^1.13"
fastmcp = "^0.9"          # for custom MCP server (Option C)
```

---

*Document version 1.0 — ADK Command Center*
