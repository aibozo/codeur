"""
Test Executor Agent for running tests and analyzing results.

This agent specializes in:
- Running tests in isolated environments
- Capturing and filtering error logs
- Analyzing failure reasons
- Providing concise summaries to TestAgent
"""

import asyncio
import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import tempfile
import sys

from .models import TestResult, TestReport, TestFailureReason
from ..core.logging import get_logger

logger = get_logger(__name__)


class TestExecutor:
    """
    Agent responsible for test execution and result analysis.
    
    Runs tests, captures output, and provides intelligent analysis
    of failures to help the TestAgent adapt tests.
    """
    
    def __init__(self, project_path: str):
        """Initialize the Test Executor."""
        self.project_path = Path(project_path)
        self.test_framework = self._detect_test_framework()
        
        # Configure test runners
        self.test_runners = {
            "pytest": self._run_pytest,
            "unittest": self._run_unittest
        }
        
        logger.info(f"TestExecutor initialized for {project_path}")
        
    def _detect_test_framework(self) -> str:
        """Detect which test framework to use."""
        if (self.project_path / "pytest.ini").exists():
            return "pytest"
        return "pytest"  # Default
        
    async def execute_tests(
        self,
        test_files: List[str],
        specific_tests: Optional[List[str]] = None,
        capture_coverage: bool = True
    ) -> Tuple[TestReport, Dict[str, Any]]:
        """
        Execute tests and return detailed results.
        
        Args:
            test_files: List of test files to run
            specific_tests: Specific test names to run
            capture_coverage: Whether to capture coverage data
            
        Returns:
            Tuple of (TestReport, detailed_analysis)
        """
        logger.info(f"Executing tests in {len(test_files)} files")
        
        # Run tests
        runner = self.test_runners.get(self.test_framework, self._run_pytest)
        raw_results = await runner(test_files, specific_tests, capture_coverage)
        
        # Parse and analyze results
        test_results, analysis = self._analyze_test_output(raw_results)
        
        # Create report
        report = self._create_test_report(test_results, raw_results)
        
        return report, analysis
        
    async def _run_pytest(
        self,
        test_files: List[str],
        specific_tests: Optional[List[str]],
        capture_coverage: bool
    ) -> Dict[str, Any]:
        """Run tests using pytest."""
        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "--json-report"]
        
        # Add test files
        for test_file in test_files:
            cmd.append(str(self.project_path / test_file))
            
        # Add specific tests if provided
        if specific_tests:
            for test in specific_tests:
                cmd.extend(["-k", test])
                
        # Add coverage if requested
        if capture_coverage:
            cmd.extend(["--cov=.", "--cov-report=json"])
            
        # Run tests
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "json_report": self._load_pytest_json_report(),
                "coverage": self._load_coverage_report() if capture_coverage else None
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Test execution timed out after 5 minutes",
                "timeout": True
            }
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "error": True
            }
            
    def _analyze_test_output(self, raw_results: Dict[str, Any]) -> Tuple[List[TestResult], Dict[str, Any]]:
        """
        Analyze test output to extract meaningful information.
        
        Returns:
            Tuple of (test_results, detailed_analysis)
        """
        test_results = []
        detailed_analysis = {}
        
        # Parse pytest JSON report if available
        if raw_results.get("json_report"):
            test_results, detailed_analysis = self._parse_pytest_json_report(
                raw_results["json_report"]
            )
        else:
            # Fallback to parsing text output
            # For now, return empty results - in a full implementation
            # we would parse the text output
            test_results = []
            detailed_analysis = {
                "stdout": raw_results.get("stdout", ""),
                "stderr": raw_results.get("stderr", ""),
                "success": raw_results.get("success", False)
            }
            
        return test_results, detailed_analysis
        
    def _parse_pytest_json_report(self, report: Dict[str, Any]) -> Tuple[List[TestResult], Dict[str, Any]]:
        """Parse pytest JSON report."""
        test_results = []
        detailed_analysis = {}
        
        for test in report.get("tests", []):
            # Extract test info
            test_name = test["nodeid"].split("::")[-1]
            passed = test["outcome"] == "passed"
            
            # Analyze failure
            failure_reason = None
            error_message = None
            stack_trace = None
            
            if not passed:
                failure_info = test.get("call", {})
                error_message = failure_info.get("longrepr", "")
                
                # Determine failure reason
                failure_reason = self._classify_failure(error_message)
                
                # Extract clean stack trace
                stack_trace = self._extract_relevant_stack_trace(error_message)
                
                # Store detailed analysis
                detailed_analysis[test_name] = {
                    "raw_error": error_message,
                    "clean_trace": stack_trace,
                    "local_variables": failure_info.get("locals", {}),
                    "assertion_details": self._extract_assertion_details(error_message)
                }
                
            test_result = TestResult(
                test_name=test_name,
                passed=passed,
                execution_time=test.get("duration", 0.0),
                failure_reason=failure_reason,
                error_message=self._summarize_error(error_message) if error_message else None,
                stack_trace=stack_trace
            )
            
            test_results.append(test_result)
            
        return test_results, detailed_analysis
        
    def _classify_failure(self, error_message: str) -> TestFailureReason:
        """Classify the type of test failure."""
        if not error_message:
            return TestFailureReason.UNKNOWN
            
        error_lower = error_message.lower()
        
        if "assertionerror" in error_lower:
            return TestFailureReason.ASSERTION_ERROR
        elif "syntaxerror" in error_lower:
            return TestFailureReason.SYNTAX_ERROR
        elif "importerror" in error_lower or "modulenotfounderror" in error_lower:
            return TestFailureReason.IMPORT_ERROR
        elif "attributeerror" in error_lower and ("mock" in error_lower or "none" in error_lower):
            return TestFailureReason.MISSING_DEPENDENCY
        elif "timeout" in error_lower:
            return TestFailureReason.TIMEOUT
        elif any(err in error_lower for err in ["valueerror", "typeerror", "keyerror", "indexerror"]):
            return TestFailureReason.CODE_BUG
        else:
            return TestFailureReason.UNKNOWN
            
    def _extract_relevant_stack_trace(self, error_message: str) -> str:
        """Extract only the relevant parts of the stack trace."""
        if not error_message:
            return ""
            
        lines = error_message.split('\n')
        relevant_lines = []
        
        # Skip pytest internal frames
        skip_patterns = [
            "_pytest/",
            "pluggy/",
            "site-packages/",
            "__pycache__"
        ]
        
        for line in lines:
            if any(pattern in line for pattern in skip_patterns):
                continue
            relevant_lines.append(line)
            
        # Keep only last 10 relevant lines
        return '\n'.join(relevant_lines[-10:])
        
    def _extract_assertion_details(self, error_message: str) -> Dict[str, Any]:
        """Extract assertion comparison details."""
        details = {}
        
        # Look for assertion comparisons
        assertion_match = re.search(r'assert (.+?) == (.+?)$', error_message, re.MULTILINE)
        if assertion_match:
            details["expected"] = assertion_match.group(2)
            details["actual"] = assertion_match.group(1)
            
        # Look for pytest's assertion introspection
        if "where" in error_message:
            where_match = re.search(r'where (.+?)$', error_message, re.MULTILINE)
            if where_match:
                details["where"] = where_match.group(1)
                
        return details
        
    def _summarize_error(self, error_message: str) -> str:
        """Create a concise summary of the error."""
        if not error_message:
            return "Unknown error"
            
        lines = error_message.split('\n')
        
        # Find the actual error line
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith('>') and not line.startswith('E'):
                if len(line) > 200:
                    return line[:200] + "..."
                return line
                
        # Fallback to first non-empty line
        for line in lines:
            line = line.strip()
            if line:
                if len(line) > 200:
                    return line[:200] + "..."
                return line
                
        return "Error details unavailable"
        
    def _create_test_report(
        self,
        test_results: List[TestResult],
        raw_results: Dict[str, Any]
    ) -> TestReport:
        """Create a comprehensive test report."""
        passed_tests = sum(1 for t in test_results if t.passed)
        failed_tests = len(test_results) - passed_tests
        
        # Extract coverage if available
        coverage = None
        if raw_results.get("coverage"):
            coverage_data = raw_results["coverage"]
            coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            
        # Generate recommendations based on failures
        recommendations = self._generate_recommendations(test_results)
        
        return TestReport(
            task_id="",  # Will be set by caller
            total_tests=len(test_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            test_results=test_results,
            coverage_percentage=coverage,
            execution_time=sum(t.execution_time for t in test_results),
            recommendations=recommendations
        )
        
    def _generate_recommendations(self, test_results: List[TestResult]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Count failure types
        failure_counts = {}
        for result in test_results:
            if not result.passed and result.failure_reason:
                failure_counts[result.failure_reason] = failure_counts.get(result.failure_reason, 0) + 1
                
        # Generate recommendations
        if failure_counts.get(TestFailureReason.IMPORT_ERROR, 0) > 0:
            recommendations.append("Fix import errors - ensure all dependencies are installed")
            
        if failure_counts.get(TestFailureReason.ASSERTION_ERROR, 0) > 2:
            recommendations.append("Review assertions - multiple tests have incorrect expectations")
            
        if failure_counts.get(TestFailureReason.MISSING_DEPENDENCY, 0) > 0:
            recommendations.append("Add necessary test fixtures or mocks for dependencies")
            
        if failure_counts.get(TestFailureReason.CODE_BUG, 0) > 0:
            recommendations.append("Fix bugs in implementation code before continuing with tests")
            
        return recommendations
        
    def _load_pytest_json_report(self) -> Optional[Dict[str, Any]]:
        """Load pytest JSON report if it exists."""
        report_path = self.project_path / ".pytest_cache" / "json_report.json"
        if report_path.exists():
            try:
                with open(report_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load pytest report: {e}")
        return None
        
    def _load_coverage_report(self) -> Optional[Dict[str, Any]]:
        """Load coverage report if it exists."""
        coverage_path = self.project_path / "coverage.json"
        if coverage_path.exists():
            try:
                with open(coverage_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load coverage report: {e}")
        return None
        
    async def _run_unittest(
        self,
        test_files: List[str],
        specific_tests: Optional[List[str]],
        capture_coverage: bool
    ) -> Dict[str, Any]:
        """Run tests using unittest."""
        # TODO: Implement unittest runner
        logger.warning("Unittest runner not yet implemented, falling back to pytest")
        return await self._run_pytest(test_files, specific_tests, capture_coverage)