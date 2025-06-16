# Frontend Visual Mockups & Specifications

## Web Dashboard Mockup

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 🤖 Codeur Dashboard                                    [Settings] [Docs] [User]  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ ┌─── Agents (3/3 active) ──┐ ┌─────────── Agent Network Graph ──────────┐ ┌─── │
│ │                           │ │                                          │ │ S  │
│ │ 📋 Request Planner       │ │         [Request Planner]                │ │ y  │
│ │ 🟢 Active | Claude Opus  │ │              ↓      ↓                    │ │ s  │
│ │ ▼ Model: [Opus ▼]        │ │     [Code Planner] [RAG Service]        │ │ t  │
│ │                           │ │         ↓               ↓                │ │ e  │
│ │ 🔧 Code Planner          │ │    [Coding Agent]←─────┘                 │ │ m  │
│ │ 🟡 Idle | GPT-4         │ │         ↓                                │ │    │
│ │ ▼ Model: [GPT-4 ▼]       │ │    [Git Operations]                     │ │ 📊 │
│ │                           │ │                                          │ │    │
│ │ ✏️  Coding Agent          │ │ Nodes pulse when active                  │ │ CPU │
│ │ 🟢 Active | Claude 3.5   │ │ Edges show data flow direction          │ │ 45% │
│ │ ▼ Model: [Claude 3.5 ▼]  │ │                                          │ │    │
│ │                           │ └──────────────────────────────────────────┘ │ Mem │
│ └───────────────────────────┘                                              │ 2.1G│
│                                                                             │    │
│ ┌─── Current Job: Implementing Authentication ─────────────────────────────┐ │ Q  │
│ │ Status: 🟢 Running | Started: 2 min ago | Progress: ████████░░ 75%      │ │ 3  │
│ │                                                                          │ └────┘
│ │ 📄 Plan                          🔍 Diff                    📋 Logs     │
│ │ ┌────────────────────────────┐ ┌─────────────────────┐ ┌──────────────┐
│ │ │ ## Authentication Plan      │ │ + def authenticate():│ │ [14:23] 🤖  │
│ │ │                             │ │ +     """Verify user │ │ Starting... │
│ │ │ 1. Add JWT library          │ │ +     credentials""" │ │ [14:23] 📋  │
│ │ │ 2. Create auth middleware   │ │ +     token = request│ │ Planning... │
│ │ │ 3. Add login endpoint       │ │ +     if not token:  │ │ [14:24] 🔧  │
│ │ │ 4. Secure existing routes   │ │ +         raise 401  │ │ Analyzing.. │
│ │ │                             │ │                      │ │ [14:25] ✏️  │
│ │ │ The agent will implement... │ │ 15 files changed     │ │ Writing...  │
│ │ └────────────────────────────┘ └─────────────────────┘ └──────────────┘
│ │                                                                          │
│ │ [🔄 Refresh] [⏸️ Pause] [🛑 Stop] [↩️ Revert] [📤 Export]               │
│ └──────────────────────────────────────────────────────────────────────────┘
│                                                                             │
│ ┌─── Live Logs ────────────────────────────────────────────────[▼ Follow]─┐
│ │ [2024-01-15 14:25:32] INFO  coding_agent: Writing auth.py               │
│ │ [2024-01-15 14:25:33] DEBUG request_planner: Context window: 8K/32K    │
│ │ [2024-01-15 14:25:34] INFO  git_ops: Creating branch: feature/auth     │
│ │ [2024-01-15 14:25:35] WARN  validator: Line 45 exceeds 120 chars       │
│ └──────────────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Terminal Dashboard Mockup

