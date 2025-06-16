"""
WebSocket handler for real-time voice interaction.

This module provides WebSocket endpoints for streaming audio input/output
and real-time voice interaction with the codebase.
"""

import asyncio
import json
import base64
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import WebSocket, WebSocketDisconnect, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.logging import get_logger
from ..core.realtime import WebSocketMessage, EventType
from .integrated_voice_agent import IntegratedVoiceAgent
from .audio_interfaces import AudioChunk

logger = get_logger(__name__)

# Optional security
security = HTTPBearer(auto_error=False)


class VoiceWebSocketHandler:
    """Handles WebSocket connections for voice interaction."""
    
    def __init__(self, voice_agent: IntegratedVoiceAgent):
        """
        Initialize WebSocket handler.
        
        Args:
            voice_agent: Integrated voice agent instance
        """
        self.voice_agent = voice_agent
        self.active_connections: Dict[str, Dict[str, Any]] = {}
    
    async def handle_connection(self, 
                              websocket: WebSocket,
                              credentials: Optional[HTTPAuthorizationCredentials] = None):
        """
        Handle a WebSocket connection for voice interaction.
        
        Args:
            websocket: WebSocket connection
            credentials: Optional authentication credentials
        """
        connection_id = str(uuid.uuid4())
        session_id = f"voice_{connection_id}"
        
        try:
            # Accept connection
            await websocket.accept()
            
            # Initialize connection data
            self.active_connections[connection_id] = {
                "websocket": websocket,
                "session_id": session_id,
                "authenticated": credentials is not None,
                "audio_buffer": bytearray(),
                "stream_active": False
            }
            
            # Start voice session
            session_data = await self.voice_agent.start_voice_session(
                session_id,
                user_preferences={"format": "webm", "sample_rate": 16000}
            )
            
            # Send session initialization
            await self._send_message(websocket, {
                "type": "session_started",
                "session_id": session_id,
                "welcome_text": session_data["welcome_text"],
                "capabilities": [
                    "streaming_audio",
                    "text_input",
                    "code_search",
                    "explanations"
                ]
            })
            
            # Handle messages
            await self._handle_messages(websocket, connection_id)
            
        except WebSocketDisconnect:
            logger.info(f"Voice WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"Voice WebSocket error: {e}")
        finally:
            # Clean up
            await self._cleanup_connection(connection_id)
    
    async def _handle_messages(self, websocket: WebSocket, connection_id: str):
        """Handle incoming WebSocket messages."""
        conn_data = self.active_connections[connection_id]
        
        while True:
            try:
                # Receive message
                message = await websocket.receive_json()
                msg_type = message.get("type")
                
                if msg_type == "audio_chunk":
                    await self._handle_audio_chunk(connection_id, message)
                
                elif msg_type == "text_input":
                    await self._handle_text_input(connection_id, message)
                
                elif msg_type == "start_streaming":
                    conn_data["stream_active"] = True
                    await self._send_message(websocket, {
                        "type": "streaming_started"
                    })
                
                elif msg_type == "stop_streaming":
                    conn_data["stream_active"] = False
                    await self._process_audio_buffer(connection_id)
                
                elif msg_type == "command":
                    await self._handle_command(connection_id, message)
                
                elif msg_type == "ping":
                    await self._send_message(websocket, {"type": "pong"})
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await self._send_error(websocket, "Invalid JSON")
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                await self._send_error(websocket, str(e))
    
    async def _handle_audio_chunk(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming audio chunk."""
        conn_data = self.active_connections[connection_id]
        
        # Decode base64 audio data
        audio_data = base64.b64decode(message.get("data", ""))
        is_final = message.get("is_final", False)
        
        # Add to buffer
        conn_data["audio_buffer"].extend(audio_data)
        
        # Process if buffer is large enough or final chunk
        if len(conn_data["audio_buffer"]) > 16000 or is_final:  # ~1 second at 16kHz
            await self._process_audio_buffer(connection_id)
    
    async def _process_audio_buffer(self, connection_id: str):
        """Process accumulated audio buffer."""
        conn_data = self.active_connections[connection_id]
        websocket = conn_data["websocket"]
        
        if not conn_data["audio_buffer"]:
            return
        
        try:
            # Send processing indicator
            await self._send_message(websocket, {
                "type": "processing_audio"
            })
            
            # Process audio through voice agent
            audio_data = bytes(conn_data["audio_buffer"])
            response = await self.voice_agent.process_voice_input(
                conn_data["session_id"],
                audio_data
            )
            
            # Clear buffer
            conn_data["audio_buffer"] = bytearray()
            
            # Send text response
            await self._send_message(websocket, {
                "type": "transcription",
                "text": response.text,
                "metadata": response.metadata
            })
            
            # Send audio response if available
            if response.audio:
                # Send in chunks for streaming
                audio_data = response.audio.audio_data
                chunk_size = 4096
                
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    is_final = (i + chunk_size) >= len(audio_data)
                    
                    await self._send_message(websocket, {
                        "type": "audio_response",
                        "data": base64.b64encode(chunk).decode('utf-8'),
                        "format": response.audio.format,
                        "is_final": is_final
                    })
                    
                    # Small delay for streaming effect
                    await asyncio.sleep(0.01)
            
            # Send completion
            await self._send_message(websocket, {
                "type": "response_complete",
                "source_files": response.source_files
            })
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self._send_error(websocket, "Audio processing failed")
    
    async def _handle_text_input(self, connection_id: str, message: Dict[str, Any]):
        """Handle text input."""
        conn_data = self.active_connections[connection_id]
        websocket = conn_data["websocket"]
        text = message.get("text", "")
        
        if not text:
            return
        
        try:
            # Send processing indicator
            await self._send_message(websocket, {
                "type": "processing_text"
            })
            
            # Process through voice agent
            response = await self.voice_agent.voice_agent.process_text(
                text,
                conn_data["session_id"],
                synthesize_response=True
            )
            
            # Send response
            await self._send_message(websocket, {
                "type": "text_response",
                "text": response.text,
                "metadata": response.metadata
            })
            
            # Send audio if available
            if response.audio:
                await self._send_message(websocket, {
                    "type": "audio_response",
                    "data": base64.b64encode(response.audio.audio_data).decode('utf-8'),
                    "format": response.audio.format,
                    "is_final": True
                })
            
            # Send completion
            await self._send_message(websocket, {
                "type": "response_complete",
                "source_files": response.source_files
            })
            
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            await self._send_error(websocket, "Text processing failed")
    
    async def _handle_command(self, connection_id: str, message: Dict[str, Any]):
        """Handle special commands."""
        conn_data = self.active_connections[connection_id]
        websocket = conn_data["websocket"]
        command = message.get("command")
        
        if command == "get_overview":
            # Get codebase overview
            response = await self.voice_agent.get_codebase_overview(
                conn_data["session_id"]
            )
            
            await self._send_message(websocket, {
                "type": "overview_response",
                "text": response.text,
                "has_audio": response.audio is not None
            })
            
        elif command == "get_recent_changes":
            # Get recent changes
            response = await self.voice_agent.explain_recent_changes(
                conn_data["session_id"]
            )
            
            await self._send_message(websocket, {
                "type": "changes_response",
                "text": response.text,
                "has_audio": response.audio is not None
            })
            
        elif command == "get_session_summary":
            # Get session summary
            summary = self.voice_agent.voice_agent.get_session_summary(
                conn_data["session_id"]
            )
            
            await self._send_message(websocket, {
                "type": "session_summary",
                "summary": summary
            })
            
        elif command == "clear_session":
            # Clear session history
            self.voice_agent.voice_agent.clear_session(conn_data["session_id"])
            
            await self._send_message(websocket, {
                "type": "session_cleared"
            })
    
    async def _send_message(self, websocket: WebSocket, data: Dict[str, Any]):
        """Send a message to the client."""
        data["timestamp"] = datetime.utcnow().isoformat()
        await websocket.send_json(data)
    
    async def _send_error(self, websocket: WebSocket, error: str):
        """Send an error message."""
        await self._send_message(websocket, {
            "type": "error",
            "error": error
        })
    
    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection resources."""
        if connection_id in self.active_connections:
            conn_data = self.active_connections[connection_id]
            
            # End voice session
            try:
                await self.voice_agent.end_voice_session(conn_data["session_id"])
            except Exception as e:
                logger.error(f"Error ending voice session: {e}")
            
            # Remove connection
            del self.active_connections[connection_id]


async def voice_websocket_endpoint(
    websocket: WebSocket,
    voice_agent: IntegratedVoiceAgent,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    FastAPI WebSocket endpoint for voice interaction.
    
    Usage:
        @app.websocket("/ws/voice")
        async def voice_ws(websocket: WebSocket, ...):
            return await voice_websocket_endpoint(websocket, voice_agent)
    """
    handler = VoiceWebSocketHandler(voice_agent)
    await handler.handle_connection(websocket, credentials)