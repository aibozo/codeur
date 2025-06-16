"""
Speech-to-Text using OpenAI Whisper API.

This module provides STT functionality for voice input.
"""

import os
import logging
import tempfile
import subprocess
from typing import Optional, Tuple
from pathlib import Path
import wave
import json

try:
    import openai
except ImportError:
    openai = None
    
try:
    import pyaudio
except ImportError:
    pyaudio = None

from ..core.logging import get_logger

logger = get_logger(__name__)


class WhisperSTT:
    """Speech-to-Text using OpenAI Whisper."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "whisper-1",
        language: str = "en"
    ):
        """Initialize Whisper STT.
        
        Args:
            api_key: OpenAI API key
            model: Whisper model to use
            language: Language code for transcription
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required for Whisper STT")
        
        if not openai:
            raise ImportError("openai package required. Install with: pip install openai")
            
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        self.language = language
        self.recording = False
        
        # Check if we can record audio
        self.can_record = self._check_recording_support()
        
        logger.info(f"Initialized Whisper STT (model: {model}, language: {language})")
        if not self.can_record:
            logger.warning("Audio recording not supported - will use file input only")
    
    def _check_recording_support(self) -> bool:
        """Check if audio recording is supported."""
        if not pyaudio:
            return False
            
        try:
            p = pyaudio.PyAudio()
            p.terminate()
            return True
        except Exception:
            return False
    
    def record_audio(
        self,
        duration: Optional[float] = None,
        sample_rate: int = 16000,
        channels: int = 1
    ) -> Optional[str]:
        """Record audio from microphone.
        
        Args:
            duration: Recording duration in seconds (None for manual stop)
            sample_rate: Sample rate (16000 recommended for Whisper)
            channels: Number of channels (1 for mono)
            
        Returns:
            Path to recorded audio file, or None if failed
        """
        if not self.can_record:
            logger.error("Audio recording not supported")
            return None
            
        try:
            p = pyaudio.PyAudio()
            
            # Find default input device
            device_info = p.get_default_input_device_info()
            logger.info(f"Recording from: {device_info['name']}")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                audio_file = tmp.name
            
            # Open stream
            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=1024
            )
            
            logger.info("🎤 Recording... (press Ctrl+C to stop)")
            frames = []
            self.recording = True
            
            try:
                if duration:
                    # Record for fixed duration
                    for _ in range(0, int(sample_rate / 1024 * duration)):
                        if not self.recording:
                            break
                        data = stream.read(1024, exception_on_overflow=False)
                        frames.append(data)
                else:
                    # Record until interrupted
                    while self.recording:
                        data = stream.read(1024, exception_on_overflow=False)
                        frames.append(data)
                        
            except KeyboardInterrupt:
                logger.info("Recording stopped by user")
            finally:
                self.recording = False
                stream.stop_stream()
                stream.close()
                p.terminate()
            
            # Save audio
            with wave.open(audio_file, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(sample_rate)
                wf.writeframes(b''.join(frames))
            
            logger.info(f"Audio saved to: {audio_file}")
            return audio_file
            
        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None
    
    def stop_recording(self):
        """Stop ongoing recording."""
        self.recording = False
    
    def transcribe_file(self, audio_file: str, prompt: Optional[str] = None) -> Optional[str]:
        """Transcribe audio file using Whisper.
        
        Args:
            audio_file: Path to audio file
            prompt: Optional prompt to guide transcription
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            with open(audio_file, "rb") as f:
                logger.info(f"Transcribing {Path(audio_file).name}...")
                
                kwargs = {
                    "model": self.model,
                    "file": f,
                    "language": self.language
                }
                
                if prompt:
                    kwargs["prompt"] = prompt
                
                response = self.client.audio.transcriptions.create(**kwargs)
                
                text = response.text
                logger.info(f"Transcription: {text}")
                return text
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def record_and_transcribe(
        self,
        duration: Optional[float] = None,
        prompt: Optional[str] = None,
        keep_audio: bool = False
    ) -> Tuple[Optional[str], Optional[str]]:
        """Record audio and transcribe it.
        
        Args:
            duration: Recording duration (None for manual stop)
            prompt: Optional prompt for transcription
            keep_audio: Whether to keep the audio file
            
        Returns:
            Tuple of (transcribed_text, audio_file_path)
        """
        # Record audio
        audio_file = self.record_audio(duration)
        if not audio_file:
            return None, None
        
        # Transcribe
        text = self.transcribe_file(audio_file, prompt)
        
        # Clean up if requested
        if not keep_audio and audio_file and os.path.exists(audio_file):
            os.unlink(audio_file)
            audio_file = None
            
        return text, audio_file


class BrowserSTT:
    """Browser-based STT using Web Speech API."""
    
    @staticmethod
    def generate_html() -> str:
        """Generate HTML/JS for browser-based STT."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Voice Input</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #1a1a1a;
            color: #fff;
        }
        .mic-button {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: none;
            background: #4a5568;
            color: white;
            font-size: 40px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .mic-button:hover {
            background: #5a6578;
        }
        .mic-button.recording {
            background: #ef4444;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        #transcript {
            margin-top: 20px;
            padding: 20px;
            background: #2a2a2a;
            border-radius: 8px;
            min-height: 100px;
        }
        .status {
            margin-top: 10px;
            font-size: 14px;
            color: #888;
        }
    </style>
</head>
<body>
    <h1>🎤 Voice Input</h1>
    <button id="micButton" class="mic-button">🎤</button>
    <div class="status" id="status">Click microphone to start</div>
    <div id="transcript"></div>
    
    <script>
        const micButton = document.getElementById('micButton');
        const status = document.getElementById('status');
        const transcript = document.getElementById('transcript');
        
        let recognition = null;
        let isRecording = false;
        
        // Check browser support
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {
                isRecording = true;
                micButton.classList.add('recording');
                status.textContent = 'Listening...';
            };
            
            recognition.onend = () => {
                isRecording = false;
                micButton.classList.remove('recording');
                status.textContent = 'Click microphone to start';
            };
            
            recognition.onresult = (event) => {
                let finalTranscript = '';
                let interimTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const result = event.results[i];
                    if (result.isFinal) {
                        finalTranscript += result[0].transcript + ' ';
                    } else {
                        interimTranscript += result[0].transcript;
                    }
                }
                
                transcript.innerHTML = 
                    '<strong>Final:</strong> ' + finalTranscript + '<br>' +
                    '<em>Listening:</em> ' + interimTranscript;
                
                // Send to parent window or API
                if (finalTranscript) {
                    window.parent.postMessage({
                        type: 'speech',
                        text: finalTranscript.trim()
                    }, '*');
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                status.textContent = 'Error: ' + event.error;
                isRecording = false;
                micButton.classList.remove('recording');
            };
            
        } else {
            status.textContent = 'Speech recognition not supported in this browser';
            micButton.disabled = true;
        }
        
        micButton.addEventListener('click', () => {
            if (!recognition) return;
            
            if (isRecording) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
    </script>
</body>
</html>
"""


# Test function
async def test_whisper():
    """Test Whisper STT functionality."""
    print("🎤 Testing Whisper STT")
    print("=" * 50)
    
    try:
        stt = WhisperSTT()
        print(f"✅ Whisper STT initialized")
        print(f"   Can record: {stt.can_record}")
        
        if stt.can_record:
            print("\nPress Enter to start recording (5 seconds)...")
            input()
            
            text, audio_file = stt.record_and_transcribe(
                duration=5,
                keep_audio=True
            )
            
            if text:
                print(f"\n✅ Transcription: {text}")
                if audio_file:
                    print(f"   Audio saved: {audio_file}")
            else:
                print("❌ Transcription failed")
        else:
            print("\n⚠️  Audio recording not available")
            print("   Install pyaudio: pip install pyaudio")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_whisper())