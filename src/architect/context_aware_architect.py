"""
Context-Aware Architect Agent with integrated Context Graph.

This module provides an enhanced Architect that uses the context graph system
to manage conversation history intelligently, reducing token usage while
maintaining full conversation context.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import asyncio

from .architect import Architect
from .context_graph import ContextGraph
from .context_graph_models import (
    ResolutionConfig, ConversationPhase, 
    BALANCED, AGGRESSIVE_COMPRESSION, CONTEXT_RICH
)
from .context_summarizer import ContextSummarizer
from .context_compiler import ContextCompiler
from ..core.summarizer import SummarizationService
from ..core.logging import get_logger

logger = get_logger(__name__)


class ContextAwareArchitect(Architect):
    """
    Enhanced Architect with integrated context graph for intelligent conversation management.
    
    This class extends the base Architect with:
    - Context graph for conversation history
    - Intelligent summarization of old messages
    - Optimized context windows for LLM calls
    - Task-based conversation organization
    """
    
    def __init__(
        self,
        project_path: str,
        rag_service: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        auto_index: bool = True,
        use_enhanced_task_graph: bool = True,
        context_config: Optional[ResolutionConfig] = None,
        summarization_service: Optional[SummarizationService] = None
    ):
        """
        Initialize the Context-Aware Architect.
        
        Args:
            project_path: Root path of the project
            rag_service: RAG service for storing/retrieving project context
            llm_client: LLM client for AI-powered design decisions
            auto_index: Whether to automatically index the project
            use_enhanced_task_graph: Enable enhanced task graph features
            context_config: Configuration for context resolution (defaults to BALANCED)
            summarization_service: Service for summarizing messages (will create if not provided)
        """
        # Initialize base architect
        super().__init__(
            project_path=project_path,
            rag_service=rag_service,
            llm_client=llm_client,
            auto_index=auto_index,
            use_enhanced_task_graph=use_enhanced_task_graph
        )
        
        # Initialize context graph system
        self.context_config = context_config or BALANCED
        self.context_graph = ContextGraph(
            project_id=f"architect_{self.project_path.name}",
            config=self.context_config
        )
        
        # Initialize summarization service
        self.summarization_service = summarization_service or SummarizationService(
            llm_client=self.llm_client
        )
        
        # Initialize context summarizer
        self.context_summarizer = ContextSummarizer(
            self.context_graph,
            self.summarization_service
        )
        
        # Initialize context compiler
        self.context_compiler = ContextCompiler(self.context_graph)
        
        # Track current task context
        self.current_task_ids: List[str] = []
        self.current_phase = ConversationPhase.EXPLORATION
        
        # Background summarization task
        self._summarization_task = None
        
        logger.info(f"Context-Aware Architect initialized with {self.context_config.__class__.__name__} config")
        
    async def process_message(
        self,
        user_message: str,
        task_ids: Optional[List[str]] = None,
        phase: Optional[ConversationPhase] = None,
        importance: float = 1.0
    ) -> str:
        """
        Process a user message with context graph integration.
        
        Args:
            user_message: The user's message
            task_ids: Associated task IDs (uses current if not provided)
            phase: Conversation phase (auto-detected if not provided)
            importance: Message importance (0-1)
            
        Returns:
            The architect's response
        """
        # Update task context if provided
        if task_ids:
            self.current_task_ids = task_ids
            
        # Auto-detect phase if not provided
        if not phase:
            phase = self._detect_conversation_phase(user_message)
            
        # Add user message to context graph
        user_node = await self.context_graph.add_message(
            role="user",
            content=user_message,
            task_ids=self.current_task_ids,
            phase=phase,
            importance=importance
        )
        
        logger.debug(f"Added user message {user_node.id[:8]} to context graph")
        
        # Compile optimized context window
        context_window = await self.context_compiler.compile_context(
            user_node.id,
            max_tokens=self.context_config.target_context_size,
            include_communities=True
        )
        
        logger.info(
            f"Compiled context: {context_window.total_tokens} tokens "
            f"({context_window.full_nodes}F/{context_window.summary_nodes}S/"
            f"{context_window.title_nodes}T/{context_window.hidden_nodes}H)"
        )
        
        # Get formatted context
        formatted_context = context_window.get_formatted_context()
        
        # Process with LLM using optimized context
        response = await self._generate_response_with_context(
            user_message,
            formatted_context,
            task_ids=self.current_task_ids
        )
        
        # Add response to context graph
        response_node = await self.context_graph.add_message(
            role="assistant",
            content=response,
            parent_id=user_node.id,
            task_ids=self.current_task_ids,
            phase=phase,
            importance=self._estimate_response_importance(response)
        )
        
        logger.debug(f"Added assistant response {response_node.id[:8]} to context graph")
        
        # Trigger background summarization if needed
        await self._trigger_background_summarization()
        
        return response
        
    async def _generate_response_with_context(
        self,
        user_message: str,
        context: str,
        task_ids: Optional[List[str]] = None
    ) -> str:
        """
        Generate response using LLM with optimized context.
        
        Args:
            user_message: Current user message
            context: Optimized conversation context
            task_ids: Current task IDs
            
        Returns:
            Generated response
        """
        if not self.llm_client:
            # Mock response
            return f"I understand you're asking about: {user_message[:50]}... [Using mock response]"
            
        try:
            # Prepare system prompt with context awareness
            system_prompt = self.get_enhanced_system_prompt()
            if task_ids:
                system_prompt += f"\n\nCurrent tasks: {', '.join(task_ids)}"
                
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"Conversation context:\n{context}"},
                {"role": "user", "content": user_message}
            ]
            
            # Add function definitions if using enhanced task graph
            kwargs = {}
            if self.use_enhanced_task_graph:
                kwargs["functions"] = self.get_enhanced_task_functions()
                kwargs["function_call"] = "auto"
                
            # Call LLM
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                **kwargs
            )
            
            # Handle function calls if present
            message = response.choices[0].message
            
            if hasattr(message, 'function_call') and message.function_call:
                # Handle function call
                function_name = message.function_call.name
                arguments = json.loads(message.function_call.arguments)
                
                # Get current project ID
                project_id = self.current_task_ids[0] if self.current_task_ids else "default"
                
                # Execute function
                result = await self.handle_function_call(
                    function_name,
                    arguments,
                    project_id
                )
                
                # Generate final response
                messages.append(message.model_dump())
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(result)
                })
                
                final_response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7
                )
                
                return final_response.choices[0].message.content
            else:
                return message.content
                
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
            
    def _detect_conversation_phase(self, message: str) -> ConversationPhase:
        """
        Auto-detect the conversation phase from message content.
        
        Args:
            message: User message
            
        Returns:
            Detected conversation phase
        """
        message_lower = message.lower()
        
        # Keywords for different phases
        exploration_keywords = ["what", "how", "can you", "explain", "tell me", "overview"]
        planning_keywords = ["plan", "design", "architecture", "structure", "approach"]
        implementation_keywords = ["implement", "code", "create", "build", "write", "fix"]
        review_keywords = ["review", "check", "test", "validate", "verify", "improve"]
        
        # Check keywords
        if any(keyword in message_lower for keyword in implementation_keywords):
            return ConversationPhase.IMPLEMENTATION
        elif any(keyword in message_lower for keyword in planning_keywords):
            return ConversationPhase.PLANNING
        elif any(keyword in message_lower for keyword in review_keywords):
            return ConversationPhase.REVIEW
        elif any(keyword in message_lower for keyword in exploration_keywords):
            return ConversationPhase.EXPLORATION
        else:
            # Default to current phase
            return self.current_phase
            
    def _estimate_response_importance(self, response: str) -> float:
        """
        Estimate the importance of a response.
        
        Args:
            response: Assistant response
            
        Returns:
            Importance score (0-1)
        """
        # High importance indicators
        if any(marker in response for marker in ["DECISION:", "IMPORTANT:", "WARNING:", "ERROR:"]):
            return 0.9
            
        # Medium importance - contains code or technical details
        if "```" in response or any(keyword in response.lower() for keyword in ["implement", "architecture", "design"]):
            return 0.7
            
        # Default importance
        return 0.5
        
    async def _trigger_background_summarization(self):
        """
        Trigger background summarization of old messages.
        """
        # Cancel previous task if running
        if self._summarization_task and not self._summarization_task.done():
            self._summarization_task.cancel()
            
        # Start new summarization task
        self._summarization_task = asyncio.create_task(
            self._background_summarization()
        )
        
    async def _background_summarization(self):
        """
        Background task to summarize old messages.
        """
        try:
            # Wait a bit to batch multiple messages
            await asyncio.sleep(5)
            
            # Summarize old nodes
            summarized = await self.context_summarizer.summarize_old_nodes()
            
            if summarized > 0:
                logger.info(f"Background summarization completed: {summarized} nodes")
                
        except asyncio.CancelledError:
            logger.debug("Background summarization cancelled")
        except Exception as e:
            logger.error(f"Background summarization failed: {e}")
            
    async def create_checkpoint(
        self,
        title: str,
        checkpoint_type: str = "milestone",
        message_count: int = 10
    ) -> str:
        """
        Create a semantic checkpoint for important conversation moments.
        
        Args:
            title: Checkpoint title
            checkpoint_type: Type of checkpoint
            message_count: Number of recent messages to include
            
        Returns:
            Checkpoint ID
        """
        # Get recent message IDs
        recent_nodes = list(self.context_graph.nodes.values())[-message_count:]
        message_ids = [node.id for node in recent_nodes]
        
        # Generate summary of messages
        summary_text = "\n".join([
            f"{node.role}: {node.content[:100]}..." 
            for node in recent_nodes
        ])
        
        summary = f"Checkpoint covering {len(message_ids)} messages about {title}"
        
        # Create checkpoint
        checkpoint = self.context_graph.add_checkpoint(
            message_ids=message_ids,
            checkpoint_type=checkpoint_type,
            title=title,
            summary=summary,
            importance_reason=f"User-requested checkpoint for {checkpoint_type}"
        )
        
        logger.info(f"Created checkpoint '{title}' with {len(message_ids)} messages")
        
        return checkpoint.id
        
    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current conversation.
        
        Returns:
            Conversation statistics
        """
        stats = self.context_summarizer.get_summarization_stats()
        
        # Add graph stats
        stats.update({
            "total_messages": len(self.context_graph.nodes),
            "communities": len(self.context_graph.communities),
            "checkpoints": len(self.context_graph.checkpoints),
            "current_phase": self.current_phase.value,
            "active_tasks": len(self.current_task_ids)
        })
        
        return stats
        
    def switch_context_mode(self, mode: str) -> ResolutionConfig:
        """
        Switch between different context compression modes.
        
        Args:
            mode: One of "aggressive", "balanced", "rich"
            
        Returns:
            New configuration
        """
        configs = {
            "aggressive": AGGRESSIVE_COMPRESSION,
            "balanced": BALANCED,
            "rich": CONTEXT_RICH
        }
        
        if mode not in configs:
            raise ValueError(f"Unknown mode: {mode}. Use one of: {list(configs.keys())}")
            
        self.context_config = configs[mode]
        self.context_graph.config = self.context_config
        
        logger.info(f"Switched to {mode} context mode")
        
        return self.context_config
        
    async def save_conversation_state(self) -> Path:
        """
        Save the current conversation state to disk.
        
        Returns:
            Path to saved state file
        """
        # Create state directory
        state_dir = self.project_path / ".architect_state"
        state_dir.mkdir(exist_ok=True)
        
        # Save context graph
        graph_data = self.context_graph.to_dict()
        graph_file = state_dir / "context_graph.json"
        
        with open(graph_file, 'w') as f:
            json.dump(graph_data, f, indent=2)
            
        logger.info(f"Saved conversation state to {graph_file}")
        
        return graph_file
        
    async def load_conversation_state(self) -> bool:
        """
        Load conversation state from disk.
        
        Returns:
            True if loaded successfully
        """
        state_dir = self.project_path / ".architect_state"
        graph_file = state_dir / "context_graph.json"
        
        if not graph_file.exists():
            logger.warning("No saved conversation state found")
            return False
            
        try:
            with open(graph_file, 'r') as f:
                graph_data = json.load(f)
                
            # Restore context graph
            self.context_graph = ContextGraph.from_dict(
                graph_data,
                self.context_config
            )
            
            # Reinitialize dependent components
            self.context_summarizer = ContextSummarizer(
                self.context_graph,
                self.summarization_service
            )
            self.context_compiler = ContextCompiler(self.context_graph)
            
            logger.info(f"Loaded conversation state with {len(self.context_graph.nodes)} messages")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load conversation state: {e}")
            return False


# Convenience function for creating context-aware architect
def create_context_aware_architect(
    project_path: str,
    mode: str = "balanced",
    **kwargs
) -> ContextAwareArchitect:
    """
    Create a context-aware architect with specified mode.
    
    Args:
        project_path: Project path
        mode: Context mode ("aggressive", "balanced", "rich")
        **kwargs: Additional arguments for ContextAwareArchitect
        
    Returns:
        Configured ContextAwareArchitect instance
    """
    configs = {
        "aggressive": AGGRESSIVE_COMPRESSION,
        "balanced": BALANCED,
        "rich": CONTEXT_RICH
    }
    
    context_config = configs.get(mode, BALANCED)
    
    return ContextAwareArchitect(
        project_path=project_path,
        context_config=context_config,
        **kwargs
    )