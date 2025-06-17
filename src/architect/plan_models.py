"""
Data models for phased implementation plans.

This module defines the structure for detailed implementation plans that
provide rich context throughout the development pipeline.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
import uuid


class PlanStatus(Enum):
    """Status of an implementation plan."""
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PhaseType(Enum):
    """Types of implementation phases."""
    RESEARCH = "research"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    OPTIMIZATION = "optimization"


@dataclass
class PlanChunk:
    """
    A chunk of implementation context that can be attached to tasks.
    
    Chunks are the atomic units of context that get passed to execution agents.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""
    chunk_type: str = "general"  # general, technical, architectural, testing, etc.
    
    # Context details
    technologies: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)
    
    # Code context
    relevant_files: List[str] = field(default_factory=list)
    relevant_patterns: List[str] = field(default_factory=list)
    api_specifications: Dict[str, Any] = field(default_factory=dict)
    
    # Testing context
    test_requirements: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    tags: Set[str] = field(default_factory=set)
    priority: int = 0  # Higher number = higher priority
    
    # Task associations
    task_ids: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "chunk_type": self.chunk_type,
            "technologies": self.technologies,
            "dependencies": self.dependencies,
            "constraints": self.constraints,
            "examples": self.examples,
            "relevant_files": self.relevant_files,
            "relevant_patterns": self.relevant_patterns,
            "api_specifications": self.api_specifications,
            "test_requirements": self.test_requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "created_at": self.created_at.isoformat(),
            "tags": list(self.tags),
            "priority": self.priority,
            "task_ids": list(self.task_ids)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanChunk':
        """Create from dictionary."""
        chunk = cls()
        chunk.id = data.get("id", str(uuid.uuid4()))
        chunk.title = data.get("title", "")
        chunk.content = data.get("content", "")
        chunk.chunk_type = data.get("chunk_type", "general")
        chunk.technologies = data.get("technologies", [])
        chunk.dependencies = data.get("dependencies", [])
        chunk.constraints = data.get("constraints", [])
        chunk.examples = data.get("examples", [])
        chunk.relevant_files = data.get("relevant_files", [])
        chunk.relevant_patterns = data.get("relevant_patterns", [])
        chunk.api_specifications = data.get("api_specifications", {})
        chunk.test_requirements = data.get("test_requirements", [])
        chunk.acceptance_criteria = data.get("acceptance_criteria", [])
        chunk.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        chunk.tags = set(data.get("tags", []))
        chunk.priority = data.get("priority", 0)
        chunk.task_ids = set(data.get("task_ids", []))
        return chunk


@dataclass
class PlanMilestone:
    """
    A milestone within a phase representing a significant achievement.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    
    # Deliverables
    deliverables: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    
    # Context chunks for this milestone
    chunks: List[PlanChunk] = field(default_factory=list)
    
    # Dependencies
    depends_on_milestones: Set[str] = field(default_factory=set)
    
    # Metadata
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    status: str = "pending"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "deliverables": self.deliverables,
            "success_criteria": self.success_criteria,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "depends_on_milestones": list(self.depends_on_milestones),
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanMilestone':
        """Create from dictionary."""
        milestone = cls()
        milestone.id = data.get("id", str(uuid.uuid4()))
        milestone.title = data.get("title", "")
        milestone.description = data.get("description", "")
        milestone.deliverables = data.get("deliverables", [])
        milestone.success_criteria = data.get("success_criteria", [])
        milestone.chunks = [PlanChunk.from_dict(c) for c in data.get("chunks", [])]
        milestone.depends_on_milestones = set(data.get("depends_on_milestones", []))
        milestone.estimated_hours = data.get("estimated_hours", 0.0)
        milestone.actual_hours = data.get("actual_hours", 0.0)
        milestone.status = data.get("status", "pending")
        return milestone


@dataclass
class ImplementationPhase:
    """
    A phase of the implementation plan (e.g., Design, Implementation, Testing).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    phase_type: PhaseType = PhaseType.IMPLEMENTATION
    description: str = ""
    
    # Phase objectives
    objectives: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    
    # Milestones in this phase
    milestones: List[PlanMilestone] = field(default_factory=list)
    
    # Phase-level context
    technologies: List[str] = field(default_factory=list)
    architectural_decisions: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # Dependencies
    depends_on_phases: Set[str] = field(default_factory=set)
    
    # Metadata
    order: int = 0  # Execution order
    estimated_days: float = 0.0
    actual_days: float = 0.0
    status: str = "pending"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "phase_type": self.phase_type.value,
            "description": self.description,
            "objectives": self.objectives,
            "key_decisions": self.key_decisions,
            "milestones": [m.to_dict() for m in self.milestones],
            "technologies": self.technologies,
            "architectural_decisions": self.architectural_decisions,
            "risk_factors": self.risk_factors,
            "depends_on_phases": list(self.depends_on_phases),
            "order": self.order,
            "estimated_days": self.estimated_days,
            "actual_days": self.actual_days,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImplementationPhase':
        """Create from dictionary."""
        phase = cls()
        phase.id = data.get("id", str(uuid.uuid4()))
        phase.name = data.get("name", "")
        phase.phase_type = PhaseType(data.get("phase_type", "implementation"))
        phase.description = data.get("description", "")
        phase.objectives = data.get("objectives", [])
        phase.key_decisions = data.get("key_decisions", [])
        phase.milestones = [PlanMilestone.from_dict(m) for m in data.get("milestones", [])]
        phase.technologies = data.get("technologies", [])
        phase.architectural_decisions = data.get("architectural_decisions", [])
        phase.risk_factors = data.get("risk_factors", [])
        phase.depends_on_phases = set(data.get("depends_on_phases", []))
        phase.order = data.get("order", 0)
        phase.estimated_days = data.get("estimated_days", 0.0)
        phase.actual_days = data.get("actual_days", 0.0)
        phase.status = data.get("status", "pending")
        return phase


