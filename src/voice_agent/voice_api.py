"""
FastAPI routes for Voice Agent integration.

This module provides REST API endpoints and WebSocket support for
voice-based interaction with the codebase.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import base64
import uuid

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.logging import get_logger
from .integrated_voice_agent import IntegratedVoiceAgent
from .audio_interfaces import AudioInput, AudioOutput

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/voice", tags=["voice"])


# Request/Response models
class VoiceSessionRequest(BaseModel):
    """Request to create a voice session."""
    user_preferences: Optional[Dict[str, Any]] = None


class VoiceSessionResponse(BaseModel):
    """Response for voice session creation."""
    session_id: str
    status: str
    welcome_text: str
    audio_format: Optional[str] = None


class TextInputRequest(BaseModel):
    """Text input request."""
    text: str
    session_id: str
    synthesize_audio: bool = True


class TextInputResponse(BaseModel):
    """Response for text input."""
    text: str
    has_audio: bool
    source_files: List[str]
    metadata: Optional[Dict[str, Any]] = None


class AudioInputResponse(BaseModel):
    """Response for audio input."""
    transcription: str
    response_text: str
    has_audio: bool
    source_files: List[str]
    confidence: float


# Dependency to get voice agent
async def get_voice_agent() -> IntegratedVoiceAgent:
    """Get the voice agent instance."""
    # This would be properly injected in a real application
    # For now, return a placeholder
    raise NotImplementedError("Voice agent dependency not configured")


# Session management
active_sessions: Dict[str, Dict[str, Any]] = {}


@router.post("/sessions", response_model=VoiceSessionResponse)
async def create_voice_session(
    request: VoiceSessionRequest,
    voice_agent: IntegratedVoiceAgent = Depends(get_voice_agent)
):
    """
    Create a new voice interaction session.
    
    This initializes a session for voice-based code exploration.
    """
    try:
        # Generate session ID
        session_id = f"api_voice_{uuid.uuid4().hex[:8]}"
        
        # Start session
        session_data = await voice_agent.start_voice_session(
            session_id,
            request.user_preferences
        )
        
        # Store session info
        active_sessions[session_id] = {
            "created_at": session_data.get("created_at"),
            "preferences": request.user_preferences
        }
        
        return VoiceSessionResponse(
            session_id=session_id,
            status=session_data["status"],
            welcome_text=session_data["welcome_text"],
            audio_format=session_data.get("audio_format")
        )
        
    except Exception as e:
        logger.error(f"Error creating voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def end_voice_session(
    session_id: str,
    voice_agent: IntegratedVoiceAgent = Depends(get_voice_agent)
):
    """End a voice interaction session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # End session
        summary = await voice_agent.end_voice_session(session_id)
        
        # Remove from active sessions
        active_sessions.pop(session_id, None)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text", response_model=TextInputResponse)
async def process_text_input(
    request: TextInputRequest,
    voice_agent: IntegratedVoiceAgent = Depends(get_voice_agent)
):
    """
    Process text input and get a response.
    
    This endpoint allows text-based queries about the codebase.
    """
    if request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Process text through voice agent
        response = await voice_agent.voice_agent.process_text(
            request.text,
            request.session_id,
            synthesize_response=request.synthesize_audio
        )
        
        return TextInputResponse(
            text=response.text,
            has_audio=response.audio is not None,
            source_files=response.source_files,
            metadata=response.metadata
        )
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio", response_model=AudioInputResponse)
async def process_audio_input(
    session_id: str = Form(...),
    audio_file: UploadFile = File(...),
    voice_agent: IntegratedVoiceAgent = Depends(get_voice_agent)
):
    """
    Process audio input and get a response.
    
    Upload audio file (WAV, MP3, WebM) with a spoken query.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Read audio data
        audio_data = await audio_file.read()
        
        # Process through voice agent
        response = await voice_agent.process_voice_input(
            session_id,
            audio_data
        )
        
        # Get transcription from metadata
        transcription = response.metadata.get("transcription", "")
        
        return AudioInputResponse(
            transcription=transcription,
            response_text=response.text,
            has_audio=response.audio is not None,
            source_files=response.source_files,
            confidence=response.confidence
        )
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio/{session_id}/latest")
async def get_latest_audio_response(
    session_id: str,
    voice_agent: IntegratedVoiceAgent = Depends(get_voice_agent)
):
    """
    Get the latest audio response for a session.
    
    Returns audio data as streaming response.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # This would retrieve the latest audio from session storage
    # For now, return a placeholder
    raise HTTPException(status_code=501, detail="Audio retrieval not implemented")


@router.post("/commands/{session_id}/{command}")
async def execute_voice_command(
    session_id: str,
    command: str,
    voice_agent: IntegratedVoiceAgent = Depends(get_voice_agent)
):
    """
    Execute a voice command.
    
    Available commands:
    - overview: Get codebase overview
    - recent_changes: Explain recent changes
    - summary: Get session summary
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        if command == "overview":
            response = await voice_agent.get_codebase_overview(session_id)
            return {
                "command": "overview",
                "text": response.text,
                "has_audio": response.audio is not None
            }
            
        elif command == "recent_changes":
            response = await voice_agent.explain_recent_changes(session_id)
            return {
                "command": "recent_changes",
                "text": response.text,
                "has_audio": response.audio is not None
            }
            
        elif command == "summary":
            summary = voice_agent.voice_agent.get_session_summary(session_id)
            return {
                "command": "summary",
                "data": summary
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown command: {command}")
            
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_active_sessions():
    """List all active voice sessions."""
    return {
        "sessions": [
            {
                "session_id": sid,
                "created_at": data.get("created_at"),
                "preferences": data.get("preferences", {})
            }
            for sid, data in active_sessions.items()
        ]
    }


@router.get("/capabilities")
async def get_voice_capabilities(
    voice_agent: IntegratedVoiceAgent = Depends(get_voice_agent)
):
    """Get voice agent capabilities."""
    return {
        "capabilities": [
            "code_search",
            "function_explanation", 
            "file_analysis",
            "architecture_overview",
            "usage_finding",
            "streaming_audio",
            "text_input"
        ],
        "supported_languages": ["python"],  # Could be extended
        "audio_formats": ["wav", "mp3", "webm", "opus"],
        "voices": voice_agent.audio_output.get_available_voices()
    }


# Health check
@router.get("/health")
async def voice_health_check():
    """Check voice service health."""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions)
    }


def create_voice_routes(voice_agent: IntegratedVoiceAgent) -> APIRouter:
    """
    Create voice routes with a specific agent instance.
    
    This is useful for dependency injection in the main app.
    
    Args:
        voice_agent: The voice agent instance to use
        
    Returns:
        Configured router
    """
    # Override the dependency
    async def get_configured_agent():
        return voice_agent
    
    router.dependency_overrides[get_voice_agent] = get_configured_agent
    
    return router