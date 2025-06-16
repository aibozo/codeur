"""
UI state management for both terminal and web interfaces.
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
from enum import Enum


class ViewMode(str, Enum):
    """Available view modes."""
    DASHBOARD = "dashboard"
    MONITOR = "monitor"
    JOB_DETAIL = "job_detail"
    SETTINGS = "settings"


class AgentStatus(str, Enum):
    """Agent status states."""
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentState:
    """State of an individual agent."""
    agent_type: str
    status: AgentStatus
    model: str
    current_task: Optional[str] = None
    last_active: Optional[datetime] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type,
            "status": self.status.value,
            "model": self.model,
            "current_task": self.current_task,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "metrics": self.metrics
        }


@dataclass
class JobState:
    """State of a job/task."""
    job_id: str
    title: str
    status: str
    progress: float
    created_at: datetime
    updated_at: datetime
    agent_type: Optional[str] = None
    plan: Optional[str] = None
    diff: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "title": self.title,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "agent_type": self.agent_type,
            "plan": self.plan,
            "diff": self.diff,
            "logs": self.logs
        }


class UIState:
    """Central UI state management."""
    
    def __init__(self):
        """Initialize UI state."""
        self.view_mode = ViewMode.DASHBOARD
        self.agents: Dict[str, AgentState] = {}
        self.current_job: Optional[JobState] = None
        self.job_history: List[JobState] = []
        self.metrics: Dict[str, Any] = {
            "cpu": 0,
            "memory": 0,
            "queue_size": 0,
            "total_tokens": 0
        }
        self.preferences: Dict[str, Any] = {
            "theme": "dark",
            "auto_scroll_logs": True,
            "show_debug_logs": False,
            "graph_layout": "force-directed"
        }
        self._observers: List[Callable] = []
        
    def add_observer(self, callback: Callable):
        """Add state change observer."""
        self._observers.append(callback)
        
    def remove_observer(self, callback: Callable):
        """Remove state change observer."""
        if callback in self._observers:
            self._observers.remove(callback)
            
    def _notify_observers(self):
        """Notify all observers of state change."""
        for observer in self._observers:
            try:
                observer(self)
            except Exception:
                pass  # Ignore observer errors
                
    def update_agent(self, agent_type: str, **kwargs):
        """Update agent state."""
        if agent_type not in self.agents:
            self.agents[agent_type] = AgentState(
                agent_type=agent_type,
                status=AgentStatus.OFFLINE,
                model="unknown"
            )
            
        agent = self.agents[agent_type]
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
                
        if agent.status == AgentStatus.ACTIVE:
            agent.last_active = datetime.now()
            
        self._notify_observers()
        
    def set_current_job(self, job: JobState):
        """Set the current active job."""
        self.current_job = job
        self._notify_observers()
        
    def add_job_to_history(self, job: JobState):
        """Add completed job to history."""
        self.job_history.insert(0, job)
        # Keep only last 100 jobs
        self.job_history = self.job_history[:100]
        self._notify_observers()
        
    def update_metrics(self, **kwargs):
        """Update system metrics."""
        self.metrics.update(kwargs)
        self._notify_observers()
        
    def set_preference(self, key: str, value: Any):
        """Update UI preference."""
        self.preferences[key] = value
        self._notify_observers()
        
    def get_active_agents(self) -> List[AgentState]:
        """Get list of active agents."""
        return [
            agent for agent in self.agents.values()
            if agent.status == AgentStatus.ACTIVE
        ]
        
    def export_state(self) -> str:
        """Export current state as JSON."""
        state_dict = {
            "view_mode": self.view_mode.value,
            "agents": {k: v.to_dict() for k, v in self.agents.items()},
            "current_job": self.current_job.to_dict() if self.current_job else None,
            "metrics": self.metrics,
            "preferences": self.preferences
        }
        return json.dumps(state_dict, indent=2)
        
    def import_state(self, state_json: str):
        """Import state from JSON."""
        try:
            state_dict = json.loads(state_json)
            
            # Restore view mode
            self.view_mode = ViewMode(state_dict.get("view_mode", "dashboard"))
            
            # Restore agents
            for agent_type, agent_data in state_dict.get("agents", {}).items():
                self.agents[agent_type] = AgentState(
                    agent_type=agent_type,
                    status=AgentStatus(agent_data["status"]),
                    model=agent_data["model"],
                    current_task=agent_data.get("current_task"),
                    last_active=datetime.fromisoformat(agent_data["last_active"]) 
                        if agent_data.get("last_active") else None,
                    metrics=agent_data.get("metrics", {})
                )
                
            # Restore other state
            self.metrics.update(state_dict.get("metrics", {}))
            self.preferences.update(state_dict.get("preferences", {}))
            
            self._notify_observers()
            
        except Exception as e:
            raise ValueError(f"Failed to import state: {e}")