@dataclass
class ImplementationPlan:
    """
    Complete phased implementation plan for a project or feature.
    
    This is the top-level container that holds all phases, milestones, and chunks
    that provide context throughout the development process.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # High-level project context
    project_type: str = ""  # feature, bugfix, refactor, infrastructure, etc.
    scope: str = ""  # small, medium, large, enterprise
    
    # Strategic context
    business_objectives: List[str] = field(default_factory=list)
    technical_requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    
    # Phases of implementation
    phases: List[ImplementationPhase] = field(default_factory=list)
    
    # Global context that applies to all phases
    technology_stack: List[str] = field(default_factory=list)
    architectural_patterns: List[str] = field(default_factory=list)
    coding_standards: List[str] = field(default_factory=list)
    
    # Plan metadata
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "architect"
    
    # Metrics
    total_estimated_days: float = 0.0
    total_actual_days: float = 0.0
    completion_percentage: float = 0.0
    
    # Associated task graph
    task_graph_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "scope": self.scope,
            "business_objectives": self.business_objectives,
            "technical_requirements": self.technical_requirements,
            "constraints": self.constraints,
            "assumptions": self.assumptions,
            "phases": [phase.to_dict() for phase in self.phases],
            "technology_stack": self.technology_stack,
            "architectural_patterns": self.architectural_patterns,
            "coding_standards": self.coding_standards,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "total_estimated_days": self.total_estimated_days,
            "total_actual_days": self.total_actual_days,
            "completion_percentage": self.completion_percentage,
            "task_graph_id": self.task_graph_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImplementationPlan':
        """Create from dictionary."""
        plan = cls()
        plan.id = data.get("id", str(uuid.uuid4()))
        plan.name = data.get("name", "")
        plan.description = data.get("description", "")
        plan.project_type = data.get("project_type", "")
        plan.scope = data.get("scope", "")
        plan.business_objectives = data.get("business_objectives", [])
        plan.technical_requirements = data.get("technical_requirements", [])
        plan.constraints = data.get("constraints", [])
        plan.assumptions = data.get("assumptions", [])
        plan.phases = [ImplementationPhase.from_dict(p) for p in data.get("phases", [])]
        plan.technology_stack = data.get("technology_stack", [])
        plan.architectural_patterns = data.get("architectural_patterns", [])
        plan.coding_standards = data.get("coding_standards", [])
        plan.status = PlanStatus(data.get("status", "draft"))
        plan.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        plan.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        plan.created_by = data.get("created_by", "architect")
        plan.total_estimated_days = data.get("total_estimated_days", 0.0)
        plan.total_actual_days = data.get("total_actual_days", 0.0)
        plan.completion_percentage = data.get("completion_percentage", 0.0)
        plan.task_graph_id = data.get("task_graph_id")
        return plan
    
    def get_all_chunks(self) -> List[PlanChunk]:
        """Get all chunks from all phases and milestones."""
        chunks = []
        for phase in self.phases:
            for milestone in phase.milestones:
                chunks.extend(milestone.chunks)
        return chunks
    
    def get_chunks_for_task(self, task_id: str) -> List[PlanChunk]:
        """Get all chunks associated with a specific task."""
        chunks = []
        for chunk in self.get_all_chunks():
            if task_id in chunk.task_ids:
                chunks.append(chunk)
        return sorted(chunks, key=lambda c: c.priority, reverse=True)
    
    def calculate_metrics(self):
        """Calculate plan metrics based on phase and milestone data."""
        self.total_estimated_days = sum(phase.estimated_days for phase in self.phases)
        self.total_actual_days = sum(phase.actual_days for phase in self.phases)
        
        # Calculate completion percentage
        total_milestones = sum(len(phase.milestones) for phase in self.phases)
        completed_milestones = sum(
            1 for phase in self.phases 
            for milestone in phase.milestones 
            if milestone.status == "completed"
        )
        
        if total_milestones > 0:
            self.completion_percentage = (completed_milestones / total_milestones) * 100
        else:
            self.completion_percentage = 0.0