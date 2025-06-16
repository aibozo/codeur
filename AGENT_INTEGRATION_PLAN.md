# Agent Task Graph & RAG Integration Plan

## Overview
This document provides a comprehensive analysis of all agents in the system and their integration requirements for the task graph and RAG systems.

## Identified Agents

### 1. **Architect Agent** (`src/architect/architect.py`)
- **Purpose**: Designs overall system architecture, creates task dependency graphs, orchestrates development workflow
- **Current State**: Already has enhanced task graph integration and RAG support
- **Task Graph Access**:
  - ✅ **Write Access**: Creates and manages task graphs
  - ✅ **Read Access**: Monitors task progress
- **RAG Access**:
  - ✅ **Write Access**: Stores architecture documents, task graphs
  - ✅ **Read Access**: Retrieves project context for planning

### 2. **Request Planner Agent** (`src/request_planner/planner.py`)
- **Purpose**: Understands user requests, creates implementation plans, orchestrates task execution
- **Current State**: Has basic LLM integration, no direct task graph or RAG access
- **Task Graph Access**:
  - 🔲 **Write Access**: Should create high-level tasks from user requests
  - 🔲 **Read Access**: Should monitor plan execution progress
- **RAG Access**:
  - 🔲 **Read Access**: Should retrieve project context and similar implementations
  - 🔲 **Write Access**: Should store plans and decisions for future reference

### 3. **Code Planner Agent** (`src/code_planner/code_planner.py`)
- **Purpose**: Transforms Plans into detailed CodingTasks with AST analysis
- **Current State**: Has RAG integration for code search, no task graph access
- **Task Graph Access**:
  - 🔲 **Write Access**: Should update task details and dependencies
  - 🔲 **Read Access**: Should understand task context and priorities
- **RAG Access**:
  - ✅ **Read Access**: Already retrieves code context
  - 🔲 **Write Access**: Should store code analysis results

### 4. **Coding Agent** (`src/coding_agent/agent.py`)
- **Purpose**: Implements actual code changes, generates patches, creates commits
- **Current State**: Has RAG client for context, tracks changes, no task graph access
- **Task Graph Access**:
  - 🔲 **Write Access**: Should update task status (in progress, completed, failed)
  - 🔲 **Read Access**: Should understand task requirements and dependencies
- **RAG Access**:
  - ✅ **Read Access**: Already uses for context gathering
  - 🔲 **Write Access**: Should store implementation decisions and patterns

### 5. **Analyzer Agent** (`src/analyzer/analyzer.py`)
- **Purpose**: Analyzes project architecture, generates diagrams, maintains documentation
- **Current State**: Has RAG service, automatic analysis triggers, no task graph access
- **Task Graph Access**:
  - 🔲 **Read Access**: Should analyze task completion impact on architecture
  - 🔲 **Write Access**: Should create analysis/documentation tasks
- **RAG Access**:
  - ✅ **Read Access**: Already retrieves architecture info
  - ✅ **Write Access**: Already stores analysis results

### 6. **Code Tester Agent** (Referenced but not implemented)
- **Purpose**: Would run tests, validate changes, ensure quality
- **Current State**: Not yet implemented
- **Task Graph Access**:
  - 🔲 **Write Access**: Should update test task status
  - 🔲 **Read Access**: Should understand what to test
- **RAG Access**:
  - 🔲 **Read Access**: Should retrieve test patterns and coverage data
  - 🔲 **Write Access**: Should store test results and coverage reports

## Integration Priority Matrix

| Agent | Task Graph Read | Task Graph Write | RAG Read | RAG Write | Priority |
|-------|----------------|------------------|----------|-----------|----------|
| Architect | ✅ Done | ✅ Done | ✅ Done | ✅ Done | - |
| Request Planner | 🔲 High | 🔲 High | 🔲 High | 🔲 Medium | 1 |
| Coding Agent | 🔲 High | 🔲 High | ✅ Done | 🔲 Low | 2 |
| Code Planner | 🔲 Medium | 🔲 Medium | ✅ Done | 🔲 Low | 3 |
| Analyzer | 🔲 Low | 🔲 Low | ✅ Done | ✅ Done | 4 |
| Code Tester | 🔲 Medium | 🔲 Medium | 🔲 Medium | 🔲 Medium | 5 |

## Implementation Phases

### Phase 1: Request Planner Integration (Priority 1)
1. **Task Graph Integration**:
   - Add `TaskGraphManager` instance to RequestPlanner
   - Implement `create_request_task()` method to create top-level tasks
   - Add `update_plan_status()` to track plan execution
   - Integrate with Architect's task graph for hierarchical task creation

2. **RAG Integration**:
   - Add RAG client to RequestPlanner initialization
   - Implement `search_similar_requests()` for finding past solutions
   - Add `store_plan_context()` to save successful plans
   - Use RAG for enhanced context retrieval in `create_plan()`

### Phase 2: Coding Agent Integration (Priority 2)
1. **Task Graph Integration**:
   - Add task graph client to CodingAgent
   - Implement `update_task_progress()` for status updates
   - Add `get_task_context()` to retrieve full task requirements
   - Update `process_task()` to report completion/failure

2. **RAG Enhancement**:
   - Implement `store_implementation_pattern()` for successful changes
   - Add commit metadata to RAG for future reference

### Phase 3: Code Planner Integration (Priority 3)
1. **Task Graph Integration**:
   - Add ability to read parent task context
   - Implement task refinement based on AST analysis
   - Update task estimates based on complexity analysis

2. **RAG Enhancement**:
   - Store AST analysis results for pattern detection
   - Save dependency graphs for impact analysis

### Phase 4: Analyzer Integration (Priority 4)
1. **Task Graph Integration**:
   - Subscribe to task completion events
   - Trigger architecture analysis on significant changes
   - Create documentation update tasks

### Phase 5: Code Tester Implementation (Priority 5)
1. **Create Code Tester Agent**:
   - Design test execution framework
   - Implement test discovery and execution
   - Add coverage analysis

2. **Integrations**:
   - Full task graph integration for test tasks
   - RAG integration for test pattern learning

## Technical Implementation Details

### Task Graph Integration Pattern
```python
class AgentWithTaskGraph:
    def __init__(self, task_graph_manager: TaskGraphManager):
        self.task_graph = task_graph_manager
    
    async def update_task_status(self, task_id: str, status: TaskStatus):
        await self.task_graph.update_task_status(task_id, status)
    
    async def get_task_context(self, task_id: str) -> Dict:
        return await self.task_graph.expand_task_context(task_id)
```

### RAG Integration Pattern
```python
class AgentWithRAG:
    def __init__(self, rag_client: RAGClient):
        self.rag_client = rag_client
    
    async def search_context(self, query: str) -> List[Dict]:
        return await self.rag_client.search(query, k=10)
    
    async def store_knowledge(self, doc_type: str, content: str):
        await self.rag_client.index_document(doc_type, content)
```

## Benefits of Integration

1. **Better Context Awareness**: Agents can access full project history and patterns
2. **Improved Coordination**: Task graph ensures proper sequencing and dependency management
3. **Knowledge Accumulation**: RAG stores lessons learned for future use
4. **Progress Visibility**: Real-time task status updates across all agents
5. **Pattern Recognition**: Historical data helps identify optimal solutions

## Next Steps

1. Create integration interfaces for consistent access patterns
2. Implement Phase 1 (Request Planner) as proof of concept
3. Set up event system for task status propagation
4. Create monitoring dashboard for integrated system
5. Develop test suite for integration points