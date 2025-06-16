"""
Audio input/output interfaces for voice agent.

Provides abstract interfaces and implementations for:
- Speech-to-text (STT)
- Text-to-speech (TTS)
- Audio streaming
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator, Union, Dict, Any
import asyncio
import io
import os

# Optional imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None


class AudioInput(ABC):
    """Abstract interface for speech-to-text."""
    
    @abstractmethod
    async def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Raw audio bytes
            format: Audio format (wav, mp3, etc.)
            
        Returns:
            Transcribed text
        """
        pass
    
    @abstractmethod
    async def stream_transcribe(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """
        Stream transcription of audio chunks.
        
        Args:
            audio_stream: Async iterator of audio chunks
            
        Yields:
            Partial transcriptions
        """
        pass


class AudioOutput(ABC):
    """Abstract interface for text-to-speech."""
    
    @abstractmethod
    async def synthesize(self, text: str, voice: str = "alloy") -> bytes:
        """
        Synthesize text to speech.
        
        Args:
            text: Text to synthesize
            voice: Voice to use
            
        Returns:
            Audio data bytes
        """
        pass
    
    @abstractmethod
    async def stream_synthesize(self, text: str, voice: str = "alloy") -> AsyncIterator[bytes]:
        """
        Stream synthesis of text.
        
        Args:
            text: Text to synthesize
            voice: Voice to use
            
        Yields:
            Audio chunks
        """
        pass


class OpenAIAudioInput(AudioInput):
    """OpenAI Whisper implementation for speech-to-text."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available. Install with: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        
        self.client = openai.OpenAI(api_key=self.api_key)
    
    async def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        """Transcribe audio using Whisper."""
        # Create a file-like object
        audio_file = io.BytesIO(audio_data)
        audio_file.name = f"audio.{format}"
        
        # Use Whisper API
        response = await asyncio.to_thread(
            self.client.audio.transcriptions.create,
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
        
        return response
    
    async def stream_transcribe(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Stream transcription (accumulates chunks for Whisper)."""
        # Whisper doesn't support true streaming, so we accumulate chunks
        audio_buffer = io.BytesIO()
        chunk_size = 1024 * 1024  # 1MB chunks
        
        async for chunk in audio_stream:
            audio_buffer.write(chunk)
            
            # Process when we have enough data
            if audio_buffer.tell() >= chunk_size:
                audio_buffer.seek(0)
                audio_data = audio_buffer.read()
                
                # Transcribe accumulated audio
                text = await self.transcribe(audio_data)
                if text:
                    yield text
                
                # Reset buffer
                audio_buffer = io.BytesIO()
        
        # Process remaining audio
        if audio_buffer.tell() > 0:
            audio_buffer.seek(0)
            text = await self.transcribe(audio_buffer.read())
            if text:
                yield text


class OpenAIAudioOutput(AudioOutput):
    """OpenAI TTS implementation for text-to-speech."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available. Install with: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        
        self.client = openai.OpenAI(api_key=self.api_key)
    
    async def synthesize(self, text: str, voice: str = "alloy") -> bytes:
        """Synthesize text using OpenAI TTS."""
        response = await asyncio.to_thread(
            self.client.audio.speech.create,
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Convert response to bytes
        audio_data = b""
        for chunk in response.iter_bytes():
            audio_data += chunk
        
        return audio_data
    
    async def stream_synthesize(self, text: str, voice: str = "alloy") -> AsyncIterator[bytes]:
        """Stream synthesis of text."""
        response = await asyncio.to_thread(
            self.client.audio.speech.create,
            model="tts-1",
            voice=voice,
            input=text,
            response_format="mp3"
        )
        
        # Stream chunks
        for chunk in response.iter_bytes(chunk_size=1024):
            yield chunk


class MockAudioInput(AudioInput):
    """Mock implementation for testing."""
    
    async def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        """Mock transcription."""
        return "What does the EventBridge class do?"
    
    async def stream_transcribe(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Mock streaming transcription."""
        yield "What does"
        await asyncio.sleep(0.1)
        yield " the EventBridge"
        await asyncio.sleep(0.1)
        yield " class do?"


class MockAudioOutput(AudioOutput):
    """Mock implementation for testing."""
    
    async def synthesize(self, text: str, voice: str = "alloy") -> bytes:
        """Mock synthesis."""
        # Return empty audio data
        return b"MOCK_AUDIO_DATA"
    
    async def stream_synthesize(self, text: str, voice: str = "alloy") -> AsyncIterator[bytes]:
        """Mock streaming synthesis."""
        # Stream mock audio chunks
        for i in range(5):
            yield f"CHUNK_{i}".encode()
            await asyncio.sleep(0.05)