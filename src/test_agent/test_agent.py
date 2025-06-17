"""
Test Agent for intelligent test generation and planning.

This agent focuses on:
- Analyzing code to determine test requirements
- Generating comprehensive tests with minimal mocks
- Planning test strategies
- Coordinating with TestExecutor for running tests
- Adapting tests based on execution feedback
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import ast

from .models import TestCase, TestStrategy, TestReport, TestFailureReason
from ..core.logging import get_logger

logger = get_logger(__name__)


class TestAgent:
    """
    Agent responsible for test generation and planning.
    
    Works with TestExecutor to run tests and analyze results.
    """
    
    def __init__(
        self,
        project_path: str,
        llm_client: Optional[Any] = None,
        rag_client: Optional[Any] = None
    ):
        """Initialize the Test Agent."""
        self.project_path = Path(project_path)
        self.llm_client = llm_client
        self.rag_client = rag_client
        
        # Test framework detection
        self.test_framework = self._detect_test_framework()
        
        # Track test generation history
        self.generated_tests: Dict[str, List[TestCase]] = {}
        
        logger.info(f"TestAgent initialized for {project_path}")
        logger.info(f"Detected test framework: {self.test_framework}")
        
    def _detect_test_framework(self) -> str:
        """Detect which test framework the project uses."""
        # Check for pytest
        if (self.project_path / "pytest.ini").exists() or \
           (self.project_path / "pyproject.toml").exists():
            return "pytest"
            
        # Check for unittest patterns
        test_files = list(self.project_path.rglob("test_*.py"))
        if test_files:
            # Sample a test file to check imports
            with open(test_files[0], 'r') as f:
                content = f.read()
                if "import unittest" in content:
                    return "unittest"
                elif "import pytest" in content:
                    return "pytest"
                    
        # Default to pytest
        return "pytest"
        
    async def generate_tests(
        self,
        target_file: str,
        target_functions: List[str],
        strategy: TestStrategy = TestStrategy.UNIT,
        context: Optional[Dict[str, Any]] = None
    ) -> List[TestCase]:
        """
        Generate tests for specified functions.
        
        Args:
            target_file: File containing functions to test
            target_functions: List of function names to test
            strategy: Type of tests to generate
            context: Additional context from task
            
        Returns:
            List of generated test cases
        """
        logger.info(f"Generating {strategy.value} tests for {len(target_functions)} functions in {target_file}")
        
        # Analyze target code
        code_analysis = await self._analyze_target_code(target_file, target_functions, context)
        
        # Search for similar tests in codebase
        similar_tests = await self._find_similar_tests(target_functions)
        
        # Generate tests using LLM
        test_cases = await self._generate_tests_with_llm(
            code_analysis,
            similar_tests,
            strategy,
            context,
            target_file
        )
        
        # Store generated tests
        self.generated_tests[target_file] = test_cases
        
        return test_cases
        
    async def _analyze_target_code(
        self,
        target_file: str,
        target_functions: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze the target code to understand what needs testing."""
        file_path = self.project_path / target_file
        
        # First, search RAG for the latest implementation
        if self.rag_client and context:
            # Check if this is newly implemented code
            impl_context = context.get("implementation_context", {})
            if target_file in impl_context.get("modified_files", []):
                logger.info(f"Searching RAG for newly implemented code in {target_file}")
                
                # Search for the specific functions
                for func_name in target_functions:
                    query = f"function {func_name} in {target_file} implementation"
                    results = await self.rag_client.search(query, top_k=1)
                    
                    if results:
                        logger.info(f"Found fresh implementation for {func_name} in RAG")
                        # The RAG should have the latest indexed content
        
        if not file_path.exists():
            logger.warning(f"Target file {target_file} not found")
            return {}
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.error(f"Syntax error in {target_file}: {e}")
            return {}
            
        analysis = {
            "functions": {},
            "imports": [],
            "classes": {},
            "file_content": content  # Include full content for RAG context
        }
        
        # Extract function signatures and docstrings
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in target_functions:
                # Get the function source code
                import astor
                try:
                    func_source = astor.to_source(node)
                except:
                    func_source = ""
                
                analysis["functions"][node.name] = {
                    "args": [arg.arg for arg in node.args.args],
                    "returns": ast.unparse(node.returns) if node.returns else None,
                    "docstring": ast.get_docstring(node),
                    "complexity": self._estimate_complexity(node),
                    "source": func_source
                }
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                analysis["imports"].append(node.module)
                
        return analysis
        
    def _estimate_complexity(self, node: ast.FunctionDef) -> int:
        """Estimate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
                
        return complexity
        
    async def _find_similar_tests(self, target_functions: List[str]) -> List[Dict[str, Any]]:
        """Find similar tests in the codebase using RAG."""
        if not self.rag_client:
            return []
            
        similar_tests = []
        for func_name in target_functions:
            query = f"test function {func_name} pytest unittest assert"
            results = await self.rag_client.search(query, k=3)
            
            for result in results:
                if "test" in result.get("file_path", "").lower():
                    similar_tests.append({
                        "function": func_name,
                        "example": result.get("content", ""),
                        "file": result.get("file_path", "")
                    })
                    
        return similar_tests
        
    async def _generate_tests_with_llm(
        self,
        code_analysis: Dict[str, Any],
        similar_tests: List[Dict[str, Any]],
        strategy: TestStrategy,
        context: Optional[Dict[str, Any]],
        target_file: str
    ) -> List[TestCase]:
        """Generate tests using LLM."""
        if not self.llm_client:
            # Fallback to template-based generation
            return self._generate_template_tests(code_analysis, strategy)
            
        # Build prompt
        prompt = self._build_test_generation_prompt(
            code_analysis,
            similar_tests,
            strategy,
            context
        )
        
        # Generate tests
        response = self.llm_client.generate(
            prompt,
            system_prompt=self._get_test_generation_system_prompt()
        )
        
        # For now, return a simple test case based on the response
        # In a full implementation, we would parse the LLM response
        from .models import TestCase, TestStrategy
        
        test_cases = []
        for func_name in code_analysis.get("functions", {}):
            test_case = TestCase(
                name=f"test_{func_name}",
                description=f"Test for {func_name} function",
                test_function=response,  # The LLM response contains the test code
                strategy=strategy,
                target_function=func_name,
                target_file=target_file
            )
            test_cases.append(test_case)
            
        return test_cases
        
    def _get_test_generation_system_prompt(self) -> str:
        """Get system prompt for test generation."""
        return f"""You are an expert test engineer specializing in Python testing with {self.test_framework}.

