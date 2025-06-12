# Agent Architecture Implementation Roadmap

## Overview

This document outlines the implementation plan for building a self-healing agent loop system, starting with the Request Planner as a Claude Code/Codex style coding agent interface.

## Phase 1: Request Planner as Coding Agent Interface (MVP)

### Goals
- Build a functional Request Planner that acts as the primary interface with users
- Implement it as a Claude Code/Codex style agent that can:
  - Accept natural language requests
  - Plan implementations and break down tasks
  - Act as the orchestrator for the system
  - Monitor agent status and report results
  - Answer codebase questions

### Key Components

#### 1.1 Request Planner Core
- **Location**: `src/request_planner/`
- **Responsibilities**:
  - Natural language understanding and request parsing
  - Task decomposition and planning
  - Context retrieval (simplified RAG)
  - User interaction and feedback
  - Task monitoring and status reporting

#### 1.2 Simplified Infrastructure
- **Message Queue**: In-memory queue for MVP (upgrade to Kafka/RabbitMQ later)
- **Task Management**: Simple task tracking system
- **Git Integration**: Basic file reading and modification
- **RAG Service**: Simplified code search and context retrieval

### Implementation Steps

1. **Core Request Planner Agent** (Week 1-2)
   - Command-line interface for user interaction
   - Basic natural language request parsing
   - Task planning and decomposition logic
   - Simple JSON-based plan generation

2. **Basic RAG Service** (Week 2-3)
   - File-based code indexing
   - Simple keyword and semantic search
   - Context snippet extraction
   - Integration with Request Planner

3. **Task Management System** (Week 3-4)
   - Task state tracking
   - Simple orchestration logic
   - Status monitoring and reporting
   - Basic error handling

4. **Git Integration** (Week 4)
   - File reading and parsing
   - Basic diff generation
   - Simple commit functionality

## Phase 2: Extended Agent Capabilities

### Goals
- Add code generation capabilities
- Implement basic testing functionality
- Add simple CI/CD integration

### Components

#### 2.1 Code Generation
- Integrate LLM for code generation
- Basic patch application
- Simple validation and linting

#### 2.2 Test Planning
- Basic test requirement generation
- Simple test execution

## Phase 3: Full Agent Loop Implementation

### Goals
- Implement all agents as specified in architecture docs
- Production-ready message queue
- Full RAG service with vector search
- Complete CI/CD integration

### Components
- Code Planner Agent
- Coding Agent
- Build/CI Runner
- Test Planner
- Test Builder
- Verifier
- Production RAG Service

## Technical Stack (MVP)

### Languages & Frameworks
- **Python 3.11**: Primary language
- **FastAPI**: API framework for services
- **Click**: CLI framework
- **Pydantic**: Data validation

### Storage & Queues
- **SQLite**: Simple persistence for MVP
- **In-memory queue**: Task management for MVP

### Development Tools
- **pytest**: Testing framework
- **black/ruff**: Code formatting and linting
- **poetry**: Dependency management

## Success Metrics

### Phase 1 Success Criteria
- Can accept natural language requests
- Can generate structured plans
- Can retrieve relevant code context
- Can track task execution
- Can report status to users

### MVP Deliverables
1. Working Request Planner CLI
2. Basic task planning and tracking
3. Simple code context retrieval
4. Documentation and examples

## Next Steps

1. Set up development environment
2. Create basic project structure
3. Implement Request Planner CLI interface
4. Build simple task management system
5. Integrate basic RAG functionality

## Notes

- Start simple, iterate quickly
- Focus on user experience first
- Build with extensibility in mind
- Maintain clear interfaces between components
- Document as we build