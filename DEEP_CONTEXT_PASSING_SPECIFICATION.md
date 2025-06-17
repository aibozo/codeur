# Deep Context Passing System - Comprehensive Specification

## Overview

The Deep Context Passing System is a comprehensive solution that enables the architect agent to create detailed phased implementation plans with rich context that flows seamlessly through the entire development pipeline. This system ensures that every task executed by any agent has access to the full context hierarchy, from high-level strategic goals down to specific implementation details.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Deep Context Passing System                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Plan Models   │  │  Plan Storage   │  │   RAG Index     │  │
│  │                 │  │                 │  │                 │  │
│  │ • ImplementationPlan │ • File Storage  │  │ • Semantic Search│  │
│  │ • PlanPhase     │  │ • Versioning    │  │ • Context Chunks│  │
│  │ • PlanMilestone │  │ • Indexing      │  │ • Embeddings    │  │
│  │ • PlanChunk     │  │ • Metadata      │  │ • Retrieval     │  │
│  │ • PlanTask      │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│           │                     │                     │          │
│           └─────────────────────┼─────────────────────┘          │
│                                 │                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Plan Manager   │  │ Plan-Aware      │  │    Plan API     │  │
│  │                 │  │   Architect     │  │                 │  │
│  │ • Orchestration │  │                 │  │ • Task Context  │  │
│  │ • Templates     │  │ • LLM Enhanced  │  │ • Progress Mgmt │  │
│  │ • Lifecycle     │  │ • Plan Creation │  │ • Search & Query│  │
│  │ • Metrics       │  │ • Context Graph │  │ • Integration   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
User Request → Plan-Aware Architect → Implementation Plan
                        ↓
                LLM Enhancement → Rich Context Generation
                        ↓
                Plan Storage → File System + RAG Index
                        ↓
                Task Execution → Context Retrieval → Agent Execution
                        ↓
                Progress Updates → Plan State Management
```

## Plan Structure Design

### Hierarchical Plan Model

The system uses a 5-level hierarchical structure:

```
Implementation Plan (Level 1)
├── Plan Phases (Level 2)
│   ├── Plan Milestones (Level 3)
│   │   ├── Plan Chunks (Level 4)
│   │   │   ├── Plan Tasks (Level 5)
│   │   │   └── Plan Tasks
│   │   └── Plan Chunks
│   └── Plan Milestones
└── Plan Phases
```

### Data Structures

#### PlanContext
Rich context information that flows through all levels:

```python
@dataclass
class PlanContext:
    # Technical context
    technologies: List[str]          # Technologies/frameworks used
    dependencies: List[str]          # External dependencies
    constraints: List[str]           # Technical constraints
    
    # Business context  
    stakeholders: List[str]          # Key stakeholders
    requirements: List[str]          # Business requirements
    acceptance_criteria: List[str]   # Success criteria
    
    # Implementation context
    affected_files: List[str]        # Files to be modified
    related_components: List[str]    # Related system components
    integration_points: List[str]    # Integration interfaces
    
    # Quality context
    performance_requirements: List[str]  # Performance needs
    security_considerations: List[str]   # Security requirements
    scalability_factors: List[str]       # Scalability concerns
```

#### Task Hierarchy
Each level inherits and enriches context from parent levels:

1. **ImplementationPlan**: Strategic-level context and overall objectives
2. **PlanPhase**: Phase-specific goals and technology stack
3. **PlanMilestone**: Concrete deliverables and integration points
4. **PlanChunk**: Implementation approach and file-level details
5. **PlanTask**: Specific execution instructions and acceptance criteria

## Storage & Retrieval System

### Directory Structure

```
.agent/
├── plans/
│   ├── active/           # Currently active plans
│   │   ├── {plan_id}.json
│   │   └── ...
│   ├── archived/         # Completed/deprecated plans
│   │   ├── {plan_id}.json
│   │   └── ...
│   ├── templates/        # Plan templates
│   │   ├── feature_development.json
│   │   ├── bug_fix.json
│   │   └── ...
│   └── index.json        # Plan metadata index
├── plan_chunks/          # Individual chunk storage for RAG
│   ├── {chunk_id}.json
│   └── ...
└── plan_context/         # Context mappings
    ├── {plan_id}_mappings.json
    └── ...
