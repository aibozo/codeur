# End-to-End Test Plan for Agent System

## Overview
This comprehensive test plan verifies that all agents are properly integrated with:
- LLM tool calls
- RAG (Retrieval-Augmented Generation) service
- Event system
- Change tracking
- Architecture analysis

## Test Environment Setup

### Prerequisites
1. OpenAI API key configured in `.env`
2. Test repository initialized
3. All services running (frontend, backend, RAG)
4. Sample codebase for testing

### Test Repository Structure
```
test_project/
├── src/
│   ├── api/
│   │   ├── server.py
│   │   └── routes.py
│   ├── models/
│   │   ├── user.py
│   │   └── product.py
│   └── utils/
│       └── helpers.py
├── tests/
│   └── test_api.py
└── README.md
```

## Test Scenarios

### 1. Frontend to Backend Integration

#### Test 1.1: Project Initialization
**Steps:**
1. Open frontend at http://localhost:5173
2. Navigate to Build page
3. Click Browse and select test_project directory
4. Verify project status changes: "No Initialized Project" → "Initializing..." → "Project Initialized"

**Expected Results:**
- RAG indexing completes successfully
- Project directory is sandboxed
- Status indicator shows green/positive state
- Backend logs show successful initialization

#### Test 1.2: Directory Sandboxing
**Steps:**
1. After initialization, try to browse parent directories
2. Attempt to select directories outside project root

**Expected Results:**
- Cannot navigate above project root
- Security manager blocks access to parent directories
- Error messages are user-friendly

### 2. Architect Agent Testing

#### Test 2.1: Basic Architecture Design
**Steps:**
1. In Build page chat, send: "Design a REST API for user management with authentication"
2. Wait for Architect response

**Expected Results:**
- Architect uses RAG to understand existing codebase
- Response includes:
  - Task graph structure
  - Module breakdown
  - Integration points with existing code
- LLM response is properly formatted JSON
- Task dependencies are logical

#### Test 2.2: RAG Context Usage
**Steps:**
1. Send: "How does the current authentication system work?"
2. Verify Architect queries RAG

**Expected Results:**
- Architect retrieves relevant code snippets
- Response references actual files from the codebase
- Context is accurate and relevant

### 3. Analyzer Agent Testing

#### Test 3.1: Initial Architecture Analysis
**Steps:**
1. Trigger initial analysis (should happen automatically on project init)
2. Check for generated architecture diagram

**Expected Results:**
- Mermaid diagram generated
- Components properly identified
- Relationships accurately mapped
- Diagram stored in RAG

#### Test 3.2: Change-Triggered Analysis
**Steps:**
1. Make significant code changes (>50 lines)
2. Apply changes through coding agent
3. Verify analyzer triggers automatically

**Expected Results:**
- Change tracker detects threshold exceeded
- Analyzer regenerates architecture
- New diagram reflects changes
- Event logged in system

### 4. Request Planner Testing

#### Test 4.1: Complex Request Processing
**Steps:**
1. Submit request: "Add user profile management with avatar upload, bio, and preferences"
2. Monitor Request Planner processing

**Expected Results:**
- Request Planner uses RAG to find similar features
- Creates detailed plan with multiple steps
- Plan includes:
  - Database changes
  - API endpoints
  - Frontend components
  - Tests

#### Test 4.2: RAG-Enhanced Planning
**Steps:**
1. Submit: "Refactor the authentication to use JWT tokens like in the product service"
2. Verify RAG queries

**Expected Results:**
- Planner finds product service JWT implementation
- Plan references specific files and patterns
- Suggests consistent approach

### 5. Code Planner Testing

#### Test 5.1: Task Generation
**Steps:**
1. Monitor Code Planner receiving plans from Request Planner
2. Verify task breakdown

**Expected Results:**
- Tasks are atomic and implementable
- Each task has clear file paths
- Dependencies properly mapped
- Complexity accurately assessed

#### Test 5.2: RAG-Based Code Analysis
**Steps:**
1. Check Code Planner logs for RAG usage
2. Verify symbol lookups and pattern matching

**Expected Results:**
- AST analysis enhanced with RAG context
- Similar code patterns identified
- Relevant examples included in tasks

### 6. Coding Agent Testing

#### Test 6.1: Code Implementation
**Steps:**
1. Monitor Coding Agent executing tasks
2. Verify patch generation

