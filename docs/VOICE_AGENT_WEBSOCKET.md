# Voice Agent WebSocket Implementation

## Overview

We've successfully implemented a WebSocket-based voice agent that works with Gemini's streaming API for natural voice conversations about your codebase.

## Key Features

### 1. **WebSocket Architecture**
- Uses raw WebSocket API instead of google-genai SDK
- Direct connection to: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent`
- Better control over audio streaming
- Proven to work with continuous audio streaming

### 2. **Audio Configuration**
- **Input**: 16-bit PCM, 16kHz mono (microphone)
- **Output**: 24kHz (Gemini responses)
- Chunk size: 512 bytes for low latency
- Base64 encoding for WebSocket transport

### 3. **Architecture Context**
- Automatically loads project architecture from:
  - `ARCHITECTURE.md`
  - `docs/ARCHITECTURE.md`
  - `README.md`
  - `.claude_docs/architecture.md`
- Falls back to auto-generated structure
- Provides context to Gemini about your project

### 4. **Dual Input Modes**
- **Voice**: Continuous audio streaming
- **Text**: Type messages while voice is active
- Seamless switching between modes

## Implementation Details

### WebSocket Message Format

**Audio Input**:
```json
{
  "realtime_input": {
    "media_chunks": [{
      "data": "<base64-encoded-audio>",
      "mime_type": "audio/pcm"
    }]
  }
}
```

**Text Input**:
```json
{
  "clientContent": {
    "turns": [{
      "role": "user",
      "parts": [{"text": "Your message here"}]
    }]
  }
}
```

### Current Limitations

1. **No Direct Tool Calling**: The WebSocket API doesn't support function calling in the setup
2. **Context-Based Responses**: The agent uses loaded architecture context to answer questions
3. **Manual Search**: Users need to ask specific questions about files/functions

## Usage

### CLI Command
```bash
agent voice
```

### Direct Python
```python
from src.voice_agent.gemini_native_audio_simple import WebSocketVoiceAgent

agent = WebSocketVoiceAgent(project_path=Path.cwd())
await agent.run()
```

## Future Enhancements

1. **Hybrid Approach**: Combine WebSocket for audio with REST API for tool calls
2. **Local Search Integration**: Pre-process queries locally and inject results
3. **RAG Integration**: Connect with existing RAG service for better code search
4. **Multi-Turn Context**: Maintain conversation history with code references

## Audio Flow

1. **Microphone** → PyAudio → 16kHz PCM → Base64 → WebSocket → **Gemini**
2. **Gemini** → WebSocket → Base64 → 24kHz PCM → PyAudio → **Speaker**

## Benefits Over SDK Approach

- ✅ Continuous audio streaming works perfectly
- ✅ Natural conversation flow with VAD
- ✅ Better control over message format
- ✅ Can handle interruptions properly
- ✅ Lower latency for audio responses