# Frontend Modernization Plan: From CLI to Chef's Kiss 👨‍🍳

## Vision
Transform Codeur from a powerful CLI tool into a beautiful, modern system with both terminal and web interfaces that provide real-time insights, visual agent monitoring, and seamless team collaboration.

## Current State → Target State

### Current State 😐
- CLI-only interface with Rich formatting
- Disconnected UI components in test files
- No real-time monitoring beyond terminal output
- Limited visual feedback for long operations
- No model selection flexibility

### Target State 🎯
- **Dual Interface**: Beautiful terminal UI + modern web dashboard
- **Real-time Everything**: Live agent graph, streaming logs, instant updates
- **Visual Intelligence**: See what agents are thinking/doing in real-time
- **Flexible Configuration**: Per-agent model selection with GUI controls
- **Trust & Transparency**: Show plans, diffs, and one-click reverts
- **Team Ready**: Shareable dashboards, persistent sessions

## Implementation Plan

### Phase 1: Foundation (Week 1)
**Goal**: Set up core infrastructure for real-time communication and persistence

#### 1.1 Enhanced Backend Infrastructure
```python
# src/core/realtime.py
- WebSocket manager for bi-directional communication
- SSE endpoint for one-way streaming
- Redis-based session persistence
- Event streaming from message bus to WebSocket

# src/api/models.py
- Pydantic models for all frontend communication
- Agent state representations
- Graph data structures for visualization
```

#### 1.2 Unified UI Module
```python
# src/ui/
├── terminal/          # Terminal UI components
│   ├── components.py  # Reusable Rich components
│   ├── themes.py      # Consistent color schemes
│   └── layouts.py     # Standard layout patterns
├── shared/           # Shared UI logic
│   ├── formatters.py # Code formatting, diff display
│   └── state.py      # UI state management
└── __init__.py
```

#### 1.3 API Extensions
```python
# New FastAPI endpoints
POST   /api/agents/{agent_type}/model    # Set model per agent
GET    /api/agents/graph                 # Live agent graph data
WS     /ws/agents                        # WebSocket for real-time updates
GET    /api/stream/logs                  # SSE log streaming
GET    /api/jobs/{job_id}               # Persistent job status
POST   /api/jobs/{job_id}/revert        # One-click revert
```

### Phase 2: Terminal UI Enhancement (Week 2)
**Goal**: Create a cohesive, beautiful terminal experience

#### 2.1 Integrated Dashboard Mode
```bash
# New command
agent-system monitor --dashboard

# Features:
- Split-pane layout (logs, metrics, agent status)
- Real-time graph visualization in terminal (using Rich + Graphviz)
- Model switcher UI (using Rich prompts)
- Keyboard shortcuts for common actions
```

#### 2.2 Terminal Components Library
```python
# Reusable components
- AgentCard: Shows agent status, current task, model
- GraphView: ASCII/Unicode agent relationship graph
- LogStream: Formatted, filterable log output
- MetricsBar: Performance indicators
- PlanView: Collapsible plan/diff viewer
```

#### 2.3 Consistent Theming
```python
# Dark theme with accent colors
Primary:   #00D9FF (Cyan)     - Headers, active elements
Success:   #00FF88 (Green)    - Successful operations
Warning:   #FFB800 (Amber)    - Warnings, idle states
Error:     #FF0066 (Pink)     - Errors, failures
Accent:    #B794F4 (Purple)   - Special elements, AI actions
```

### Phase 3: Web Dashboard (Week 3-4)
**Goal**: Build a modern, reactive web interface

#### 3.1 Tech Stack
```javascript
// Frontend
- React 18 with TypeScript
- Vite for blazing fast HMR
- TanStack Query for server state
- Zustand for client state
- D3.js for agent graph
- Tailwind CSS + Radix UI
- Framer Motion for animations

// Real-time
- Native WebSocket API
- EventSource for SSE
- Automatic reconnection
```

#### 3.2 Core Views

##### Dashboard View
```typescript
interface DashboardView {
  // Left sidebar: Agent list with model selectors
  agents: AgentCard[]
  
  // Center: Live agent graph
  graph: ForceDirectedGraph
  
  // Right sidebar: System metrics
  metrics: MetricsPanel
  
  // Bottom: Streaming logs
  logs: LogStream
}
```

##### Job Detail View
```typescript
interface JobDetailView {
  // Top: Job metadata and controls
  header: JobHeader      // Status, duration, revert button
  
  // Tabs
  plan: PlanViewer      // Natural language plan
  diff: DiffViewer      // Git diff with syntax highlighting
  logs: LogHistory      // Full execution log
  graph: JobGraph       // Agent interaction for this job
}
```