```

### Storage Features

- **Versioning**: Plans are versioned and changes are tracked
- **Indexing**: Fast lookup by plan ID, status, project, etc.
- **Chunking**: Individual components stored for RAG indexing
- **Mapping**: Quick task-to-context lookups
- **Archival**: Automatic archiving of completed plans

### RAG Integration

#### Indexing Strategy
Each plan component is indexed as separate chunks:

1. **Plan Overview**: High-level plan information
2. **Phase Details**: Phase-specific context and goals
3. **Milestone Specs**: Concrete deliverables and timeline
4. **Chunk Implementation**: Technical implementation details
5. **Task Instructions**: Specific execution guidance

#### Search Capabilities
- **Semantic Search**: Vector-based similarity search
- **Keyword Search**: Traditional text search
- **Hybrid Search**: Combined vector + keyword
- **Filtered Search**: By component type, status, project
- **Context Search**: Find related plan components

## Integration Points

### Plan Creation Workflow

```python
# 1. Architect creates plan from request
architect = PlanAwareArchitect(project_path, rag_service, llm_client)

plan = await architect.create_implementation_plan(
    request_description="Add notification system",
    project_id="agent_framework",
    plan_type="feature_development"
)

# 2. LLM enhancement adds rich context
# - Strategic goals and outcomes
# - Technical requirements and constraints
# - File-level implementation details
# - Acceptance criteria and success metrics

# 3. Plan is stored and indexed
architect.plan_manager.save_plan(plan, index_in_rag=True)
```

### Task Execution Workflow

```python
# 1. Agent gets ready tasks with context
plan_api = create_plan_api(project_path)
ready_tasks = plan_api.get_ready_tasks(agent_type="coding_agent")

# 2. Get comprehensive execution context
task = ready_tasks[0]
context = plan_api.get_task_context(task['task_id'])

# Context includes:
# - Full plan hierarchy (plan → phase → milestone → chunk → task)
# - Execution guidance (approach, challenges, success criteria)
# - Related context (similar tasks, affected files, dependencies)
# - Business context (requirements, stakeholders, acceptance criteria)

# 3. Execute with rich context
result = execute_task_with_context(task, context)

# 4. Report progress and completion
plan_api.mark_task_completed(task['task_id'], result)
```

### Search and Discovery

```python
# Semantic search across all plan components
results = plan_api.search_context("notification websocket real-time")

# Find tasks affecting specific files
tasks = plan_api.get_tasks_by_file("src/notification/handler.py")

# Find related tasks
related = plan_api.find_related_tasks(task_id)
```

## Implementation Components

### Core Classes

#### 1. Plan Models (`plan_models.py`)
- **ImplementationPlan**: Top-level plan container
- **PlanPhase**: High-level development phases
- **PlanMilestone**: Concrete deliverable milestones
- **PlanChunk**: Implementation chunks with specific goals
- **PlanTask**: Individual executable tasks
- **PlanContext**: Rich context information container

#### 2. Plan Storage (`plan_storage.py`)
- **PlanStorageManager**: File system storage management
- Persistent storage in `.agent/plans/` structure
- Plan indexing and metadata management
- Version control and archival

#### 3. RAG Integration (`plan_rag_integration.py`)
- **PlanRAGIndexer**: Indexes plans into RAG service
- **PlanContextRetriever**: Retrieves context during execution
- Semantic search and context discovery
- Chunk management for efficient retrieval

#### 4. Plan Manager (`plan_manager.py`)
- **PlanManager**: Orchestrates all plan operations
- Plan creation, modification, and lifecycle management
- Template-based plan generation
- Metrics and analytics

#### 5. Plan-Aware Architect (`plan_aware_architect.py`)
- **PlanAwareArchitect**: Enhanced architect with plan integration
- LLM-powered plan creation and enhancement
- Context-aware conversation management
- Integration with existing architect capabilities

#### 6. Plan API (`plan_api.py`)
- **PlanAPI**: Clean interface for agent integration
- Task context retrieval and progress management
- Search and discovery operations
- System-wide monitoring and metrics

### API Interfaces

#### Task Execution Context API

```python
# Get comprehensive task context
context = plan_api.get_task_context(task_id)
# Returns:
# {
#   "plan": {"id": "...", "title": "...", "context": {...}},
#   "phase": {"id": "...", "title": "...", "context": {...}},
#   "milestone": {"id": "...", "title": "...", "context": {...}},
#   "chunk": {"id": "...", "title": "...", "context": {...}},
#   "task": {"id": "...", "title": "...", "context": {...}},
#   "execution_guidance": {
#     "approach_suggestions": [...],
#     "success_criteria": [...],
#     "files_to_modify": [...],
#     "dependencies": [...]
#   },
#   "related_context": [...]
# }
```

#### Task Discovery API

```python
# Get ready tasks for execution
ready_tasks = plan_api.get_ready_tasks(
    agent_type="coding_agent",
    limit=5
)