Your goals:
1. Generate comprehensive tests that thoroughly validate functionality
2. Use minimal mocks - prefer testing with real implementations when possible
3. Test edge cases, error conditions, and happy paths
4. Follow the existing test patterns in the codebase
5. Write clear, maintainable test code with descriptive names

Test Guidelines:
- Each test should have a single, clear purpose
- Use descriptive test names that explain what is being tested
- Include assertions that verify the expected behavior
- Handle setup and teardown appropriately
- Consider performance implications of tests

For {self.test_framework}:
- Use appropriate decorators and fixtures
- Follow naming conventions (test_* for pytest, test* for unittest)
- Structure tests in a logical, readable way
"""

    def _build_test_generation_prompt(
        self,
        code_analysis: Dict[str, Any],
        similar_tests: List[Dict[str, Any]],
        strategy: TestStrategy,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for test generation."""
        prompt = f"Generate {strategy.value} tests for the following functions:\n\n"
        
        # Add function details
        for func_name, details in code_analysis.get("functions", {}).items():
            prompt += f"Function: {func_name}\n"
            prompt += f"Arguments: {', '.join(details['args'])}\n"
            if details.get('returns'):
                prompt += f"Returns: {details['returns']}\n"
            if details.get('docstring'):
                prompt += f"Description: {details['docstring']}\n"
            prompt += f"Complexity: {details['complexity']}\n\n"
            
        # Add similar test examples
        if similar_tests:
            prompt += "\nSimilar tests in codebase:\n"
            for example in similar_tests[:2]:  # Limit to 2 examples
                prompt += f"\nExample for {example['function']}:\n"
                prompt += f"```python\n{example['example'][:500]}...\n```\n"
                
        # Add context
        if context:
            # Extract implementation details
            impl_context = context.get("implementation_context", {})
            if impl_context:
                prompt += "\nImplementation context:\n"
                if impl_context.get("modified_files"):
                    prompt += f"- Modified files: {', '.join(impl_context['modified_files'])}\n"
                if impl_context.get("added_functions"):
                    prompt += f"- Added functions: {', '.join(impl_context['added_functions'])}\n"
                if impl_context.get("implementation_details"):
                    prompt += f"- Implementation details: {impl_context['implementation_details']}\n"
            
            # Add any other context
            task_desc = context.get("task", {}).get("description", "")
            if task_desc:
                prompt += f"\nTask description: {task_desc}\n"
            
        prompt += "\nGenerate comprehensive tests following the codebase patterns."
        
        return prompt
        
    async def adapt_failed_tests(
        self,
        test_report: TestReport,
        executor_analysis: Dict[str, Any]
    ) -> List[TestCase]:
        """
        Adapt tests based on failure analysis from executor.
        
        Args:
            test_report: Report from test execution
            executor_analysis: Detailed analysis from TestExecutor
            
        Returns:
            Updated test cases
        """
        logger.info(f"Adapting {len(test_report.failed_tests)} failed tests")
        
        adapted_tests = []
        
        for test_result in test_report.test_results:
            if not test_result.passed:
                # Get detailed failure analysis
                failure_details = executor_analysis.get(test_result.test_name, {})
                
                # Determine adaptation strategy
                if test_result.failure_reason == TestFailureReason.ASSERTION_ERROR:
                    # Fix assertions based on actual behavior
                    adapted_test = await self._fix_assertions(test_result, failure_details)
                elif test_result.failure_reason == TestFailureReason.IMPORT_ERROR:
                    # Fix imports and dependencies
                    adapted_test = await self._fix_imports(test_result, failure_details)
                elif test_result.failure_reason == TestFailureReason.MISSING_DEPENDENCY:
                    # Add necessary setup/mocks
                    adapted_test = await self._add_test_setup(test_result, failure_details)
                else:
                    # General adaptation using LLM
                    adapted_test = await self._adapt_test_with_llm(test_result, failure_details)
                    
                if adapted_test:
                    adapted_tests.append(adapted_test)
                    
        return adapted_tests
        
    def _generate_template_tests(
        self,
        code_analysis: Dict[str, Any],
        strategy: TestStrategy
    ) -> List[TestCase]:
        """Fallback template-based test generation."""
        tests = []
        
        for func_name, details in code_analysis.get("functions", {}).items():
            test_code = self._generate_test_template(func_name, details, strategy)
            
            test_case = TestCase(
                name=f"test_{func_name}",
                description=f"Test {func_name} function",
                test_function=test_code,
                strategy=strategy,
                target_function=func_name
            )
            
            tests.append(test_case)
            
        return tests
        
    def _generate_test_template(
        self,
        func_name: str,
        details: Dict[str, Any],
        strategy: TestStrategy
    ) -> str:
        """Generate basic test template."""
        if self.test_framework == "pytest":
            template = f'''def test_{func_name}():
    """Test {func_name} function."""
    # TODO: Implement test
    result = {func_name}({', '.join(details["args"])})
    assert result is not None
'''
        else:
            template = f'''def test_{func_name}(self):
    """Test {func_name} function."""
    # TODO: Implement test
    result = {func_name}({', '.join(details["args"])})
    self.assertIsNotNone(result)
'''
        
        return template