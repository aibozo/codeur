"""
Text-to-Speech voice mode for the architect using Gemini TTS.

This provides a simpler alternative to the Live API by using regular
LLM generation with TTS output for voice responses.
"""

import os
import wave
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile
import subprocess

from google import genai
from google.genai import types

from ..core.logging import get_logger
from ..architect.architect import Architect

logger = get_logger(__name__)


class TTSVoiceMode:
    """Voice mode using Gemini TTS for audio output."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_name: str = "Kore",
        tts_model: str = "gemini-2.5-flash-preview-tts"
    ):
        """Initialize TTS voice mode.
        
        Args:
            api_key: Gemini API key
            voice_name: Prebuilt voice name (e.g., "Kore", "Aoede")
            tts_model: TTS model to use
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY required")
            
        self.voice_name = voice_name
        self.tts_model = tts_model
        self.client = genai.Client(api_key=self.api_key)
        self.playback_supported = self._check_playback_support()
        
        logger.info(f"Initialized TTS Voice Mode with voice: {voice_name}")
        if not self.playback_supported:
            logger.warning("Audio playback not supported on this system")
    
    def _check_playback_support(self) -> bool:
        """Check if audio playback is supported on this system."""
        import platform
        
        system = platform.system().lower()
        
        if system == "darwin":  # macOS
            return subprocess.run(["which", "afplay"], capture_output=True).returncode == 0
        elif system == "windows":
            try:
                import winsound
                return True
            except ImportError:
                return False
        elif system == "linux":
            # Check for any Linux audio player
            for player in ["aplay", "paplay", "ffplay"]:
                if subprocess.run(["which", player], capture_output=True).returncode == 0:
                    return True
            return False
        else:
            return False
    
    def _save_audio(self, audio_data: bytes, filename: str) -> str:
        """Save audio data to a wave file.
        
        Args:
            audio_data: PCM audio data
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(24000)  # 24kHz
            wf.writeframes(audio_data)
        
        return filename
    
    def _play_audio(self, filename: str):
        """Play audio file using system audio player."""
        import platform
        
        try:
            system = platform.system().lower()
            
            if system == "darwin":  # macOS
                subprocess.run(["afplay", filename], check=True)
            elif system == "windows":
                # Windows has built-in sound playback
                import winsound
                winsound.PlaySound(filename, winsound.SND_FILENAME)
            elif system == "linux":
                # Try different Linux audio players
                if subprocess.run(["which", "aplay"], capture_output=True).returncode == 0:
                    subprocess.run(["aplay", filename], check=True)
                elif subprocess.run(["which", "paplay"], capture_output=True).returncode == 0:
                    subprocess.run(["paplay", filename], check=True)
                elif subprocess.run(["which", "ffplay"], capture_output=True).returncode == 0:
                    subprocess.run(["ffplay", "-nodisp", "-autoexit", filename], check=True, capture_output=True)
                else:
                    logger.warning("No audio player found on Linux (tried aplay, paplay, ffplay)")
            else:
                logger.warning(f"Unsupported platform for audio playback: {system}")
                self._try_python_playback(filename)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error playing audio: {e}")
            self._try_python_playback(filename)
        except ImportError as e:
            logger.error(f"Missing required module for audio playback: {e}")
            self._try_python_playback(filename)
        except Exception as e:
            logger.error(f"Unexpected error playing audio: {e}")
    
    def _try_python_playback(self, filename: str):
        """Try to play audio using Python libraries as fallback."""
        try:
            # Try pygame first (cross-platform)
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            logger.info("Audio played using pygame")
        except ImportError:
            try:
                # Try pyaudio as second fallback
                import pyaudio
                import wave
                
                wf = wave.open(filename, 'rb')
                p = pyaudio.PyAudio()
                
                stream = p.open(
                    format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                data = wf.readframes(1024)
                while data:
                    stream.write(data)
                    data = wf.readframes(1024)
                
                stream.stop_stream()
                stream.close()
                p.terminate()
                wf.close()
                logger.info("Audio played using pyaudio")
            except ImportError:
                logger.info(f"No Python audio libraries available. Audio saved to: {filename}")
    
    async def text_to_speech(self, text: str, play: bool = True) -> Optional[str]:
        """Convert text to speech and optionally play it.
        
        Args:
            text: Text to convert to speech
            play: Whether to play the audio immediately
            
        Returns:
            Path to audio file if saved, None otherwise
        """
        try:
            logger.info(f"Generating TTS for {len(text)} chars")
            
            # Generate audio
            response = self.client.models.generate_content(
                model=self.tts_model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice_name,
                            )
                        )
                    ),
                )
            )
            
            # Extract audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                audio_file = self._save_audio(audio_data, tmp.name)
                logger.info(f"Audio saved to: {audio_file}")
                
                if play:
                    if self.playback_supported:
                        self._play_audio(audio_file)
                    else:
                        logger.info(f"Audio playback skipped - not supported on this system. File saved to: {audio_file}")
                
                return audio_file
                
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None
    
    async def speak_response(self, text: str):
        """Speak a response using TTS."""
        # Split long text into sentences for better flow
        sentences = text.replace("...", ".").split(". ")
        
        for sentence in sentences:
            if sentence.strip():
                # Add period back if missing
                if not sentence.endswith("."):
                    sentence += "."
                    
                await self.text_to_speech(sentence, play=True)
                
                # Small pause between sentences
                await asyncio.sleep(0.1)


class VoiceArchitect:
    """Architect with TTS voice output."""
    
    def __init__(
        self,
        project_path: Path,
        voice_name: str = "Kore",
        tts_model: str = "gemini-2.5-flash-preview-tts"
    ):
        """Initialize voice-enabled architect.
        
        Args:
            project_path: Path to project
            voice_name: TTS voice to use
            tts_model: TTS model name
        """
        self.architect = Architect(str(project_path))
        self.tts = TTSVoiceMode(voice_name=voice_name, tts_model=tts_model)
        self.project_path = project_path
        
        logger.info(f"Initialized Voice Architect for {project_path}")
    
    async def process_request(self, request: str, voice_output: bool = True) -> str:
        """Process a request with optional voice output.
        
        Args:
            request: User request
            voice_output: Whether to speak the response
            
        Returns:
            Text response
        """
        try:
            # For now, use analyze_project_requirements which takes a requirements string
            # In the future, we could add more sophisticated request routing
            result = await self.architect.analyze_project_requirements(request)
            
            # Extract the response text
            if isinstance(result, dict):
                # Look for response in various fields
                response = (
                    result.get("summary", "") or
                    result.get("description", "") or
                    result.get("response", "") or
                    str(result)
                )
            else:
                response = str(result)
            
            if voice_output and response:
                # Speak the response
                await self.tts.speak_response(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Voice architect error: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            
            if voice_output:
                await self.tts.speak_response(error_msg)
                
            return error_msg
    
    async def run_interactive(self):
        """Run interactive voice session."""
        print("\n🎤 Voice Architect (TTS Mode)")
        print("=" * 50)
        print(f"Project: {self.project_path}")
        print(f"Voice: {self.tts.voice_name}")
        print(f"Audio Playback: {'✅ Supported' if self.tts.playback_supported else '❌ Not supported (files will be saved only)'}")
        print("\nType your requests (or 'quit' to exit)")
        if self.tts.playback_supported:
            print("Responses will be spoken aloud\n")
        else:
            print("Audio files will be saved (playback not available on this system)\n")
        
        # Greeting
        greeting = f"Hello! I'm your voice architect for the {self.project_path.name} project. How can I help you today?"
        await self.tts.speak_response(greeting)
        
        while True:
            try:
                # Get text input (could be replaced with STT later)
                request = input("\n📝 You: ").strip()
                
                if request.lower() in ["quit", "exit", "bye"]:
                    farewell = "Goodbye! Have a great day!"
                    await self.tts.speak_response(farewell)
                    break
                
                if request:
                    print("\n🤔 Thinking...")
                    response = await self.process_request(request)
                    print(f"\n🤖 Architect: {response}")
                    
            except KeyboardInterrupt:
                print("\n\nStopped by user")
                break
            except EOFError:
                # Handle EOF (e.g., when input is redirected)
                print("\n\n👋 Session ended")
                break
            except Exception as e:
                logger.error(f"Interactive session error: {e}")
                print(f"\n❌ Error: {e}")


async def test_tts():
    """Test TTS functionality."""
    tts = TTSVoiceMode()
    
    # Test different voices
    voices = ["Kore", "Aoede", "Aura", "Eos", "Fenrir", "Orbit", "Puck", "Glimmer", "Vega", "Eclipse"]
    
    for voice in voices[:3]:  # Test first 3 voices
        print(f"\nTesting voice: {voice}")
        tts.voice_name = voice
        await tts.text_to_speech(f"Hello! This is the {voice} voice. How do I sound?")
        await asyncio.sleep(1)


if __name__ == "__main__":
    # Run test
    asyncio.run(test_tts())