"""
Data models for the Analyzer agent.
"""

from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class ComponentType(Enum):
    """Types of components in the architecture."""
    SERVICE = "service"
    CONTROLLER = "controller"
    MODEL = "model"
    VIEW = "view"
    UTILITY = "utility"
    MIDDLEWARE = "middleware"
    REPOSITORY = "repository"
    FACTORY = "factory"
    INTERFACE = "interface"
    CONFIG = "config"
    TEST = "test"
    ENTRY_POINT = "entry_point"


class DependencyType(Enum):
    """Types of dependencies between components."""
    IMPORTS = "imports"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    USES = "uses"
    CALLS = "calls"
    INSTANTIATES = "instantiates"
    CONFIGURES = "configures"


@dataclass
class ComponentNode:
    """Represents a component in the architecture."""
    id: str
    name: str
    type: ComponentType
    file_path: str
    module_path: str
    description: str = ""
    symbols: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    metrics: Dict[str, int] = field(default_factory=dict)  # lines, complexity, etc.
    technologies: Set[str] = field(default_factory=set)
    patterns: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'file_path': self.file_path,
            'module_path': self.module_path,
            'description': self.description,
            'symbols': self.symbols,
            'imports': self.imports,
            'exports': self.exports,
            'metrics': self.metrics,
            'technologies': list(self.technologies),
            'patterns': list(self.patterns)
        }


@dataclass
class DependencyEdge:
    """Represents a dependency between components."""
    source_id: str
    target_id: str
    type: DependencyType
    details: Dict[str, Any] = field(default_factory=dict)
    strength: float = 1.0  # 0-1, how strong the dependency is
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'type': self.type.value,
            'details': self.details,
            'strength': self.strength
        }


@dataclass
class ArchitectureGraph:
    """Represents the complete architecture of the project."""
    project_path: str
    components: Dict[str, ComponentNode] = field(default_factory=dict)
    dependencies: List[DependencyEdge] = field(default_factory=list)
    layers: Dict[str, List[str]] = field(default_factory=dict)  # layer -> component IDs
    technologies: Set[str] = field(default_factory=set)
    patterns: Set[str] = field(default_factory=set)
    entry_points: List[str] = field(default_factory=list)  # Component IDs
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_component(self, component: ComponentNode) -> None:
        """Add a component to the graph."""
        self.components[component.id] = component
        self.technologies.update(component.technologies)
        self.patterns.update(component.patterns)
        self.updated_at = datetime.utcnow()
    
    def add_dependency(self, dependency: DependencyEdge) -> None:
        """Add a dependency to the graph."""
        self.dependencies.append(dependency)
        self.updated_at = datetime.utcnow()
    
    def get_component_dependencies(self, component_id: str) -> Dict[str, List[str]]:
        """Get all dependencies for a component."""
        deps = {
            'imports_from': [],
            'imported_by': [],
            'uses': [],
            'used_by': []
        }
        
        for dep in self.dependencies:
            if dep.source_id == component_id:
                deps['imports_from'].append(dep.target_id)
            elif dep.target_id == component_id:
                deps['imported_by'].append(dep.source_id)
        
        return deps
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'project_path': self.project_path,
            'components': {cid: c.to_dict() for cid, c in self.components.items()},
            'dependencies': [d.to_dict() for d in self.dependencies],
            'layers': self.layers,
            'technologies': list(self.technologies),
            'patterns': list(self.patterns),
            'entry_points': self.entry_points,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'stats': {
                'total_components': len(self.components),
                'total_dependencies': len(self.dependencies),
                'total_technologies': len(self.technologies),
                'total_patterns': len(self.patterns)
            }
        }
    
    def to_mermaid(self) -> str:
        """Generate Mermaid diagram code for the architecture."""
        mermaid = "graph TB\n"
        
        # Group components by layer if available
        if self.layers:
            for layer_name, component_ids in self.layers.items():
                mermaid += f"    subgraph {layer_name}\n"
                for comp_id in component_ids:
                    if comp_id in self.components:
                        comp = self.components[comp_id]
                        # Escape special characters and limit name length
                        safe_name = comp.name.replace('"', '').replace("'", "")[:30]
                        mermaid += f'        {comp_id}["{safe_name}"]\n'
                mermaid += "    end\n"
        else:
            # Just add all components
            for comp_id, comp in self.components.items():
                safe_name = comp.name.replace('"', '').replace("'", "")[:30]
                shape = self._get_mermaid_shape(comp.type)
                mermaid += f'    {comp_id}{shape[0]}"{safe_name}"{shape[1]}\n'
        
        # Add dependencies as edges
        for dep in self.dependencies:
            if dep.source_id in self.components and dep.target_id in self.components:
                arrow = self._get_mermaid_arrow(dep.type)
                mermaid += f"    {dep.source_id} {arrow} {dep.target_id}\n"
        
        # Add styling
        mermaid += "\n    %% Styling\n"
        for comp_id, comp in self.components.items():
            color = self._get_component_color(comp.type)
            mermaid += f"    style {comp_id} fill:{color}\n"
        
        return mermaid
    
    def _get_mermaid_shape(self, comp_type: ComponentType) -> tuple:
        """Get Mermaid shape for component type."""
        shapes = {
            ComponentType.SERVICE: ("[", "]"),
            ComponentType.CONTROLLER: ("(", ")"),
            ComponentType.MODEL: ("[", "]"),
            ComponentType.VIEW: ("((", "))"),
            ComponentType.REPOSITORY: ("[", "]"),
            ComponentType.ENTRY_POINT: ("{", "}"),
            ComponentType.CONFIG: ("[", "]")
        }
        return shapes.get(comp_type, ("[", "]"))
    
    def _get_mermaid_arrow(self, dep_type: DependencyType) -> str:
        """Get Mermaid arrow for dependency type."""
        arrows = {
            DependencyType.IMPORTS: "-->",
            DependencyType.INHERITS: "-.->",
            DependencyType.USES: "-->",
            DependencyType.CALLS: "-->",
            DependencyType.IMPLEMENTS: "-.->",
        }
        return arrows.get(dep_type, "-->")
    
    def _get_component_color(self, comp_type: ComponentType) -> str:
        """Get color for component type."""
        colors = {
            ComponentType.SERVICE: "#E8F5E9",
            ComponentType.CONTROLLER: "#E3F2FD",
            ComponentType.MODEL: "#FFF3E0",
            ComponentType.VIEW: "#F3E5F5",
            ComponentType.REPOSITORY: "#FFF9C4",
            ComponentType.ENTRY_POINT: "#FFEBEE",
            ComponentType.CONFIG: "#E0E0E0"
        }
        return colors.get(comp_type, "#F5F5F5")


@dataclass
class AnalysisReport:
    """Report from architecture analysis."""
    graph: ArchitectureGraph
    summary: str
    insights: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    mermaid_diagram: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'graph': self.graph.to_dict(),
            'summary': self.summary,
            'insights': self.insights,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'metrics': self.metrics,
            'mermaid_diagram': self.mermaid_diagram
        }


@dataclass
class ChangeThreshold:
    """Thresholds for triggering re-analysis."""
    files_changed: int = 5
    lines_changed: int = 100
    time_elapsed_hours: int = 24
    force_on_critical_files: List[str] = field(default_factory=lambda: [
        "package.json", "requirements.txt", "pyproject.toml",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle"
    ])