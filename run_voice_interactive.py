#!/usr/bin/env python3
"""
Interactive voice agent with proper audio streaming.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Suppress ALSA errors
from ctypes import *
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

# Set environment
if not os.environ.get("PULSE_SERVER"):
    os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"


async def run_interactive_voice_agent():
    """Run the voice agent interactively."""
    from src.voice_agent.gemini_native_audio_simple import SimplifiedNativeAudioAgent
    
    print("🎤 INTERACTIVE VOICE AGENT")
    print("=" * 50)
    print("Starting voice agent...")
    
    # Create agent
    agent = SimplifiedNativeAudioAgent(
        project_path=Path.cwd(),
        thinking_mode=False,
        voice_name="Zephyr"
    )
    
    # Run the full interactive agent
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(run_interactive_voice_agent())
    except KeyboardInterrupt:
        print("\n\n👋 Voice agent stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()