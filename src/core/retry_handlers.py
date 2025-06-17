"""
Agent-specific retry handlers that integrate with the self-healing coordinator.

Each handler implements domain-specific retry logic and recovery strategies.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Tuple
from abc import ABC, abstractmethod
import json

from .self_healing_coordinator import (
    FailureContext, RecoveryAction, FailureType, RetryPolicy
)
from .logging import get_logger

logger = get_logger(__name__)


class RetryHandler(ABC):
    """Base class for agent-specific retry handlers."""
    
    def __init__(self, agent_id: str, event_bridge: Any):
        self.agent_id = agent_id
        self.event_bridge = event_bridge
        
    @abstractmethod
    async def can_retry(self, context: FailureContext) -> bool:
        """Check if the failure can be retried."""
        pass
        
    @abstractmethod
    async def prepare_retry(self, context: FailureContext) -> Dict[str, Any]:
        """Prepare parameters for retry attempt."""
        pass
        
    @abstractmethod
    async def handle_success(self, task_id: str, result: Any):
        """Handle successful retry."""
        pass
        

class RequestPlannerRetryHandler(RetryHandler):
    """
    Retry handler for Request Planner.
    
    Handles:
    - LLM schema mismatches
    - RAG context retrieval failures
    - Duplicate request detection
    """
    
    async def can_retry(self, context: FailureContext) -> bool:
        """Check if request planning can be retried."""
        # Don't retry duplicates
        if "duplicate" in context.error_message.lower():
            return False
            
        # Schema mismatches are retryable with prompt adjustments
        if context.failure_type == FailureType.SCHEMA_MISMATCH:
            return context.attempt_number <= 2
            
        # RAG failures might be temporary
        if "rag" in context.error_message.lower():
            return context.attempt_number <= 1
            
        return True
        
    async def prepare_retry(self, context: FailureContext) -> Dict[str, Any]:
        """Prepare retry with adjusted parameters."""
        params = {}
        
        if context.failure_type == FailureType.SCHEMA_MISMATCH:
            # Add more explicit schema instructions
            params["enhanced_schema_prompt"] = True
            params["simplify_output"] = True
            
        elif "rag" in context.error_message.lower():
            # Reduce RAG dependency
            params["rag_optional"] = True
            params["fallback_context"] = True
            
        # Increase timeout for retries
        params["timeout"] = 45.0  # seconds
        
        return params
        
    async def handle_success(self, task_id: str, result: Any):
        """Record successful planning."""
        await self.event_bridge.publish("planning.retry.success", {
            "task_id": task_id,
            "plan_id": result.get("plan_id")
        })
        

class CodingAgentRetryHandler(RetryHandler):
    """
    Retry handler for Coding Agent.
    
    Handles:
    - Patch application failures
    - Validation errors
    - Self-check failures
    - Git operation errors
    """
    
    def __init__(self, agent_id: str, event_bridge: Any, rag_client: Optional[Any] = None):
        super().__init__(agent_id, event_bridge)
        self.rag_client = rag_client
        
    async def can_retry(self, context: FailureContext) -> bool:
        """Check if coding task can be retried."""
        # Hard failures in git operations
        if any(word in context.error_message.lower() for word in ["permission", "access denied"]):
            return False
            
        # Syntax errors might need different approach
        if context.failure_type == FailureType.SYNTAX_ERROR:
            return context.attempt_number <= 2
            
        # Validation errors are retryable
        if context.failure_type == FailureType.VALIDATION_ERROR:
            return context.attempt_number <= 3
            
        return True
        
    async def prepare_retry(self, context: FailureContext) -> Dict[str, Any]:
        """Prepare retry with context adjustments."""
        params = {}
        
        # For syntax errors, try different generation approach
        if context.failure_type == FailureType.SYNTAX_ERROR:
            params["generation_strategy"] = "full_file"  # Instead of patch
            params["syntax_validation"] = "strict"
            
            # Search for similar working code
            if self.rag_client:
                similar_code = await self._find_similar_working_code(context)
                if similar_code:
                    params["reference_implementations"] = similar_code
                    
        # For validation errors, adjust validation parameters
        elif context.failure_type == FailureType.VALIDATION_ERROR:
            validation_type = context.metadata.get("validation_type", "")
            
            if validation_type == "linting":
                params["linting_rules"] = "relaxed"
            elif validation_type == "type_checking":
                params["type_checking"] = "gradual"
            elif validation_type == "tests":
                params["skip_slow_tests"] = True
                
        # For patch failures, try smaller patches
        elif "patch" in context.error_message.lower():
            params["patch_strategy"] = "incremental"
            params["max_patch_size"] = 50  # lines
            
        return params
        
    async def _find_similar_working_code(self, context: FailureContext) -> List[Dict[str, Any]]:
        """Find similar code that works correctly."""
        if not self.rag_client:
            return []
            
        # Extract function/class name from error
        error_msg = context.error_message
        query = f"working implementation {error_msg[:50]}"
        
        try:
            results = await self.rag_client.search(query, top_k=3)
            
            # Filter for actual code
            code_examples = []
            for result in results:
                if any(keyword in result.get("content", "") for keyword in ["def ", "class ", "function"]):
                    code_examples.append({
                        "code": result.get("content", ""),
                        "file": result.get("metadata", {}).get("file", "")
                    })
                    
            return code_examples
            
        except Exception as e:
            logger.error(f"Failed to find similar code: {e}")
            return []
            
    async def handle_success(self, task_id: str, result: Any):
        """Record successful code generation."""
        # Store successful implementation in RAG
        if self.rag_client and result.get("code"):
            await self.rag_client.store_implementation(
                code=result.get("code", ""),
                description=f"Successful implementation for task {task_id}",
                metadata={
                    "task_id": task_id,
                    "retry_success": True
                }
            )
            

class TestAgentRetryHandler(RetryHandler):
    """
    Retry handler for Test Agent.
    
    Handles:
    - Test generation failures
    - Test execution failures
    - Assertion errors
    - Coverage issues
    """
    
    async def can_retry(self, context: FailureContext) -> bool:
        """Check if test task can be retried."""
        # Import errors usually need code fixes, not test retries
        if context.failure_type == FailureType.DEPENDENCY_ERROR:
            return False
            
        # Test failures are generally retryable
        if context.failure_type == FailureType.TEST_FAILURE:
            # Check if it's a flaky test
            if await self._is_flaky_test(context):
                return context.attempt_number <= 5  # More retries for flaky tests
            return context.attempt_number <= 3
            
        return True
        
    async def prepare_retry(self, context: FailureContext) -> Dict[str, Any]:
        """Prepare retry with test adjustments."""
        params = {}
        
        failure_reason = context.metadata.get("failure_reason", "")
        
        # For assertion errors, adjust test expectations
        if "assertion" in failure_reason.lower():
            params["test_strategy"] = "adaptive_assertions"
            params["capture_actual_values"] = True
            
        # For timeout issues, increase limits
        elif "timeout" in failure_reason.lower():
            params["test_timeout"] = 60.0  # seconds
            params["async_timeout"] = 30.0
            
        # For flaky tests, add retry logic
        elif await self._is_flaky_test(context):
            params["add_retry_decorator"] = True
            params["retry_count"] = 3
            params["retry_delay"] = 1.0
            
        # For missing mocks, generate them
        elif "mock" in context.error_message.lower():
            params["auto_generate_mocks"] = True
            params["mock_strategy"] = "minimal"
            
        return params
        
    async def _is_flaky_test(self, context: FailureContext) -> bool:
        """Check if a test is flaky based on history."""
        # Look for inconsistent failures
        test_name = context.metadata.get("test_name", "")
        
        if not test_name:
            return False
            
        # Query event history for this test
        # In a real implementation, this would check historical data
        # For now, use simple heuristics
        
        flaky_indicators = [
            "connection", "timeout", "race condition",
            "intermittent", "sometimes", "occasionally"
        ]
        
        return any(indicator in context.error_message.lower() for indicator in flaky_indicators)
        
    async def handle_success(self, task_id: str, result: Any):
        """Record successful test execution."""
        await self.event_bridge.publish("test.retry.success", {
            "task_id": task_id,
            "tests_passed": result.get("passed_tests", 0),
            "coverage": result.get("coverage", 0)
        })
        

class BuildRetryHandler(RetryHandler):
    """
    Retry handler for Build/CI processes.
    
    Handles:
    - Dependency resolution failures
    - Compilation errors
    - Environment issues
    """
    
    async def can_retry(self, context: FailureContext) -> bool:
        """Check if build can be retried."""
        # Compilation errors usually need code fixes
        if "compilation" in context.error_message.lower():
            return False
            
        # Dependency issues might be transient
        if "dependency" in context.error_message.lower():
            return context.attempt_number <= 2
            
        # Network issues during package download
        if any(word in context.error_message.lower() for word in ["download", "fetch", "network"]):
            return context.attempt_number <= 3
            
        return True
        
    async def prepare_retry(self, context: FailureContext) -> Dict[str, Any]:
        """Prepare retry with build adjustments."""
        params = {}
        
        # For dependency issues, try different resolution strategies
        if "dependency" in context.error_message.lower():
            params["dependency_resolution"] = "conservative"
            params["clear_cache"] = True
            
        # For network issues, use mirrors
        elif any(word in context.error_message.lower() for word in ["download", "fetch"]):
            params["use_mirrors"] = True
            params["parallel_downloads"] = False  # Sequential might be more stable
            
        # For environment issues, try clean build
        elif "environment" in context.error_message.lower():
            params["clean_build"] = True
            params["reset_environment"] = True
            
        return params
        
    async def handle_success(self, task_id: str, result: Any):
        """Record successful build."""
        await self.event_bridge.publish("build.retry.success", {
            "task_id": task_id,
            "build_time": result.get("duration", 0)
        })
        

class AnalyzerRetryHandler(RetryHandler):
    """
    Retry handler for Analyzer agent.
    
    Handles:
    - File parsing errors
    - Pattern detection failures
    - Resource limitations
    """
    
    async def can_retry(self, context: FailureContext) -> bool:
        """Check if analysis can be retried."""
        # Syntax errors in files being analyzed aren't retryable
        if context.failure_type == FailureType.SYNTAX_ERROR:
            return False
            
        # Resource issues might be temporary
        if "memory" in context.error_message.lower():
            return context.attempt_number <= 1
            
        return True
        
    async def prepare_retry(self, context: FailureContext) -> Dict[str, Any]:
        """Prepare retry with analysis adjustments."""
        params = {}
        
        # For memory issues, analyze in smaller chunks
        if "memory" in context.error_message.lower():
            params["chunk_size"] = "small"
            params["incremental_analysis"] = True
            
        # For parsing errors, try different strategies
        elif "parse" in context.error_message.lower():
            params["parsing_strategy"] = "fault_tolerant"
            params["skip_unparseable"] = True
            
        # For pattern detection, reduce complexity
        elif "pattern" in context.error_message.lower():
            params["pattern_complexity"] = "basic"
            params["skip_advanced_patterns"] = True
            
        return params
        
    async def handle_success(self, task_id: str, result: Any):
        """Record successful analysis."""
        await self.event_bridge.publish("analysis.retry.success", {
            "task_id": task_id,
            "components_found": len(result.get("components", []))
        })


class RetryHandlerFactory:
    """Factory for creating agent-specific retry handlers."""
    
    def __init__(self, event_bridge: Any, rag_client: Optional[Any] = None):
        self.event_bridge = event_bridge
        self.rag_client = rag_client
        self.handlers: Dict[str, RetryHandler] = {}
        
        # Initialize handlers
        self._initialize_handlers()
        
    def _initialize_handlers(self):
        """Initialize all retry handlers."""
        self.handlers["request_planner"] = RequestPlannerRetryHandler(
            "request_planner", self.event_bridge
        )
        
        self.handlers["coding_agent"] = CodingAgentRetryHandler(
            "coding_agent", self.event_bridge, self.rag_client
        )
        
        self.handlers["test_agent"] = TestAgentRetryHandler(
            "test_agent", self.event_bridge
        )
        
        self.handlers["build_runner"] = BuildRetryHandler(
            "build_runner", self.event_bridge
        )
        
        self.handlers["analyzer"] = AnalyzerRetryHandler(
            "analyzer", self.event_bridge
        )
        
    def get_handler(self, agent_id: str) -> Optional[RetryHandler]:
        """Get retry handler for an agent."""
        return self.handlers.get(agent_id)
        
    async def handle_retry(
        self,
        context: FailureContext
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Handle retry for a specific agent.
        
        Returns:
            Tuple of (can_retry, retry_parameters)
        """
        handler = self.get_handler(context.agent_id)
        if not handler:
            logger.warning(f"No retry handler for agent {context.agent_id}")
            return False, {}
            
        # Check if can retry
        can_retry = await handler.can_retry(context)
        if not can_retry:
            return False, {}
            
        # Prepare retry parameters
        params = await handler.prepare_retry(context)
        
        return True, params