"""
Request Planner implementation.

This module contains the core logic for the Request Planner agent, which
understands user requests, creates implementation plans, and orchestrates
task execution.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import logging

from .models import (
    ChangeRequest, Plan, Step, StepKind, ComplexityLevel,
    Task, TaskStatus, SearchResult
)
from .context import ContextRetriever
from .parser import RequestParser
from .llm import LLMClient
from .git_adapter import GitAdapter

logger = logging.getLogger(__name__)


class RequestPlanner:
    """
    The main Request Planner agent that interfaces with users and
    orchestrates the agent system.
    """
    
    def __init__(self, repo_path: str = ".", use_llm: bool = True):
        """Initialize the Request Planner."""
        self.repo_path = Path(repo_path).resolve()
        self.context_retriever = ContextRetriever(self.repo_path)
        self.request_parser = RequestParser()
        self.active_tasks: List[Task] = []
        self.use_llm = use_llm
        
        # Initialize Git adapter
        self.git_adapter = GitAdapter(self.repo_path)
        
        # Initialize LLM client if enabled
        if self.use_llm:
            try:
                self.llm_client = LLMClient()
                logger.info("LLM client initialized successfully")
            except ValueError as e:
                logger.warning(f"LLM initialization failed: {e}")
                logger.warning("Falling back to heuristic planning")
                self.use_llm = False
                self.llm_client = None
        else:
            self.llm_client = None
    
    def load_repository(self, repo_url: Optional[str] = None, branch: str = "main") -> bool:
        """
        Load a repository from URL or use existing path.
        
        Args:
            repo_url: Git repository URL (optional)
            branch: Branch to checkout
            
        Returns:
            Success status
        """
        if repo_url:
            # Clone the repository
            success, repo_path = self.git_adapter.clone_repository(repo_url, branch)
            if success and repo_path:
                self.repo_path = repo_path
                # Reinitialize context retriever with new path
                self.context_retriever = ContextRetriever(self.repo_path)
                logger.info(f"Repository loaded from {repo_url}")
                return True
            else:
                logger.error(f"Failed to clone repository from {repo_url}")
                return False
        else:
            # Check if current path is a Git repository
            repo_info = self.git_adapter.get_repo_info()
            if repo_info["is_git_repo"]:
                logger.info(f"Using existing Git repository at {self.repo_path}")
                return True
            else:
                logger.warning(f"Path {self.repo_path} is not a Git repository")
                return True  # Still allow non-Git directories
        
    def get_repository_info(self) -> Dict[str, Any]:
        """Get information about the current repository."""
        info = self.git_adapter.get_repo_info()
        
        # Add additional context
        info["files_count"] = len(self.git_adapter.list_files())
        info["python_files"] = len(self.git_adapter.list_files("*.py"))
        
        return info
        
    def create_plan(self, request: ChangeRequest) -> Plan:
        """
        Create an implementation plan from a change request.
        
        Args:
            request: The change request to process
            
        Returns:
            A plan with steps to implement the request
        """
        # Parse the request to understand intent
        intent = self.request_parser.parse(request.description)
        
        # Retrieve relevant context
        context = self.context_retriever.get_context(
            query=request.description,
            intent=intent
        )
        
        # Use LLM if available, otherwise fall back to heuristics
        if self.use_llm and self.llm_client:
            try:
                logger.info("Creating plan with LLM")
                plan = self.llm_client.create_plan(request, context)
                return plan
            except Exception as e:
                logger.error(f"LLM planning failed: {e}")
                logger.info("Falling back to heuristic planning")
        
        # Heuristic-based planning (fallback)
        logger.info("Creating plan with heuristics")
        
        # Generate steps based on intent and context
        steps = self._generate_steps(intent, context)
        
        # Identify affected files
        affected_paths = self._identify_affected_paths(steps, context)
        
        # Estimate complexity
        complexity = self._estimate_complexity(steps, affected_paths)
        
        # Create the plan
        plan = Plan(
            id=str(uuid.uuid4()),
            parent_request_id=request.id,
            steps=steps,
            rationale=self._generate_rationale(intent, steps),
            affected_paths=affected_paths,
            complexity_label=complexity,
            estimated_tokens=self._estimate_tokens(steps, complexity)
        )
        
        return plan
    
    def search_codebase(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the codebase for relevant information.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        results = self.context_retriever.search(query, limit=limit)
        
        # Convert to dictionary format for CLI
        return [
            {
                "file": str(r.file),
                "line": r.line,
                "content": r.content,
                "score": r.score
            }
            for r in results
        ]
    
    def analyze_code(self, query: str) -> str:
        """
        Analyze code and answer questions using LLM.
        
        Args:
            query: Question about the code
            
        Returns:
            Analysis response
        """
        if not self.use_llm or not self.llm_client:
            return "Code analysis requires LLM integration. Please set OPENAI_API_KEY."
        
        # Search for relevant code
        search_results = self.context_retriever.search(query, limit=20)
        
        # Convert to snippets format
        code_snippets = [
            {
                "file": str(r.file),
                "line": r.line,
                "content": r.content
            }
            for r in search_results
        ]
        
        try:
            analysis = self.llm_client.analyze_code(query, code_snippets)
            return analysis
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return f"Error analyzing code: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent system.
        
        Returns:
            Status information including active tasks
        """
        return {
            "system_status": "operational",
            "active_tasks": [task.to_dict() for task in self.active_tasks],
            "repo_path": str(self.repo_path),
            "timestamp": datetime.now().isoformat()
        }
    
    def execute_plan(self, plan: Plan) -> List[Task]:
        """
        Execute a plan by creating and scheduling tasks.
        
        Args:
            plan: The plan to execute
            
        Returns:
            List of created tasks
        """
        tasks = []
        
        for step in plan.steps:
            task = Task(
                id=str(uuid.uuid4()),
                description=step.goal,
                status=TaskStatus.PENDING,
                plan_id=plan.id,
                step_number=step.order
            )
            tasks.append(task)
            self.active_tasks.append(task)
        
        # TODO: Actually execute the tasks
        # For now, just return the created tasks
        return tasks
    
    def _generate_steps(self, intent: Dict[str, Any], context: Dict[str, Any]) -> List[Step]:
        """Generate implementation steps based on intent and context."""
        steps = []
        
        # Simple heuristic-based step generation
        # TODO: Replace with LLM-based generation
        
        if intent["type"] == "add_feature":
            steps.extend([
                Step(
                    order=1,
                    goal=f"Implement {intent['feature']} functionality",
                    kind=StepKind.ADD,
                    hints=["Create new module or extend existing one"]
                ),
                Step(
                    order=2,
                    goal=f"Add tests for {intent['feature']}",
                    kind=StepKind.TEST,
                    hints=["Cover success and error cases"]
                ),
                Step(
                    order=3,
                    goal="Update documentation",
                    kind=StepKind.EDIT,
                    hints=["Add usage examples"]
                )
            ])
        elif intent["type"] == "fix_bug":
            steps.extend([
                Step(
                    order=1,
                    goal="Identify and fix the bug",
                    kind=StepKind.EDIT,
                    hints=["Check error handling", "Validate inputs"]
                ),
                Step(
                    order=2,
                    goal="Add regression test",
                    kind=StepKind.TEST,
                    hints=["Ensure bug doesn't reoccur"]
                )
            ])
        elif intent["type"] == "refactor":
            steps.extend([
                Step(
                    order=1,
                    goal=f"Refactor {intent.get('target', 'code')}",
                    kind=StepKind.REFACTOR,
                    hints=["Improve structure", "Maintain functionality"]
                ),
                Step(
                    order=2,
                    goal="Ensure tests still pass",
                    kind=StepKind.TEST,
                    hints=["Run existing test suite"]
                )
            ])
        else:
            # Generic steps for unknown intent
            steps.append(
                Step(
                    order=1,
                    goal="Implement requested changes",
                    kind=StepKind.EDIT,
                    hints=["Follow best practices"]
                )
            )
        
        return steps
    
    def _identify_affected_paths(self, steps: List[Step], context: Dict[str, Any]) -> List[str]:
        """Identify files that will be affected by the plan."""
        affected = set()
        
        # Add files from context
        if "relevant_files" in context:
            affected.update(context["relevant_files"])
        
        # Add common patterns based on step types
        for step in steps:
            if step.kind == StepKind.TEST:
                affected.add("tests/")
            elif step.kind == StepKind.ADD:
                affected.add("src/")
        
        return sorted(list(affected))
    
    def _estimate_complexity(self, steps: List[Step], affected_paths: List[str]) -> ComplexityLevel:
        """Estimate the complexity of the plan."""
        # Simple heuristic based on number of steps and files
        if len(steps) <= 2 and len(affected_paths) <= 2:
            return ComplexityLevel.TRIVIAL
        elif len(steps) <= 4 and len(affected_paths) <= 5:
            return ComplexityLevel.MODERATE
        else:
            return ComplexityLevel.COMPLEX
    
    def _generate_rationale(self, intent: Dict[str, Any], steps: List[Step]) -> List[str]:
        """Generate rationale for the plan."""
        rationale = []
        
        if intent["type"] == "add_feature":
            rationale.append(f"Adding new feature: {intent.get('feature', 'requested functionality')}")
            rationale.append("Including tests to ensure reliability")
        elif intent["type"] == "fix_bug":
            rationale.append("Fixing identified bug to improve stability")
            rationale.append("Adding regression test to prevent reoccurrence")
        elif intent["type"] == "refactor":
            rationale.append("Refactoring to improve code quality and maintainability")
        
        if len(steps) > 3:
            rationale.append("Breaking down into multiple steps for clarity")
        
        return rationale
    
    def _estimate_tokens(self, steps: List[Step], complexity: ComplexityLevel) -> int:
        """Estimate token usage for the plan."""
        base_tokens = {
            ComplexityLevel.TRIVIAL: 1000,
            ComplexityLevel.MODERATE: 3000,
            ComplexityLevel.COMPLEX: 5000
        }
        
        # Add tokens per step
        step_tokens = len(steps) * 500
        
        return base_tokens[complexity] + step_tokens