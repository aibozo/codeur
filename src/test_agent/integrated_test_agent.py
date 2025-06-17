"""
Integrated Test Agent with task graph and event system integration.
"""

import logging
from typing import Dict, Any, Optional, Set, List
from pathlib import Path

from ..core.integrated_agent_base import (
    IntegratedAgentBase, AgentContext, IntegrationLevel, AgentCapability
)
from .test_agent import TestAgent
from .test_executor import TestExecutor
from .models import TestStrategy, TestReport
from ..core.logging import get_logger

logger = get_logger(__name__)


class IntegratedTestAgent(IntegratedAgentBase):
    """
    Test Agent with full integration into the agent system.
    
    Coordinates test generation and execution through:
    - TestAgent for test planning and generation
    - TestExecutor for running and analyzing tests
    """
    
    def __init__(self, context: AgentContext):
        """Initialize integrated test agent."""
        super().__init__(context)
        
        # Create LLM client for test agent
        from src.llm import LLMClient
        llm_client = LLMClient(agent_name="test_agent")
        
        # Initialize test components
        self.test_agent = TestAgent(
            project_path=str(context.project_path),
            llm_client=llm_client,
            rag_client=context.rag_client
        )
        
        self.test_executor = TestExecutor(
            project_path=str(context.project_path)
        )
        
        # Track test execution state
        self.current_task_id: Optional[str] = None
        self.test_history: Dict[str, TestReport] = {}
        
        logger.info("Integrated TestAgent initialized")
        
    def get_integration_level(self) -> IntegrationLevel:
        """Test agent needs full integration."""
        return IntegrationLevel.FULL
        
    def get_capabilities(self) -> Set[AgentCapability]:
        """Test agent capabilities."""
        return {
            AgentCapability.TESTING,
            AgentCapability.ANALYSIS
        }
        
    async def on_task_assigned(self, task_id: str):
        """Handle test task assignment."""
        logger.info(f"TestAgent assigned task: {task_id}")
        
        # Get task details
        task = await self._task_integration.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
            
        self.current_task_id = task_id
        
        # Update task status
        await self.update_task_progress(task_id, 0.1, "Starting test generation")
        
        try:
            # Execute the test task
            result = await self.execute_test_task(task)
            
            # Mark task as completed
            await self.complete_task(task_id, result)
            
        except Exception as e:
            logger.error(f"Failed to execute test task {task_id}: {e}", exc_info=True)
            await self.fail_task(task_id, str(e))
            
    async def execute_test_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a test task including generation, execution, and adaptation.
        
        Args:
            task: Task details including target functions and context
            
        Returns:
            Test execution results
        """
        title = task.get("title", "")
        description = task.get("description", "")
        
        logger.info(f"Executing test task: {title}")
        
        # Get context from related coding task if available
        task_metadata = task.get("metadata", {})
        related_coding_task_id = task_metadata.get("related_coding_task_id")
        
        if related_coding_task_id and self._task_integration:
            # Fetch the coding task to get implementation context
            coding_task = await self._task_integration.get_task(related_coding_task_id)
            if coding_task and "metadata" in coding_task:
                impl_context = coding_task.get("metadata", {}).get("implementation_context", {})
                
                # Merge implementation context into task metadata
                if impl_context:
                    logger.info(f"Found implementation context from coding task: {impl_context}")
                    task_metadata.update(impl_context)
                    
                    # Update target files if we have better info from coding task
                    if impl_context.get("modified_files"):
                        task_metadata["target_files"] = impl_context["modified_files"]
        
        # Parse task to extract test targets
        test_targets = self._parse_test_targets(task)
        
        if not test_targets:
            logger.error("No test targets found in task")
            return {"status": "failed", "error": "No test targets specified"}
            
        # Phase 1: Generate tests
        await self.update_task_progress(
            self.current_task_id,
            0.2,
            "Generating test cases"
        )
        
        all_test_cases = []
        for target in test_targets:
            # Include implementation context in test generation
            test_context = {
                "task": task,
                "implementation_context": task_metadata.get("implementation_context", {}),
                "modified_files": task_metadata.get("modified_files", []),
                "added_functions": task_metadata.get("added_functions", [])
            }
            
            test_cases = await self.test_agent.generate_tests(
                target_file=target["file"],
                target_functions=target["functions"],
                strategy=target.get("strategy", TestStrategy.UNIT),
                context=test_context
            )
            all_test_cases.extend(test_cases)
            
        # Write test files
        test_files = await self._write_test_files(all_test_cases)
        
        # Emit test.generated event
        await self._event_integration.publish_event("test.generated", {
            "task_id": self.current_task_id,
            "test_count": len(all_test_cases),
            "test_files": test_files
        })
        
        # Phase 2: Execute tests
        await self.update_task_progress(
            self.current_task_id,
            0.5,
            "Executing tests"
        )
        
        report, analysis = await self.test_executor.execute_tests(
            test_files=test_files,
            capture_coverage=True
        )
        
        # Set task ID in report
        report.task_id = self.current_task_id
        
        # Emit test.executed event
        await self._event_integration.publish_event("test.executed", {
            "task_id": self.current_task_id,
            "passed": report.passed_tests,
            "failed": report.failed_tests,
            "coverage": report.coverage_percentage
        })
        
        # Phase 3: Adapt failed tests if needed
        if report.failed_tests > 0:
            await self.update_task_progress(
                self.current_task_id,
                0.7,
                "Adapting failed tests"
            )
            
            # Analyze failures
            for test_result in report.test_results:
                if not test_result.passed:
                    await self._event_integration.publish_event("test.failed", {
                        "task_id": self.current_task_id,
                        "test_name": test_result.test_name,
                        "failure_reason": test_result.failure_reason.value if test_result.failure_reason else "unknown",
                        "error_summary": test_result.error_message
                    })
                    
            # Try to adapt tests
            adapted_tests = await self.test_agent.adapt_failed_tests(report, analysis)
            
            if adapted_tests:
                # Write adapted tests
                adapted_files = await self._write_test_files(adapted_tests, suffix="_fixed")
                
                # Re-run adapted tests
                adapted_report, _ = await self.test_executor.execute_tests(
                    test_files=adapted_files,
                    capture_coverage=False
                )
                
                # Emit test.fixed event for successful adaptations
                for test_result in adapted_report.test_results:
                    if test_result.passed:
                        await self._event_integration.publish_event("test.fixed", {
                            "task_id": self.current_task_id,
                            "test_name": test_result.test_name
                        })
                        
        # Phase 4: Report to architect
        await self.update_task_progress(
            self.current_task_id,
            0.9,
            "Reporting results"
        )
        
        await self._report_to_architect(report, analysis)
        
        # Store test history
        self.test_history[self.current_task_id] = report
        
        # Final progress
        await self.update_task_progress(
            self.current_task_id,
            1.0,
            f"Testing complete: {report.passed_tests}/{report.total_tests} passed"
        )
        
        # Emit coverage event
        if report.coverage_percentage is not None:
            await self._event_integration.publish_event("test.coverage", {
                "task_id": self.current_task_id,
                "coverage": report.coverage_percentage,
                "test_files": test_files
            })
            
        return {
            "status": "completed",
            "total_tests": report.total_tests,
            "passed_tests": report.passed_tests,
            "failed_tests": report.failed_tests,
            "coverage": report.coverage_percentage,
            "recommendations": report.recommendations,
            "test_files": test_files
        }
        
    def _parse_test_targets(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse task to extract test targets.
        
        Returns list of dicts with:
        - file: target file path
        - functions: list of function names
        - strategy: test strategy to use
        """
        targets = []
        
        # Check for explicit test targets in task
        if "test_targets" in task:
            return task["test_targets"]
            
        # Check task metadata/context for target files
        task_metadata = task.get("metadata", {})
        task_context = task.get("context", {})
        context_files = task_metadata.get("target_files", []) or task_context.get("target_files", [])
        
        # Parse from description
        description = task.get("description", "")
        title = task.get("title", "")
        
        # Look for patterns like "test the power method in calculator.py"
        import re
        
        # If we have context files, use them as the default target
        default_file = None
        if context_files:
            # Prefer .py files that aren't test files
            for f in context_files:
                if f.endswith('.py') and 'test' not in f.lower():
                    default_file = f
                    break
            if not default_file and context_files:
                default_file = context_files[0]
        
        # Pattern for "test X in Y.py"
        pattern = r"test\s+(?:the\s+)?(\w+)(?:\s+method|\s+function)?\s+in\s+([\w/]+\.py)"
        matches = re.findall(pattern, description.lower())
        
        for func_name, file_path in matches:
            targets.append({
                "file": file_path,
                "functions": [func_name],
                "strategy": TestStrategy.UNIT
            })
            
        # Also check title
        title_matches = re.findall(pattern, title.lower())
        for func_name, file_path in title_matches:
            # Avoid duplicates
            if not any(t["file"] == file_path and func_name in t["functions"] for t in targets):
                targets.append({
                    "file": file_path,
                    "functions": [func_name],
                    "strategy": TestStrategy.UNIT
                })
                
        # Look for multiple methods pattern
        multi_pattern = r"test.*?(?:for|the)\s+([\w\s,]+)\s+method"
        multi_matches = re.findall(multi_pattern, description.lower())
        
        for methods_str in multi_matches:
            methods = [m.strip() for m in methods_str.split(',')]
            # Try to find associated file
            file_pattern = r"in\s+([\w/]+\.py)"
            file_match = re.search(file_pattern, description.lower())
            if file_match:
                targets.append({
                    "file": file_match.group(1),
                    "functions": methods,
                    "strategy": TestStrategy.UNIT
                })
                
        # Simpler pattern without file path requirement
        simple_pattern = r"(?:add\s+)?tests?\s+for\s+(?:the\s+)?(\w+)(?:\s+method|\s+function)?"
        simple_matches = re.findall(simple_pattern, title.lower())
        
        for func_name in simple_matches:
            # Use default file if available
            if default_file and not any(func_name in t["functions"] for t in targets):
                targets.append({
                    "file": default_file,
                    "functions": [func_name],
                    "strategy": TestStrategy.UNIT
                })
                
        # If still no targets but we have a default file, extract function names from title/description
        if not targets and default_file:
            # First check if we have added_functions from implementation context
            added_functions = task_metadata.get("added_functions", [])
            
            if added_functions:
                # Use the actual function names from the implementation
                targets.append({
                    "file": default_file,
                    "functions": added_functions,
                    "strategy": TestStrategy.UNIT
                })
            else:
                # Fallback to pattern matching
                # Look for function names in title/description
                func_pattern = r"\b(power|square_?root|sqrt|add|subtract|multiply|divide)\b"
                func_matches = re.findall(func_pattern, title.lower() + " " + description.lower())
                
                if func_matches:
                    # Deduplicate
                    unique_funcs = list(set(func_matches))
                    targets.append({
                        "file": default_file,
                        "functions": unique_funcs,
                        "strategy": TestStrategy.UNIT
                    })
                
        return targets
        
    async def _write_test_files(
        self,
        test_cases: List['TestCase'],
        suffix: str = ""
    ) -> List[str]:
        """Write test cases to files."""
        test_files = []
        
        # Group tests by target file
        tests_by_file = {}
        for test_case in test_cases:
            # Determine test file name
            if test_case.target_file:
                base_name = Path(test_case.target_file).stem
                test_file = f"tests/test_{base_name}{suffix}.py"
            else:
                test_file = f"tests/test_generated{suffix}.py"
                
            if test_file not in tests_by_file:
                tests_by_file[test_file] = []
            tests_by_file[test_file].append(test_case)
            
        # Write each test file
        for test_file, tests in tests_by_file.items():
            file_path = self.context.project_path / test_file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate file content
            content = self._generate_test_file_content(tests)
            
            # Write file
            file_path.write_text(content)
            test_files.append(test_file)
            
            logger.info(f"Wrote {len(tests)} tests to {test_file}")
            
        return test_files
        
    def _generate_test_file_content(self, test_cases: List['TestCase']) -> str:
        """Generate complete test file content."""
        imports = set()
        test_functions = []
        
        # Collect imports and functions
        for test_case in test_cases:
            # Add standard imports based on framework
            if self.test_agent.test_framework == "pytest":
                imports.add("import pytest")
            else:
                imports.add("import unittest")
                
            # Add test function
            test_functions.append(test_case.test_function)
            
            # Extract imports from test function
            # This is a simple approach - in production, use AST
            if "pytest.raises" in test_case.test_function:
                imports.add("import pytest")
                
        # Build file content
        content = "#!/usr/bin/env python3\n"
        content += '"""Generated test file."""\n\n'
        
        # Add imports
        for imp in sorted(imports):
            content += f"{imp}\n"
        content += "\n\n"
        
        # Add test class for unittest
        if self.test_agent.test_framework == "unittest":
            content += "class TestGenerated(unittest.TestCase):\n"
            content += '    """Generated test cases."""\n\n'
            
            # Indent test functions
            for func in test_functions:
                indented = '\n'.join('    ' + line for line in func.split('\n'))
                content += indented + "\n\n"
        else:
            # Just add functions for pytest
            for func in test_functions:
                content += func + "\n\n"
                
        return content
        
    async def _report_to_architect(
        self,
        report: TestReport,
        analysis: Dict[str, Any]
    ):
        """Report test results to architect."""
        # Create structured report
        architect_report = {
            "task_id": self.current_task_id,
            "test_summary": {
                "total": report.total_tests,
                "passed": report.passed_tests,
                "failed": report.failed_tests,
                "success_rate": report.success_rate,
                "coverage": report.coverage_percentage
            },
            "failures": [],
            "recommendations": report.recommendations
        }
        
        # Add failure details
        for test_result in report.test_results:
            if not test_result.passed:
                architect_report["failures"].append({
                    "test": test_result.test_name,
                    "reason": test_result.failure_reason.value if test_result.failure_reason else "unknown",
                    "summary": test_result.error_message,
                    "suggested_action": self._suggest_action(test_result, analysis.get(test_result.test_name, {}))
                })
                
        # Send to architect via event
        await self._event_integration.publish_event("test.report", architect_report)
        
    def _suggest_action(self, test_result: 'TestResult', analysis: Dict[str, Any]) -> str:
        """Suggest action based on test failure."""
        if test_result.failure_reason == TestFailureReason.CODE_BUG:
            return "Fix bug in implementation code"
        elif test_result.failure_reason == TestFailureReason.ASSERTION_ERROR:
            assertion_details = analysis.get("assertion_details", {})
            if assertion_details:
                return f"Update assertion: expected {assertion_details.get('expected', '?')}"
            return "Review and update test assertions"
        elif test_result.failure_reason == TestFailureReason.IMPORT_ERROR:
            return "Fix import statements or install missing dependencies"
        elif test_result.failure_reason == TestFailureReason.MISSING_DEPENDENCY:
            return "Add required test fixtures or mocks"
        else:
            return "Review test implementation"