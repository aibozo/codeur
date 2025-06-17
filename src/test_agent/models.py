"""
Data models for the Test Agent.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class TestStrategy(Enum):
    """Test strategy types."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PROPERTY = "property"
    REGRESSION = "regression"


class TestFailureReason(Enum):
    """Reasons why a test might fail."""
    ASSERTION_ERROR = "assertion_error"
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    MISSING_DEPENDENCY = "missing_dependency"
    CODE_BUG = "code_bug"
    SETUP_ERROR = "setup_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class TestCase:
    """Represents a single test case."""
    name: str
    description: str
    test_function: str
    strategy: TestStrategy
    target_function: Optional[str] = None
    target_file: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    assertions: List[str] = field(default_factory=list)
    
    
@dataclass
class TestResult:
    """Result of running a test."""
    test_name: str
    passed: bool
    execution_time: float
    failure_reason: Optional[TestFailureReason] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    suggested_fix: Optional[str] = None
    

@dataclass
class TestReport:
    """Comprehensive test execution report."""
    task_id: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    test_results: List[TestResult]
    coverage_percentage: Optional[float] = None
    execution_time: float = 0.0
    generated_files: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate test success rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100