```
┌─ Codeur Monitor ────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  Agents                          Active Job                    System           │
│ ┌─────────────────────────┐ ┌─────────────────────────┐ ┌───────────────────┐ │
│ │ 📋 Request Planner     │ │ 🔄 Adding Authentication │ │ CPU:    ▇▇▇▇░ 45% │ │
│ │    Status: 🟢 Active   │ │    Progress: ████████░░  │ │ Memory: ▇▇░░░ 2.1G│ │
│ │    Model:  Opus        │ │    Duration: 00:02:34    │ │ Queue:  3 pending │ │
│ │    Task:   Planning... │ │    Agent:    Coding      │ │ Tokens: 15.2K     │ │
│ ├─────────────────────────┤ ├─────────────────────────┤ └───────────────────┘ │
│ │ 🔧 Code Planner        │ │ Recent Actions:          │                       │
│ │    Status: 🟡 Idle     │ │ ✓ Analyzed 15 files      │   Agent Graph        │
│ │    Model:  GPT-4       │ │ ✓ Generated plan         │ ┌─────────────────┐ │
│ │    Last:   2 min ago   │ │ ⚡ Writing auth.py       │ │   RP → CP → CA  │ │
│ ├─────────────────────────┤ │ ⏳ Pending: tests        │ │    ↓         ↓   │ │
│ │ ✏️  Coding Agent        │ └─────────────────────────┘ │   RAG ← ← ← Git  │ │
│ │    Status: 🟢 Active   │                               └─────────────────┘ │
│ │    Model:  Claude 3.5  │ ┌─ Current Plan ─────────────────────────────────┐ │
│ │    Task:   Writing...  │ │ 1. Install PyJWT library                        │ │
│ └─────────────────────────┘ │ 2. Create authentication middleware             │ │
│                             │ 3. Add login/logout endpoints                   │ │
│ Model Selection:            │ 4. Secure existing API routes                   │ │
│ [1] Request Planner → Opus  │ 5. Add tests for auth flow                      │ │
│ [2] Code Planner → GPT-4    └─────────────────────────────────────────────────┘ │
│ [3] Coding Agent → Claude   ┌─ Logs ─────────────────────────────[↓ Auto]────┐ │
│ [Q] Quit  [P] Pause  [?]    │ 14:25:32 INFO  Writing authentication module    │ │
│                             │ 14:25:33 DEBUG Token usage: 15,234 / 32,000    │ │
└─────────────────────────────┘─────────────────────────────────────────────────┘
```

## Key Visual Elements

### 1. Agent Cards
```
┌─────────────────────┐
│ 🤖 Agent Name       │  ← Icon indicates agent type
│ 🟢 Status | Model   │  ← Status: 🟢 Active 🟡 Idle 🔴 Error
│ ▼ Model: [Select ▼] │  ← Dropdown for model selection
│ Current task info   │  ← Real-time task description
└─────────────────────┘
```

### 2. Agent Network Graph
- **Nodes**: Circles with agent icons, pulse when active
- **Edges**: Animated arrows showing data flow
- **Colors**: Match agent status (green=active, yellow=idle)
- **Interactions**: Hover for details, click to focus

### 3. Job Progress Panel
```
┌──────────────────────────────────────┐
│ Job Title                            │
│ Status | Time | Progress Bar         │
│                                      │
│ [Plan] [Diff] [Logs] ← Tabs         │
│ ┌──────────────────────────────────┐ │
│ │ Tab content area                 │ │
│ └──────────────────────────────────┘ │
│                                      │
│ [Action Buttons] ← Contextual       │
└──────────────────────────────────────┘
```

### 4. Real-time Elements
- **Pulsing dots** for active operations
- **Smooth progress bars** with percentage
- **Streaming logs** with syntax highlighting
- **Live metrics** with sparkline graphs

## Color Palette

### Dark Theme (Default)
```
Background:     #0A0A0B   (Near black)
Surface:        #1A1A1D   (Dark gray)
Border:         #2A2A2D   (Subtle border)
Text Primary:   #FFFFFF   (Pure white)
Text Secondary: #A0A0A0   (Muted gray)

Primary:        #00D9FF   (Cyan)
Success:        #00FF88   (Green)
Warning:        #FFB800   (Amber)
Error:          #FF0066   (Pink)
Info:           #B794F4   (Purple)

Gradient 1:     #00D9FF → #B794F4
Gradient 2:     #1A1A1D → #2D2D30
```

### Light Theme (Optional)
```
Background:     #FFFFFF
Surface:        #F7F7F8
Border:         #E0E0E0
Text Primary:   #000000
Text Secondary: #666666

(Same accent colors with adjusted saturation)
```

## Interactive Elements

### 1. Model Selector Dropdown
```
┌─────────────────┐
│ Claude Opus  ▼ │ ← Click to open
├─────────────────┤
│ ✓ Claude Opus   │ ← Current selection
│   Claude 3.5    │
│   GPT-4         │
│   GPT-3.5       │
│   Llama 2       │
└─────────────────┘
```

### 2. Hover States
- **Agent nodes**: Show detailed stats
- **Log entries**: Expand to show full message
- **Buttons**: Subtle glow effect

### 3. Animations
- **Page transitions**: Smooth slide
- **Graph updates**: Spring physics
- **Progress bars**: Smooth increments
- **Status changes**: Fade transitions

## Responsive Breakpoints

### Desktop (1200px+)
- Full 3-column layout
- Side-by-side panels
- Large graph view

### Tablet (768px-1199px)
- 2-column layout
- Stacked job details
- Compact graph

### Mobile (< 768px)
- Single column
- Collapsible sections
- Essential controls only

## Accessibility

- **ARIA labels** on all interactive elements
- **Keyboard navigation** support
- **High contrast mode** option
- **Screen reader** friendly
- **WCAG AA** compliant colors

This design creates a modern, professional interface that's both beautiful and functional, providing real-time insights while maintaining usability across all devices.