# Find tasks by criteria
tasks_by_file = plan_api.get_tasks_by_file("src/module.py")
related_tasks = plan_api.find_related_tasks(task_id)
```

#### Progress Management API

```python
# Report task lifecycle
plan_api.mark_task_started(task_id, agent_id="agent_1")
plan_api.report_task_progress(task_id, 50.0, "Half complete")
plan_api.mark_task_completed(task_id, result_data)
```

#### Search and Analytics API

```python
# Semantic search
results = plan_api.search_context("notification system", k=5)

# Plan metrics
metrics = plan_api.get_plan_metrics(plan_id)
system_status = plan_api.get_system_status()
```

## Integration Workflows

### Architect → Plan Creation

1. **Request Analysis**: LLM analyzes user request for planning information
2. **Template Selection**: Choose appropriate plan template
3. **Context Enhancement**: LLM generates detailed context at each level
4. **Storage & Indexing**: Plan saved to storage and indexed in RAG
5. **Validation**: Plan structure validated and metrics calculated

### Plan → Task Execution

1. **Task Discovery**: Agents query for ready tasks by type
2. **Context Retrieval**: Full context hierarchy retrieved for task
3. **Execution Guidance**: System provides approach suggestions and success criteria
4. **Progress Tracking**: Task progress reported back to plan
5. **Completion**: Task results stored and plan metrics updated

### Cross-Agent Context Sharing

1. **Contextual Search**: Agents search for related work and dependencies
2. **File-Based Discovery**: Find tasks affecting same files
3. **Dependency Resolution**: Understand task dependencies and blockers
4. **Knowledge Transfer**: Share insights and results across agents

## Plan Templates

### Feature Development Template

```
Phase 1: Analysis & Design
├── Milestone: Requirements Complete
│   ├── Chunk: Requirements Analysis
│   │   ├── Task: Gather Requirements (architect)
│   │   └── Task: Document Constraints (architect)
│   └── Chunk: Technical Design
│       ├── Task: Create Architecture (architect)
│       └── Task: Design Interfaces (architect)
├── Milestone: Design Approved
    └── ...

Phase 2: Implementation
├── Milestone: Core Features Complete
│   ├── Chunk: Core Implementation
│   │   ├── Task: Implement Core Logic (coding_agent)
│   │   └── Task: Add Error Handling (coding_agent)
│   └── Chunk: Integration Layer
│       └── Task: Build APIs (coding_agent)
└── ...

Phase 3: Testing & Deployment
└── Milestone: Feature Live
    ├── Chunk: Testing Suite
    │   ├── Task: Write Unit Tests (test_agent)
    │   └── Task: Integration Tests (test_agent)
    └── Chunk: Deployment
        └── Task: Deploy to Production (coding_agent)
```

### Bug Fix Template

```
Phase 1: Investigation
├── Milestone: Root Cause Identified
│   ├── Chunk: Bug Reproduction
│   │   ├── Task: Reproduce Issue (architect)
│   │   └── Task: Document Symptoms (architect)
│   └── Chunk: Root Cause Analysis
│       └── Task: Identify Root Cause (architect)

Phase 2: Fix Implementation
├── Milestone: Fix Applied
│   ├── Chunk: Code Fix
│   │   └── Task: Implement Fix (coding_agent)
│   └── Chunk: Verification
│       └── Task: Verify Fix (test_agent)
```

## Context Flow Examples

### Example 1: Feature Implementation Context

```
Plan Level:
- Title: "Real-time Notification System"
- Strategic Goal: "Enable real-time communication between agents"
- Technologies: ["WebSocket", "Python", "asyncio"]

Phase Level:
- Title: "Implementation Phase"
- Goals: ["Implement core notification service", "Add WebSocket support"]
- Dependencies: ["Authentication system", "Message queue"]

Milestone Level:
- Title: "Core Service Complete"
- Deliverables: ["NotificationService class", "WebSocket handler", "Tests"]
- Integration Points: ["User authentication", "Frontend WebSocket client"]

Chunk Level:
- Title: "WebSocket Handler Implementation"
- Type: FEATURE
- Rationale: "WebSocket needed for real-time bidirectional communication"
- Files: ["src/notification/websocket_handler.py", "src/notification/models.py"]

Task Level:
- Title: "Implement WebSocket connection handler"
- Category: IMPLEMENTATION
- Agent: "coding_agent"
- Success Criteria: ["Handles connection lifecycle", "Supports message routing", "Includes error handling"]
- Files: ["src/notification/websocket_handler.py"]
```

### Example 2: Test Task Context

```
Task: "Write integration tests for notification service"
Context Hierarchy:
- Plan: Real-time Notification System
- Phase: Testing & Validation
- Milestone: Comprehensive Test Coverage
- Chunk: Integration Testing Suite

