from datetime import datetime, timezone
from uuid import UUID
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DomainType(str, Enum):
    calendar = "calendar"
    task = "task"
    email = "email"
    research = "research"
    compound = "compound"

class UserRequest(BaseModel):
    session_id: str
    user_id: str
    message: str
    context_hints: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ParsedCommand(BaseModel):
    domain: DomainType
    intent: str
    entities: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 3
    ambiguity_score: float = 0.0
    session_ctx: Dict[str, Any] = Field(default_factory=dict)

class AgentTask(BaseModel):
    task_id: UUID
    agent_id: DomainType
    task_type: str
    payload: Dict[str, Any]
    deadline: Optional[datetime] = None
    depends_on: List[UUID] = Field(default_factory=list)

class RetryConfig(BaseModel):
    max_attempts: int = 3
    backoff_ms: int = 500

class ToolCall(BaseModel):
    tool_name: str
    params: Dict[str, Any]
    auth_token: str
    timeout_ms: int = 10000
    retry_policy: RetryConfig = Field(default_factory=RetryConfig)

class ToolResponseStatus(str, Enum):
    success = "success"
    error = "error"
    timeout = "timeout"

class ToolResponse(BaseModel):
    status: ToolResponseStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: int
    source: str

class ErrorDetail(BaseModel):
    error_code: str
    message: str
    tool_name: Optional[str] = None
    recoverable: bool = False

class AgentResultStatus(str, Enum):
    success = "success"
    partial = "partial"
    failed = "failed"

class AgentResult(BaseModel):
    task_id: UUID
    agent_id: str
    status: AgentResultStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[ErrorDetail] = Field(default_factory=list)
    tool_calls_made: List[str] = Field(default_factory=list)

class ActionRecord(BaseModel):
    agent: str
    action: str
    result_summary: str
    success: bool

class RenderFormat(str, Enum):
    json = "json"
    text = "text"
    sse = "sse"

class FinalResponse(BaseModel):
    session_id: str
    summary: str
    actions_taken: List[ActionRecord] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)
    render_format: RenderFormat = RenderFormat.json
