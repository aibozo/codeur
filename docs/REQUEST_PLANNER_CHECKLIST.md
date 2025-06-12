# Request Planner Implementation Checklist

Based on the specification in `request_planner.txt`, here's what needs to be implemented:

## 1. Protocol Buffers & Messaging ❌

### Required Protobuf Definitions
```proto
message ChangeRequest {
  string id              = 1;
  string requester       = 2;
  string repo            = 3;
  string branch          = 4;
  string description_md  = 5;
  repeated FileDelta deltas = 6;
}

message Plan {
  string id                  = 1;
  string parent_request_id   = 2;
  repeated Step steps        = 3;
  repeated string rationale  = 4;
  repeated string affected_paths = 5;
  string complexity_label    = 6;
  int32 estimated_tokens     = 7;
  string created_by_sha      = 8;
}

message Step {
  int32 order           = 1;
  string goal           = 2;
  StepKind kind         = 3;
  repeated string hints = 4;
}
```

### Tasks:
- [ ] Install protobuf compiler
- [ ] Create proto definitions in `src/proto/`
- [ ] Generate Python bindings
- [ ] Replace dataclasses with protobuf messages

## 2. gRPC Service Integration ❌

### Required Services
1. **RAG Service**
   - `HybridSearch(query, k, alpha, filter)`
   - `Snippet(id, radius)`

2. **Git Adapter**
   - `Diff(request_sha)`
   - `ReadFile(path)`

3. **Orchestrator**
   - `Emit(Plan)`

### Tasks:
- [ ] Create gRPC client stubs
- [ ] Implement service interfaces
- [ ] Add connection management
- [ ] Add retry logic for service calls

## 3. LLM Integration (OpenAI) ❌

### Required Implementation
```python
SYSTEM = """You are Request‑Planner v1. Turn a software change request into a numbered
action plan for downstream agents. Think step‑by‑step but OUTPUT ONLY JSON
conforming to Plan schema."""

# Few-shot examples needed:
# - Bug fix example
# - Feature add example  
# - Refactor example
```

### Tasks:
- [ ] Add OpenAI client initialization
- [ ] Implement prompt templates
- [ ] Add few-shot examples
- [ ] Implement function calling for JSON output
- [ ] Add chain-of-thought reasoning
- [ ] Implement retry logic for LLM failures

## 4. Context Retrieval Enhancement ❌

### Current vs Required
- Current: Simple file search
- Required: RAG hybrid search with k=40, alpha=0.25

### Tasks:
- [ ] Replace simple search with RAG client calls
- [ ] Implement snippet extraction with radius
- [ ] Add repository filtering
- [ ] Format snippets for prompt context

## 5. Complexity Scoring ❌

### Required Algorithm
```python
# Heuristic based on:
- len(steps)
- max(diff LOC)  
- cross-file edges via networkx dependency DAG
```

### Tasks:
- [ ] Install networkx
- [ ] Build dependency graph from affected files
- [ ] Calculate complexity metrics
- [ ] Map to complexity labels

## 6. Self-Verification Pass ❌

### Required "Reflection" Logic
```python
# Re-ask model: "Does each step map to at least one affected_path?"
# Retry up to 2x on FALSE
```

### Tasks:
- [ ] Implement verification prompt
- [ ] Add retry mechanism
- [ ] Track verification attempts

## 7. Message Queue Integration ❌

### Required Behavior
- Receive from `plan.in` topic
- Emit to Orchestrator queue
- Handle dead letter queue

### Tasks:
- [ ] Add Kafka/AMQP client (or in-memory for MVP)
- [ ] Implement message consumer
- [ ] Add message producer for Plan emission
- [ ] Handle acknowledgments

## 8. Observability & Metrics ❌

### Required Metrics
```python
# Prometheus metrics:
- plan_steps_count
- plan_latency_ms
- rag_docs_used
- llm_tokens_used
```

### Tasks:
- [ ] Install prometheus_client
- [ ] Add metric collectors
- [ ] Instrument key operations
- [ ] Add OpenTelemetry tracing

## 9. Error Handling ❌

### Required Strategies
| Failure | Strategy | Max Attempts |
|---------|----------|--------------|
| RAG timeout | Fall back to BM25 | 1 |
| LLM 5xx | Exponential backoff | 3 |
| Schema validation | Re-prompt | 2 |
| Emit failure | Dead letter queue | n/a |

### Tasks:
- [ ] Implement timeout handling
- [ ] Add exponential backoff
- [ ] Add schema validation with retry
- [ ] Implement dead letter queue

## 10. Security & Policy ❌

### Required Features
- Strip secrets (API_KEY, PASSWORD, PEM headers)
- Read-only Git clone
- Network egress restrictions
- License tag preservation

### Tasks:
- [ ] Add secret detection regex
- [ ] Implement content sanitization
- [ ] Add license detection
- [ ] Enforce read-only operations

## 11. Containerization ❌

### Required Setup
- Base image: `python:3.11-slim`
- Additional: `git`, `openssh-client`
- K8s Job configuration

### Tasks:
- [ ] Create Dockerfile
- [ ] Add K8s manifests
- [ ] Configure resource limits
- [ ] Add health checks

## 12. Testing ❌

### Required Coverage
- 93% branch coverage target
- Fixtures for mini Git repos
- E2E testing framework

### Tasks:
- [ ] Create test fixtures
- [ ] Add unit tests for each component
- [ ] Add integration tests
- [ ] Add E2E test harness

## Implementation Priority

### MVP Phase 1 (Make it work)
1. LLM Integration with OpenAI
2. Basic message queue (in-memory)
3. Enhanced context retrieval
4. Error handling basics

### MVP Phase 2 (Make it right)
5. Protobuf integration
6. Proper RAG service client
7. Git adapter
8. Metrics collection

### Production Phase (Make it scale)
9. Full gRPC services
10. Kafka integration
11. Containerization
12. Complete test coverage

## Current Implementation Gaps

### High Priority
- **No LLM**: Using heuristics instead of AI
- **No Message Queue**: Direct function calls
- **No Git Integration**: File system access only
- **No Metrics**: No observability

### Medium Priority  
- **No Protobuf**: Using Python dataclasses
- **No gRPC**: No service communication
- **No Complexity Analysis**: Simple heuristics
- **No Verification**: No self-checking

### Low Priority (for MVP)
- **No Container**: Running directly
- **No Kafka**: Can use in-memory queue
- **Full RAG**: Simple search works for MVP