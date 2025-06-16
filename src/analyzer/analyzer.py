"""
Analyzer Agent implementation.

The Analyzer automatically analyzes project architecture, generates diagrams,
and maintains up-to-date architectural documentation.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import re
import ast

from .models import (
    ArchitectureGraph, ComponentNode, DependencyEdge,
    ComponentType, DependencyType, AnalysisReport, ChangeThreshold
)
from src.core.logging import get_logger

# Optional imports
try:
    from src.rag_service import RAGService, RAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAGService = None
    RAGClient = None
    RAG_AVAILABLE = False

# Import change tracker
try:
    from src.core.change_tracker import ChangeTracker, get_change_tracker
    CHANGE_TRACKING_AVAILABLE = True
except ImportError:
    ChangeTracker = None
    get_change_tracker = None
    CHANGE_TRACKING_AVAILABLE = False

logger = get_logger(__name__)


class Analyzer:
    """
    The Analyzer agent that automatically analyzes and documents architecture.
    """
    
    def __init__(
        self,
        project_path: str,
        rag_service: Optional[Any] = None,
        thresholds: Optional[ChangeThreshold] = None,
        auto_analyze: bool = True
    ):
        """
        Initialize the Analyzer agent.
        
        Args:
            project_path: Root path of the project
            rag_service: RAG service for storing analysis results
            thresholds: Thresholds for triggering re-analysis
            auto_analyze: Whether to automatically analyze on threshold events
        """
        self.project_path = Path(project_path).resolve()
        self.thresholds = thresholds or ChangeThreshold()
        self.graph = ArchitectureGraph(project_path=str(self.project_path))
        self.auto_analyze = auto_analyze
        self._analysis_lock = asyncio.Lock()
        
        # Initialize RAG if available
        if rag_service:
            self.rag_service = rag_service
            self.rag_client = RAGClient(service=rag_service) if RAG_AVAILABLE else None
        elif RAG_AVAILABLE:
            rag_dir = self.project_path / ".rag"
            rag_dir.mkdir(exist_ok=True)
            self.rag_service = RAGService(
                persist_directory=str(rag_dir),
                repo_path=str(self.project_path)
            )
            self.rag_client = RAGClient(service=self.rag_service)
        else:
            self.rag_service = None
            self.rag_client = None
        
        # Setup change tracking if available
        if auto_analyze and CHANGE_TRACKING_AVAILABLE:
            self._setup_change_tracking()
        
        # Create analysis output directory
        self.output_dir = self.project_path / ".architecture"
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"Analyzer initialized for project: {self.project_path}")
    
    def _setup_change_tracking(self):
        """Setup change tracking for automatic analysis."""
        if not CHANGE_TRACKING_AVAILABLE:
            logger.warning("Change tracking not available - automatic analysis disabled")
            return
        
        # Get or create change tracker
        change_tracker = get_change_tracker()
        
        # Add callback for threshold events
        def on_threshold_reached(metrics):
            logger.info(f"Change threshold reached: {metrics.total_lines_changed} lines changed")
            # Run analysis in background
            asyncio.create_task(self._run_analysis_safe())
        
        change_tracker.add_threshold_callback(on_threshold_reached)
        
        logger.info("Change tracking enabled for automatic analysis")
    
    async def _run_analysis_safe(self):
        """Run analysis with lock to prevent concurrent analyses."""
        async with self._analysis_lock:
            try:
                await self.analyze(force=True)
            except Exception as e:
                logger.error(f"Auto-analysis failed: {e}")
    
    async def analyze(self, force: bool = False) -> AnalysisReport:
        """
        Analyze the project architecture.
        
        Args:
            force: Force analysis even if recent analysis exists
            
        Returns:
            AnalysisReport with findings
        """
        logger.info("Starting architecture analysis...")
        
        # Check if recent analysis exists
        if not force and self._has_recent_analysis():
            logger.info("Using cached analysis")
            return self._load_cached_analysis()
        
        # Clear existing graph
        self.graph = ArchitectureGraph(project_path=str(self.project_path))
        
        # Phase 1: Discover components
        await self._discover_components()
        
        # Phase 2: Analyze dependencies
        await self._analyze_dependencies()
        
        # Phase 3: Detect patterns and layers
        await self._detect_patterns()
        
        # Phase 4: Generate insights
        report = await self._generate_report()
        
        # Save analysis results
        await self._save_analysis(report)
        
        # Update RAG if available
        if self.rag_client:
            await self._update_rag(report)
        
        logger.info(f"Analysis complete: {len(self.graph.components)} components, {len(self.graph.dependencies)} dependencies")
        
        return report
    
    async def _discover_components(self):
        """Discover all components in the project."""
        logger.info("Discovering components...")
        
        # File patterns for different component types
        patterns = {
            ComponentType.CONTROLLER: ["*controller*", "*handler*", "*route*"],
            ComponentType.SERVICE: ["*service*", "*manager*", "*provider*"],
            ComponentType.MODEL: ["*model*", "*schema*", "*entity*"],
            ComponentType.VIEW: ["*view*", "*component*", "*page*"],
            ComponentType.REPOSITORY: ["*repository*", "*repo*", "*dao*"],
            ComponentType.CONFIG: ["config*", "settings*", "*config.py", "*config.js"],
            ComponentType.TEST: ["test_*", "*_test*", "*spec*"],
            ComponentType.ENTRY_POINT: ["main*", "app*", "index*", "server*", "__main__*"]
        }
        
        for comp_type, file_patterns in patterns.items():
            for pattern in file_patterns:
                files = list(self.project_path.rglob(pattern))
                for file_path in files:
                    if self._should_analyze_file(file_path):
                        component = await self._analyze_file(file_path, comp_type)
                        if component:
                            self.graph.add_component(component)
        
        # Find entry points
        for comp_id, comp in self.graph.components.items():
            if comp.type == ComponentType.ENTRY_POINT or "main" in comp.name.lower():
                self.graph.entry_points.append(comp_id)
    
    async def _analyze_file(self, file_path: Path, suggested_type: ComponentType) -> Optional[ComponentNode]:
        """Analyze a single file to extract component information."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Skip if too small or too large
            if len(content) < 10 or len(content) > 100000:
                return None
            
            # Create component
            component = ComponentNode(
                id=self._generate_component_id(file_path),
                name=file_path.stem,
                type=suggested_type,
                file_path=str(file_path.relative_to(self.project_path)),
                module_path=self._get_module_path(file_path)
            )
            
            # Extract based on file type
            if file_path.suffix == '.py':
                self._analyze_python_file(content, component)
            elif file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
                self._analyze_javascript_file(content, component)
            elif file_path.suffix in ['.java']:
                self._analyze_java_file(content, component)
            
            # Add metrics
            component.metrics = {
                'lines': len(content.splitlines()),
                'size_bytes': len(content.encode('utf-8'))
            }
            
            return component
            
        except Exception as e:
            logger.debug(f"Failed to analyze {file_path}: {e}")
            return None
    
    def _analyze_python_file(self, content: str, component: ComponentNode):
        """Extract information from Python file."""
        try:
            tree = ast.parse(content)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        component.imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        component.imports.append(node.module)
                
                # Extract class and function names
                elif isinstance(node, ast.ClassDef):
                    component.symbols.append(f"class {node.name}")
                elif isinstance(node, ast.FunctionDef):
                    component.symbols.append(f"def {node.name}")
            
            # Detect patterns
            if any("Controller" in s for s in component.symbols):
                component.patterns.add("MVC")
            if any("Repository" in s for s in component.symbols):
                component.patterns.add("Repository Pattern")
            
            # Detect technologies
            if "flask" in component.imports or "Flask" in content:
                component.technologies.add("Flask")
            if "django" in component.imports:
                component.technologies.add("Django")
            if "fastapi" in component.imports or "FastAPI" in content:
                component.technologies.add("FastAPI")
                
        except:
            # Fall back to regex if AST parsing fails
            imports = re.findall(r'(?:from|import)\s+(\S+)', content)
            component.imports.extend(imports)
    
    def _analyze_javascript_file(self, content: str, component: ComponentNode):
        """Extract information from JavaScript/TypeScript file."""
        # Extract imports
        imports = re.findall(r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]', content)
        component.imports.extend(imports)
        
        # Extract exports
        exports = re.findall(r'export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)', content)
        component.exports.extend(exports)
        
        # Extract class and function names
        classes = re.findall(r'class\s+(\w+)', content)
        functions = re.findall(r'function\s+(\w+)', content)
        component.symbols.extend([f"class {c}" for c in classes])
        component.symbols.extend([f"function {f}" for f in functions])
        
        # Detect technologies
        if "react" in component.imports or "React" in content:
            component.technologies.add("React")
        if "express" in component.imports:
            component.technologies.add("Express")
        if "@angular" in content:
            component.technologies.add("Angular")
        if "vue" in component.imports:
            component.technologies.add("Vue")
    
    def _analyze_java_file(self, content: str, component: ComponentNode):
        """Extract information from Java file."""
        # Extract imports
        imports = re.findall(r'import\s+([\w.]+);', content)
        component.imports.extend(imports)
        
        # Extract class names
        classes = re.findall(r'(?:public\s+)?class\s+(\w+)', content)
        component.symbols.extend([f"class {c}" for c in classes])
        
        # Detect patterns
        if "@Controller" in content:
            component.patterns.add("Spring MVC")
        if "@Service" in content:
            component.patterns.add("Service Layer")
        if "@Repository" in content:
            component.patterns.add("Repository Pattern")
        
        # Detect technologies
        if "springframework" in str(component.imports):
            component.technologies.add("Spring")
    
    async def _analyze_dependencies(self):
        """Analyze dependencies between components."""
        logger.info("Analyzing dependencies...")
        
        for source_id, source in self.graph.components.items():
            for imp in source.imports:
                # Find target component
                target = self._find_component_by_import(imp)
                if target:
                    dep = DependencyEdge(
                        source_id=source_id,
                        target_id=target.id,
                        type=DependencyType.IMPORTS,
                        details={'import': imp}
                    )
                    self.graph.add_dependency(dep)
    
    async def _detect_patterns(self):
        """Detect architectural patterns and organize into layers."""
        logger.info("Detecting patterns and layers...")
        
        # Organize into layers based on component types
        layers = {
            "Presentation": [],
            "Business": [],
            "Data": [],
            "Infrastructure": []
        }
        
        for comp_id, comp in self.graph.components.items():
            if comp.type in [ComponentType.VIEW, ComponentType.CONTROLLER]:
                layers["Presentation"].append(comp_id)
            elif comp.type in [ComponentType.SERVICE, ComponentType.FACTORY]:
                layers["Business"].append(comp_id)
            elif comp.type in [ComponentType.MODEL, ComponentType.REPOSITORY]:
                layers["Data"].append(comp_id)
            elif comp.type in [ComponentType.CONFIG, ComponentType.MIDDLEWARE]:
                layers["Infrastructure"].append(comp_id)
        
        # Only include non-empty layers
        self.graph.layers = {k: v for k, v in layers.items() if v}
        
        # Detect common patterns
        if layers["Presentation"] and layers["Business"] and layers["Data"]:
            self.graph.patterns.add("Layered Architecture")
        
        if any("Controller" in str(c.symbols) for c in self.graph.components.values()):
            self.graph.patterns.add("MVC Pattern")
    
    async def _generate_report(self) -> AnalysisReport:
        """Generate analysis report with insights."""
        logger.info("Generating report...")
        
        # Generate Mermaid diagram
        mermaid_diagram = self.graph.to_mermaid()
        
        # Generate summary
        summary = f"Architecture analysis of {self.project_path.name}:\n"
        summary += f"- {len(self.graph.components)} components discovered\n"
        summary += f"- {len(self.graph.dependencies)} dependencies mapped\n"
        summary += f"- Technologies: {', '.join(self.graph.technologies)}\n"
        summary += f"- Patterns: {', '.join(self.graph.patterns)}"
        
        # Generate insights
        insights = []
        
        # Complexity insights
        avg_deps = len(self.graph.dependencies) / max(len(self.graph.components), 1)
        if avg_deps > 5:
            insights.append("High coupling detected - consider reducing dependencies")
        
        # Pattern insights
        if "Layered Architecture" in self.graph.patterns:
            insights.append("Project follows layered architecture pattern")
        
        # Technology insights
        if len(self.graph.technologies) > 5:
            insights.append("Multiple technologies detected - ensure consistency")
        
        # Generate warnings
        warnings = []
        
        # Circular dependency check (simplified)
        if self._has_circular_dependencies():
            warnings.append("Potential circular dependencies detected")
        
        # Large file warnings
        large_components = [c for c in self.graph.components.values() 
                          if c.metrics.get('lines', 0) > 500]
        if large_components:
            warnings.append(f"{len(large_components)} large files detected (>500 lines)")
        
        # Generate recommendations
        recommendations = []
        
        if not self.graph.patterns:
            recommendations.append("Consider adopting a clear architectural pattern")
        
        if len(self.graph.entry_points) > 3:
            recommendations.append("Multiple entry points detected - consider consolidation")
        
        # Create report
        report = AnalysisReport(
            graph=self.graph,
            summary=summary,
            insights=insights,
            warnings=warnings,
            recommendations=recommendations,
            metrics={
                'total_lines': sum(c.metrics.get('lines', 0) for c in self.graph.components.values()),
                'avg_component_size': sum(c.metrics.get('lines', 0) for c in self.graph.components.values()) / max(len(self.graph.components), 1),
                'coupling_score': avg_deps
            },
            mermaid_diagram=mermaid_diagram
        )
        
        return report
    
    async def _save_analysis(self, report: AnalysisReport):
        """Save analysis results to files."""
        # Save JSON report
        report_path = self.output_dir / "architecture-report.json"
        with open(report_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        # Save Mermaid diagram
        diagram_path = self.output_dir / "architecture-diagram.mmd"
        with open(diagram_path, 'w') as f:
            f.write(report.mermaid_diagram)
        
        # Save markdown summary
        summary_path = self.output_dir / "ARCHITECTURE.md"
        with open(summary_path, 'w') as f:
            f.write(self._generate_markdown_summary(report))
        
        logger.info(f"Analysis saved to {self.output_dir}")
    
    async def _update_rag(self, report: AnalysisReport):
        """Update RAG service with analysis results."""
        if not self.rag_client:
            return
        
        try:
            # Store architecture summary
            await self._store_in_rag(
                "architecture_summary",
                self._generate_markdown_summary(report)
            )
            
            # Store component details
            for comp_id, comp in self.graph.components.items():
                await self._store_in_rag(
                    f"component_{comp_id}",
                    f"Component: {comp.name}\nType: {comp.type.value}\nFile: {comp.file_path}\nTechnologies: {comp.technologies}\nPatterns: {comp.patterns}"
                )
            
            logger.info("RAG updated with analysis results")
            
        except Exception as e:
            logger.error(f"Failed to update RAG: {e}")
    
    def _generate_markdown_summary(self, report: AnalysisReport) -> str:
        """Generate markdown summary of the analysis."""
        md = f"# Architecture Analysis\n\n"
        md += f"Generated: {datetime.utcnow().isoformat()}\n\n"
        
        md += f"## Summary\n\n{report.summary}\n\n"
        
        if report.insights:
            md += "## Insights\n\n"
            for insight in report.insights:
                md += f"- {insight}\n"
            md += "\n"
        
        if report.warnings:
            md += "## Warnings\n\n"
            for warning in report.warnings:
                md += f"- ⚠️ {warning}\n"
            md += "\n"
        
        if report.recommendations:
            md += "## Recommendations\n\n"
            for rec in report.recommendations:
                md += f"- 💡 {rec}\n"
            md += "\n"
        
        md += "## Architecture Diagram\n\n"
        md += "```mermaid\n"
        md += report.mermaid_diagram
        md += "\n```\n\n"
        
        md += "## Metrics\n\n"
        for key, value in report.metrics.items():
            md += f"- **{key.replace('_', ' ').title()}**: {value}\n"
        
        return md
    
    # Helper methods
    def _should_analyze_file(self, file_path: Path) -> bool:
        """Check if file should be analyzed."""
        # Skip common directories
        skip_dirs = {'node_modules', '.git', '.venv', '__pycache__', 'dist', 'build', '.next'}
        if any(skip in str(file_path) for skip in skip_dirs):
            return False
        
        # Only analyze code files
        valid_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp', '.go', '.rs'}
        return file_path.suffix in valid_extensions
    
    def _generate_component_id(self, file_path: Path) -> str:
        """Generate unique component ID."""
        relative_path = file_path.relative_to(self.project_path)
        return str(relative_path).replace('/', '_').replace('\\', '_').replace('.', '_')
    
    def _get_module_path(self, file_path: Path) -> str:
        """Get module path for imports."""
        relative_path = file_path.relative_to(self.project_path)
        module_path = str(relative_path.with_suffix('')).replace('/', '.').replace('\\', '.')
        return module_path
    
    def _find_component_by_import(self, import_name: str) -> Optional[ComponentNode]:
        """Find component by import name."""
        # Try exact module path match
        for comp in self.graph.components.values():
            if comp.module_path == import_name:
                return comp
            # Try partial match
            if import_name in comp.module_path or comp.name in import_name:
                return comp
        return None
    
    def _has_circular_dependencies(self) -> bool:
        """Simple check for circular dependencies."""
        # This is a simplified check - real implementation would use graph algorithms
        for dep in self.graph.dependencies:
            # Check if there's a reverse dependency
            reverse = any(
                d.source_id == dep.target_id and d.target_id == dep.source_id
                for d in self.graph.dependencies
            )
            if reverse:
                return True
        return False
    
    def _has_recent_analysis(self) -> bool:
        """Check if recent analysis exists."""
        report_path = self.output_dir / "architecture-report.json"
        if report_path.exists():
            # Check if less than threshold hours old
            mod_time = datetime.fromtimestamp(report_path.stat().st_mtime)
            age = datetime.utcnow() - mod_time
            return age < timedelta(hours=self.thresholds.time_elapsed_hours)
        return False
    
    def _load_cached_analysis(self) -> AnalysisReport:
        """Load cached analysis."""
        report_path = self.output_dir / "architecture-report.json"
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        # Reconstruct report (simplified - real implementation would deserialize properly)
        report = AnalysisReport(
            graph=self.graph,  # Would need to reconstruct from data
            summary=data.get('summary', ''),
            insights=data.get('insights', []),
            warnings=data.get('warnings', []),
            recommendations=data.get('recommendations', []),
            metrics=data.get('metrics', {}),
            mermaid_diagram=data.get('mermaid_diagram', '')
        )
        return report
    
    async def _store_in_rag(self, doc_id: str, content: str):
        """Store document in RAG service."""
        # Implementation would use actual RAG storage
        pass
    
    def stop(self):
        """Stop the analyzer and cleanup."""
        # Cleanup would go here if needed
        logger.info("Analyzer stopped")