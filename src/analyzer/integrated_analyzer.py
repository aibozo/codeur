"""
Integrated Analyzer Agent
========================

This module provides the integrated version of the Analyzer agent
that works with the task graph and event system.
"""

from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from ..core.integrated_agent_base import IntegratedAgentBase, AgentContext
from .analyzer import Analyzer


class IntegratedAnalyzer(IntegratedAgentBase):
    """Analyzer with full system integration."""
    
    def __init__(self, context: AgentContext):
        """Initialize integrated analyzer."""
        super().__init__(context)
        
        # Create base analyzer
        self.analyzer = Analyzer(
            project_path=str(context.project_path),
            rag_service=None  # We'll use the context's rag_client directly
        )
        
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities."""
        return ["analysis", "architecture_review", "quality_check"]
        
    def get_integration_level(self) -> str:
        """Return integration level."""
        return "full"
        
    async def on_task_assigned(self, task: Dict[str, Any]) -> None:
        """Handle task assignment."""
        await self.publish_event("agent.task_assigned", {
            "agent_id": self.agent_id,
            "task_id": task["id"]
        })
        
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an analysis task."""
        await self.publish_event("task.started", {
            "task_id": task["id"],
            "agent_id": self.agent_id
        })
        
        try:
            # Extract analysis request
            analysis_type = task.get("analysis_type", "architecture")
            target_files = task.get("target_files", [])
            
            if analysis_type == "architecture":
                result = await self.analyze_architecture()
            elif analysis_type == "dependencies":
                result = await self.analyze_dependencies(target_files)
            elif analysis_type == "quality":
                result = await self.analyze_code_quality(target_files)
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            # Create task result
            task_result = {
                "status": "completed",
                "analysis": result,
                "type": analysis_type
            }
            
            await self.publish_event("task.completed", {
                "task_id": task["id"],
                "agent_id": self.context.agent_id,
                "result": task_result
            })
            
            return task_result
            
        except Exception as e:
            error_result = {
                "status": "failed",
                "error": str(e)
            }
            
            await self.publish_event("task.failed", {
                "task_id": task["id"],
                "agent_id": self.context.agent_id,
                "error": str(e)
            })
            
            return error_result
            
    async def analyze_architecture(self) -> Dict[str, Any]:
        """Analyze project architecture."""
        # Publish analysis start event
        if self._event_integration:
            await self._event_integration.publish_event("analysis.started", {
                "type": "architecture",
                "agent_id": self.context.agent_id
            })
        
        # Run analysis
        result = await self.analyzer.analyze()
        
        # Publish results
        if self._event_integration:
            # Handle AnalysisReport object
            if hasattr(result, 'graph'):
                component_count = len(result.graph.components)
                dependency_count = len(result.graph.dependencies)
            else:
                # Fallback for dict result
                component_count = len(result.get("components", []))
                dependency_count = len(result.get("dependencies", []))
                
            await self._event_integration.publish_event("analysis.completed", {
                "type": "architecture",
                "agent_id": self.context.agent_id,
                "component_count": component_count,
                "dependency_count": dependency_count
            })
        
        # Convert to dict if it's an AnalysisReport object
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        
        return result
        
    async def analyze_dependencies(self, files: List[str]) -> Dict[str, Any]:
        """Analyze dependencies for specific files."""
        # Run dependency analysis
        dependencies = {}
        for file in files:
            deps = self.analyzer.analyze_file_dependencies(file)
            dependencies[file] = deps
            
        return {
            "files": files,
            "dependencies": dependencies,
            "summary": self._summarize_dependencies(dependencies)
        }
        
    async def analyze_code_quality(self, files: List[str]) -> Dict[str, Any]:
        """Analyze code quality metrics."""
        # Run quality analysis
        metrics = {}
        for file in files:
            file_metrics = self.analyzer.analyze_file_quality(file)
            metrics[file] = file_metrics
            
        return {
            "files": files,
            "metrics": metrics,
            "summary": self._summarize_quality(metrics)
        }
        
    def _summarize_dependencies(self, dependencies: Dict[str, List[str]]) -> Dict[str, Any]:
        """Summarize dependency analysis."""
        all_deps = set()
        for deps in dependencies.values():
            all_deps.update(deps)
            
        return {
            "total_files": len(dependencies),
            "unique_dependencies": len(all_deps),
            "most_common": self._get_most_common(dependencies)
        }
        
    def _summarize_quality(self, metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize quality metrics."""
        total_lines = sum(m.get("lines", 0) for m in metrics.values())
        avg_complexity = sum(m.get("complexity", 0) for m in metrics.values()) / max(len(metrics), 1)
        
        return {
            "total_files": len(metrics),
            "total_lines": total_lines,
            "average_complexity": avg_complexity
        }
        
    def _get_most_common(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """Get most common dependencies."""
        dep_count = {}
        for deps in dependencies.values():
            for dep in deps:
                dep_count[dep] = dep_count.get(dep, 0) + 1
                
        # Sort by count and return top 5
        sorted_deps = sorted(dep_count.items(), key=lambda x: x[1], reverse=True)
        return [dep for dep, _ in sorted_deps[:5]]