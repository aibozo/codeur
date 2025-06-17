"""
API for execution agents to retrieve plan context.

This module provides a clean interface for agents to access implementation
plan context during task execution.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from .plan_manager import PlanManager
from .plan_models import PlanChunk, PlanStatus
from ..core.logging import get_logger

logger = get_logger(__name__)


class PlanAPI:
    """
    Clean API interface for accessing plan context.
    
    This API is designed to be used by execution agents to retrieve
    relevant context for their tasks without needing to understand
    the full plan structure.
    """
    
    def __init__(self, plan_manager: PlanManager):
        """
        Initialize the plan API.
        
        Args:
            plan_manager: Plan manager instance
        """
        self.plan_manager = plan_manager
    
    def get_task_context(self, task_id: str, task_description: str = "") -> Dict[str, Any]:
        """
        Get comprehensive context for a task.
        
        This is the primary method execution agents should use to get
        all relevant context for their task.
        
        Args:
            task_id: ID of the task being executed
            task_description: Optional task description for enhanced search
            
        Returns:
            Dictionary containing:
            - implementation_guide: Step-by-step implementation guidance
            - technical_context: Technical details and constraints
            - relevant_files: Files to examine or modify
            - test_requirements: Testing requirements
            - acceptance_criteria: Success criteria
            - examples: Code examples if available
            - dependencies: Dependencies to be aware of
        """
        # Get raw context from plan manager
        raw_context = self.plan_manager.get_task_context(task_id, task_description)
        
        # Transform into agent-friendly format
        context = {
            "task_id": task_id,
            "implementation_guide": self._extract_implementation_guide(raw_context),
            "technical_context": self._extract_technical_context(raw_context),
            "relevant_files": self._extract_relevant_files(raw_context),
            "test_requirements": self._extract_test_requirements(raw_context),
            "acceptance_criteria": self._extract_acceptance_criteria(raw_context),
            "examples": self._extract_examples(raw_context),
            "dependencies": self._extract_dependencies(raw_context),
            "constraints": self._extract_constraints(raw_context),
            "technologies": self._extract_technologies(raw_context)
        }
        
        logger.info(f"Retrieved context for task {task_id}")
        return context
    
    def _extract_implementation_guide(self, raw_context: Dict[str, Any]) -> str:
        """Extract step-by-step implementation guidance."""
        guide_parts = []
        
        # Add high-level objectives
        if raw_context.get("plan_context"):
            plan = raw_context["plan_context"][0]
            guide_parts.append("## Project Overview")
            guide_parts.append(f"**Description**: {plan['description']}")
            guide_parts.append("\n**Business Objectives**:")
            for obj in plan.get("objectives", []):
                guide_parts.append(f"- {obj}")
        
        # Add phase-specific guidance
        if raw_context.get("phase_context"):
            phase = raw_context["phase_context"][0]
            guide_parts.append(f"\n## Current Phase: {phase['phase_name']}")
            guide_parts.append("**Phase Objectives**:")
            for obj in phase.get("objectives", []):
                guide_parts.append(f"- {obj}")
        
        # Add milestone deliverables
        if raw_context.get("milestone_context"):
            milestone = raw_context["milestone_context"][0]
            guide_parts.append(f"\n## Current Milestone: {milestone['milestone_title']}")
            guide_parts.append("**Deliverables**:")
            for deliverable in milestone.get("deliverables", []):
                guide_parts.append(f"- {deliverable}")
        
        # Add implementation chunks
        guide_parts.append("\n## Implementation Steps")
        
        # Direct chunks have highest priority
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            if chunk.get("chunk_type") in ["implementation", "general"]:
                guide_parts.append(f"\n### {chunk['title']}")
                guide_parts.append(chunk["content"])
        
        # Add semantic chunks if relevant
        for result in raw_context.get("semantic_chunks", [])[:2]:
            if result.get("match_type") == "semantic" and result.get("relevance_score", 0) > 0.7:
                content = result.get("content", "")
                if "implement" in content.lower() or "steps" in content.lower():
                    guide_parts.append(f"\n### Related Context")
                    guide_parts.append(content)
        
        return "\n".join(guide_parts)
    
    def _extract_technical_context(self, raw_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technical details and decisions."""
        tech_context = {
            "architectural_patterns": [],
            "architectural_decisions": [],
            "key_decisions": [],
            "risk_factors": []
        }
        
        # From plan level
        if raw_context.get("plan_context"):
            plan = raw_context["plan_context"][0]
            tech_context["architectural_patterns"] = plan.get("patterns", [])
        
        # From phase level
        if raw_context.get("phase_context"):
            phase = raw_context["phase_context"][0]
            tech_context["architectural_decisions"] = phase.get("decisions", [])
        
        # From chunks
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            if chunk.get("chunk_type") in ["technical", "architectural"]:
                # Extract patterns mentioned in content
                content = chunk.get("content", "")
                if "pattern" in content.lower():
                    tech_context["key_decisions"].append(chunk.get("title", "Technical Decision"))
        
        return tech_context
    
    def _extract_relevant_files(self, raw_context: Dict[str, Any]) -> List[str]:
        """Extract list of relevant files."""
        files = set()
        
        # From direct chunks
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            for file in chunk.get("relevant_files", []):
                files.add(file)
        
        # From semantic results
        for result in raw_context.get("semantic_chunks", []):
            metadata = result.get("metadata", {})
            for file in metadata.get("relevant_files", []):
                files.add(file)
        
        return sorted(list(files))
    
    def _extract_test_requirements(self, raw_context: Dict[str, Any]) -> List[str]:
        """Extract testing requirements."""
        requirements = []
        seen = set()
        
        # From direct chunks
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            for req in chunk.get("test_requirements", []):
                if req not in seen:
                    requirements.append(req)
                    seen.add(req)
        
        # From chunks with testing type
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            if chunk.get("chunk_type") == "testing":
                # Extract requirements from content
                content = chunk.get("content", "")
                if "test" in content.lower():
                    lines = content.split("\n")
                    for line in lines:
                        if line.strip().startswith("-") and "test" in line.lower():
                            req = line.strip()[1:].strip()
                            if req not in seen:
                                requirements.append(req)
                                seen.add(req)
        
        return requirements
    
    def _extract_acceptance_criteria(self, raw_context: Dict[str, Any]) -> List[str]:
        """Extract acceptance criteria."""
        criteria = []
        seen = set()
        
        # From milestone context
        if raw_context.get("milestone_context"):
            milestone = raw_context["milestone_context"][0]
            for criterion in milestone.get("success_criteria", []):
                if criterion not in seen:
                    criteria.append(criterion)
                    seen.add(criterion)
        
        # From direct chunks
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            for criterion in chunk.get("acceptance_criteria", []):
                if criterion not in seen:
                    criteria.append(criterion)
                    seen.add(criterion)
        
        return criteria
    
    def _extract_examples(self, raw_context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract code examples."""
        examples = []
        
        # From direct chunks
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            for example in chunk.get("examples", []):
                examples.append(example)
        
        return examples
    
    def _extract_dependencies(self, raw_context: Dict[str, Any]) -> List[str]:
        """Extract dependencies."""
        deps = set()
        
        # From direct chunks
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            for dep in chunk.get("dependencies", []):
                deps.add(dep)
        
        return sorted(list(deps))
    
    def _extract_constraints(self, raw_context: Dict[str, Any]) -> List[str]:
        """Extract constraints."""
        constraints = []
        seen = set()
        
        # From plan level
        if raw_context.get("plan_context"):
            plan = raw_context["plan_context"][0]
            for constraint in plan.get("constraints", []):
                if constraint not in seen:
                    constraints.append(constraint)
                    seen.add(constraint)
        
        # From direct chunks
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            for constraint in chunk.get("constraints", []):
                if constraint not in seen:
                    constraints.append(constraint)
                    seen.add(constraint)
        
        return constraints
    
    def _extract_technologies(self, raw_context: Dict[str, Any]) -> List[str]:
        """Extract technology stack."""
        techs = set()
        
        # From plan level
        if raw_context.get("plan_context"):
            plan = raw_context["plan_context"][0]
            for tech in plan.get("tech_stack", []):
                techs.add(tech)
        
        # From phase level
        if raw_context.get("phase_context"):
            phase = raw_context["phase_context"][0]
            for tech in phase.get("technologies", []):
                techs.add(tech)
        
        # From chunks
        for chunk_info in raw_context.get("direct_chunks", []):
            chunk = chunk_info["chunk"]
            for tech in chunk.get("technologies", []):
                techs.add(tech)
        
        return sorted(list(techs))
    
    def get_similar_implementations(self, description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar implementations from past plans.
        
        Args:
            description: What to search for
            limit: Maximum results
            
        Returns:
            List of similar implementations with context
        """
        if self.plan_manager.rag_integration:
            return self.plan_manager.rag_integration.retrieve_similar_implementations(
                description, limit=limit
            )
        return []
    
    def get_technology_examples(self, technologies: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get examples using specific technologies.
        
        Args:
            technologies: List of technology names
            limit: Maximum results
            
        Returns:
            List of relevant examples
        """
        if self.plan_manager.rag_integration:
            return self.plan_manager.rag_integration.retrieve_context_by_technology(
                technologies, limit=limit
            )
        return []
    
    def report_task_progress(self, task_id: str, status: str, notes: str = ""):
        """
        Report progress on a task.
        
        Args:
            task_id: ID of the task
            status: Status (started, in_progress, completed, failed)
            notes: Optional notes about progress
        """
        logger.info(f"Task {task_id} progress: {status}")
        
        # TODO: Update milestone status based on task completion
        # This would require tracking task->milestone mapping
    
    def get_next_tasks(self) -> List[Dict[str, Any]]:
        """
        Get the next tasks that are ready to work on.
        
        Returns:
            List of ready tasks with basic info
        """
        ready_tasks = self.plan_manager.get_ready_tasks_from_plans()
        
        # Simplify for agents
        simplified_tasks = []
        for task in ready_tasks:
            simplified_tasks.append({
                "milestone_title": task["milestone_title"],
                "milestone_description": task["milestone_description"],
                "phase_name": task["phase_name"],
                "priority": task["priority"],
                "deliverables": task["deliverables"]
            })
        
        return simplified_tasks
    
    def search_plans(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for plans by query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching plans
        """
        return self.plan_manager.storage.search_plans(query)


# Agent-specific convenience functions

def get_context_for_agent(task_id: str, 
                         task_description: str = "",
                         plan_api: Optional[PlanAPI] = None) -> Dict[str, Any]:
    """
    Convenience function for agents to get task context.
    
    This can be called from within agent code to retrieve
    implementation context.
    
    Args:
        task_id: ID of the current task
        task_description: Optional task description
        plan_api: Plan API instance (will create if not provided)
        
    Returns:
        Task context dictionary
    """
    if not plan_api:
        # Try to create from default location
        try:
            from .plan_manager import PlanManager
            plan_manager = PlanManager()
            plan_api = PlanAPI(plan_manager)
        except Exception as e:
            logger.error(f"Failed to create plan API: {e}")
            return {}
    
    return plan_api.get_task_context(task_id, task_description)


def format_implementation_guide(context: Dict[str, Any]) -> str:
    """
    Format context into a readable implementation guide.
    
    Args:
        context: Context dictionary from get_task_context
        
    Returns:
        Formatted implementation guide as markdown
    """
    parts = []
    
    # Add implementation guide
    if context.get("implementation_guide"):
        parts.append(context["implementation_guide"])
    
    # Add technical context
    if context.get("technical_context"):
        tech = context["technical_context"]
        if tech.get("architectural_patterns"):
            parts.append("\n## Architectural Patterns")
            for pattern in tech["architectural_patterns"]:
                parts.append(f"- {pattern}")
    
    # Add relevant files
    if context.get("relevant_files"):
        parts.append("\n## Relevant Files")
        for file in context["relevant_files"]:
            parts.append(f"- {file}")
    
    # Add test requirements
    if context.get("test_requirements"):
        parts.append("\n## Test Requirements")
        for req in context["test_requirements"]:
            parts.append(f"- {req}")
    
    # Add acceptance criteria
    if context.get("acceptance_criteria"):
        parts.append("\n## Acceptance Criteria")
        for criteria in context["acceptance_criteria"]:
            parts.append(f"- {criteria}")
    
    return "\n".join(parts)