#!/usr/bin/env python3
"""
Test voice streaming using WebSocket approach (mimicking GitHub example).
"""

import asyncio
import base64
import json
import os
import pyaudio
from websockets.asyncio.client import connect
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

# Set PulseAudio
if not os.environ.get("PULSE_SERVER"):
    os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"


class GeminiVoiceAssistant:
    def __init__(self):
        self._audio_queue = asyncio.Queue()
        self._api_key = os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY not set")
        self._model = "gemini-2.0-flash-exp"
        self._uri = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={self._api_key}"
        # Audio settings
        self._FORMAT = pyaudio.paInt16
        self._CHANNELS = 1
        self._CHUNK = 512
        self._RATE = 16000

    async def _connect_to_gemini(self):
        print("🔌 Connecting to Gemini WebSocket...")
        return await connect(
            self._uri, additional_headers={"Content-Type": "application/json"}
        )

    async def _start_audio_streaming(self):
        print("🎤 Starting audio streaming...")
        try:
            # Python 3.11+ TaskGroup
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._capture_audio())
                tg.create_task(self._stream_audio())
                tg.create_task(self._play_response())
        except AttributeError:
            # Python 3.10 fallback
            await asyncio.gather(
                self._capture_audio(),
                self._stream_audio(),
                self._play_response()
            )

    async def _capture_audio(self):
        print("🎤 Starting audio capture...")
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self._FORMAT,
            channels=self._CHANNELS,
            rate=self._RATE,
            input=True,
            frames_per_buffer=self._CHUNK,
        )

        chunk_count = 0
        while True:
            try:
                data = await asyncio.to_thread(stream.read, self._CHUNK)
                chunk_count += 1
                
                # Show activity every 100 chunks (~3 seconds)
                if chunk_count % 100 == 0:
                    print(f"📊 Sent {chunk_count} audio chunks")
                
                await self._ws.send(
                    json.dumps(
                        {
                            "realtime_input": {
                                "media_chunks": [
                                    {
                                        "data": base64.b64encode(data).decode(),
                                        "mime_type": "audio/pcm",
                                    }
                                ]
                            }
                        }
                    )
                )
            except Exception as e:
                print(f"❌ Capture error: {e}")
                break

    async def _stream_audio(self):
        print("👂 Listening for responses...")
        response_count = 0
        async for msg in self._ws:
            response = json.loads(msg)
            try:
                audio_data = response["serverContent"]["modelTurn"]["parts"][0][
                    "inlineData"
                ]["data"]
                self._audio_queue.put_nowait(base64.b64decode(audio_data))
                response_count += 1
                print(f"🔊 Response {response_count}: Received audio data")
            except KeyError:
                pass
            
            # Check for text responses
            try:
                text = response["serverContent"]["modelTurn"]["parts"][0]["text"]
                print(f"📝 Text: {text}")
            except KeyError:
                pass
            
            try:
                turn_complete = response["serverContent"]["turnComplete"]
            except KeyError:
                pass
            else:
                if turn_complete:
                    # If you interrupt the model, it sends an end_of_turn. For interruptions to work, we need to empty out the audio queue
                    print("\n✅ End of turn")
                    while not self._audio_queue.empty():
                        self._audio_queue.get_nowait()

    async def _play_response(self):
        print("🔊 Ready to play responses...")
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self._FORMAT, 
            channels=self._CHANNELS, 
            rate=24000,  # Output at 24kHz
            output=True
        )
        play_count = 0
        while True:
            data = await self._audio_queue.get()
            play_count += 1
            print(f"🎵 Playing chunk {play_count}")
            await asyncio.to_thread(stream.write, data)

    async def start(self):
        self._ws = await self._connect_to_gemini()
        print("✅ Connected!")
        
        # Send setup
        setup_msg = {"setup": {"model": f"models/{self._model}"}}
        print(f"📤 Sending setup: {setup_msg}")
        await self._ws.send(json.dumps(setup_msg))
        
        # Wait for setup response
        setup_response = await self._ws.recv()
        print(f"📥 Setup response received: {len(setup_response)} bytes")
        
        print("\n✅ Connected to Gemini, You can start talking now")
        print("🎤 Speak clearly and wait for response\n")
        
        await self._start_audio_streaming()


async def main():
    print("🎵 GEMINI VOICE ASSISTANT (WebSocket Method)")
    print("=" * 50)
    print("Using exact approach from GitHub example")
    print("Press Ctrl+C to stop\n")
    
    client = GeminiVoiceAssistant()
    try:
        await client.start()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())