**Expected Results:**
- Patches apply cleanly
- Code follows project conventions
- Change tracking activated
- RAG queries for examples

#### Test 6.2: Change Tracking Integration
**Steps:**
1. Apply multiple patches
2. Monitor change metrics

**Expected Results:**
- Each patch tracked with line counts
- Metrics accumulate correctly
- Threshold triggers when exceeded

### 7. Event System Testing

#### Test 7.1: Event Flow
**Steps:**
1. Open browser developer console
2. Monitor WebSocket messages
3. Trigger various agent actions

**Expected Results:**
- Agent status updates broadcast
- Task progress events received
- Change events propagated
- No event loss or duplication

#### Test 7.2: Agent Coordination
**Steps:**
1. Submit complex request requiring multiple agents
2. Monitor event flow between agents

**Expected Results:**
- Proper handoff between agents
- Status updates coherent
- No race conditions
- Error handling works

### 8. RAG Service Testing

#### Test 8.1: Index Quality
**Steps:**
1. Query RAG directly: "find authentication code"
2. Verify search results

**Expected Results:**
- Relevant code chunks returned
- Ranking makes sense
- Symbol resolution works
- Performance acceptable (<1s)

#### Test 8.2: Multi-Agent RAG Usage
**Steps:**
1. Submit request that triggers all agents
2. Monitor RAG query logs

**Expected Results:**
- Each agent queries appropriately
- No redundant queries
- Context sharing works
- Cache utilized effectively

### 9. Architecture Diagram Testing

#### Test 9.1: Diagram Accuracy
**Steps:**
1. Generate architecture diagram
2. Manually verify against codebase

**Expected Results:**
- All major components identified
- Relationships accurate
- Layers properly organized
- Mermaid syntax valid

#### Test 9.2: Diagram Updates
**Steps:**
1. Add new service/component
2. Trigger analysis
3. Compare diagrams

**Expected Results:**
- New component appears
- Relationships updated
- Layout still readable
- History maintained

### 10. Error Handling and Recovery

#### Test 10.1: LLM Failures
**Steps:**
1. Simulate API rate limit
2. Submit requests

**Expected Results:**
- Graceful degradation
- User-friendly error messages
- Retry logic works
- System remains stable

#### Test 10.2: RAG Service Unavailable
**Steps:**
1. Stop RAG service
2. Test agent functionality

**Expected Results:**
- Agents fall back gracefully
- Basic functionality maintained
- Clear indication of degraded mode
- Recovery when service returns

## Performance Benchmarks

### Expected Performance Metrics
- Project initialization: <30 seconds for 1000 files
- RAG query response: <1 second
- Architecture analysis: <10 seconds
- Agent response time: <5 seconds
- WebSocket latency: <100ms

## Test Execution Checklist

- [ ] Environment setup complete
- [ ] Test repository prepared
- [ ] All services running
- [ ] Frontend accessible
- [ ] Backend logs monitored
- [ ] LLM API key valid
- [ ] RAG index cleared
- [ ] Change tracker reset

## Success Criteria

1. **Integration Success**
   - All agents communicate properly
   - Events flow correctly
   - No integration errors

2. **RAG Effectiveness**
   - Relevant context retrieved
   - Query performance acceptable
   - All agents utilize RAG

3. **LLM Tool Usage**
   - Proper function calling
   - Response formatting correct
   - Error handling robust

4. **Architecture Analysis**
   - Diagrams accurate and useful
   - Auto-updates working
   - Mermaid rendering correct

5. **Change Tracking**
   - All changes captured
   - Thresholds trigger correctly
   - Metrics accurate

## Logging and Monitoring

### Key Log Files to Monitor
- Frontend console (browser)
- Backend server logs
- Agent-specific logs
- RAG service logs
- WebSocket event logs

### Metrics to Track
- Agent task completion rate
- RAG query performance
- LLM API usage
- Change tracking accuracy
- Event delivery reliability

## Test Report Template

```markdown
# E2E Test Report - [Date]

## Summary
- Total Tests: X
- Passed: X
- Failed: X
- Skipped: X

## Detailed Results
[Test results by category]

## Issues Found
[List of bugs/issues]

## Performance Metrics
[Actual vs expected]

## Recommendations
[Improvements needed]
```