"""
Pydantic models for all frontend communication.

These models define the API contract between backend and frontend.
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


# Enums

class AgentType(str, Enum):
    """Available agent types."""
    REQUEST_PLANNER = "request_planner"
    CODE_PLANNER = "code_planner"
    CODING_AGENT = "coding_agent"
    RAG_SERVICE = "rag_service"
    GIT_OPERATIONS = "git_operations"


class AgentStatus(str, Enum):
    """Agent status states."""
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    OFFLINE = "offline"


class JobStatus(str, Enum):
    """Job/task status states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


# Request Models

class SetAgentModelRequest(BaseModel):
    """Request to set model for an agent."""
    model: str = Field(..., description="Model name to use")
    
    @validator('model')
    def validate_model(cls, v):
        """Validate model name."""
        allowed_models = [
            "claude-opus", "claude-3.5", "gpt-4", "gpt-3.5", 
            "llama-2", "codellama", "mixtral"
        ]
        if v not in allowed_models:
            raise ValueError(f"Model must be one of: {allowed_models}")
        return v


class WebSocketMessage(BaseModel):
    """WebSocket message from client."""
    type: Literal["subscribe", "unsubscribe", "command"]
    topic: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# Response Models

class AgentInfo(BaseModel):
    """Information about an agent."""
    type: AgentType
    status: AgentStatus
    model: str
    current_task: Optional[str] = None
    last_active: Optional[datetime] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentGraphNode(BaseModel):
    """Node in the agent graph."""
    id: str
    type: AgentType
    status: AgentStatus
    x: Optional[float] = None
    y: Optional[float] = None


class AgentGraphEdge(BaseModel):
    """Edge in the agent graph."""
    source: str
    target: str
    active: bool = False
    data_flow: Optional[str] = None


class AgentGraph(BaseModel):
    """Complete agent graph data."""
    nodes: List[AgentGraphNode]
    edges: List[AgentGraphEdge]
    timestamp: datetime = Field(default_factory=datetime.now)


class LogEntry(BaseModel):
    """Single log entry."""
    timestamp: datetime
    level: LogLevel
    source: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobSummary(BaseModel):
    """Summary of a job for list views."""
    job_id: str
    title: str
    status: JobStatus
    progress: float = Field(ge=0, le=100)
    created_at: datetime
    updated_at: datetime
    agent_type: Optional[AgentType] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobDetail(BaseModel):
    """Detailed job information."""
    job_id: str
    title: str
    status: JobStatus
    progress: float = Field(ge=0, le=100)
    created_at: datetime
    updated_at: datetime
    agent_type: Optional[AgentType] = None
    plan: Optional[str] = None
    diff: Optional[str] = None
    logs: List[LogEntry] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemMetrics(BaseModel):
    """System performance metrics."""
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    memory_mb: float
    queue_size: int = Field(ge=0)
    active_jobs: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# API Response Wrappers

class ApiResponse(BaseModel):
    """Base API response."""
    success: bool
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentsResponse(ApiResponse):
    """Response containing agent information."""
    agents: List[AgentInfo]


class JobsResponse(ApiResponse):
    """Response containing job list."""
    jobs: List[JobSummary]
    total: int
    limit: int
    offset: int


class JobDetailResponse(ApiResponse):
    """Response containing job details."""
    job: JobDetail


class MetricsResponse(ApiResponse):
    """Response containing system metrics."""
    metrics: SystemMetrics


# WebSocket Event Models

class WebSocketEvent(BaseModel):
    """Base WebSocket event from server."""
    type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentUpdateEvent(WebSocketEvent):
    """Agent status update event."""
    type: Literal["agent_update"] = "agent_update"
    data: AgentInfo


class GraphUpdateEvent(WebSocketEvent):
    """Agent graph update event."""
    type: Literal["graph_update"] = "graph_update"
    data: AgentGraph


class LogEntryEvent(WebSocketEvent):
    """New log entry event."""
    type: Literal["log_entry"] = "log_entry"
    data: LogEntry


class JobStatusEvent(WebSocketEvent):
    """Job status update event."""
    type: Literal["job_status"] = "job_status"
    data: JobSummary


class TaskProgressEvent(WebSocketEvent):
    """Task progress update event."""
    type: Literal["task_progress"] = "task_progress"
    data: Dict[str, Any]  # Contains task_id, progress, status