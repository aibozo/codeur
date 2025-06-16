"""
Core Voice Agent implementation with RAG integration.

This agent provides natural language voice interaction with the codebase,
leveraging the adaptive RAG system for accurate context retrieval.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
import re

from .audio_interfaces import AudioInput, AudioOutput
from ..core.logging import get_logger
from ..llm import LLMClient

# Optional imports
try:
    from ..rag_service import RAGService, AdaptiveRAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    RAGService = None
    AdaptiveRAGClient = None

logger = get_logger(__name__)


@dataclass
class VoiceSession:
    """Represents a voice interaction session."""
    session_id: str
    started_at: datetime = field(default_factory=datetime.now)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    mentioned_files: List[str] = field(default_factory=list)
    mentioned_functions: List[str] = field(default_factory=list)
    

class VoiceAgent:
    """
    Voice Agent for natural language codebase interaction.
    
    Features:
    - Natural language understanding of codebase queries
    - Context-aware responses using RAG
    - Voice input/output with streaming support
    - Session management for conversation continuity
    - Intent detection and routing
    """
    
    def __init__(
        self,
        rag_service: Optional[Any] = None,
        audio_input: Optional[AudioInput] = None,
        audio_output: Optional[AudioOutput] = None,
        llm_client: Optional[LLMClient] = None,
        project_path: Optional[Path] = None
    ):
        """
        Initialize voice agent.
        
        Args:
            rag_service: RAG service for context retrieval
            audio_input: Speech-to-text interface
            audio_output: Text-to-speech interface
            llm_client: LLM client for natural language processing
            project_path: Root path of the project
        """
        self.rag_service = rag_service
        self.audio_input = audio_input
        self.audio_output = audio_output
        self.project_path = Path(project_path) if project_path else Path.cwd()
        
        # Initialize LLM with voice-thinking model
        if llm_client:
            self.llm_client = llm_client
        else:
            self.llm_client = LLMClient(
                model="voice-thinking",  # Gemini 2.5 Flash thinking audio
                agent_name="voice_agent"
            )
        
        # Session management
        self.sessions: Dict[str, VoiceSession] = {}
        
        # Intent patterns for query classification
        self.intent_patterns = {
            "explain_function": [
                r"what does (\w+) do",
                r"explain (?:the )?(?:function |method )?(\w+)",
                r"how does (\w+) work",
                r"tell me about (?:function |method )?(\w+)"
            ],
            "find_implementation": [
                r"where is (\w+) (?:implemented|defined)",
                r"find (?:the )?implementation of (\w+)",
                r"show me where (\w+) is (?:defined|implemented)",
                r"locate (\w+)"
            ],
            "explain_file": [
                r"what does (?:the )?file ([\w/.]+) do",
                r"explain (?:the )?file ([\w/.]+)",
                r"what is in ([\w/.]+)"
            ],
            "architecture": [
                r"how does the (?:architecture|system) work",
                r"explain the (?:overall )?(?:architecture|design)",
                r"what is the (?:system )?structure"
            ],
            "find_usage": [
                r"where is (\w+) used",
                r"find usages of (\w+)",
                r"who calls (\w+)",
                r"what uses (\w+)"
            ],
            "debug_help": [
                r"why is (\w+) (?:failing|not working)",
                r"debug (\w+)",
                r"help me fix (\w+)",
                r"what's wrong with (\w+)"
            ]
        }
        
        logger.info("Initialized voice agent with thinking audio model")
    
    async def process_audio(
        self,
        audio_data: bytes,
        session_id: str,
        format: str = "wav"
    ) -> Tuple[str, bytes]:
        """
        Process audio input and return audio response.
        
        Args:
            audio_data: Input audio bytes
            session_id: Session identifier
            format: Audio format
            
        Returns:
            Tuple of (transcribed_text, response_audio)
        """
        if not self.audio_input or not self.audio_output:
            raise ValueError("Audio interfaces not configured")
        
        # Transcribe audio to text
        text = await self.audio_input.transcribe(audio_data, format)
        logger.info(f"Transcribed: {text}")
        
        # Process text query
        response_text = await self.process_text(text, session_id)
        
        # Synthesize response
        response_audio = await self.audio_output.synthesize(response_text)
        
        return text, response_audio
    
    async def process_text(
        self,
        query: str,
        session_id: str
    ) -> str:
        """
        Process text query and return response.
        
        Args:
            query: User's question
            session_id: Session identifier
            
        Returns:
            Text response
        """
        # Get or create session
        session = self._get_or_create_session(session_id)
        
        # Add query to session
        session.messages.append({
            "role": "user",
            "content": query,
            "timestamp": datetime.now().isoformat()
        })
        
        # Detect intent
        intent, entities = self._detect_intent(query)
        logger.info(f"Detected intent: {intent}, entities: {entities}")
        
        # Get context from RAG
        context_chunks = await self._retrieve_context(query, intent, entities)
        
        # Generate response
        response = await self._generate_response(
            query, intent, entities, context_chunks, session
        )
        
        # Add response to session
        session.messages.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update session context
        self._update_session_context(session, response, context_chunks)
        
        return response
    
    def _detect_intent(self, query: str) -> Tuple[str, List[str]]:
        """
        Detect intent and extract entities from query.
        
        Returns:
            Tuple of (intent, entities)
        """
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    entities = list(match.groups())
                    return intent, entities
        
        # Default intent
        return "general_query", []
    
    async def _retrieve_context(
        self,
        query: str,
        intent: str,
        entities: List[str]
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context from RAG."""
        if not self.rag_service:
            return []
        
        # Build enhanced query based on intent
        enhanced_query = query
        
        if intent == "explain_function" and entities:
            enhanced_query = f"function {entities[0]} implementation code"
        elif intent == "find_implementation" and entities:
            enhanced_query = f"where {entities[0]} is defined implementation"
        elif intent == "explain_file" and entities:
            enhanced_query = f"file {entities[0]} content purpose"
        elif intent == "architecture":
            enhanced_query = "system architecture components design structure"
        elif intent == "find_usage" and entities:
            enhanced_query = f"usage of {entities[0]} calls references"
        elif intent == "debug_help" and entities:
            enhanced_query = f"{entities[0]} error handling issues problems"
        
        # Search with adaptive RAG
        if hasattr(self.rag_service, 'search'):
            # Direct RAG service
            results = self.rag_service.search(enhanced_query, k=10)
        else:
            # Adaptive RAG client
            results = self.rag_service.search(enhanced_query, k=10)
        
        # Convert to context chunks
        context_chunks = []
        for result in results:
            context_chunks.append({
                "content": result.content,
                "metadata": result.metadata,
                "score": result.score,
                "file_path": result.metadata.get("file_path", "unknown")
            })
        
        return context_chunks
    
    async def _generate_response(
        self,
        query: str,
        intent: str,
        entities: List[str],
        context_chunks: List[Dict[str, Any]],
        session: VoiceSession
    ) -> str:
        """Generate response using LLM with context."""
        
        # Build context for LLM
        context_text = self._build_context_text(context_chunks)
        conversation_history = self._get_recent_history(session)
        
        # Build system prompt based on intent
        system_prompt = self._build_system_prompt(intent)
        
        # Build user prompt
        user_prompt = f"""Based on the following context about the codebase, please answer this question:

Question: {query}

Relevant Context:
{context_text}

Recent Conversation:
{conversation_history}

Guidelines:
- Be conversational and natural in your response
- Reference specific files and line numbers when relevant
- Keep responses concise but informative
- If you're not sure about something, say so
- Use the thinking mode to reason through complex questions
"""

        # Generate response
        response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=500
        )
        
        return response
    
    def _build_context_text(self, context_chunks: List[Dict[str, Any]]) -> str:
        """Build formatted context text from chunks."""
        if not context_chunks:
            return "No specific context found."
        
        context_parts = []
        for i, chunk in enumerate(context_chunks[:5]):  # Top 5 chunks
            file_path = chunk.get("file_path", "unknown")
            content = chunk.get("content", "")
            score = chunk.get("score", 0)
            
            context_parts.append(f"""
--- Context {i+1} (relevance: {score:.2f}) ---
File: {file_path}
{content}
""")
        
        return "\n".join(context_parts)
    
    def _build_system_prompt(self, intent: str) -> str:
        """Build system prompt based on intent."""
        base_prompt = """You are a helpful voice assistant for developers exploring a codebase. 
You have access to the codebase context and can explain code, find implementations, 
and help with debugging. Speak naturally and conversationally."""
        
        intent_prompts = {
            "explain_function": "Focus on explaining what the function does, its parameters, return values, and usage.",
            "find_implementation": "Help locate where code is implemented and provide file paths and line numbers.",
            "explain_file": "Explain the purpose and contents of the file, its main components and responsibilities.",
            "architecture": "Provide a high-level overview of the system architecture and how components interact.",
            "find_usage": "Show where and how the code is used throughout the codebase.",
            "debug_help": "Help diagnose issues and suggest debugging approaches based on the code context."
        }
        
        specific_prompt = intent_prompts.get(intent, "")
        
        return f"{base_prompt}\n\n{specific_prompt}"
    
    def _get_recent_history(self, session: VoiceSession, limit: int = 5) -> str:
        """Get recent conversation history."""
        if not session.messages:
            return "No previous conversation."
        
        recent = session.messages[-(limit*2):]  # Get last N exchanges
        history_parts = []
        
        for msg in recent:
            role = msg["role"].capitalize()
            content = msg["content"]
            history_parts.append(f"{role}: {content}")
        
        return "\n".join(history_parts)
    
    def _update_session_context(
        self,
        session: VoiceSession,
        response: str,
        context_chunks: List[Dict[str, Any]]
    ):
        """Update session with mentioned files and functions."""
        # Extract file mentions
        file_pattern = r'(?:file|File):\s*([\w/.-]+)'
        files = re.findall(file_pattern, response)
        session.mentioned_files.extend(files)
        
        # Extract function mentions
        func_pattern = r'(?:function|method|def)\s+(\w+)'
        functions = re.findall(func_pattern, response, re.IGNORECASE)
        session.mentioned_functions.extend(functions)
        
        # Add files from context
        for chunk in context_chunks:
            file_path = chunk.get("file_path")
            if file_path and file_path not in session.mentioned_files:
                session.mentioned_files.append(file_path)
        
        # Keep unique entries
        session.mentioned_files = list(set(session.mentioned_files))
        session.mentioned_functions = list(set(session.mentioned_functions))
    
    def _get_or_create_session(self, session_id: str) -> VoiceSession:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = VoiceSession(session_id=session_id)
        return self.sessions[session_id]
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of a session."""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session_id,
            "started_at": session.started_at.isoformat(),
            "message_count": len(session.messages),
            "mentioned_files": session.mentioned_files,
            "mentioned_functions": session.mentioned_functions,
            "duration": (datetime.now() - session.started_at).total_seconds()
        }
    
    def clear_session(self, session_id: str):
        """Clear a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]