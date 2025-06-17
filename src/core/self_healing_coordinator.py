"""
Self-Healing Coordinator for managing retry loops and failure recovery.

This module implements a hierarchical retry system that coordinates between
agents, manages retry policies, and escalates failures appropriately.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from ..core.event_bridge import EventBridge
from ..core.logging import get_logger

logger = get_logger(__name__)


class RetryStrategy(Enum):
    """Different retry strategies for various failure types."""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    ADAPTIVE = "adaptive"  # Adjusts based on failure patterns


class FailureType(Enum):
    """Types of failures that can occur."""
    # Temporary failures
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    RATE_LIMIT = "rate_limit"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    
    # Logic failures
    VALIDATION_ERROR = "validation_error"
    TEST_FAILURE = "test_failure"
    BUILD_FAILURE = "build_failure"
    MERGE_CONFLICT = "merge_conflict"
    
    # Critical failures
    SYNTAX_ERROR = "syntax_error"
    DEPENDENCY_ERROR = "dependency_error"
    SCHEMA_MISMATCH = "schema_mismatch"
    UNRECOVERABLE = "unrecoverable"


@dataclass
class RetryPolicy:
    """Policy for retrying failed operations."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_factor: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_failures: List[FailureType] = field(default_factory=lambda: [
        FailureType.TIMEOUT,
        FailureType.NETWORK_ERROR,
        FailureType.RATE_LIMIT,
        FailureType.RESOURCE_UNAVAILABLE,
        FailureType.TEST_FAILURE,
        FailureType.BUILD_FAILURE
    ])


@dataclass
class FailureContext:
    """Context about a failure for decision making."""
    task_id: str
    agent_id: str
    failure_type: FailureType
    error_message: str
    attempt_number: int
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_context: Optional['FailureContext'] = None


@dataclass
class RecoveryAction:
    """Action to take for recovery."""
    action_type: str  # "retry", "escalate", "alternate_path", "rollback"
    target_agent: Optional[str] = None
    modified_parameters: Dict[str, Any] = field(default_factory=dict)
    delay: float = 0.0
    reason: str = ""