##### Configuration View
```typescript
interface ConfigView {
  // Model selection per agent type
  modelConfig: {
    requestPlanner: ModelSelector
    codePlanner: ModelSelector
    codingAgent: ModelSelector
  }
  
  // Project settings
  projectConfig: ProjectSettings
  
  // Security settings
  security: SecurityConfig
}
```

#### 3.3 Component Architecture

```
src/web/
├── public/
├── src/
│   ├── components/
│   │   ├── agents/
│   │   │   ├── AgentCard.tsx        # Individual agent status
│   │   │   ├── AgentGraph.tsx       # D3 force-directed graph
│   │   │   └── ModelSelector.tsx    # Dropdown for model choice
│   │   ├── jobs/
│   │   │   ├── JobList.tsx          # Filterable job history
│   │   │   ├── PlanViewer.tsx       # Markdown plan display
│   │   │   └── DiffViewer.tsx       # Syntax-highlighted diffs
│   │   ├── shared/
│   │   │   ├── LogStream.tsx        # Real-time log viewer
│   │   │   ├── MetricsChart.tsx     # Performance graphs
│   │   │   └── Layout.tsx           # App shell
│   │   └── ui/                      # Radix UI components
│   ├── hooks/
│   │   ├── useWebSocket.ts          # WS connection management
│   │   ├── useAgentGraph.ts         # Graph data processing
│   │   └── useJobPersistence.ts     # Session restoration
│   ├── stores/
│   │   ├── agentStore.ts            # Agent state management
│   │   └── uiStore.ts               # UI preferences
│   └── styles/
│       └── globals.css              # Tailwind + custom styles
```

### Phase 4: Visual Polish & UX (Week 5)
**Goal**: Make it beautiful and delightful to use

#### 4.1 Design System
```css
/* Modern, clean aesthetic */
- Gradient accents for AI elements
- Smooth animations (Framer Motion)
- Glass-morphism for overlays
- Consistent spacing (8px grid)
- Accessible color contrasts
```

#### 4.2 Micro-interactions
- Agent cards pulse when active
- Smooth graph transitions
- Log entries slide in
- Model changes animate
- Success/error states transition

#### 4.3 Responsive Design
- Desktop: Full dashboard
- Tablet: Stacked layout
- Mobile: Essential controls only

### Phase 5: Advanced Features (Week 6+)
**Goal**: Next-level functionality

#### 5.1 Agent Intelligence Viewer
```typescript
// Show agent "thoughts"
interface AgentMindView {
  currentContext: string[]      // What agent is considering
  reasoning: string            // Current reasoning process
  alternatives: Decision[]     // Other options considered
  confidence: number          // Confidence in current approach
}
```

#### 5.2 Time Travel Debugging
- Replay agent decisions
- Step through execution
- See alternate paths

#### 5.3 Collaborative Features
- Share dashboard URLs
- Team annotations
- Audit trail

## Technical Implementation Details

### WebSocket Protocol
```typescript
// Client → Server
interface ClientMessage {
  type: 'subscribe' | 'unsubscribe' | 'command'
  topic?: 'agents' | 'jobs' | 'logs'
  data?: any
}

// Server → Client
interface ServerMessage {
  type: 'agent_update' | 'graph_update' | 'log_entry' | 'job_status'
  timestamp: string
  data: any
}
```

### State Persistence
```python
# Redis schema
jobs:{job_id} = {
  "id": "uuid",
  "status": "running|complete|failed",
  "plan": "markdown plan",
  "diff": "git diff",
  "logs": ["log entries"],
  "created_at": "2024-01-01T00:00:00Z",
  "agent_states": {}
}

sessions:{session_id} = {
  "active_jobs": ["job_ids"],
  "ui_state": {},
  "expires_at": "timestamp"
}
```

### Security Model
```python
# Backend proxy for LLM calls
@app.post("/api/proxy/llm")
async def proxy_llm_call(
    request: LLMRequest,
    token: str = Depends(verify_jwt)
):
    # Validate permissions
    # Add rate limiting
    # Make actual LLM call
    # Return response
```

## Migration Strategy

1. **No Breaking Changes**: All new features are additive
2. **Progressive Enhancement**: Terminal UI improvements first
3. **Optional Web UI**: Enable with `--web` flag
4. **Backward Compatible**: Existing CLI commands unchanged

## Success Metrics

- **Performance**: <100ms UI response time
- **Real-time**: <50ms WebSocket latency
- **Reliability**: 99.9% uptime for web dashboard
- **Adoption**: 80% of users try new UI within first month
- **Delight**: "This is beautiful!" feedback

## Conclusion

This plan transforms Codeur from a powerful CLI tool into a modern, beautiful system that developers will love to use. The combination of enhanced terminal UI and new web dashboard provides the best of both worlds: local efficiency and remote monitoring capability.

The phased approach ensures we can deliver value incrementally while building toward the ultimate vision of a chef's kiss frontend experience. 👨‍🍳✨