"""
Enhanced voice interface with better activation methods.
"""

import os
import sys
import time
import threading
import queue
from typing import Optional, Callable
from pathlib import Path

try:
    import keyboard
except ImportError:
    keyboard = None

try:
    import pyaudio
    import numpy as np
except ImportError:
    pyaudio = None
    np = None

from ..core.logging import get_logger
from .stt_whisper import WhisperSTT
from .tts_voice_mode import TTSVoiceMode

logger = get_logger(__name__)


class VoiceInterface:
    """Enhanced voice interface with multiple activation methods."""
    
    def __init__(
        self,
        stt: Optional[WhisperSTT] = None,
        tts: Optional[TTSVoiceMode] = None,
        activation_method: str = "push_to_talk",
        hotkey: str = "space",
        voice_threshold: float = 0.02,
        silence_duration: float = 1.5
    ):
        """Initialize voice interface.
        
        Args:
            stt: Speech-to-text instance
            tts: Text-to-speech instance
            activation_method: "push_to_talk", "voice_activity", or "hotword"
            hotkey: Key to hold for push-to-talk (e.g., "space", "ctrl")
            voice_threshold: Volume threshold for voice activity detection
            silence_duration: Seconds of silence before stopping recording
        """
        self.stt = stt or WhisperSTT()
        self.tts = tts or TTSVoiceMode()
        self.activation_method = activation_method
        self.hotkey = hotkey
        self.voice_threshold = voice_threshold
        self.silence_duration = silence_duration
        
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.frames = []
        
        # Check available features
        self.has_keyboard = keyboard is not None
        self.has_audio = pyaudio is not None and np is not None
        
        logger.info(f"Voice interface initialized: {activation_method}")
        logger.info(f"Keyboard support: {self.has_keyboard}")
        logger.info(f"Audio monitoring: {self.has_audio}")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for continuous audio monitoring."""
        if self.is_recording:
            self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)
    
    def _monitor_voice_activity(self, stream) -> bool:
        """Monitor audio level for voice activity."""
        if not self.has_audio:
            return False
            
        try:
            data = stream.read(1024, exception_on_overflow=False)
            # Convert byte data to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)
            # Calculate RMS (volume level)
            rms = np.sqrt(np.mean(audio_data**2))
            # Normalize to 0-1 range
            volume = rms / 32768.0
            return volume > self.voice_threshold
        except Exception:
            return False
    
    def record_with_push_to_talk(self) -> Optional[str]:
        """Record while holding a key."""
        if not self.has_keyboard:
            logger.error("keyboard package required for push-to-talk")
            logger.info("Install with: pip install keyboard")
            return None
            
        print(f"\n🎤 Hold [{self.hotkey.upper()}] to record, release to stop...")
        
        # Wait for key press
        while not keyboard.is_pressed(self.hotkey):
            time.sleep(0.01)
        
        print("🔴 Recording...")
        self.is_recording = True
        
        # Start recording in background
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_file = tmp.name
        
        # Record while key is held
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        frames = []
        while keyboard.is_pressed(self.hotkey):
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)
        
        print("⏹️  Stopped")
        self.is_recording = False
        
        # Save audio
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        import wave
        with wave.open(audio_file, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)
            wf.writeframes(b''.join(frames))
        
        # Transcribe
        text = self.stt.transcribe_file(audio_file)
        os.unlink(audio_file)
        
        return text
    
    def record_with_voice_activity(self) -> Optional[str]:
        """Record using voice activity detection."""
        if not self.has_audio:
            logger.error("pyaudio and numpy required for voice activity detection")
            logger.info("Install with: pip install pyaudio numpy")
            return None
            
        print("\n🎤 Listening for voice activity...")
        print("   (Start speaking, will stop after silence)")
        
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        frames = []
        recording = False
        silence_start = None
        
        try:
            while True:
                has_voice = self._monitor_voice_activity(stream)
                
                if has_voice and not recording:
                    print("🔴 Voice detected, recording...")
                    recording = True
                    silence_start = None
                
                if recording:
                    data = stream.read(1024, exception_on_overflow=False)
                    frames.append(data)
                    
                    if not has_voice:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > self.silence_duration:
                            print("⏹️  Silence detected, stopping")
                            break
                    else:
                        silence_start = None
                        
        except KeyboardInterrupt:
            print("\n⏹️  Recording cancelled")
            
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
        
        if not frames:
            return None
            
        # Save and transcribe
        import tempfile
        import wave
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_file = tmp.name
            
        with wave.open(audio_file, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)
            wf.writeframes(b''.join(frames))
        
        text = self.stt.transcribe_file(audio_file)
        os.unlink(audio_file)
        
        return text
    
    def record_with_timeout(self, timeout: float = 5.0) -> Optional[str]:
        """Simple recording with timeout (fallback method)."""
        print(f"\n🎤 Recording for {timeout} seconds...")
        print("🔴 Speak now!")
        
        text, _ = self.stt.record_and_transcribe(duration=timeout)
        return text
    
    def listen(self) -> Optional[str]:
        """Listen for voice input using configured method."""
        if self.activation_method == "push_to_talk" and self.has_keyboard:
            return self.record_with_push_to_talk()
        elif self.activation_method == "voice_activity" and self.has_audio:
            return self.record_with_voice_activity()
        else:
            # Fallback to timeout-based recording
            return self.record_with_timeout()
    
    async def speak(self, text: str) -> bool:
        """Speak text using TTS."""
        try:
            audio_file = await self.tts.text_to_speech(text, play=True)
            return audio_file is not None
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False


class ConversationLoop:
    """Manages a voice conversation loop."""
    
    def __init__(
        self,
        voice_interface: VoiceInterface,
        process_message: Callable[[str], str],
        wake_word: Optional[str] = None
    ):
        """Initialize conversation loop.
        
        Args:
            voice_interface: Voice interface instance
            process_message: Function to process user messages and return responses
            wake_word: Optional wake word to activate (e.g., "hey architect")
        """
        self.voice = voice_interface
        self.process_message = process_message
        self.wake_word = wake_word.lower() if wake_word else None
        self.active = False
    
    async def run(self):
        """Run the conversation loop."""
        print("\n🤖 Voice Assistant Ready")
        print("=" * 50)
        
        if self.voice.activation_method == "push_to_talk":
            print(f"📌 Hold [{self.voice.hotkey.upper()}] to speak")
        elif self.voice.activation_method == "voice_activity":
            print("📌 Just start speaking (auto-detects voice)")
        else:
            print("📌 Press Enter when ready to speak")
        
        if self.wake_word:
            print(f"📌 Say '{self.wake_word}' to activate")
        
        print("📌 Say 'goodbye' or press Ctrl+C to exit\n")
        
        # Greeting
        await self.voice.speak("Hello! I'm ready to help with your project.")
        
        try:
            while True:
                # Listen for input
                text = self.voice.listen()
                
                if not text:
                    continue
                
                print(f"\n👤 You: {text}")
                
                # Check for wake word if configured
                if self.wake_word and not self.active:
                    if self.wake_word in text.lower():
                        self.active = True
                        await self.voice.speak("Yes, I'm listening.")
                        continue
                    else:
                        continue
                
                # Check for exit commands
                if any(word in text.lower() for word in ["goodbye", "bye", "exit", "quit"]):
                    await self.voice.speak("Goodbye! Have a great day!")
                    break
                
                # Process the message
                print("🤔 Processing...")
                response = self.process_message(text)
                
                print(f"\n🤖 Assistant: {response}")
                await self.voice.speak(response)
                
                # Reset active state if using wake word
                if self.wake_word:
                    self.active = False
                    
        except KeyboardInterrupt:
            print("\n\n👋 Session ended")
            await self.voice.speak("Session ended.")


# Example usage
async def demo():
    """Demo the voice interface."""
    # Create voice interface with push-to-talk
    voice = VoiceInterface(
        activation_method="push_to_talk",  # or "voice_activity"
        hotkey="space",
        voice_threshold=0.02,
        silence_duration=1.5
    )
    
    # Simple echo processor for demo
    def process_message(text: str) -> str:
        return f"I heard you say: {text}"
    
    # Create conversation loop
    conversation = ConversationLoop(
        voice_interface=voice,
        process_message=process_message,
        wake_word=None  # or "hey assistant"
    )
    
    # Run the conversation
    await conversation.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())