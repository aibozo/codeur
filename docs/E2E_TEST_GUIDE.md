# End-to-End Integration Test Guide

This guide explains the comprehensive E2E test suite that validates the entire agent system integration.

## Overview

The E2E test suite (`tests/test_e2e_full_integration.py`) tests the complete integration of all major components:

- **Request Processing**: Natural language → structured tasks → code changes
- **Agent Coordination**: Multi-agent communication and task execution
- **RAG Integration**: Adaptive similarity gating with quality critique
- **Task Management**: Hierarchical task graphs with dependencies
- **Event System**: Asynchronous message passing and event handling
- **LLM Integration**: Real API calls with structured outputs
- **Git Operations**: Branch creation, commits, and validation

## Test Structure

### Test Environment Setup

The `E2ETestEnvironment` class creates an isolated test environment:

```python
- Temporary git repository
- Sample project structure (calculator)
- Initialized agent system
- RAG indexing
- Event monitoring
```

### Test Categories

1. **Simple Flow Tests**
   - `test_simple_feature_request_flow`: Basic request → task creation
   - `test_coding_agent_implementation`: Direct coding task execution

2. **Integration Tests**
   - `test_architect_conversation_flow`: Context graph and conversation management
   - `test_adaptive_rag_integration`: Adaptive filtering and quality metrics
   - `test_message_bus_communication`: Inter-agent messaging

3. **Component Tests**
   - `test_analyzer_architecture_detection`: Architecture analysis
   - `test_context_quality_critique`: Context quality assessment
   - `test_task_graph_hierarchy`: Hierarchical task management

4. **Full System Tests**
   - `test_webhook_integration`: External webhook processing
   - `test_full_request_to_commit_flow`: Complete end-to-end flow

## Running the Tests

### Basic Usage

```bash
# Run all E2E tests with mocked LLM
python run_e2e_tests.py

# Run with real LLM calls (requires API keys)
python run_e2e_tests.py --with-llm

# Run fast tests only
python run_e2e_tests.py --fast

# Run with coverage report
python run_e2e_tests.py --coverage --verbose
```

### Direct pytest Usage

```bash
# Run specific test
pytest tests/test_e2e_full_integration.py::TestFullE2EIntegration::test_simple_feature_request_flow -v

# Run with markers
pytest tests/test_e2e_full_integration.py -m "not slow" -v

# Run with specific log level
pytest tests/test_e2e_full_integration.py --log-cli-level=DEBUG
```

## Configuration

### Environment Variables

The test suite uses `.env.test` for test-specific configuration:

```bash
# Logging
AGENT_LOG_LEVEL=DEBUG
AGENT_DEBUG=true

# Use in-memory backends
AGENT_MESSAGING_BACKEND=memory
AGENT_CACHE_BACKEND=memory

# Adaptive RAG
USE_ADAPTIVE_RAG=true
ADAPTIVE_RATE=0.5  # Faster for tests

# Cost limits
AGENT_MAX_COST_PER_SESSION=1.00
```

### API Keys

For real LLM testing, configure API keys in `.env`:

```bash
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
```

## Test Scenarios

### 1. Simple Feature Request

```python
request = "Add a divide method to the Calculator class that handles division by zero"
```

**Validates**:
- Request parsing and understanding
- RAG search for relevant code
- Task creation with proper structure
- Event generation

### 2. Coding Implementation

```python
task = {
    "type": "coding",
    "description": "Add divide method to Calculator class",
    "goals": ["Add divide(a, b) method", "Handle division by zero"]
}
```

**Validates**:
- Code generation
- File modification
- Git operations
- Validation pipeline

### 3. Complex Multi-Task Flow

```python
request = """Add the following features:
1. A power method that calculates a^b
2. A square root method that handles negative numbers
3. Add comprehensive tests for both methods"""
```

**Validates**:
- Multi-task planning
- Task dependencies
- Multiple file changes
- Test generation

## Debugging Tests

### Enable Debug Logging

```python
# In test file
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via pytest
pytest -v --log-cli-level=DEBUG
```

### Inspect Events

```python
# In test
env.clear_events()
# ... run operation ...
events = env.get_events_by_type("task.created")
for event in events:
    print(json.dumps(event, indent=2))
```

### Check Git State

```python
# In test
commits = list(env.repo.iter_commits())
for commit in commits:
    print(f"Commit: {commit.hexsha[:7]} - {commit.message}")
    print(f"Files: {commit.stats.files}")
```

## Common Issues

### 1. LLM Timeout

**Problem**: Tests timeout waiting for LLM response
**Solution**: Increase timeout or use mocked responses

```bash
# Increase timeout
export AGENT_LLM_REQUEST_TIMEOUT_SECONDS=60
```

### 2. Missing Dependencies

**Problem**: Import errors for test dependencies
**Solution**: Install test requirements

```bash
pip install pytest pytest-asyncio pytest-timeout pytest-cov
```

### 3. Git Operations Fail

**Problem**: Git commands fail in test environment
**Solution**: Ensure git is configured

```bash
git config --global user.email "test@example.com"
git config --global user.name "Test User"
```

### 4. RAG Indexing Slow

**Problem**: Initial indexing takes too long
**Solution**: Use smaller test project or mock RAG

## Test Coverage

The test suite aims for comprehensive coverage:

- **Request Planning**: 90%+ coverage
- **Agent Integration**: 85%+ coverage
- **RAG Service**: 80%+ coverage
- **Event System**: 95%+ coverage
- **Git Operations**: 90%+ coverage

Generate coverage report:

```bash
python run_e2e_tests.py --coverage
# View HTML report
open htmlcov/index.html
```

## Adding New Tests

### Test Template

```python
@pytest.mark.asyncio
async def test_new_feature(self, env):
    """Test description."""
    # Clear events for isolation
    env.clear_events()
    
    # Setup test data
    # ...
    
    # Execute operation
    # ...
    
    # Verify results
    assert expected_condition
    
    # Verify events
    events = env.get_events_by_type("expected.event")
    assert len(events) > 0
```

### Best Practices

1. **Isolation**: Clear events between tests
2. **Assertions**: Check both results and side effects
3. **Events**: Verify expected events were published
4. **Cleanup**: Test environment handles cleanup automatically
5. **Timeouts**: Use appropriate timeouts for async operations

## Performance Considerations

### Speed Optimization

- Use `--fast` flag to skip slow tests
- Mock LLM calls when possible
- Use in-memory backends
- Parallelize independent tests

### Resource Usage

- Tests create temporary directories
- Each test uses ~50-100MB memory
- LLM calls can be expensive
- Clean up happens automatically

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run E2E tests
        run: python run_e2e_tests.py --fast
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Monitoring Test Health

### Key Metrics

1. **Test Duration**: Should complete in <5 minutes
2. **Flakiness**: Track intermittent failures
3. **Coverage**: Maintain >80% coverage
4. **API Usage**: Monitor LLM API costs

### Regular Maintenance

- Update test data monthly
- Review flaky tests weekly
- Update mocks for API changes
- Verify against production scenarios