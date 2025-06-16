# Context-Aware Architect

The Context-Aware Architect extends the base Architect agent with intelligent conversation management using the Context Graph system. This integration provides:

- **Reduced token usage** through intelligent summarization
- **Better context retention** across long conversations
- **Task-based organization** of conversation history
- **Configurable compression modes** for different use cases

## Features

### 1. Intelligent Context Management

The Context-Aware Architect uses a graph-based approach to manage conversation history:

```python
from src.architect.context_aware_architect import create_context_aware_architect

# Create architect with balanced compression
architect = create_context_aware_architect(
    project_path="./my_project",
    mode="balanced"  # Options: "aggressive", "balanced", "rich"
)
```

### 2. Conversation Processing

Process messages with automatic context optimization:

```python
# Simple message
response = await architect.process_message(
    "I want to build a web API"
)

# With task context and phase
response = await architect.process_message(
    "How should I structure the database?",
    task_ids=["API-001", "DB-001"],
    phase=ConversationPhase.PLANNING,
    importance=0.8  # Higher importance for critical decisions
)
```

### 3. Context Compression Modes

Three modes are available for different scenarios:

#### Aggressive Mode
- Maximum compression for very long conversations
- Keeps only 3 recent messages in full
- Aggressively summarizes older content
- Best for: Extended development sessions

```python
architect.switch_context_mode("aggressive")
```

#### Balanced Mode (Default)
- Moderate compression with good context retention
- Keeps 5 recent messages in full
- Gradual summarization of older content
- Best for: Most use cases

```python
architect.switch_context_mode("balanced")
```

#### Context Rich Mode
- Minimal compression for maximum detail
- Keeps 10 recent messages in full
- Preserves more historical context
- Best for: Complex architectural discussions

```python
architect.switch_context_mode("rich")
```

### 4. Task-Based Organization

Messages are automatically organized by associated tasks:

```python
# Messages tagged with task IDs are grouped
await architect.process_message(
    "Let's implement user authentication",
    task_ids=["AUTH-001"]
)

# Multiple tasks can be associated
await architect.process_message(
    "Connect auth to the database layer",
    task_ids=["AUTH-001", "DB-001"]
)
```

### 5. Semantic Checkpoints

Create checkpoints for important moments:

```python
# Create a checkpoint after key decisions
checkpoint_id = await architect.create_checkpoint(
    title="Architecture Design Complete",
    checkpoint_type="milestone",
    message_count=10  # Include last 10 messages
)
```

### 6. Conversation Persistence

Save and restore conversation state:

```python
# Save current conversation
state_file = await architect.save_conversation_state()

# Later, restore the conversation
new_architect = create_context_aware_architect(
    project_path="./my_project"
)
await new_architect.load_conversation_state()
```

## Architecture

### Components

1. **Context Graph**: Manages conversation as a directed graph
2. **Context Summarizer**: Creates intelligent summaries of old messages
3. **Context Compiler**: Assembles optimized context windows
4. **Resolution Strategies**: Determine visibility of messages

### Message Resolution Levels

Messages are displayed at different resolution levels based on distance and importance:

- **FULL**: Complete message content
- **SUMMARY**: Condensed version (~50 tokens)
- **TITLE**: Brief description (~10 tokens)
- **HIDDEN**: Not included in context

### Automatic Summarization

The system automatically summarizes older messages to stay within token budgets:

1. Messages beyond the "full context distance" are candidates for summarization
2. Summarization runs in the background after a delay
3. Summaries preserve key information while reducing tokens by ~70%

## Usage Examples

### Basic Project Discussion

```python
architect = create_context_aware_architect("./project", mode="balanced")

# Initial requirements
await architect.process_message(
    "I need a real-time chat application with video calling"
)

# Architecture planning
await architect.process_message(
    "What's the best architecture for real-time features?",
    phase=ConversationPhase.PLANNING
)

# Implementation details
await architect.process_message(
    "Create tasks for building the WebRTC integration",
    task_ids=["CHAT-001", "VIDEO-001"],
    phase=ConversationPhase.IMPLEMENTATION
)
```

### Long Development Session

```python
# Use aggressive mode for extended conversations
architect = create_context_aware_architect("./project", mode="aggressive")

# Many implementation discussions...
for feature in features:
    await architect.process_message(
        f"How do I implement {feature}?",
        task_ids=[f"{feature}-001"]
    )

# Check compression stats
stats = architect.get_conversation_stats()
print(f"Compressed {stats['summarized_nodes']} messages")
print(f"Saved {stats['compression_ratio']:.0%} tokens")
```

### Complex Architecture Review

```python
# Use rich mode for detailed discussions
architect = create_context_aware_architect("./project", mode="rich")

# Detailed architecture review
await architect.process_message(
    "Let's review the microservices architecture",
    phase=ConversationPhase.REVIEW,
    importance=0.9
)

# Create checkpoint after decisions
checkpoint = await architect.create_checkpoint(
    "Architecture Review Complete",
    checkpoint_type="decision"
)
```

## Performance Characteristics

### Token Usage

Typical token usage with different modes:

| Mode | 10 msgs | 50 msgs | 100 msgs | 500 msgs |
|------|---------|---------|----------|----------|
| Rich | ~2000 | ~8000 | ~15000 | ~25000 |
| Balanced | ~1500 | ~4000 | ~6000 | ~10000 |
| Aggressive | ~1000 | ~2000 | ~3000 | ~5000 |

### Summarization Costs

Using GPT-4o-mini for summarization:
- Cost: ~$0.001 per 10 messages summarized
- Compression: ~70% token reduction
- Quality: Preserves key decisions and context

## Best Practices

1. **Use appropriate modes**: 
   - Start with balanced mode
   - Switch to aggressive for very long sessions
   - Use rich mode for critical discussions

2. **Tag messages with tasks**:
   - Always provide task_ids for better organization
   - Use multiple task_ids for cross-cutting concerns

3. **Create checkpoints**:
   - After major decisions
   - Before switching topics
   - At natural break points

4. **Monitor compression**:
   - Check stats regularly with `get_conversation_stats()`
   - Adjust mode if needed

5. **Save state periodically**:
   - For long projects
   - Before major changes
   - At session end

## Integration with Enhanced Task Graph

The Context-Aware Architect seamlessly integrates with the enhanced task graph system:

```python
# Task creation is context-aware
response = await architect.process_message(
    "Create tasks for building the authentication system"
)

# The architect remembers previous discussions
response = await architect.process_message(
    "Update the auth tasks based on our earlier database decisions"
)
```

## Troubleshooting

### High Token Usage
- Switch to aggressive mode
- Create checkpoints to mark completed topics
- Check if important messages are being preserved

### Lost Context
- Ensure important messages have high importance scores
- Use checkpoints for critical decisions
- Consider using rich mode for complex topics

### Slow Summarization
- Summarization runs in background
- Check `get_conversation_stats()` for progress
- Force summarization with `context_summarizer.summarize_old_nodes(force=True)`