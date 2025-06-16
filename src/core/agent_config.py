"""
Unified agent configuration system.

This module provides centralized configuration for all agent types,
including default model selection, parameters, and capabilities.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class AgentType(Enum):
    """Supported agent types in the system."""
    ARCHITECT = "architect"
    REQUEST_PLANNER = "request_planner"
    CODING = "coding"
    ANALYZER = "analyzer"
    CODE_PLANNER = "code_planner"
    TEST = "test"
    GENERAL = "general"


@dataclass
class AgentConfig:
    """Configuration for a specific agent type."""
    agent_type: AgentType
    default_model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    description: str = ""
    capabilities: list = field(default_factory=list)
    
    def get_model(self) -> str:
        """Get the model for this agent, checking env override first."""
        # Check for environment variable override
        env_key = f"{self.agent_type.value.upper()}_MODEL"
        env_model = os.getenv(env_key)
        return env_model if env_model else self.default_model


# Default agent configurations
# All set to use Gemini 2.5 Flash as requested
AGENT_CONFIGS: Dict[AgentType, AgentConfig] = {
    AgentType.ARCHITECT: AgentConfig(
        agent_type=AgentType.ARCHITECT,
        default_model="gemini-2.5-flash",
        temperature=0.7,
        max_tokens=4000,
        description="High-level system design and task orchestration",
        capabilities=["planning", "architecture", "task_creation"]
    ),
    
    AgentType.REQUEST_PLANNER: AgentConfig(
        agent_type=AgentType.REQUEST_PLANNER,
        default_model="gemini-2.5-flash",
        temperature=0.7,
        max_tokens=3000,
        description="Convert user requests into actionable plans",
        capabilities=["planning", "decomposition", "orchestration"]
    ),
    
    AgentType.CODING: AgentConfig(
        agent_type=AgentType.CODING,
        default_model="gemini-2.5-flash",
        temperature=0.2,  # Lower temperature for more consistent code
        max_tokens=4000,
        description="Generate code patches and implementations",
        capabilities=["coding", "patching", "refactoring"]
    ),
    
    AgentType.ANALYZER: AgentConfig(
        agent_type=AgentType.ANALYZER,
        default_model="gemini-2.5-flash",
        temperature=0.5,
        max_tokens=2000,
        description="Analyze code architecture and patterns",
        capabilities=["analysis", "pattern_detection", "reporting"]
    ),
    
    AgentType.CODE_PLANNER: AgentConfig(
        agent_type=AgentType.CODE_PLANNER,
        default_model="gemini-2.5-flash",
        temperature=0.7,
        max_tokens=3000,
        description="Plan code-level implementation details",
        capabilities=["code_planning", "task_breakdown"]
    ),
    
    AgentType.TEST: AgentConfig(
        agent_type=AgentType.TEST,
        default_model="gemini-2.5-flash",
        temperature=0.3,  # Lower for test consistency
        max_tokens=3000,
        description="Generate and update test cases",
        capabilities=["testing", "test_generation", "validation"]
    ),
    
    AgentType.GENERAL: AgentConfig(
        agent_type=AgentType.GENERAL,
        default_model="gemini-2.5-flash",
        temperature=0.7,
        max_tokens=2000,
        description="General purpose agent for various tasks",
        capabilities=["general"]
    ),
}


class AgentConfigManager:
    """Manager for agent configurations."""
    
    @staticmethod
    def get_config(agent_type: str) -> AgentConfig:
        """
        Get configuration for an agent type.
        
        Args:
            agent_type: String name of the agent type
            
        Returns:
            AgentConfig for the specified type
        """
        # Convert string to enum
        try:
            agent_enum = AgentType(agent_type.lower())
        except ValueError:
            # Default to general if unknown type
            agent_enum = AgentType.GENERAL
            
        return AGENT_CONFIGS.get(agent_enum, AGENT_CONFIGS[AgentType.GENERAL])
    
    @staticmethod
    def get_model_for_agent(agent_type: str) -> str:
        """
        Get the model for a specific agent type.
        
        Args:
            agent_type: String name of the agent type
            
        Returns:
            Model name to use
        """
        config = AgentConfigManager.get_config(agent_type)
        return config.get_model()
    
    @staticmethod
    def get_all_configs() -> Dict[str, AgentConfig]:
        """Get all agent configurations."""
        return {agent.value: config for agent, config in AGENT_CONFIGS.items()}
    
    @staticmethod
    def update_default_model(agent_type: str, model: str) -> None:
        """
        Update the default model for an agent type.
        
        This is useful for runtime configuration changes.
        
        Args:
            agent_type: String name of the agent type
            model: New default model name
        """
        try:
            agent_enum = AgentType(agent_type.lower())
            if agent_enum in AGENT_CONFIGS:
                AGENT_CONFIGS[agent_enum].default_model = model
        except ValueError:
            pass
    
    @staticmethod
    def update_all_models(model: str) -> None:
        """
        Update all agent types to use the same model.
        
        Args:
            model: Model name to use for all agents
        """
        for config in AGENT_CONFIGS.values():
            config.default_model = model


# Helper function for backward compatibility
def get_agent_model(agent_type: str) -> str:
    """Get the model for an agent type (backward compatible helper)."""
    return AgentConfigManager.get_model_for_agent(agent_type)