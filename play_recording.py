#!/usr/bin/env python3
"""
Play back the recorded audio file
"""

import pyaudio
import wave
import sys

def play_wav(filename):
    """Play a WAV file."""
    try:
        # Open the wav file
        wf = wave.open(filename, 'rb')
        
        # Create PyAudio instance
        p = pyaudio.PyAudio()
        
        # Open stream
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        
        print(f"Playing: {filename}")
        print(f"Duration: {wf.getnframes() / wf.getframerate():.1f} seconds")
        
        # Read and play chunks
        chunk_size = 1024
        data = wf.readframes(chunk_size)
        
        while data:
            stream.write(data)
            data = wf.readframes(chunk_size)
        
        # Clean up
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        print("✅ Playback complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else "test_recording_1.wav"
    play_wav(filename)