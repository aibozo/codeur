"""
Architect Agent package.

The Architect agent is responsible for high-level project design,
task graph creation, orchestrating the overall development process,
and managing detailed implementation plans with deep context passing.
"""

from .architect import Architect
from .models import TaskGraph, TaskNode, ProjectStructure, TaskPriority, TaskStatus
from .enhanced_task_graph import (
    EnhancedTaskGraph, EnhancedTaskNode, TaskCommunity, 
    TaskGranularity, DisplayMode, RAGContext
)
from .community_detector import CommunityDetector, CommunityTheme
from .task_graph_manager import TaskGraphManager, TaskGraphContext

# Deep Context Passing System
from .plan_models import (
    ImplementationPlan, ImplementationPhase, PlanMilestone, PlanChunk,
    PlanStatus, PhaseType
)
from .plan_manager import PlanManager
from .plan_storage import PlanStorage
from .plan_rag_integration import PlanRAGIntegration
from .plan_aware_architect import PlanAwareArchitect
from .plan_api import PlanAPI, get_context_for_agent, format_implementation_guide

# Context-aware capabilities (if exists)
try:
    from .context_aware_architect import ContextAwareArchitect, create_context_aware_architect
    CONTEXT_AWARE_AVAILABLE = True
except ImportError:
    CONTEXT_AWARE_AVAILABLE = False

__all__ = [
    # Core architect functionality
    'Architect', 
    'TaskGraph', 
    'TaskNode', 
    'ProjectStructure',
    'TaskPriority',
    'TaskStatus',
    'EnhancedTaskGraph',
    'EnhancedTaskNode',
    'TaskCommunity',
    'TaskGranularity',
    'DisplayMode',
    'RAGContext',
    'CommunityDetector',
    'CommunityTheme',
    'TaskGraphManager',
    'TaskGraphContext',
    
    # Deep context passing system
    'ImplementationPlan',
    'ImplementationPhase', 
    'PlanMilestone',
    'PlanChunk',
    'PlanStatus',
    'PhaseType',
    'PlanManager',
    'PlanStorage',
    'PlanRAGIntegration',
    'PlanAwareArchitect',
    'PlanAPI',
    'get_context_for_agent',
    'format_implementation_guide'
]

# Add context-aware exports if available
if CONTEXT_AWARE_AVAILABLE:
    __all__.extend([
        'ContextAwareArchitect',
        'create_context_aware_architect'
    ])