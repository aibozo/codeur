"""
Consistent color schemes for terminal UI.

Based on the design specification from FRONTEND_MOCKUPS.md
"""

# Dark theme with accent colors
THEME = {
    # Base colors
    "background": "#0A0A0B",  # Near black
    "surface": "#1A1A1D",     # Dark gray
    "border": "#2A2A2D",      # Subtle border
    "text_primary": "#FFFFFF", # Pure white
    "text_secondary": "#A0A0A0", # Muted gray
    
    # Accent colors
    "primary": "#00D9FF",     # Cyan - Headers, active elements
    "success": "#00FF88",     # Green - Successful operations
    "warning": "#FFB800",     # Amber - Warnings, idle states
    "error": "#FF0066",       # Pink - Errors, failures
    "info": "#B794F4",        # Purple - Special elements, AI actions
}

# Rich style mappings
RICH_STYLES = {
    "heading": f"bold {THEME['primary']}",
    "success": f"bold {THEME['success']}",
    "warning": f"bold {THEME['warning']}",
    "error": f"bold {THEME['error']}",
    "info": f"{THEME['info']}",
    "dim": "dim white",
    "active": f"{THEME['success']}",
    "idle": f"{THEME['warning']}",
    "offline": "dim white"
}

# Agent type icons
AGENT_ICONS = {
    "request_planner": "📋",
    "code_planner": "🔧", 
    "coding_agent": "✏️",
    "rag_service": "🔍",
    "git_operations": "📦",
    "monitoring": "📊",
    "security": "🔒"
}

# Status indicators
STATUS_SYMBOLS = {
    "active": "🟢",
    "idle": "🟡",
    "error": "🔴",
    "pending": "⏳",
    "completed": "✓",
    "failed": "✗",
    "running": "⚡",
    "paused": "⏸️"
}