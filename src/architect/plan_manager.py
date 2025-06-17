"""
Plan management system for the architect agent.

This module provides a central interface for creating, managing, and mapping
implementation plans to tasks throughout the development pipeline.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
import uuid

from .plan_models import (
    ImplementationPlan, ImplementationPhase, PlanMilestone, 
    PlanChunk, PlanStatus, PhaseType
)
from .plan_storage import PlanStorage
from .plan_rag_integration import PlanRAGIntegration
from ..core.logging import get_logger

logger = get_logger(__name__)


class PlanManager:
    """
    Central manager for implementation plans.
    
    Orchestrates plan creation, storage, RAG indexing, and task mapping.
    """
    
    def __init__(self, 
                 base_path: str = ".agent",
                 rag_client: Optional[Any] = None,
                 auto_index: bool = True):
        """
        Initialize the plan manager.
        
        Args:
            base_path: Base directory for agent data
            rag_client: Optional RAG client for semantic search
            auto_index: Whether to automatically index plans in RAG
        """
        self.base_path = Path(base_path)
        self.storage = PlanStorage(base_path)
        self.auto_index = auto_index
        
        # Initialize RAG integration if client provided
        if rag_client:
            self.rag_integration = PlanRAGIntegration(rag_client, self.storage)
        else:
            self.rag_integration = None
            if auto_index:
                logger.warning("Auto-indexing requested but no RAG client provided")
        
        # Task-to-chunk mapping
        self.task_chunk_map_path = self.base_path / "plan_context" / "task_chunk_map.json"
        self.task_chunk_map_path.parent.mkdir(parents=True, exist_ok=True)
        self.task_chunk_map = self._load_task_chunk_map()
    
    def _load_task_chunk_map(self) -> Dict[str, List[str]]:
        """Load the task-to-chunk mapping."""
        if self.task_chunk_map_path.exists():
            try:
                with open(self.task_chunk_map_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load task-chunk map: {e}")
                return {}
        return {}
    
    def _save_task_chunk_map(self):
        """Save the task-to-chunk mapping."""
        try:
            with open(self.task_chunk_map_path, 'w') as f:
                json.dump(self.task_chunk_map, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save task-chunk map: {e}")
    
    def create_plan(self,
                   name: str,
                   description: str,
                   project_type: str = "feature",
                   scope: str = "medium") -> ImplementationPlan:
        """
        Create a new implementation plan.
        
        Args:
            name: Name of the plan
            description: Description of what the plan implements
            project_type: Type of project (feature, bugfix, refactor, etc.)
            scope: Scope of the project (small, medium, large, enterprise)
            
        Returns:
            The created implementation plan
        """
        plan = ImplementationPlan(
            name=name,
            description=description,
            project_type=project_type,
            scope=scope,
            status=PlanStatus.DRAFT
        )
        
        logger.info(f"Created new plan '{name}' (ID: {plan.id})")
        return plan
    
    def add_phase(self,
                  plan: ImplementationPlan,
                  name: str,
                  phase_type: PhaseType,
                  description: str,
                  objectives: List[str],
                  estimated_days: float = 0.0) -> ImplementationPhase:
        """
        Add a phase to an implementation plan.
        
        Args:
            plan: The implementation plan
            name: Name of the phase
            phase_type: Type of phase
            description: Phase description
            objectives: List of phase objectives
            estimated_days: Estimated days for the phase
            
        Returns:
            The created phase
        """
        phase = ImplementationPhase(
            name=name,
            phase_type=phase_type,
            description=description,
            objectives=objectives,
            estimated_days=estimated_days,
            order=len(plan.phases)
        )
        
        plan.phases.append(phase)
        plan.updated_at = datetime.now()
        
        logger.info(f"Added phase '{name}' to plan '{plan.name}'")
        return phase
    
    def add_milestone(self,
                      phase: ImplementationPhase,
                      title: str,
                      description: str,
                      deliverables: List[str],
                      success_criteria: List[str]) -> PlanMilestone:
        """
        Add a milestone to a phase.
        
        Args:
            phase: The phase to add milestone to
            title: Milestone title
            description: Milestone description
            deliverables: List of deliverables
            success_criteria: List of success criteria
            
        Returns:
            The created milestone
        """
        milestone = PlanMilestone(
            title=title,
            description=description,
            deliverables=deliverables,
            success_criteria=success_criteria
        )
        
        phase.milestones.append(milestone)
        
        logger.info(f"Added milestone '{title}' to phase '{phase.name}'")
        return milestone
    
    def add_chunk(self,
                  milestone: PlanMilestone,
                  title: str,
                  content: str,
                  chunk_type: str = "general",
                  priority: int = 0) -> PlanChunk:
        """
        Add a context chunk to a milestone.
        
        Args:
            milestone: The milestone to add chunk to
            title: Chunk title
            content: Chunk content
            chunk_type: Type of chunk (general, technical, architectural, etc.)
            priority: Priority of the chunk (higher = more important)
            
        Returns:
            The created chunk
        """
        chunk = PlanChunk(
            title=title,
            content=content,
            chunk_type=chunk_type,
            priority=priority
        )
        
        milestone.chunks.append(chunk)
        
        logger.info(f"Added chunk '{title}' to milestone '{milestone.title}'")
        return chunk
    
    def map_task_to_chunks(self, task_id: str, chunk_ids: List[str]):
        """
        Map a task to specific plan chunks.
        
        Args:
            task_id: ID of the task
            chunk_ids: List of chunk IDs to associate with the task
        """
        # Update chunk objects
        for plan_info in self.storage.list_plans():
            plan = self.storage.load_plan(plan_info["id"])
            if plan:
                for chunk in plan.get_all_chunks():
                    if chunk.id in chunk_ids:
                        chunk.task_ids.add(task_id)
                
                # Save updated plan
                self.storage.save_plan(plan)
        
        # Update task-chunk map
        self.task_chunk_map[task_id] = chunk_ids
        self._save_task_chunk_map()
        
        logger.info(f"Mapped task {task_id} to {len(chunk_ids)} chunks")
    
    def get_task_context(self, task_id: str, task_description: str = "") -> Dict[str, Any]:
        """
        Get all relevant context for a task.
        
        Args:
            task_id: ID of the task
            task_description: Optional task description for semantic search
            
        Returns:
            Dictionary containing all relevant context
        """
        context = {
            "task_id": task_id,
            "direct_chunks": [],
            "semantic_chunks": [],
            "plan_context": [],
            "phase_context": [],
            "milestone_context": []
        }
        
        # Get directly mapped chunks
        if task_id in self.task_chunk_map:
            chunk_ids = self.task_chunk_map[task_id]
            for plan_info in self.storage.list_plans():
                plan = self.storage.load_plan(plan_info["id"])
                if plan:
                    for chunk in plan.get_chunks_for_task(task_id):
                        context["direct_chunks"].append({
                            "chunk": chunk.to_dict(),
                            "plan_name": plan.name,
                            "plan_id": plan.id
                        })
        
        # Get semantic context if RAG available
        if self.rag_integration and task_description:
            semantic_results = self.rag_integration.retrieve_context_for_task(
                task_description, task_id
            )
            context["semantic_chunks"] = semantic_results
        
        # Aggregate higher-level context
        seen_plans = set()
        seen_phases = set()
        seen_milestones = set()
        
        for chunk_info in context["direct_chunks"]:
            plan_id = chunk_info["plan_id"]
            if plan_id not in seen_plans:
                plan = self.storage.load_plan(plan_id)
                if plan:
                    context["plan_context"].append({
                        "plan_name": plan.name,
                        "description": plan.description,
                        "objectives": plan.business_objectives,
                        "requirements": plan.technical_requirements,
                        "tech_stack": plan.technology_stack,
                        "patterns": plan.architectural_patterns
                    })
                    seen_plans.add(plan_id)
                    
                    # Find relevant phase and milestone
                    for phase in plan.phases:
                        for milestone in phase.milestones:
                            for chunk in milestone.chunks:
                                if chunk.id in chunk_ids:
                                    if phase.id not in seen_phases:
                                        context["phase_context"].append({
                                            "phase_name": phase.name,
                                            "phase_type": phase.phase_type.value,
                                            "objectives": phase.objectives,
                                            "technologies": phase.technologies,
                                            "decisions": phase.architectural_decisions
                                        })
                                        seen_phases.add(phase.id)
                                    
                                    if milestone.id not in seen_milestones:
                                        context["milestone_context"].append({
                                            "milestone_title": milestone.title,
                                            "deliverables": milestone.deliverables,
                                            "success_criteria": milestone.success_criteria
                                        })
                                        seen_milestones.add(milestone.id)
        
        return context
    
    def save_plan(self, plan: ImplementationPlan) -> bool:
        """
        Save a plan to storage and optionally index in RAG.
        
        Args:
            plan: The plan to save
            
        Returns:
            True if successful, False otherwise
        """
        # Save to storage
        success = self.storage.save_plan(plan)
        
        # Index in RAG if enabled
        if success and self.auto_index and self.rag_integration:
            self.rag_integration.index_plan(plan)
        
        return success
    
    def load_plan(self, plan_id: str) -> Optional[ImplementationPlan]:
        """
        Load a plan from storage.
        
        Args:
            plan_id: ID of the plan to load
            
        Returns:
            The plan or None if not found
        """
        return self.storage.load_plan(plan_id)
    
    def list_plans(self, status: Optional[PlanStatus] = None) -> List[Dict[str, Any]]:
        """
        List all plans, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of plan summaries
        """
        return self.storage.list_plans(status)
    
    def activate_plan(self, plan_id: str) -> bool:
        """
        Activate a plan, making it ready for execution.
        
        Args:
            plan_id: ID of the plan to activate
            
        Returns:
            True if successful, False otherwise
        """
        plan = self.load_plan(plan_id)
        if not plan:
            return False
        
        plan.status = PlanStatus.ACTIVE
        plan.updated_at = datetime.now()
        
        return self.save_plan(plan)
    
    def complete_milestone(self, plan_id: str, milestone_id: str) -> bool:
        """
        Mark a milestone as completed.
        
        Args:
            plan_id: ID of the plan
            milestone_id: ID of the milestone
            
        Returns:
            True if successful, False otherwise
        """
        plan = self.load_plan(plan_id)
        if not plan:
            return False
        
        for phase in plan.phases:
            for milestone in phase.milestones:
                if milestone.id == milestone_id:
                    milestone.status = "completed"
                    plan.updated_at = datetime.now()
                    plan.calculate_metrics()
                    return self.save_plan(plan)
        
        return False
    
    def get_ready_tasks_from_plans(self) -> List[Dict[str, Any]]:
        """
        Get all tasks that are ready to be worked on from active plans.
        
        Returns:
            List of ready tasks with their context
        """
        ready_tasks = []
        
        for plan_info in self.list_plans(PlanStatus.ACTIVE):
            plan = self.load_plan(plan_info["id"])
            if not plan:
                continue
            
            # Find next milestone to work on
            for phase in plan.phases:
                if phase.status == "completed":
                    continue
                
                # Check phase dependencies
                dependencies_met = True
                for dep_phase_id in phase.depends_on_phases:
                    dep_phase = next((p for p in plan.phases if p.id == dep_phase_id), None)
                    if dep_phase and dep_phase.status != "completed":
                        dependencies_met = False
                        break
                
                if not dependencies_met:
                    continue
                
                # Find ready milestones in this phase
                for milestone in phase.milestones:
                    if milestone.status != "pending":
                        continue
                    
                    # Check milestone dependencies
                    milestone_deps_met = True
                    for dep_milestone_id in milestone.depends_on_milestones:
                        dep_milestone = next(
                            (m for p in plan.phases for m in p.milestones if m.id == dep_milestone_id),
                            None
                        )
                        if dep_milestone and dep_milestone.status != "completed":
                            milestone_deps_met = False
                            break
                    
                    if milestone_deps_met:
                        # This milestone is ready
                        ready_tasks.append({
                            "plan_id": plan.id,
                            "plan_name": plan.name,
                            "phase_id": phase.id,
                            "phase_name": phase.name,
                            "milestone_id": milestone.id,
                            "milestone_title": milestone.title,
                            "milestone_description": milestone.description,
                            "deliverables": milestone.deliverables,
                            "success_criteria": milestone.success_criteria,
                            "chunks": [chunk.to_dict() for chunk in milestone.chunks],
                            "priority": max([chunk.priority for chunk in milestone.chunks] + [0])
                        })
        
        # Sort by priority
        ready_tasks.sort(key=lambda t: t["priority"], reverse=True)
        
        return ready_tasks
    
    def create_plan_from_template(self, template_name: str, customizations: Dict[str, Any]) -> Optional[ImplementationPlan]:
        """
        Create a new plan from a template.
        
        Args:
            template_name: Name of the template to use
            customizations: Dictionary of customizations to apply
            
        Returns:
            The created plan or None if template not found
        """
        plan = self.storage.load_template(template_name)
        if not plan:
            return None
        
        # Apply customizations
        if "name" in customizations:
            plan.name = customizations["name"]
        if "description" in customizations:
            plan.description = customizations["description"]
        if "business_objectives" in customizations:
            plan.business_objectives = customizations["business_objectives"]
        if "technical_requirements" in customizations:
            plan.technical_requirements = customizations["technical_requirements"]
        if "technology_stack" in customizations:
            plan.technology_stack = customizations["technology_stack"]
        
        # Save the new plan
        self.save_plan(plan)
        
        return plan
    
    def get_plan_metrics(self) -> Dict[str, Any]:
        """Get overall metrics for all plans."""
        metrics = {
            "total_plans": 0,
            "active_plans": 0,
            "completed_plans": 0,
            "total_milestones": 0,
            "completed_milestones": 0,
            "average_completion": 0.0,
            "plans_by_type": {},
            "plans_by_scope": {}
        }
        
        plans = self.list_plans()
        metrics["total_plans"] = len(plans)
        
        completion_percentages = []
        
        for plan_info in plans:
            plan = self.load_plan(plan_info["id"])
            if not plan:
                continue
            
            # Status counts
            if plan.status == PlanStatus.ACTIVE:
                metrics["active_plans"] += 1
            elif plan.status == PlanStatus.COMPLETED:
                metrics["completed_plans"] += 1
            
            # Type and scope counts
            if plan.project_type not in metrics["plans_by_type"]:
                metrics["plans_by_type"][plan.project_type] = 0
            metrics["plans_by_type"][plan.project_type] += 1
            
            if plan.scope not in metrics["plans_by_scope"]:
                metrics["plans_by_scope"][plan.scope] = 0
            metrics["plans_by_scope"][plan.scope] += 1
            
            # Milestone counts
            for phase in plan.phases:
                for milestone in phase.milestones:
                    metrics["total_milestones"] += 1
                    if milestone.status == "completed":
                        metrics["completed_milestones"] += 1
            
            # Completion percentage
            plan.calculate_metrics()
            completion_percentages.append(plan.completion_percentage)
        
        # Average completion
        if completion_percentages:
            metrics["average_completion"] = sum(completion_percentages) / len(completion_percentages)
        
        return metrics