"""
Voice Agent for natural language codebase interaction.

This agent provides voice-based interaction with the codebase,
allowing users to ask questions and get intelligent responses
about code structure, functionality, and implementation details.
"""

from .voice_agent import VoiceAgent
from .integrated_voice_agent import IntegratedVoiceAgent
from .audio_interfaces import (
    AudioInput, AudioOutput,
    OpenAIAudioInput, OpenAIAudioOutput,
    MockAudioInput, MockAudioOutput
)

__all__ = [
    'VoiceAgent',
    'IntegratedVoiceAgent',
    'AudioInput',
    'AudioOutput',
    'OpenAIAudioInput',
    'OpenAIAudioOutput',
    'MockAudioInput',
    'MockAudioOutput'
]