Available Context:
- Requirements: ["Support 1000+ concurrent connections", "Sub-second message delivery"]
- Files to Test: ["websocket_handler.py", "notification_service.py", "message_router.py"]
- Integration Points: ["User auth service", "Message queue", "Frontend client"]
- Acceptance Criteria: ["99.9% message delivery", "Graceful connection handling", "Proper error responses"]
- Related Tests: ["Unit tests for NotificationService", "Load tests for WebSocket"]
```

## Benefits and Impact

### For Execution Agents

1. **Rich Context**: Every task comes with comprehensive context about why it's needed and how it fits into the bigger picture
2. **Clear Guidance**: Specific instructions, success criteria, and approach suggestions
3. **Dependency Awareness**: Understanding of what depends on this task and what it depends on
4. **Quality Assurance**: Built-in acceptance criteria and testing requirements

### For Project Management

1. **Visibility**: Complete visibility into project progress at all levels
2. **Metrics**: Detailed metrics on progress, bottlenecks, and resource utilization
3. **Planning**: Template-based planning for consistent project structure
4. **Traceability**: Clear traceability from requirements to implementation

### For Knowledge Management

1. **Searchability**: Semantic search across all project plans and context
2. **Reusability**: Context and patterns can be reused across projects
3. **Learning**: System learns from successful patterns and approaches
4. **Documentation**: Automatic documentation of decisions and rationale

### for System Integration

1. **Modularity**: Clean API interfaces for easy integration
2. **Extensibility**: Template system allows custom plan types
3. **Scalability**: Efficient storage and retrieval for large projects
4. **Monitoring**: Comprehensive monitoring and alerting capabilities

## Usage Examples

### Creating a New Plan

```python
from src.architect import PlanAwareArchitect, create_plan_api

# Initialize the system
architect = PlanAwareArchitect(
    project_path="./my_project",
    rag_service=rag_service,
    llm_client=llm_client
)

# Create comprehensive plan
plan = await architect.create_implementation_plan(
    request_description="Add user authentication system",
    project_id="web_app",
    plan_type="feature_development"
)

print(f"Created plan with {len(plan.get_all_tasks())} tasks")
```

### Agent Integration

```python
# Coding agent getting work
plan_api = create_plan_api("./my_project")

# Get next task
ready_tasks = plan_api.get_ready_tasks(agent_type="coding_agent", limit=1)
task = ready_tasks[0]

# Get full context
context = plan_api.get_task_context(task['task_id'])

# Execute with context
files_to_modify = context['execution_guidance']['files_to_modify']
requirements = context['task']['context']['requirements']
success_criteria = context['execution_guidance']['success_criteria']

# Report completion
result = {"files_modified": files_to_modify, "tests_added": 3}
plan_api.mark_task_completed(task['task_id'], result)
```

### Search and Discovery

```python
# Find relevant context
results = plan_api.search_context("authentication login security")

# Find tasks affecting specific files
auth_tasks = plan_api.get_tasks_by_file("src/auth/models.py")

# Get system overview
status = plan_api.get_system_status()
print(f"Ready tasks: {status['ready_tasks_count']}")
```

## Future Enhancements

### Advanced Context Features

1. **Dynamic Context Updates**: Context that evolves based on execution results
2. **Cross-Project Learning**: Learning from similar projects and tasks
3. **Predictive Analytics**: Predicting task duration and resource needs
4. **Automated Optimization**: Automatic plan optimization based on metrics

### Enhanced Integration

1. **Git Integration**: Automatic plan updates based on code changes
2. **Issue Tracking**: Integration with GitHub/JIRA issue tracking
3. **CI/CD Integration**: Plan updates from build and deployment results
4. **Real-time Collaboration**: Multi-user plan editing and coordination

### Advanced Analytics

1. **Performance Metrics**: Detailed performance tracking and optimization
2. **Resource Analytics**: Resource utilization and bottleneck identification
3. **Quality Metrics**: Code quality and defect rate correlation with plans
4. **Predictive Modeling**: Machine learning for project success prediction

---

## Conclusion

The Deep Context Passing System transforms how development projects are planned and executed by ensuring that rich, hierarchical context flows seamlessly from high-level strategic decisions down to specific implementation tasks. This enables more informed decision-making, better quality outcomes, and improved project visibility across the entire development lifecycle.

The system's modular design, comprehensive APIs, and integration with existing architect capabilities make it a powerful foundation for AI-driven development workflows while maintaining the flexibility to adapt to different project types and requirements.