"""
Data models for the Request Planner.

This module defines the core data structures used throughout the agent system,
including change requests, plans, and task specifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid


class StepKind(str, Enum):
    """Types of steps that can be performed."""
    EDIT = "edit"
    ADD = "add"
    REMOVE = "remove"
    REFACTOR = "refactor"
    TEST = "test"
    REVIEW = "review"


class ComplexityLevel(str, Enum):
    """Complexity levels for tasks."""
    TRIVIAL = "trivial"
    MODERATE = "moderate"
    COMPLEX = "complex"


class TaskStatus(str, Enum):
    """Status of a task in the system."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FileDelta:
    """Represents a change to a file."""
    path: str
    action: str  # add, modify, delete
    diff: Optional[str] = None
    

@dataclass
class ChangeRequest:
    """A request for a code change from a user or upstream system."""
    description: str
    repo: str = "."
    branch: str = "main"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requester: str = "user"
    created_at: datetime = field(default_factory=datetime.now)
    deltas: List[FileDelta] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "requester": self.requester,
            "repo": self.repo,
            "branch": self.branch,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "deltas": [{"path": d.path, "action": d.action} for d in self.deltas]
        }


@dataclass
class Step:
    """A single step in an implementation plan."""
    order: int
    goal: str
    kind: StepKind
    hints: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "order": self.order,
            "goal": self.goal,
            "kind": self.kind.value,
            "hints": self.hints,
            "dependencies": self.dependencies
        }


@dataclass
class Plan:
    """An implementation plan generated from a change request."""
    id: str
    parent_request_id: str
    steps: List[Step]
    rationale: List[str] = field(default_factory=list)
    affected_paths: List[str] = field(default_factory=list)
    complexity_label: ComplexityLevel = ComplexityLevel.MODERATE
    estimated_tokens: int = 0
    created_by: str = "request_planner"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "parent_request_id": self.parent_request_id,
            "steps": [step.to_dict() for step in self.steps],
            "rationale": self.rationale,
            "affected_paths": self.affected_paths,
            "complexity_label": self.complexity_label.value,
            "estimated_tokens": self.estimated_tokens,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        """Create a Plan from dictionary representation."""
        steps = [
            Step(
                order=s["order"],
                goal=s["goal"],
                kind=StepKind(s["kind"]),
                hints=s.get("hints", []),
                dependencies=s.get("dependencies", [])
            )
            for s in data["steps"]
        ]
        
        return cls(
            id=data["id"],
            parent_request_id=data["parent_request_id"],
            steps=steps,
            rationale=data.get("rationale", []),
            affected_paths=data.get("affected_paths", []),
            complexity_label=ComplexityLevel(data.get("complexity_label", "moderate")),
            estimated_tokens=data.get("estimated_tokens", 0),
            created_by=data.get("created_by", "request_planner")
        )


@dataclass
class Task:
    """A task being tracked by the system."""
    id: str
    description: str
    status: TaskStatus
    plan_id: Optional[str] = None
    step_number: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "plan_id": self.plan_id,
            "step_number": self.step_number,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error": self.error
        }


@dataclass
class SearchResult:
    """A search result from the codebase."""
    file: str
    line: int
    content: str
    score: float = 0.0
    context: Optional[str] = None