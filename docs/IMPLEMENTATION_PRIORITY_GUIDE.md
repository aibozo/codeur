# Implementation Priority Guide

## Goal: Claude Code/Codex Style Agent

Since we want the Request Planner to function as a Claude Code/Codex style coding agent, here's the priority order to achieve that:

## Priority 1: LLM Integration (Make it Smart)

### Why First?
Without LLM, we just have a rule-based system. The intelligence comes from AI.

### Implementation Steps:

#### 1.1 Add OpenAI Integration
```python
# src/request_planner/llm.py
class LLMClient:
    def __init__(self):
        self.client = OpenAI()
    
    def create_plan(self, request: ChangeRequest) -> Plan:
        # Use function calling for structured output
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[system_prompt, user_prompt],
            functions=[plan_function_schema],
            function_call={"name": "create_plan"}
        )
```

#### 1.2 Implement Proper Prompts
```python
SYSTEM_PROMPT = """You are Request-Planner v1, a Claude Code/Codex style agent.
You help users by understanding their requests and creating detailed implementation plans.
Think step-by-step but OUTPUT ONLY structured JSON."""

# Add few-shot examples for:
- Bug fixes
- Feature additions  
- Refactoring
- Documentation
```

## Priority 2: Enhanced Context (Make it Aware)

### Why Second?
Good plans need good context. The agent needs to understand the codebase.

### Implementation Steps:

#### 2.1 Improve Code Search
```python
# Enhance src/request_planner/context.py
- Add semantic search capability
- Implement symbol extraction
- Add import/dependency tracking
- Cache frequently accessed files
```

#### 2.2 Add Code Understanding
```python
# New: src/request_planner/code_analyzer.py
- Parse function signatures
- Extract class hierarchies
- Identify patterns
- Track dependencies
```

## Priority 3: Interactive Features (Make it Useful)

### Why Third?
Claude Code style means being helpful and interactive.

### Implementation Steps:

#### 3.1 Add Conversational Abilities
```python
# Enhance CLI to support:
agent chat  # Interactive mode
agent explain "How does X work?"
agent suggest "Better way to do Y"
agent review "Check this code"
```

#### 3.2 Add Code Generation Preview
```python
# Show potential changes before executing
agent request --preview "Add logging"
# Shows diff preview without applying
```

## Priority 4: Task Execution (Make it Act)

### Why Fourth?
Once it can plan well, let it execute simple tasks.

### Implementation Steps:

#### 4.1 Add Simple Execution
```python
# src/request_planner/executor.py
- File modifications
- Simple refactoring
- Add imports/functions
- Basic error handling
```

#### 4.2 Add Verification
```python
# Verify changes are valid:
- Syntax checking
- Import validation
- Basic linting
```

## Priority 5: Monitoring & Feedback (Make it Transparent)

### Implementation Steps:

#### 5.1 Add Progress Tracking
```python
# Real-time status updates
- Task progress bars
- Step completion tracking
- Error reporting
- Success confirmation
```

#### 5.2 Add Result Reporting
```python
# Clear outcome communication
- What was changed
- Why it was changed
- Any issues encountered
- Next steps suggested
```

## MVP Feature Set (2 Weeks)

### Week 1: Core Intelligence
- [ ] OpenAI integration
- [ ] Basic prompt engineering
- [ ] Structured output parsing
- [ ] Context retrieval improvement
- [ ] Error handling for LLM

### Week 2: Usability
- [ ] Interactive chat mode
- [ ] Code explanation features
- [ ] Preview capabilities
- [ ] Basic execution
- [ ] Progress tracking

## Key Differences from Full Spec

### What We're Prioritizing (Claude Code Style)
1. **Conversational Interface** - Not just request/response
2. **Code Understanding** - Can explain and suggest
3. **Incremental Execution** - Show changes as we go
4. **User Guidance** - Help users formulate requests
5. **Learning Examples** - Show similar patterns

### What We're Deferring (Full Architecture)
1. **Message Queues** - Direct execution for now
2. **Protobuf/gRPC** - Use Python native
3. **Full RAG** - Enhanced search is enough
4. **Other Agents** - Focus on Request Planner
5. **Containerization** - Run locally first

## Success Metrics for MVP

### Functional Success
- Can understand natural language requests
- Generates accurate, detailed plans
- Provides helpful code context
- Executes simple changes correctly
- Gives clear feedback

### User Experience Success
- Feels like pair programming
- Provides helpful suggestions
- Explains its reasoning
- Handles errors gracefully
- Improves with feedback

## Implementation Checklist

### Immediate Next Steps (Today)
1. [ ] Create `llm.py` with OpenAI client
2. [ ] Add environment variable for API key
3. [ ] Implement basic prompt templates
4. [ ] Add function calling schema
5. [ ] Test with simple requests

### This Week
6. [ ] Enhance context retrieval
7. [ ] Add code analysis features
8. [ ] Implement chat mode
9. [ ] Add preview capability
10. [ ] Create execution framework

### Next Week
11. [ ] Add progress tracking
12. [ ] Implement verification
13. [ ] Add error recovery
14. [ ] Create test suite
15. [ ] Document usage patterns

## Example Usage (Target MVP)

```bash
# Basic request
$ agent request "Add error handling to the fetch_data function"
Understanding request... ✓
Analyzing codebase... ✓
Creating plan... ✓

I'll add error handling to fetch_data. Here's my plan:
1. Add try-catch block around the HTTP request
2. Add retry logic for transient failures  
3. Log errors with context
4. Return meaningful error to caller

Preview changes? [Y/n]: y
[shows diff]

Proceed? [Y/n]: y
Applying changes... ✓
Running validation... ✓
Changes complete! The function now handles network errors gracefully.

# Interactive mode
$ agent chat
Agent: Hi! I'm here to help with your code. What would you like to work on?
You: How does the authentication system work?
Agent: Let me analyze the authentication system...
[provides detailed explanation with code references]

You: Can we add rate limiting?
Agent: I can help add rate limiting. Here's what I suggest...
[shows implementation plan]
```

This approach gets us to a useful Claude Code style agent quickly while keeping the door open for the full architecture later.