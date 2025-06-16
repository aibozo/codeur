# Voice Agent for Codebase Exploration

The Voice Agent provides natural language voice interaction with your codebase, allowing developers to ask questions and get spoken answers about code structure, functionality, and implementation details.

## Features

### Core Capabilities
- **Speech-to-Text**: Convert spoken questions into text queries
- **RAG-Powered Responses**: Leverage the codebase's RAG system for accurate, context-aware answers
- **Text-to-Speech**: Convert responses back to natural speech
- **Streaming Support**: Real-time audio streaming for interactive conversations
- **Session Management**: Maintain conversation context across multiple queries

### Query Types Supported
1. **Function Explanations**: "Explain the function `search_code` in the RAG service"
2. **Implementation Search**: "Where is the `EventBridge` class implemented?"
3. **File Analysis**: "What does the `voice_agent.py` file do?"
4. **Architecture Questions**: "How does the WebSocket system work?"
5. **Usage Finding**: "Where is `TaskGraphManager` used in the codebase?"
6. **Code Listings**: "List all functions in the `audio_interfaces.py` file"

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Audio Input   │────▶│   Voice Agent    │────▶│  Audio Output   │
│  (Speech-to-Text)     │                    │     │ (Text-to-Speech)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   RAG Service    │
                        │ (Adaptive Search) │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │    Codebase      │
                        │   Knowledge      │
                        └──────────────────┘
```

## Components

### 1. Audio Interfaces (`audio_interfaces.py`)
Abstract interfaces and implementations for audio processing:
- `AudioInput`: Speech-to-text interface
- `AudioOutput`: Text-to-speech interface
- `OpenAIAudioInput/Output`: OpenAI Whisper and TTS implementations
- `MockAudioInput/Output`: Testing implementations

### 2. Voice Agent (`voice_agent.py`)
Core voice processing logic:
- Intent detection from natural language
- Context-aware query processing
- Response generation with code references
- Session and conversation management

### 3. Integrated Voice Agent (`integrated_voice_agent.py`)
Integration with the agent system:
- Task graph integration for complex queries
- Event system for real-time updates
- Collaboration with other agents
- WebSocket support for streaming

### 4. WebSocket Handler (`voice_websocket.py`)
Real-time voice interaction via WebSocket:
- Streaming audio input/output
- Low-latency responses
- Session persistence
- Binary audio data handling

### 5. REST API (`voice_api.py`)
HTTP endpoints for voice interaction:
- Session management
- File upload for audio
- Text-based queries
- Command execution

## Usage Examples

### Basic Voice Agent
```python
from src.voice_agent import VoiceAgent
from src.voice_agent.audio_interfaces import OpenAIAudioInput, OpenAIAudioOutput
from src.rag_service.adaptive_rag_service import AdaptiveRAGService

# Initialize components
rag_service = AdaptiveRAGService(
    persist_directory=".rag",
    repo_path=".",
    enable_adaptive_gating=True
)

audio_input = OpenAIAudioInput(api_key="your-key")
audio_output = OpenAIAudioOutput(api_key="your-key")

# Create voice agent
voice_agent = VoiceAgent(
    rag_service=rag_service,
    audio_input=audio_input,
    audio_output=audio_output,
    project_path=Path(".")
)

# Process a voice query
response = await voice_agent.process_text(
    "What does the EventBridge class do?",
    session_id="my_session"
)
print(response.text)
```

### Integrated Voice Agent
```python
from src.voice_agent import IntegratedVoiceAgent
from src.core.integrated_agent_base import AgentContext

# Create agent context
context = AgentContext(
    project_path=Path("."),
    event_bridge=event_bridge,
    rag_client=rag_client,
    agent_id="voice_001"
)

# Create integrated agent
voice_agent = IntegratedVoiceAgent(
    context=context,
    audio_input=audio_input,
    audio_output=audio_output
)

# Start a session
session = await voice_agent.start_voice_session(
    "user_session",
    user_preferences={"voice": "nova"}
)

# Process voice input
audio_data = load_audio_file("question.wav")
response = await voice_agent.process_voice_input(
    "user_session",
    audio_data
)
```

### WebSocket Streaming
```javascript
// Client-side WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws/voice');

ws.onopen = () => {
    console.log('Voice connection established');
};

// Send audio chunk
ws.send(JSON.stringify({
    type: 'audio_chunk',
    data: base64AudioData,
    is_final: false
}));

// Receive response
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'transcription') {
        console.log('You said:', msg.text);
    } else if (msg.type === 'audio_response') {
        playAudio(msg.data);
    }
};
```

## Configuration

### Environment Variables
```bash
# OpenAI API key for audio services
OPENAI_API_KEY=sk-...

# Voice preferences
VOICE_DEFAULT_MODEL=tts-1
VOICE_DEFAULT_VOICE=nova
VOICE_WHISPER_MODEL=whisper-1

# Audio settings
VOICE_SAMPLE_RATE=16000
VOICE_AUDIO_FORMAT=webm
```

### Voice Agent Settings
```python
voice_config = {
    "enable_streaming": True,
    "max_session_duration": 3600,  # 1 hour
    "audio_chunk_size": 4096,
    "transcription_language": "en",
    "response_format": "conversational"
}
```

## API Endpoints

### REST API
- `POST /api/voice/sessions` - Create voice session
- `DELETE /api/voice/sessions/{id}` - End session
- `POST /api/voice/text` - Process text input
- `POST /api/voice/audio` - Process audio file
- `GET /api/voice/capabilities` - Get agent capabilities

### WebSocket
- `ws://host/ws/voice` - Real-time voice interaction

## Advanced Features

### 1. Intent Detection
The voice agent automatically detects user intent:
- Function explanations
- Implementation searches
- Architecture questions
- Code navigation

### 2. Context Preservation
Sessions maintain context across queries:
- Recent topics
- Mentioned files and functions
- Conversation history

### 3. Adaptive Responses
Responses adapt based on:
- Query complexity
- Available context
- User preferences

### 4. Multi-Agent Collaboration
Voice agent can delegate to other agents:
- Complex implementations → Coding Agent
- Architecture questions → Analyzer
- Planning queries → Code Planner

## Security Considerations

1. **Audio Data**: Audio is processed in memory and not persisted by default
2. **Session Isolation**: Each session is isolated with its own context
3. **Code Execution**: Code execution is disabled by default for safety
4. **Authentication**: WebSocket and API endpoints support authentication

## Performance Optimization

1. **Streaming**: Use streaming for real-time interaction
2. **Chunk Size**: Optimize audio chunk size for latency
3. **RAG Caching**: Leverage adaptive RAG for faster responses
4. **Session Limits**: Configure appropriate session timeouts

## Troubleshooting

### Common Issues

1. **No Audio Output**
   - Check OpenAI API key
   - Verify audio format compatibility
   - Check TTS model availability

2. **Poor Transcription**
   - Ensure good audio quality
   - Check sample rate (16kHz recommended)
   - Verify language settings

3. **Slow Responses**
   - Check RAG indexing status
   - Optimize chunk retrieval count
   - Enable response streaming

## Future Enhancements

1. **Multi-language Support**: Extend beyond English
2. **Voice Cloning**: Custom voice synthesis
3. **Emotion Detection**: Detect frustration/confusion
4. **Code Generation**: Voice-driven code writing
5. **IDE Integration**: Direct IDE plugin support