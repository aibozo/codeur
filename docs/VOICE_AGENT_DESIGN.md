# Voice Agent Design and Implementation

## Overview

The Voice Agent provides natural language voice interaction with any codebase, leveraging the Gemini 2.5 Flash Native Audio Thinking model for intelligent responses. It integrates with the adaptive RAG system to provide accurate, context-aware answers about code structure, functionality, and implementation details.

## Architecture

### Core Components

1. **Audio Interfaces** (`audio_interfaces.py`)
   - Abstract interfaces for speech-to-text and text-to-speech
   - Implementations for OpenAI (Whisper/TTS) and mock testing
   - Streaming support for real-time interaction

2. **Voice Agent** (`voice_agent.py`)
   - Core voice processing logic
   - Intent detection and entity extraction
   - RAG integration for context retrieval
   - Session management for conversation continuity

3. **Integrated Voice Agent** (`integrated_voice_agent.py`)
   - Full system integration with task graphs and events
   - Multi-agent collaboration capabilities
   - Real-time notifications and updates

## Context Strategy

The voice agent uses a multi-layered context strategy to answer any question about the codebase:

### 1. Intent-Based Query Enhancement
The agent detects user intent and enhances queries accordingly:

```python
intent_patterns = {
    "explain_function": ["what does X do", "explain function X"],
    "find_implementation": ["where is X implemented"],
    "explain_file": ["what does file X do"],
    "architecture": ["how does the architecture work"],
    "find_usage": ["where is X used"],
    "debug_help": ["why is X failing"]
}
```

### 2. Adaptive RAG Integration
- Uses the adaptive RAG system with quality gating
- Retrieves top 10 most relevant context chunks
- Filters based on similarity scores and relevance

### 3. Session Context Management
- Maintains conversation history
- Tracks mentioned files and functions
- Provides context continuity across queries

### 4. Multi-Agent Collaboration
For complex queries, the voice agent can:
- Delegate to specialized agents (analyzer, coding agent, architect)
- Synthesize responses from multiple agents
- Create tasks for implementation requests

## Usage Examples

### Basic Usage
```bash
# Single query
agent voice "What does the EventBridge class do?"

# Interactive mode
agent voice --interactive

# With OpenAI audio (requires OpenAI API key)
agent voice --audio-input openai --audio-output openai

# With Gemini Live API (requires GEMINI_API_KEY)
agent voice --audio-input gemini-live
```

### Gemini Live API Setup
```bash
# Install dependencies
pip install google-genai pyaudio

# Set API key
export GEMINI_API_KEY=your-gemini-api-key

# Run with native audio
agent voice --audio-input gemini-live
```

### Query Types Supported

1. **Function Explanation**
   - "What does the process_request function do?"
   - "Explain how calculate_score works"

2. **Implementation Search**
   - "Where is the RAG service implemented?"
   - "Show me where authentication is handled"

3. **File Understanding**
   - "What's in the config.py file?"
   - "Explain the purpose of utils/helpers.py"

4. **Architecture Overview**
   - "How does the system architecture work?"
   - "Explain the overall design"

5. **Usage Discovery**
   - "Where is the logger class used?"
   - "What calls the validate function?"

6. **Debugging Help**
   - "Why is the test_auth failing?"
   - "Help me debug the connection error"

## Implementation Details

### Voice Processing Flow

1. **Audio Input** → Speech-to-Text
2. **Intent Detection** → Classify query type
3. **Query Enhancement** → Optimize for RAG search
4. **Context Retrieval** → Get relevant code chunks
5. **Response Generation** → Use Gemini thinking model
6. **Audio Output** → Text-to-Speech

### Session Management

Each session maintains:
- Conversation history
- Mentioned files and functions
- Context accumulation
- Duration tracking

### Integration Points

1. **RAG Service**: For code context retrieval
2. **Task Graph**: For creating implementation tasks
3. **Event System**: For real-time notifications
4. **Other Agents**: For specialized analysis

## Configuration

### Model Selection
The voice agent uses the Gemini 2.5 Flash Native Audio Thinking model:
- Model: `gemini-2.5-flash-exp-native-audio-thinking-dialog`
- Features: Native audio, thinking mode, 128K context
- Pricing: $0.15/1M input, $3.50/1M output (thinking mode)

### Audio Configuration
- **Input**: Whisper API for speech-to-text
- **Output**: OpenAI TTS for text-to-speech
- **Streaming**: Supported for real-time interaction

## Future Enhancements

1. **Live API Integration**
   - Direct audio streaming with Gemini Live API
   - Real-time conversational experience
   - Lower latency responses

2. **Voice Commands**
   - "Create a task to implement X"
   - "Show me the code for Y"
   - "Run tests for module Z"

3. **Proactive Assistance**
   - Monitor code changes
   - Suggest improvements via voice
   - Alert on test failures

4. **Multi-Modal Support**
   - Screen sharing for code review
   - Visual diagrams with voice explanation
   - IDE integration

## Best Practices

1. **Clear Queries**: Be specific about what you're looking for
2. **Context Building**: Reference previous discussions
3. **Intent Keywords**: Use clear action words (explain, find, show)
4. **Session Management**: Use consistent session IDs

## Implementation Notes

### Gemini Live API Integration
The voice agent uses Google's Gemini Live API for native audio streaming:

1. **Audio Configuration**:
   - Input: 16kHz, mono, PCM
   - Output: 24kHz, mono, PCM
   - Chunk size: 1024 frames

2. **Context Management**:
   - Initial context sent with codebase information
   - Dynamic context injection based on queries
   - RAG search results integrated into conversation

3. **Live Features**:
   - Real-time audio streaming
   - Interruption support
   - Thinking mode for complex queries
   - Context window compression

### Code Search Integration
When a user asks about code:

1. **Query Analysis**: Detect code-related intent
2. **RAG Search**: Search codebase for relevant chunks
3. **Context Injection**: Add search results to conversation
4. **Response Generation**: Use thinking mode to synthesize answer

## API Endpoints (Future)

### WebSocket API
```javascript
ws://localhost:8000/voice/stream
{
  "type": "audio",
  "data": "<base64_audio>",
  "session_id": "user_123"
}
```

### REST API
```bash
POST /voice/process
{
  "audio": "<base64_audio>",
  "session_id": "user_123",
  "format": "wav"
}
```

## Security Considerations

1. **Audio Privacy**: Audio is processed but not stored
2. **Session Isolation**: Each session is independent
3. **Code Access**: Respects project boundaries
4. **API Keys**: Secure storage of provider keys

## Performance Metrics

- **Intent Detection**: <100ms
- **RAG Retrieval**: 200-500ms
- **Response Generation**: 1-3s (with thinking)
- **Audio Processing**: 500ms-1s

The Voice Agent transforms how developers interact with codebases, making it as easy as having a conversation with an expert who knows every line of code.