class SelfHealingCoordinator:
    """
    Coordinates self-healing retry loops across all agents.
    
    Features:
    - Hierarchical retry policies (agent-specific and global)
    - Intelligent failure classification
    - Adaptive retry strategies based on patterns
    - Circuit breaker patterns
    - Escalation to architect/user
    - RAG-enhanced recovery suggestions
    """
    
    def __init__(
        self,
        event_bridge: EventBridge,
        rag_client: Optional[Any] = None,
        architect_agent: Optional[Any] = None
    ):
        """Initialize the self-healing coordinator."""
        self.event_bridge = event_bridge
        self.rag_client = rag_client
        self.architect_agent = architect_agent
        
        # Agent-specific retry policies
        self.agent_policies: Dict[str, RetryPolicy] = {
            "request_planner": RetryPolicy(
                max_attempts=2,
                initial_delay=3.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF
            ),
            "coding_agent": RetryPolicy(
                max_attempts=3,
                initial_delay=2.0,
                max_delay=30.0,
                strategy=RetryStrategy.ADAPTIVE
            ),
            "test_agent": RetryPolicy(
                max_attempts=3,
                initial_delay=1.0,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                retryable_failures=[
                    FailureType.TEST_FAILURE,
                    FailureType.TIMEOUT,
                    FailureType.VALIDATION_ERROR
                ]
            ),
            "analyzer": RetryPolicy(
                max_attempts=2,
                initial_delay=5.0
            )
        }
        
        # Global fallback policy
        self.default_policy = RetryPolicy()
        
        # Track failure history for adaptive strategies
        self.failure_history: List[FailureContext] = []
        self.recovery_patterns: Dict[str, List[RecoveryAction]] = {}
        
        # Circuit breakers for agents
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Subscribe to failure events
        self._subscribe_to_events()
        
    def _subscribe_to_events(self):
        """Subscribe to relevant failure and recovery events."""
        # Use message bus directly if available
        if hasattr(self.event_bridge, 'message_bus'):
            # Subscribe to wildcard events and filter
            self.event_bridge.message_bus.subscribe("*", self._handle_event)
        else:
            logger.warning("EventBridge doesn't have message_bus, self-healing may be limited")
            
    def _handle_event(self, event_type: str, data: Dict[str, Any]):
        """Handle all events and filter for ones we care about."""
        # Create event dict in expected format
        event = {"data": data}
        
        if event_type == "task.failed":
            asyncio.create_task(self._on_task_failed(event))
        elif event_type == "agent.error":
            asyncio.create_task(self._on_agent_error(event))
        elif event_type == "code.validation.failed":
            asyncio.create_task(self._on_validation_failed(event))
        elif event_type == "test.failed":
            asyncio.create_task(self._on_test_failed(event))
        elif event_type == "build.failed":
            asyncio.create_task(self._on_build_failed(event))
        elif event_type == "recovery.requested":
            asyncio.create_task(self._on_recovery_requested(event))
        
    async def _on_task_failed(self, event: Dict[str, Any]):
        """Handle task failure events."""
        data = event.get("data", {})
        
        # Create failure context
        context = FailureContext(
            task_id=data.get("task_id", ""),
            agent_id=data.get("agent_id", ""),
            failure_type=self._classify_failure(data.get("error", "")),
            error_message=data.get("error", ""),
            attempt_number=data.get("attempt", 1),
            timestamp=datetime.now(),
            metadata=data
        )
        
        # Initiate recovery
        await self._handle_failure(context)
        
    def _classify_failure(self, error_message: str) -> FailureType:
        """Classify the type of failure based on error message."""
        error_lower = error_message.lower()
        
        # Timeout/network issues
        if any(word in error_lower for word in ["timeout", "timed out", "deadline"]):
            return FailureType.TIMEOUT
        elif any(word in error_lower for word in ["connection", "network", "socket"]):
            return FailureType.NETWORK_ERROR
        elif "rate limit" in error_lower:
            return FailureType.RATE_LIMIT
            
        # Test/build failures
        elif "test" in error_lower and "fail" in error_lower:
            return FailureType.TEST_FAILURE
        elif "build" in error_lower:
            return FailureType.BUILD_FAILURE
            
        # Code issues
        elif any(word in error_lower for word in ["syntax", "parse", "invalid syntax"]):
            return FailureType.SYNTAX_ERROR
        elif "validation" in error_lower:
            return FailureType.VALIDATION_ERROR
        elif "merge conflict" in error_lower:
            return FailureType.MERGE_CONFLICT
            
        # Dependencies
        elif any(word in error_lower for word in ["import", "module not found", "dependency"]):
            return FailureType.DEPENDENCY_ERROR
            
        # Default
        return FailureType.UNRECOVERABLE
        
    async def _handle_failure(self, context: FailureContext):
        """
        Handle a failure with appropriate recovery strategy.
        
        Flow:
        1. Check circuit breaker
        2. Determine if retryable
        3. Calculate retry parameters
        4. Execute recovery action
        5. Track results
        """
        logger.info(f"Handling failure for task {context.task_id} in {context.agent_id}")
        
        # Check circuit breaker
        breaker = self._get_circuit_breaker(context.agent_id)
        if not breaker.is_closed():
            logger.warning(f"Circuit breaker open for {context.agent_id}")
            await self._escalate_failure(context, "Circuit breaker open")
            return
            
        # Get retry policy
        policy = self.agent_policies.get(context.agent_id, self.default_policy)
        
        # Check if retryable
        if not self._is_retryable(context, policy):
            await self._escalate_failure(context, "Non-retryable failure")
            return
            
        # Determine recovery action
        action = await self._determine_recovery_action(context, policy)
        
        # Execute recovery
        await self._execute_recovery(context, action)
        
        # Track failure for patterns
        self._track_failure(context)
        
    def _is_retryable(self, context: FailureContext, policy: RetryPolicy) -> bool:
        """Check if a failure is retryable based on policy."""
        # Check attempt limit
        if context.attempt_number >= policy.max_attempts:
            return False
            
        # Check failure type
        if context.failure_type not in policy.retryable_failures:
            return False
            
        # Check for repeated failures
        recent_failures = self._get_recent_failures(
            context.task_id,
            timedelta(minutes=10)
        )
        if len(recent_failures) > 5:
            return False  # Too many failures in short time
            
        return True
        
    async def _determine_recovery_action(
        self,
        context: FailureContext,
        policy: RetryPolicy
    ) -> RecoveryAction:
        """
        Determine the best recovery action based on context.
        
        Uses:
        - Failure patterns
        - RAG for similar past recoveries
        - Adaptive strategies
        """
        # Check for known recovery patterns
        pattern_key = f"{context.agent_id}:{context.failure_type.value}"
        if pattern_key in self.recovery_patterns:
            past_actions = self.recovery_patterns[pattern_key]
            # Use most successful action
            if past_actions:
                return past_actions[0]
                
        # Use RAG to find similar failures and recoveries
        if self.rag_client:
            similar_recoveries = await self._search_similar_recoveries(context)
            if similar_recoveries:
                return self._adapt_recovery_action(similar_recoveries[0], context)
                
        # Default recovery based on failure type
        return self._get_default_recovery(context, policy)
        
    async def _search_similar_recoveries(
        self,
        context: FailureContext
    ) -> List[Dict[str, Any]]:
        """Search RAG for similar past failures and their recoveries."""
        if not self.rag_client:
            return []
            
        query = f"failure recovery {context.failure_type.value} {context.agent_id} {context.error_message[:100]}"
        
        try:
            results = await self.rag_client.search(query, top_k=5)
            
            # Filter for relevant recoveries
            recoveries = []
            for result in results:
                if "recovery" in result.get("metadata", {}).get("type", ""):
                    recoveries.append(result)
                    
            return recoveries
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []
            
    def _get_default_recovery(
        self,
        context: FailureContext,
        policy: RetryPolicy
    ) -> RecoveryAction:
        """Get default recovery action based on failure type."""
        delay = self._calculate_retry_delay(context, policy)
        
        # Timeout/network - simple retry
        if context.failure_type in [FailureType.TIMEOUT, FailureType.NETWORK_ERROR]:
            return RecoveryAction(
                action_type="retry",
                delay=delay,
                reason="Temporary network issue"
            )
            
        # Rate limit - longer delay
        elif context.failure_type == FailureType.RATE_LIMIT:
            return RecoveryAction(
                action_type="retry",
                delay=max(delay, 60.0),  # At least 1 minute
                reason="Rate limit exceeded"
            )
            
        # Test failure - retry with modified context
        elif context.failure_type == FailureType.TEST_FAILURE:
            return RecoveryAction(
                action_type="retry",
                modified_parameters={"increase_timeout": True, "verbose": True},
                delay=delay,
                reason="Test failure - retrying with modifications"
            )
            
        # Validation error - might need different approach
        elif context.failure_type == FailureType.VALIDATION_ERROR:
            return RecoveryAction(
                action_type="alternate_path",
                target_agent="code_planner",  # Re-plan the approach
                delay=delay,
                reason="Validation failed - trying alternate approach"
            )
            
        # Default retry
        return RecoveryAction(
            action_type="retry",
            delay=delay,
            reason=f"Retrying after {context.failure_type.value}"
        )
        
    def _calculate_retry_delay(
        self,
        context: FailureContext,
        policy: RetryPolicy
    ) -> float:
        """Calculate retry delay based on policy and context."""
        if policy.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
            
        elif policy.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = policy.initial_delay * context.attempt_number
            
        elif policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = policy.initial_delay * (policy.backoff_factor ** (context.attempt_number - 1))
            
        elif policy.strategy == RetryStrategy.ADAPTIVE:
            # Adjust based on failure patterns
            base_delay = policy.initial_delay
            
            # Increase delay if many recent failures
            recent_failures = self._get_recent_failures(
                context.task_id,
                timedelta(minutes=5)
            )
            if len(recent_failures) > 2:
                base_delay *= 2
                
            # Decrease delay if failures are rare
            if len(recent_failures) == 0:
                base_delay *= 0.5
                
            delay = base_delay * (policy.backoff_factor ** (context.attempt_number - 1))
            
        # Cap at max delay
        return min(delay, policy.max_delay)
        
    async def _execute_recovery(
        self,
        context: FailureContext,
        action: RecoveryAction
    ):
        """Execute the recovery action."""
        logger.info(
            f"Executing recovery: {action.action_type} for task {context.task_id} "
            f"(reason: {action.reason})"
        )
        
        # Wait if needed
        if action.delay > 0:
            await asyncio.sleep(action.delay)
            
        # Execute based on action type
        if action.action_type == "retry":
            # Emit retry event
            await self.event_bridge.publish("task.retry", {
                "task_id": context.task_id,
                "agent_id": context.agent_id,
                "attempt": context.attempt_number + 1,
                "modified_parameters": action.modified_parameters,
                "reason": action.reason
            })
            
        elif action.action_type == "alternate_path":
            # Re-route to different agent
            await self.event_bridge.publish("task.reroute", {
                "task_id": context.task_id,
                "from_agent": context.agent_id,
                "to_agent": action.target_agent,
                "reason": action.reason
            })
            
        elif action.action_type == "escalate":
            # Escalate to architect
            await self._escalate_failure(context, action.reason)
            
        elif action.action_type == "rollback":
            # Initiate rollback
            await self.event_bridge.publish("task.rollback", {
                "task_id": context.task_id,
                "agent_id": context.agent_id,
                "reason": action.reason
            })
            
    async def _escalate_failure(self, context: FailureContext, reason: str):
        """
        Escalate failure to architect/user.
        
        Creates a comprehensive report with:
        - Failure history
        - Attempted recoveries
        - RAG-based suggestions
        - Recommended actions
        """
        logger.warning(f"Escalating failure for task {context.task_id}: {reason}")
        
        # Build escalation report
        report = {
            "task_id": context.task_id,
            "agent_id": context.agent_id,
            "failure_type": context.failure_type.value,
            "error_message": context.error_message,
            "attempts": context.attempt_number,
            "escalation_reason": reason,
            "failure_history": self._get_failure_history(context.task_id),
            "recovery_attempts": self._get_recovery_attempts(context.task_id),
            "timestamp": datetime.now().isoformat()
        }
        
        # Get RAG suggestions if available
        if self.rag_client:
            suggestions = await self._get_recovery_suggestions(context)
            report["suggestions"] = suggestions
            
        # Add recommended actions
        report["recommended_actions"] = self._get_recommended_actions(context)
        
        # Send to architect
        if self.architect_agent:
            await self.architect_agent.handle_escalation(report)
        else:
            # Emit escalation event
            await self.event_bridge.publish("failure.escalated", report)
            
    def _get_recommended_actions(self, context: FailureContext) -> List[str]:
        """Get recommended actions based on failure type."""
        actions = []
        
        if context.failure_type == FailureType.MERGE_CONFLICT:
            actions.extend([
                "Manually resolve merge conflicts",
                "Consider rebasing the feature branch",
                "Review conflicting changes with team"
            ])
            
        elif context.failure_type == FailureType.DEPENDENCY_ERROR:
            actions.extend([
                "Check and update project dependencies",
                "Verify import statements",
                "Ensure all required packages are installed"
            ])
            
        elif context.failure_type == FailureType.TEST_FAILURE:
            actions.extend([
                "Review test implementation",
                "Check if code changes broke existing tests",
                "Consider updating test expectations",
                "Run tests locally to debug"
            ])
            
        elif context.failure_type == FailureType.SYNTAX_ERROR:
            actions.extend([
                "Review generated code for syntax issues",
                "Check language version compatibility",
                "Validate code with linter"
            ])
            
        # Generic actions
        actions.extend([
            "Review agent logs for detailed error information",
            "Consider modifying the original request",
            "Break down the task into smaller subtasks"
        ])
        
        return actions
        
    def _track_failure(self, context: FailureContext):
        """Track failure for pattern analysis."""
        self.failure_history.append(context)
        
        # Keep only recent history (last 1000 failures)
        if len(self.failure_history) > 1000:
            self.failure_history = self.failure_history[-1000:]
            
        # Update recovery patterns if we have successful recoveries
        # This would be called when a retry succeeds
        
    def _get_recent_failures(
        self,
        task_id: str,
        time_window: timedelta
    ) -> List[FailureContext]:
        """Get recent failures for a task."""
        cutoff = datetime.now() - time_window
        
        return [
            f for f in self.failure_history
            if f.task_id == task_id and f.timestamp > cutoff
        ]
        
    def _get_failure_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get failure history for a task."""
        failures = [f for f in self.failure_history if f.task_id == task_id]
        
        return [
            {
                "timestamp": f.timestamp.isoformat(),
                "failure_type": f.failure_type.value,
                "error": f.error_message[:200],  # Truncate
                "attempt": f.attempt_number
            }
            for f in failures
        ]
        
    def _get_recovery_attempts(self, task_id: str) -> List[Dict[str, Any]]:
        """Get recovery attempts for a task."""
        # This would be populated by tracking recovery actions
        # For now, return empty list
        return []
        
    async def _get_recovery_suggestions(
        self,
        context: FailureContext
    ) -> List[str]:
        """Get recovery suggestions from RAG."""
        if not self.rag_client:
            return []
            
        suggestions = []
        
        # Search for similar errors and their solutions
        query = f"error solution fix {context.error_message[:100]}"
        
        try:
            results = await self.rag_client.search(query, top_k=3)
            
            for result in results:
                if "solution" in result.get("content", "").lower():
                    # Extract suggestion from content
                    suggestion = result.get("content", "")[:200]
                    suggestions.append(suggestion)
                    
        except Exception as e:
            logger.error(f"Failed to get RAG suggestions: {e}")
            
        return suggestions
        
    def _get_circuit_breaker(self, agent_id: str) -> 'CircuitBreaker':
        """Get or create circuit breaker for an agent."""
        if agent_id not in self.circuit_breakers:
            self.circuit_breakers[agent_id] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=300.0,  # 5 minutes
                expected_exception_types=[FailureType.UNRECOVERABLE]
            )
            
        return self.circuit_breakers[agent_id]
        
    async def _on_test_failed(self, event: Dict[str, Any]):
        """Handle test failure events specifically."""
        data = event.get("data", {})
        
        # Create specialized context for test failures
        context = FailureContext(
            task_id=data.get("task_id", ""),
            agent_id="test_agent",
            failure_type=FailureType.TEST_FAILURE,
            error_message=data.get("error_summary", ""),
            attempt_number=data.get("attempt", 1),
            timestamp=datetime.now(),
            metadata={
                "test_name": data.get("test_name", ""),
                "failure_reason": data.get("failure_reason", "")
            }
        )
        
        await self._handle_failure(context)
        
    async def _on_build_failed(self, event: Dict[str, Any]):
        """Handle build failure events."""
        data = event.get("data", {})
        
        context = FailureContext(
            task_id=data.get("task_id", ""),
            agent_id="build_runner",
            failure_type=FailureType.BUILD_FAILURE,
            error_message=data.get("error", ""),
            attempt_number=data.get("attempt", 1),
            timestamp=datetime.now(),
            metadata=data
        )
        
        await self._handle_failure(context)
        
    async def _on_validation_failed(self, event: Dict[str, Any]):
        """Handle validation failure events."""
        data = event.get("data", {})
        
        context = FailureContext(
            task_id=data.get("task_id", ""),
            agent_id=data.get("agent_id", "coding_agent"),
            failure_type=FailureType.VALIDATION_ERROR,
            error_message=data.get("error", ""),
            attempt_number=data.get("attempt", 1),
            timestamp=datetime.now(),
            metadata={
                "validation_type": data.get("validation_type", ""),
                "file": data.get("file", "")
            }
        )
        
        await self._handle_failure(context)
        
    async def _on_agent_error(self, event: Dict[str, Any]):
        """Handle generic agent error events."""
        data = event.get("data", {})
        
        context = FailureContext(
            task_id=data.get("task_id", "unknown"),
            agent_id=data.get("agent_id", "unknown"),
            failure_type=self._classify_failure(data.get("error", "")),
            error_message=data.get("error", ""),
            attempt_number=data.get("attempt", 1),
            timestamp=datetime.now(),
            metadata=data
        )
        
        await self._handle_failure(context)
        
    async def _on_recovery_requested(self, event: Dict[str, Any]):
        """Handle manual recovery requests."""
        data = event.get("data", {})
        
        # Create context from request
        context = FailureContext(
            task_id=data.get("task_id", ""),
            agent_id=data.get("agent_id", ""),
            failure_type=FailureType.UNRECOVERABLE,  # Assume worst case
            error_message=data.get("reason", "Manual recovery requested"),
            attempt_number=1,
            timestamp=datetime.now(),
            metadata=data
        )
        
        # Force recovery attempt
        action = RecoveryAction(
            action_type=data.get("action_type", "retry"),
            target_agent=data.get("target_agent"),
            modified_parameters=data.get("parameters", {}),
            reason="Manual recovery requested"
        )
        
        await self._execute_recovery(context, action)
        
    def _adapt_recovery_action(
        self,
        past_recovery: Dict[str, Any],
        context: FailureContext
    ) -> RecoveryAction:
        """Adapt a past recovery action to current context."""
        # Extract action from past recovery
        action_data = past_recovery.get("metadata", {}).get("recovery_action", {})
        
        # Create new action with adapted parameters
        return RecoveryAction(
            action_type=action_data.get("action_type", "retry"),
            target_agent=action_data.get("target_agent"),
            modified_parameters=action_data.get("modified_parameters", {}),
            delay=self._calculate_retry_delay(
                context,
                self.agent_policies.get(context.agent_id, self.default_policy)
            ),
            reason=f"Based on similar past recovery: {action_data.get('reason', '')}"
        )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    
    States:
    - CLOSED: Normal operation, failures tracked
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception_types: List[FailureType] = None
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception_types = expected_exception_types or []
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"
        
    def is_closed(self) -> bool:
        """Check if circuit is closed (operational)."""
        if self.state == "CLOSED":
            return True
            
        if self.state == "OPEN":
            # Check if recovery timeout passed
            if self.last_failure_time:
                elapsed = datetime.now() - self.last_failure_time
                if elapsed.total_seconds() > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    return True
                    
        return self.state == "HALF_OPEN"
        
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
        
    def record_failure(self, failure_type: FailureType):
        """Record failed operation."""
        # Don't count expected failures
        if failure_type in self.expected_exception_types:
            return
            
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
        elif self.state == "HALF_OPEN":
            # Failed while testing recovery
            self.state = "OPEN"