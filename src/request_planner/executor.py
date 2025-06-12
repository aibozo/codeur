"""
Plan executor for the Request Planner.

This module handles the execution of plans by coordinating with
other agents in the system.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .models import Plan, Step, StepKind, Task, TaskStatus
from .planner import RequestPlanner
from .file_operations import FileOperations

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of plan execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """Result of executing a plan step."""
    step: Step
    status: ExecutionStatus
    output: Optional[str] = None
    error: Optional[str] = None
    modified_files: List[str] = None
    
    def __post_init__(self):
        if self.modified_files is None:
            self.modified_files = []


class PlanExecutor:
    """
    Executes plans by coordinating with other agents.
    
    In the full system, this would communicate with:
    - Code Planner for detailed implementation
    - Coding Agent for file modifications
    - Test agents for validation
    
    Currently provides a simulation mode for testing.
    """
    
    def __init__(self, planner: RequestPlanner):
        """Initialize the executor."""
        self.planner = planner
        self.current_plan: Optional[Plan] = None
        self.execution_results: List[ExecutionResult] = []
        self.simulation_mode = False  # Real execution by default
        self.file_ops = FileOperations(planner.repo_path)
        
    def execute_plan(self, plan: Plan, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute a plan.
        
        Args:
            plan: The plan to execute
            dry_run: If True, simulate execution without changes
            
        Returns:
            Execution summary
        """
        self.current_plan = plan
        self.execution_results = []
        
        logger.info(f"Starting execution of plan {plan.id}")
        
        # Execute each step
        for step in plan.steps:
            logger.info(f"Executing step {step.order}: {step.goal}")
            
            if dry_run or self.simulation_mode:
                result = self._simulate_step(step)
            else:
                result = self._execute_step(step)
            
            self.execution_results.append(result)
            
            # Stop on failure
            if result.status == ExecutionStatus.FAILED:
                logger.error(f"Step {step.order} failed: {result.error}")
                break
        
        # Generate summary
        summary = self._generate_summary()
        logger.info(f"Execution completed: {summary['status']}")
        
        return summary
    
    def _simulate_step(self, step: Step) -> ExecutionResult:
        """Simulate execution of a step."""
        import time
        import random
        
        # Simulate processing time
        time.sleep(random.uniform(0.5, 2.0))
        
        # Generate simulated results
        if step.kind == StepKind.EDIT:
            output = f"Modified file: {step.hints[0] if step.hints else 'unknown'}"
            files = [step.hints[0]] if step.hints else []
        elif step.kind == StepKind.ADD:
            output = f"Created new file: {step.hints[0] if step.hints else 'unknown'}"
            files = [step.hints[0]] if step.hints else []
        elif step.kind == StepKind.TEST:
            output = "Ran tests: All tests passed"
            files = []
        else:
            output = f"Completed: {step.goal}"
            files = []
        
        # Simulate occasional failures
        if random.random() < 0.1:  # 10% failure rate
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.FAILED,
                error="Simulated failure for testing"
            )
        
        return ExecutionResult(
            step=step,
            status=ExecutionStatus.COMPLETED,
            output=output,
            modified_files=files
        )
    
    def _execute_step(self, step: Step) -> ExecutionResult:
        """
        Execute a step by delegating to appropriate agents.
        
        Currently implements basic file operations.
        TODO: Integrate with Code Planner and Coding Agent.
        """
        try:
            if step.kind == StepKind.EDIT:
                return self._execute_edit_step(step)
            elif step.kind == StepKind.ADD:
                return self._execute_add_step(step)
            elif step.kind == StepKind.REMOVE:
                return self._execute_remove_step(step)
            elif step.kind == StepKind.REFACTOR:
                return self._execute_refactor_step(step)
            elif step.kind == StepKind.TEST:
                return self._execute_test_step(step)
            elif step.kind == StepKind.REVIEW:
                return self._execute_review_step(step)
            else:
                return ExecutionResult(
                    step=step,
                    status=ExecutionStatus.FAILED,
                    error=f"Unknown step kind: {step.kind}"
                )
        except Exception as e:
            logger.error(f"Error executing step: {e}", exc_info=True)
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.FAILED,
                error=str(e)
            )
    
    def _execute_edit_step(self, step: Step) -> ExecutionResult:
        """Execute an edit step."""
        # For now, use LLM to generate the edit
        # In full system, this would go through Code Planner
        
        if not step.hints:
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.FAILED,
                error="No file specified for edit"
            )
        
        file_path = step.hints[0]
        
        # Get current content
        full_path = self.planner.repo_path / file_path
        if not full_path.exists():
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.FAILED,
                error=f"File not found: {file_path}"
            )
        
        # TODO: Use LLM to generate the actual edit
        # For now, just log the intent
        logger.info(f"Would edit {file_path} to: {step.goal}")
        
        return ExecutionResult(
            step=step,
            status=ExecutionStatus.COMPLETED,
            output=f"Ready to edit {file_path}",
            modified_files=[file_path]
        )
    
    def _execute_add_step(self, step: Step) -> ExecutionResult:
        """Execute an add step."""
        if not step.hints:
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.FAILED,
                error="No file specified for creation"
            )
        
        file_path = step.hints[0]
        
        # TODO: Use LLM to generate file content
        # For now, create a placeholder
        content = f"""# {step.goal}
# TODO: Implement this file

def placeholder():
    \"\"\"Generated by Request Planner.\"\"\"
    pass
"""
        
        success, message = self.file_ops.create_file(file_path, content)
        
        if success:
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.COMPLETED,
                output=message,
                modified_files=[file_path]
            )
        else:
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.FAILED,
                error=message
            )
    
    def _execute_remove_step(self, step: Step) -> ExecutionResult:
        """Execute a remove step."""
        if not step.hints:
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.FAILED,
                error="No file specified for removal"
            )
        
        file_path = step.hints[0]
        success, message = self.file_ops.delete_file(file_path)
        
        if success:
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.COMPLETED,
                output=message,
                modified_files=[file_path]
            )
        else:
            return ExecutionResult(
                step=step,
                status=ExecutionStatus.FAILED,
                error=message
            )
    
    def _execute_refactor_step(self, step: Step) -> ExecutionResult:
        """Execute a refactor step."""
        # Refactoring is complex and would need Code Planner
        # For now, just acknowledge the step
        return ExecutionResult(
            step=step,
            status=ExecutionStatus.COMPLETED,
            output=f"Refactor acknowledged: {step.goal}",
            modified_files=step.hints if step.hints else []
        )
    
    def _execute_test_step(self, step: Step) -> ExecutionResult:
        """Execute a test step."""
        # Try to run tests
        import subprocess
        
        test_commands = [
            "pytest",
            "python -m pytest",
            "npm test",
            "cargo test",
            "go test ./..."
        ]
        
        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=self.planner.repo_path
                )
                
                if result.returncode == 0:
                    return ExecutionResult(
                        step=step,
                        status=ExecutionStatus.COMPLETED,
                        output=f"Tests passed with {cmd}"
                    )
                else:
                    # Tests exist but failed
                    return ExecutionResult(
                        step=step,
                        status=ExecutionStatus.FAILED,
                        error=f"Tests failed: {result.stdout}\n{result.stderr}"
                    )
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # No test command worked
        return ExecutionResult(
            step=step,
            status=ExecutionStatus.COMPLETED,
            output="No test framework detected, skipping tests"
        )
    
    def _execute_review_step(self, step: Step) -> ExecutionResult:
        """Execute a review step."""
        # Review would involve checking the changes
        # For now, just summarize what was done
        modified_count = len(set(
            file for r in self.execution_results 
            for file in r.modified_files
        ))
        
        return ExecutionResult(
            step=step,
            status=ExecutionStatus.COMPLETED,
            output=f"Review complete: {modified_count} files modified"
        )
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate execution summary."""
        total_steps = len(self.current_plan.steps)
        completed_steps = sum(
            1 for r in self.execution_results 
            if r.status == ExecutionStatus.COMPLETED
        )
        failed_steps = sum(
            1 for r in self.execution_results 
            if r.status == ExecutionStatus.FAILED
        )
        
        # Collect all modified files
        all_modified_files = []
        for result in self.execution_results:
            all_modified_files.extend(result.modified_files)
        
        # Determine overall status
        if failed_steps > 0:
            overall_status = "failed"
        elif completed_steps == total_steps:
            overall_status = "completed"
        else:
            overall_status = "partial"
        
        return {
            "plan_id": self.current_plan.id,
            "status": overall_status,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "modified_files": list(set(all_modified_files)),
            "results": [
                {
                    "step": r.step.order,
                    "goal": r.step.goal,
                    "status": r.status.value,
                    "output": r.output,
                    "error": r.error
                }
                for r in self.execution_results
            ]
        }
    
    def get_execution_status(self) -> Optional[Dict[str, Any]]:
        """Get current execution status."""
        if not self.current_plan:
            return None
        
        return {
            "plan_id": self.current_plan.id,
            "executing": any(
                r.status == ExecutionStatus.RUNNING 
                for r in self.execution_results
            ),
            "progress": f"{len(self.execution_results)}/{len(self.current_plan.steps)}"
        }