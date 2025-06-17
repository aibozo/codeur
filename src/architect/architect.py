"""
Architect Agent implementation.

The Architect is responsible for:
- Understanding high-level project requirements
- Designing overall system architecture
- Creating task dependency graphs
- Orchestrating the development workflow
- Managing project context and plans in RAG
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from .models import (
    TaskGraph, TaskNode, ProjectStructure,
    TaskPriority, TaskStatus
)
from .task_graph_manager import TaskGraphManager, TaskGraphContext
from .llm_tools import ArchitectTools
from .plan_manager import PlanManager
from .plan_aware_architect import PlanAwareArchitect
from .plan_api import PlanAPI
from src.core.logging import get_logger

# Optional import for RAG service
try:
    from src.rag_service import RAGService, RAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAGService = None
    RAGClient = None
    RAG_AVAILABLE = False

logger = get_logger(__name__)

# Optional import for LLM
try:
    from src.llm import LLMClient
    LLM_AVAILABLE = True
except ImportError as e:
    LLM_AVAILABLE = False
    LLMClient = None
    logger.warning(f"LLMClient import failed: {e}")

# Optional import for Analyzer
try:
    from src.analyzer.analyzer import Analyzer
    ANALYZER_AVAILABLE = True
except ImportError as e:
    ANALYZER_AVAILABLE = False
    Analyzer = None
    logger.warning(f"Analyzer import failed: {e}")


class Architect:
    """
    The Architect agent that designs project structure and creates task graphs.
    """
    
    def __init__(
        self,
        project_path: str,
        rag_service: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        auto_index: bool = True,
        use_enhanced_task_graph: bool = True
    ):
        """
        Initialize the Architect agent.
        
        Args:
            project_path: Root path of the project
            rag_service: RAG service for storing/retrieving project context
            llm_client: LLM client for AI-powered design decisions
            auto_index: Whether to automatically index the project if not already indexed
        """
        self.project_path = Path(project_path).resolve()
        self.project_structure = ProjectStructure()
        self.task_graphs: Dict[str, TaskGraph] = {}
        self.use_enhanced_task_graph = use_enhanced_task_graph
        self.task_graph_managers: Dict[str, TaskGraphManager] = {}
        
        # Initialize RAG service
        if rag_service:
            self.rag_service = rag_service
            self.rag_client = RAGClient(service=rag_service) if RAG_AVAILABLE else None
        elif RAG_AVAILABLE:
            # Create RAG service with project-specific directory
            rag_dir = self.project_path / ".rag"
            rag_dir.mkdir(exist_ok=True)
            self.rag_service = RAGService(
                persist_directory=str(rag_dir),
                repo_path=str(self.project_path)
            )
            self.rag_client = RAGClient(service=self.rag_service)
            
            # Auto-index if needed
            if auto_index:
                stats = self.rag_service.get_stats()
                if stats.total_chunks == 0:
                    logger.info("No RAG index found, indexing project...")
                    self._index_project()
        else:
            self.rag_service = None
            self.rag_client = None
            logger.warning("RAG not available - architect will work without code context")
        
        # Initialize LLM client if available and not provided
        if llm_client:
            self.llm_client = llm_client
            logger.info("Using provided LLM client")
        elif LLM_AVAILABLE:
            try:
                # Use the new LLMClient with model card system
                model = os.getenv("ARCHITECT_MODEL")
                logger.info(f"Initializing LLM client with model: {model}")
                self.llm_client = LLMClient(model=model, agent_name="architect")
                logger.info(f"Architect using model: {self.llm_client.model_card.display_name}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)
                self.llm_client = None
        else:
            self.llm_client = None
            logger.warning(f"Architect running without LLM - LLM_AVAILABLE={LLM_AVAILABLE}")
        
        logger.info(f"Architect initialized for project: {self.project_path}")
        
        # Initialize architect tools if enhanced task graph is enabled
        self.architect_tools = None
        if self.use_enhanced_task_graph:
            logger.info("Enhanced task graph system enabled")
        
        # Initialize plan manager for deep context passing
        self.plan_manager = PlanManager(
            base_path=str(self.project_path / ".agent"),
            rag_client=self.rag_client,
            auto_index=True
        )
        
        # Initialize plan-aware architect for creating phased plans
        self.plan_aware_architect = None
        
        # Initialize plan API for agents to retrieve context
        self.plan_api = PlanAPI(self.plan_manager)
        
        # Initialize analyzer for architecture understanding
        self.analyzer = None
        self._architecture_summary = None
        self._architecture_diagram = None
        if ANALYZER_AVAILABLE:
            try:
                self.analyzer = Analyzer(
                    project_path=str(self.project_path),
                    rag_service=self.rag_service,
                    auto_analyze=False  # We'll analyze on demand
                )
                logger.info("Analyzer initialized for architecture understanding")
                # Try to load cached analysis
                self._load_architecture_analysis()
            except Exception as e:
                logger.warning(f"Failed to initialize Analyzer: {e}")
                self.analyzer = None
    
    def _load_architecture_analysis(self) -> None:
        """Load cached architecture analysis if available."""
        if not self.analyzer:
            return
        
        try:
            # Check if analysis exists
            analysis_file = self.project_path / ".rag" / "architecture_analysis.json"
            if analysis_file.exists():
                with open(analysis_file, 'r') as f:
                    data = json.load(f)
                    self._architecture_summary = data.get("summary", "")
                    self._architecture_diagram = data.get("diagram", "")
                    logger.info("Loaded cached architecture analysis")
        except Exception as e:
            logger.warning(f"Failed to load cached architecture analysis: {e}")
    
    def _save_architecture_analysis(self) -> None:
        """Save architecture analysis to cache."""
        if not self._architecture_summary:
            return
        
        try:
            analysis_file = self.project_path / ".rag" / "architecture_analysis.json"
            analysis_file.parent.mkdir(exist_ok=True)
            
            with open(analysis_file, 'w') as f:
                json.dump({
                    "summary": self._architecture_summary,
                    "diagram": self._architecture_diagram or "",
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
                
            logger.info("Saved architecture analysis to cache")
        except Exception as e:
            logger.warning(f"Failed to save architecture analysis: {e}")
    
    async def analyze_architecture(self) -> bool:
        """
        Analyze the project architecture using the Analyzer.
        
        Returns:
            True if analysis was successful
        """
        if not self.analyzer:
            logger.warning("Analyzer not available - skipping architecture analysis")
            return False
        
        try:
            logger.info("Analyzing project architecture...")
            
            # Run analysis
            report = await self.analyzer.analyze_codebase()
            
            # Extract summary and diagram
            self._architecture_summary = report.summary
            self._architecture_diagram = report.mermaid_diagram
            
            logger.info("Architecture analysis completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Architecture analysis failed: {e}")
            return False
    
    def _index_project(self) -> None:
        """Index the project for RAG retrieval."""
        if not self.rag_client:
            return
            
        try:
            logger.info("Indexing project for RAG...")
            results = self.rag_client.index_directory(
                directory=str(self.project_path),
                extensions=[".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".hpp"]
            )
            logger.info(f"Indexed {results.get('files_indexed', 0)} files with {results.get('chunks_created', 0)} chunks")
        except Exception as e:
            logger.error(f"Failed to index project: {e}")
    
    async def analyze_project_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        Analyze high-level project requirements and create initial design.
        
        Args:
            requirements: Natural language project requirements
            
        Returns:
            Dictionary containing analysis results and initial design
        """
        logger.info("Analyzing project requirements")
        
        # Gather context from RAG if available
        rag_context = ""
        if self.rag_client:
            try:
                # Search for relevant code context
                search_results = self.rag_client.search(
                    query=requirements,
                    k=5,
                    filters={"chunk_type": {"$in": ["class", "function", "module"]}}
                )
                
                if search_results:
                    rag_context = "\n\nExisting codebase context:\n"
                    for result in search_results[:3]:  # Top 3 results
                        rag_context += f"\n- {result.get('file_path', 'Unknown')}: {result.get('content', '')[:200]}..."
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")
        
        # If LLM is available, use it for intelligent analysis
        if self.llm_client:
            try:
                analysis_prompt = f"""
                Analyze the following project requirements and provide:
                1. A breakdown of major components needed
                2. Key technical decisions to make
                3. Potential challenges and risks
                4. Suggested architecture pattern
                
                Requirements: {requirements}
                {rag_context}
                
                Provide response in JSON format with keys:
                - components: list of major components
                - decisions: list of technical decisions
                - risks: list of potential risks
                - pattern: suggested architecture pattern
                """
                
                response = self.llm_client.generate(analysis_prompt)
                
                # Try to parse JSON response
                try:
                    import json
                    analysis = json.loads(response)
                except:
                    # Fallback to text response
                    analysis = {
                        "raw_analysis": response,
                        "components": [],
                        "decisions": [],
                        "risks": [],
                        "pattern": "Unknown"
                    }
                    
                return {
                    "requirements": requirements,
                    "analysis": analysis,
                    "has_rag_context": bool(rag_context)
                }
                
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")
        
        # Fallback analysis without LLM
        return {
            "requirements": requirements,
            "analysis": {
                "components": ["Backend API", "Frontend UI", "Database", "Authentication"],
                "decisions": ["Technology stack", "Database choice", "API design", "Security approach"],
                "risks": ["Scalability concerns", "Security vulnerabilities", "Integration complexity"],
                "pattern": "MVC/REST API"
            },
            "has_rag_context": bool(rag_context)
        }
    
    async def create_task_graph(self, project_name: str, requirements: str, project_id: Optional[str] = None) -> TaskGraph:
        """
        Create a task graph based on requirements.
        
        Args:
            project_name: Name of the project
            requirements: Project requirements
            project_id: Optional project ID
            
        Returns:
            TaskGraph containing planned tasks
        """
        if not project_id:
            project_id = f"{project_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Creating {'enhanced' if self.use_enhanced_task_graph else 'standard'} task graph for project: {project_name}")
        
        if self.use_enhanced_task_graph:
            # Create enhanced task graph
            context = TaskGraphContext(
                project_id=project_id,
                project_path=self.project_path,
                rag_client=self.rag_client
            )
            
            manager = TaskGraphManager(context)
            self.task_graph_managers[project_id] = manager
            
            # Create initial graph ID
            graph_id = f"{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # If LLM available, use it to create intelligent tasks
            if self.llm_client:
                # Create architect tools
                self.architect_tools = ArchitectTools(manager, project_path=str(self.project_path), rag_client=self.rag_client)
                
                # Use LLM to create tasks
                try:
                    # First, use codebase understanding tools if available
                    codebase_context = ""
                    if self.rag_client:
                        # Search for relevant code
                        search_result = await self.architect_tools.search_codebase(
                            query=requirements,
                            limit=5
                        )
                        if search_result.get("results"):
                            codebase_context = "\n\nRelevant codebase context:\n"
                            for result in search_result["results"][:3]:
                                codebase_context += f"- {result['file']}: {result['preview']}\n"
                        
                        # Assess tech stack
                        tech_result = await self.architect_tools.assess_tech_stack()
                        if tech_result.get("primary_languages"):
                            codebase_context += f"\nTechnology stack: {', '.join(tech_result['primary_languages'])}"
                            if tech_result.get("frameworks"):
                                codebase_context += f"\nFrameworks: {', '.join(tech_result['frameworks'])}"
                    
                    # Create task creation prompt
                    task_prompt = f"""
                    Create a task list for the following project requirements:
                    
                    {requirements}
                    {codebase_context}
                    
                    Use the create_tasks function to create a hierarchical task structure.
                    Include time estimates and dependencies.
                    Make tasks specific and actionable.
                    """
                    
                    # Get function definitions
                    functions = self.architect_tools.get_tool_definitions()
                    
                    # For now, use text-based task creation without function calling
                    # since the LLMClient doesn't support function calling
                    task_prompt += "\n\nProvide the task structure in JSON format."
                    
                    response = self.llm_client.generate(
                        task_prompt,
                        system_prompt=self.get_enhanced_system_prompt()
                    )
                    
                    # Try to parse the response and create tasks
                    await self._create_tasks_from_text(response, project_id)
                        
                except Exception as e:
                    logger.error(f"LLM task creation failed: {e}")
                    # Fall back to mock tasks
                    graph = manager.graph
                    self._create_mock_tasks(graph)
            else:
                # No LLM, create mock tasks on the enhanced graph
                await self._create_mock_enhanced_tasks(manager, requirements)
            
            # Convert enhanced graph to standard format for compatibility
            standard_graph = self._convert_to_standard_graph(manager.graph, project_id)
            self.task_graphs[project_id] = standard_graph
            
            return standard_graph
            
        else:
            # Create standard task graph
            graph = TaskGraph(
                project_id=project_id,
                project_name=project_name,
                description=requirements
            )
            
            # Create tasks (simplified for standard graph)
            self._create_mock_tasks(graph)
            
            self.task_graphs[project_id] = graph
            return graph
    
    def _convert_to_standard_graph(self, enhanced_graph: Any, project_id: str) -> TaskGraph:
        """Convert enhanced graph to standard TaskGraph for compatibility."""
        # Get project name from graph or use project_id
        project_name = getattr(enhanced_graph, 'project_name', project_id)
        description = getattr(enhanced_graph, 'description', '')
        
        standard_graph = TaskGraph(
            project_id=project_id,
            project_name=project_name,
            description=description
        )
        
        # Convert tasks
        for node_id, node in enhanced_graph.tasks.items():
            task = TaskNode(
                id=node.id,
                title=node.title,
                description=node.description,
                agent_type=node.agent_type,
                status=TaskStatus(node.status),
                priority=TaskPriority(node.priority),
                dependencies=set(node.dependencies),
                context=getattr(node, 'metadata', {})
            )
            standard_graph.add_task(task)
        
        return standard_graph
    
    async def _create_tasks_from_text(self, text: str, project_id: str):
        """Create tasks from LLM text response as fallback."""
        if project_id not in self.task_graph_managers:
            return
            
        manager = self.task_graph_managers[project_id]
        
        # Simple parsing - look for bullet points or numbered lists
        lines = text.split('\n')
        current_parent = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for task-like patterns
            if line.startswith(('-', '*', '•')) or (len(line) > 2 and line[0].isdigit() and line[1] in '.):'):
                # Extract task title
                task_title = line.lstrip('-*•').lstrip('0123456789.)').strip()
                
                # Create task
                result = await self.architect_tools.create_tasks(
                    task_list=task_title,
                    parent_id=current_parent
                )
                
                if result.get("created_tasks"):
                    # Use first created task as potential parent for sub-tasks
                    current_parent = result["created_tasks"][0]["id"]
    
    async def get_project_context(self, project_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current project context for a specific task or the whole project.
        
        Args:
            project_id: Project identifier
            task_id: Optional specific task ID
            
        Returns:
            Dictionary containing project context, current state, and relevant information
        """
        context = {
            "project_id": project_id,
            "project_path": str(self.project_path),
            "has_rag": self.rag_client is not None,
            "task_graph": None,
            "current_task": None,
            "relevant_code": []
        }
        
        # Get task graph
        if project_id in self.task_graphs:
            graph = self.task_graphs[project_id]
            context["task_graph"] = {
                "total_tasks": len(graph.tasks),
                "completed_tasks": len([t for t in graph.tasks.values() if t.status == TaskStatus.COMPLETED]),
                "in_progress_tasks": len([t for t in graph.tasks.values() if t.status == TaskStatus.IN_PROGRESS]),
                "blocked_tasks": len([t for t in graph.tasks.values() if t.status == TaskStatus.BLOCKED])
            }
            
            # Get specific task if requested
            if task_id and task_id in graph.tasks:
                task = graph.tasks[task_id]
                context["current_task"] = {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value,
                    "dependencies": list(task.dependencies),
                    "agent_type": task.agent_type
                }
                
                # Get relevant code context from RAG
                if self.rag_client:
                    try:
                        search_query = f"{task.title} {task.description}"
                        search_results = self.rag_client.search(
                            query=search_query,
                            k=3
                        )
                        
                        for result in search_results:
                            context["relevant_code"].append({
                                "file": result.get("file_path", "Unknown"),
                                "content": result.get("content", "")[:500],  # Limit content size
                                "score": result.get("score", 0.0)
                            })
                    except Exception as e:
                        logger.warning(f"Failed to get RAG context: {e}")
        
        return context
    
    def update_task_status(self, project_id: str, task_id: str, status: TaskStatus, 
                          notes: Optional[str] = None) -> bool:
        """
        Update the status of a task.
        
        Args:
            project_id: Project identifier
            task_id: Task identifier
            status: New task status
            notes: Optional notes about the update
            
        Returns:
            True if update was successful
        """
        if project_id not in self.task_graphs:
            logger.warning(f"Project {project_id} not found")
            return False
            
        graph = self.task_graphs[project_id]
        if task_id not in graph.tasks:
            logger.warning(f"Task {task_id} not found in project {project_id}")
            return False
            
        task = graph.tasks[task_id]
        old_status = task.status
        task.status = status
        
        # Update metadata
        if not task.metadata:
            task.metadata = {}
        task.metadata["last_updated"] = datetime.now().isoformat()
        if notes:
            task.metadata["notes"] = notes
            
        # Log the update
        logger.info(f"Task {task_id} status updated: {old_status.value} -> {status.value}")
        
        # Store update in RAG if available
        if self.rag_client:
            try:
                update_doc = f"""
                Task Update: {task.title}
                Project: {project_id}
                Status Change: {old_status.value} -> {status.value}
                Time: {datetime.now().isoformat()}
                Notes: {notes or 'No notes provided'}
                """
                
                self.rag_client.add_document(
                    content=update_doc,
                    metadata={
                        "type": "task_update",
                        "project_id": project_id,
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to store task update in RAG: {e}")
                
        return True
    
    def get_task_dependencies(self, project_id: str, task_id: str) -> List[TaskNode]:
        """
        Get all tasks that must be completed before the given task.
        
        Args:
            project_id: Project identifier
            task_id: Task identifier
            
        Returns:
            List of dependent tasks
        """
        if project_id not in self.task_graphs:
            return []
            
        graph = self.task_graphs[project_id]
        if task_id not in graph.tasks:
            return []
            
        task = graph.tasks[task_id]
        dependencies = []
        
        for dep_id in task.dependencies:
            if dep_id in graph.tasks:
                dependencies.append(graph.tasks[dep_id])
                
        return dependencies
    
    def save_project_state(self, project_id: str) -> bool:
        """
        Save the current project state to disk.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if save was successful
        """
        if project_id not in self.task_graphs:
            logger.warning(f"Project {project_id} not found")
            return False
            
        try:
            # Create project directory
            project_dir = self.project_path / ".architect" / project_id
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Save task graph
            graph = self.task_graphs[project_id]
            graph_data = {
                "project_id": graph.project_id,
                "project_name": graph.project_name,
                "description": graph.description,
                "created_at": graph.created_at.isoformat(),
                "updated_at": graph.updated_at.isoformat(),
                "tasks": {}
            }
            
            # Serialize tasks
            for task_id, task in graph.tasks.items():
                graph_data["tasks"][task_id] = {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "agent_type": task.agent_type,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "dependencies": list(task.dependencies),
                    "estimated_hours": task.estimated_hours,
                    "actual_hours": task.actual_hours,
                    "metadata": task.metadata
                }
                
            # Save to file
            graph_file = project_dir / "task_graph.json"
            with open(graph_file, 'w') as f:
                json.dump(graph_data, f, indent=2)
                
            logger.info(f"Saved project state for {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save project state: {e}")
            return False
    
    def load_project_state(self, project_id: str) -> bool:
        """
        Load project state from disk.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if load was successful
        """
        try:
            # Check for saved state
            graph_file = self.project_path / ".architect" / project_id / "task_graph.json"
            if not graph_file.exists():
                logger.warning(f"No saved state found for project {project_id}")
                return False
                
            # Load graph data
            with open(graph_file, 'r') as f:
                graph_data = json.load(f)
                
            # Recreate task graph
            graph = TaskGraph(
                project_id=graph_data["project_id"],
                project_name=graph_data["project_name"],
                description=graph_data["description"]
            )
            
            # Recreate tasks
            for task_data in graph_data["tasks"].values():
                task = TaskNode(
                    id=task_data["id"],
                    title=task_data["title"],
                    description=task_data["description"],
                    agent_type=task_data["agent_type"],
                    status=TaskStatus(task_data["status"]),
                    priority=TaskPriority(task_data["priority"]),
                    dependencies=set(task_data["dependencies"]),
                    estimated_hours=task_data["estimated_hours"],
                    actual_hours=task_data["actual_hours"],
                    metadata=task_data["metadata"]
                )
                graph.add_task(task)
                
            self.task_graphs[project_id] = graph
            logger.info(f"Loaded project state for {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load project state: {e}")
            return False
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the architect agent.
        
        Returns:
            System prompt string
        """
        return """You are an expert software architect responsible for:
- Understanding high-level project requirements
- Designing overall system architecture  
- Creating phased implementation plans with actionable tasks
- Orchestrating the development workflow

## Project Planning Philosophy

When planning a project, think in terms of **phased implementation**:

1. **Research & Analysis Phase**: Understand requirements, analyze existing code, identify patterns
2. **Design Phase**: Architecture decisions, component design, API contracts
3. **Implementation Phase**: Core features, then enhancements, iterative development
4. **Testing Phase**: Unit tests, integration tests, validation
5. **Documentation & Polish Phase**: Documentation, optimization, final touches

## Task Creation Guidelines

Create tasks that are:
- **Actionable**: Each task should be a concrete step an agent can execute
- **Scoped**: Tasks should be completable in hours to a few days, not weeks
- **Context-Rich**: Include relevant files, patterns to follow, constraints
- **Dependencies Clear**: Specify what must be done before each task

Good task granularity examples:
- ✅ "Implement user authentication endpoints in src/api/auth.py"
- ✅ "Create database schema for user profiles"
- ✅ "Add JWT token validation middleware"
- ❌ "Build the backend" (too broad)
- ❌ "Fix bugs" (not actionable)

Remember: The goal is to create a roadmap that any competent developer (human or AI) could follow to build the system successfully.

Create task structures that:
- Break down complex requirements into manageable tasks
- Define clear dependencies between tasks
- Assign appropriate priorities and agents
- Estimate effort and complexity
"""
    
    def get_enhanced_system_prompt(self) -> str:
        """
        Get the enhanced system prompt that includes task management guidance.
        
        Returns:
            System prompt for architect with task management capabilities
        """
        base_prompt = """You are an expert software architect responsible for:
- Understanding high-level project requirements
- Designing overall system architecture  
- Creating phased implementation plans with actionable tasks
- Orchestrating the development workflow

## Project Planning Philosophy

When planning a project, think in terms of **phased implementation**:

1. **Research & Analysis Phase**: Understand requirements, analyze existing code, identify patterns
2. **Design Phase**: Architecture decisions, component design, API contracts
3. **Implementation Phase**: Core features, then enhancements, iterative development
4. **Testing Phase**: Unit tests, integration tests, validation
5. **Documentation & Polish Phase**: Documentation, optimization, final touches

## Task Creation Guidelines

Create tasks that are:
- **Actionable**: Each task should be a concrete step an agent can execute
- **Scoped**: Tasks should be completable in hours to a few days, not weeks
- **Context-Rich**: Include relevant files, patterns to follow, constraints
- **Dependencies Clear**: Specify what must be done before each task

Good task granularity examples:
- ✅ "Implement user authentication endpoints in src/api/auth.py"
- ✅ "Create database schema for user profiles"
- ✅ "Add JWT token validation middleware"
- ❌ "Build the backend" (too broad)
- ❌ "Fix bugs" (not actionable)

Remember: The goal is to create a roadmap that any competent developer (human or AI) could follow to build the system successfully.

"""
        
        # Add architecture understanding if available
        if self._architecture_summary:
            # Limit summary to first 5000 chars to avoid token limits
            summary = self._architecture_summary[:5000]
            if len(self._architecture_summary) > 5000:
                summary += "\n\n[Architecture summary truncated for brevity...]"
            base_prompt += f"""## Current Project Architecture

{summary}

"""
        
        if self._architecture_diagram:
            # Limit diagram to first 2000 chars to avoid token limits
            diagram = self._architecture_diagram[:2000]
            if len(self._architecture_diagram) > 2000:
                diagram += "\n... [diagram truncated]"
            base_prompt += f"""## Architecture Diagram

```mermaid
{diagram}
```

"""
        
        if self.use_enhanced_task_graph:
            base_prompt += """You have access to enhanced task management and codebase understanding tools:

## Task Management Tools

1. **create_tasks** - Create hierarchical task structures using natural language formats:
   - List format (recommended): Simple bullet lists with time estimates and dependencies
   - Markdown format: Structured markdown with headers and task details
   - YAML format: Structured YAML for complex hierarchies

2. **add_subtasks** - Break down existing tasks into subtasks

3. **get_task_status** - Check current progress and task states

4. **update_task_priority** - Adjust task priorities as needed

## Codebase Understanding Tools

5. **search_codebase** - Search for code patterns, functions, classes, or concepts
   - Use when: Finding implementations, understanding patterns, locating features
   - Example: search_codebase("authentication", file_pattern="*.py")

6. **explore_file** - Read and analyze specific files with optional focus areas
   - Use when: Understanding module structure, analyzing implementations
   - Example: explore_file("src/auth/login.py", focus_area="class LoginHandler")

7. **find_symbol** - Find where classes, functions, or variables are defined and used
   - Use when: Tracking usage, understanding dependencies
   - Example: find_symbol("UserModel", symbol_type="class")

8. **trace_imports** - Trace import dependencies for files or modules
   - Use when: Understanding module coupling, finding circular imports
   - Example: trace_imports("src/api/routes.py")

9. **analyze_component** - Deep dive into component/module structure
   - Use when: Planning modifications, understanding architecture
   - Example: analyze_component("src/auth")

10. **map_relationships** - Map component relationships from an entry point
    - Use when: Understanding interactions, planning changes
    - Example: map_relationships("src/main.py", depth=3)

11. **find_patterns** - Identify design and architectural patterns
    - Use when: Understanding conventions, ensuring consistency
    - Example: find_patterns("architectural")

12. **assess_tech_stack** - Identify technologies and frameworks in use
    - Use when: Planning integrations, making architectural decisions
    - Example: assess_tech_stack()

13. **find_entry_points** - Locate application entry points
    - Use when: Understanding startup flow, debugging initialization
    - Example: find_entry_points()

14. **analyze_data_flow** - Trace data flow through the application
    - Use when: Understanding request handling, tracking transformations
    - Example: analyze_data_flow("handle_user_request")

## Best Practices

When creating tasks:
- Use codebase tools to understand existing implementation before planning
- Search for similar features to maintain consistency
- Analyze components that will be affected by changes
- Include relevant file paths in task descriptions
- Use clear, actionable titles
- Include time estimates (e.g., "2h", "3 days")
- Specify dependencies with "needs:" or "depends:"
- Set priorities: low, medium, high, critical
- Group related tasks hierarchically

Example workflow:
1. First understand the codebase: search_codebase("existing feature")
2. Analyze affected components: analyze_component("src/module")
3. Check patterns: find_patterns()
4. Then create informed tasks with specific file references

Example task creation:
```
Build Authentication System:
  - Setup database schema (high, 2h)
    Files: src/models/user.py, migrations/
  - Implement user model:
    - Define fields (1h)
    - Add validation (1h)
  - Create auth endpoints (medium, 3h, needs: Implement user model)
    Files: src/api/auth.py, src/middleware/auth.py
  - Add JWT support (high, 2h, needs: Create auth endpoints)
  - Write tests (medium, 2h, needs: Add JWT support)
    Files: tests/test_auth.py
```
"""
        else:
            base_prompt += """Create task structures that:
- Break down complex requirements into manageable tasks
- Define clear dependencies between tasks
- Assign appropriate priorities and agents
- Estimate effort and complexity
"""
        
        return base_prompt
    
    def _analyze_component_dependencies(self, component_name: str) -> Dict[str, Any]:
        """
        Analyze dependencies for a specific component.
        
        Args:
            component_name: Name of the component to analyze
            
        Returns:
            Dictionary with dependency information
        """
        if not self.rag_client:
            return {"error": "RAG client not available"}
            
        try:
            # Search for component definition
            component_results = self.rag_client.find_symbol(
                symbol_name=component_name,
                symbol_type="class"
            )
            
            dependencies = {
                "imports": [],
                "inherits": [],
                "uses": []
            }
            
            if component_results:
                # Get the file content to analyze imports
                for result in component_results[:1]:  # First match
                    file_path = result.get('file_path', '')
                    
                    # Search for imports in the same file
                    import_search = self.rag_client.search(
                        query=f"import from {file_path}",
                        k=5
                    )
                    
                    for imp in import_search:
                        content = imp.get('content', '')
                        if 'import' in content:
                            dependencies['imports'].append(content.strip()[:100])
            
            return dependencies
            
        except Exception as e:
            logger.error(f"Component dependency analysis failed: {e}")
            return {}
    
    async def _create_mock_enhanced_tasks(self, manager: TaskGraphManager, requirements: str) -> None:
        """Create mock tasks on the enhanced task graph when LLM is not available."""
        # Phase 1: Architecture and Setup
        arch_task = await manager.create_task_from_description(
            title="Design System Architecture",
            description=f"Create detailed system design and component specifications for: {requirements}",
            agent_type="architect",
            priority=TaskPriority.CRITICAL
        )
        
        setup_task = await manager.create_task_from_description(
            title="Setup Project Structure",
            description="Initialize project with required dependencies and configuration",
            agent_type="request_planner",
            priority=TaskPriority.HIGH,
            dependencies={arch_task.id}
        )
        
        # Phase 2: Core Infrastructure
        db_task = await manager.create_task_from_description(
            title="Setup Database Schema",
            description="Design and implement database tables and relationships",
            agent_type="code_planner",
            priority=TaskPriority.HIGH,
            dependencies={setup_task.id}
        )
        
        api_task = await manager.create_task_from_description(
            title="Implement Core API",
            description="Create base API structure with routing and middleware",
            agent_type="coding_agent",
            priority=TaskPriority.HIGH,
            dependencies={setup_task.id}
        )
        
        # Phase 3: Feature Implementation
        auth_task = await manager.create_task_from_description(
            title="Implement Authentication",
            description="Add user authentication and authorization",
            agent_type="coding_agent",
            priority=TaskPriority.HIGH,
            dependencies={api_task.id, db_task.id}
        )
        
        # Detect and create communities
        manager.detect_and_create_communities()
    
    def _create_mock_tasks(self, graph: TaskGraph) -> None:
        """Create mock tasks when LLM is not available."""
        # Phase 1: Architecture and Setup
        arch_task = TaskNode(
            title="Design System Architecture",
            description="Create detailed system design and component specifications",
            agent_type="architect",
            priority=TaskPriority.CRITICAL
        )
        graph.add_task(arch_task)
        
        setup_task = TaskNode(
            title="Setup Project Structure",
            description="Initialize project with required dependencies and configuration",
            agent_type="request_planner",
            priority=TaskPriority.HIGH,
            dependencies={arch_task.id}
        )
        graph.add_task(setup_task)
        
        # Phase 2: Core Infrastructure
        db_task = TaskNode(
            title="Setup Database Schema",
            description="Design and implement database tables and relationships",
            agent_type="code_planner",
            priority=TaskPriority.HIGH,
            dependencies={setup_task.id}
        )
        graph.add_task(db_task)
        
        api_task = TaskNode(
            title="Implement Core API",
            description="Create base API structure with routing and middleware",
            agent_type="coding_agent",
            priority=TaskPriority.HIGH,
            dependencies={setup_task.id}
        )
        graph.add_task(api_task)
        
        # Phase 3: Feature Implementation
        auth_task = TaskNode(
            title="Implement Authentication",
            description="Add user authentication and authorization",
            agent_type="coding_agent",
            priority=TaskPriority.HIGH,
            dependencies={api_task.id, db_task.id}
        )
        graph.add_task(auth_task)
        
        frontend_task = TaskNode(
            title="Create Frontend Components",
            description="Build React components and pages",
            agent_type="coding_agent",
            priority=TaskPriority.MEDIUM,
            dependencies={api_task.id}
        )
        graph.add_task(frontend_task)
        
        # Phase 4: Integration and Testing
        integration_task = TaskNode(
            title="Frontend-Backend Integration",
            description="Connect frontend to API endpoints",
            agent_type="coding_agent",
            priority=TaskPriority.MEDIUM,
            dependencies={frontend_task.id, auth_task.id}
        )
        graph.add_task(integration_task)
        
        test_task = TaskNode(
            title="Write Tests",
            description="Create unit and integration tests",
            agent_type="code_tester",
            priority=TaskPriority.MEDIUM,
            dependencies={integration_task.id}
        )
        graph.add_task(test_task)
    
    async def handle_function_call(self, function_name: str, arguments: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """
        Handle function calls from the LLM for task management.
        
        Args:
            function_name: Name of the function to call
            arguments: Function arguments
            project_id: Project ID to operate on
            
        Returns:
            Function result
        """
        if not self.use_enhanced_task_graph:
            return {"error": "Enhanced task graph not enabled"}
            
        # Get or create task manager for project
        if project_id not in self.task_graph_managers:
            context = TaskGraphContext(
                project_id=project_id,
                project_path=self.project_path,
                rag_client=self.rag_client
            )
            self.task_graph_managers[project_id] = TaskGraphManager(context)
            
        manager = self.task_graph_managers[project_id]
        
        # Create architect tools if not exists
        if not self.architect_tools:
            self.architect_tools = ArchitectTools(manager, project_path=str(self.project_path), rag_client=self.rag_client)
            
        # Handle function calls
        if function_name == "create_tasks":
            return await self.architect_tools.create_tasks(**arguments)
        elif function_name == "add_subtasks":
            return await self.architect_tools.add_subtasks(**arguments)
        elif function_name == "get_task_status":
            return await self.architect_tools.get_task_status(**arguments)
        elif function_name == "update_task_priority":
            return await self.architect_tools.update_task_priority(**arguments)
        # Codebase understanding tools
        elif function_name == "search_codebase":
            return await self.architect_tools.search_codebase(**arguments)
        elif function_name == "explore_file":
            return await self.architect_tools.explore_file(**arguments)
        elif function_name == "find_symbol":
            return await self.architect_tools.find_symbol(**arguments)
        elif function_name == "trace_imports":
            return await self.architect_tools.trace_imports(**arguments)
        elif function_name == "analyze_component":
            return await self.architect_tools.analyze_component(**arguments)
        elif function_name == "map_relationships":
            return await self.architect_tools.map_relationships(**arguments)
        elif function_name == "find_patterns":
            return await self.architect_tools.find_patterns(**arguments)
        elif function_name == "assess_tech_stack":
            return await self.architect_tools.assess_tech_stack(**arguments)
        elif function_name == "find_entry_points":
            return await self.architect_tools.find_entry_points(**arguments)
        elif function_name == "analyze_data_flow":
            return await self.architect_tools.analyze_data_flow(**arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def get_enhanced_task_functions(self) -> List[Dict[str, Any]]:
        """
        Get the enhanced task management function definitions.
        
        Returns:
            List of function definitions for LLM function calling
        """
        if not self.use_enhanced_task_graph:
            return []
            
        # Create temporary tools to get definitions
        if not self.architect_tools:
            # Create dummy context and manager
            context = TaskGraphContext(
                project_id="temp",
                project_path=self.project_path,
                rag_client=self.rag_client
            )
            manager = TaskGraphManager(context)
            tools = ArchitectTools(manager)
            return tools.get_tool_definitions()
        
        return self.architect_tools.get_tool_definitions()
    
    def get_enhanced_system_prompt(self) -> str:
        """
        Get the enhanced system prompt that includes task management guidance.
        
        Returns:
            System prompt for architect with task management capabilities
        """
        base_prompt = """You are an expert software architect responsible for:
- Understanding high-level project requirements
- Designing overall system architecture  
- Creating phased implementation plans with actionable tasks
- Orchestrating the development workflow

## Project Planning Philosophy

When planning a project, think in terms of **phased implementation**:

1. **Research & Analysis Phase**: Understand requirements, analyze existing code, identify patterns
2. **Design Phase**: Architecture decisions, component design, API contracts
3. **Implementation Phase**: Core features, then enhancements, iterative development
4. **Testing Phase**: Unit tests, integration tests, validation
5. **Documentation & Polish Phase**: Documentation, optimization, final touches

## Task Creation Guidelines

Create tasks that are:
- **Actionable**: Each task should be a concrete step an agent can execute
- **Scoped**: Tasks should be completable in hours to a few days, not weeks
- **Context-Rich**: Include relevant files, patterns to follow, constraints
- **Dependencies Clear**: Specify what must be done before each task

Good task granularity examples:
- ✅ "Implement user authentication endpoints in src/api/auth.py"
- ✅ "Create database schema for user profiles"
- ✅ "Add JWT token validation middleware"
- ❌ "Build the backend" (too broad)
- ❌ "Fix bugs" (not actionable)

Remember: The goal is to create a roadmap that any competent developer (human or AI) could follow to build the system successfully.

"""
        
        # Add architecture understanding if available
        if self._architecture_summary:
            # Limit summary to first 5000 chars to avoid token limits
            summary = self._architecture_summary[:5000]
            if len(self._architecture_summary) > 5000:
                summary += "\n\n[Architecture summary truncated for brevity...]"
            base_prompt += f"""## Current Project Architecture

{summary}

"""
        
        if self._architecture_diagram:
            # Limit diagram to first 2000 chars to avoid token limits
            diagram = self._architecture_diagram[:2000]
            if len(self._architecture_diagram) > 2000:
                diagram += "\n... [diagram truncated]"
            base_prompt += f"""## Architecture Diagram

```mermaid
{diagram}
```

"""
        
        if self.use_enhanced_task_graph:
            base_prompt += """You have access to enhanced task management and codebase understanding tools:

## Task Management Tools

1. **create_tasks** - Create hierarchical task structures using natural language formats:
   - List format (recommended): Simple bullet lists with time estimates and dependencies
   - Markdown format: Structured markdown with headers and task details
   - YAML format: Structured YAML for complex hierarchies

2. **add_subtasks** - Break down existing tasks into subtasks

3. **get_task_status** - Check current progress and task states

4. **update_task_priority** - Adjust task priorities as needed

## Codebase Understanding Tools

5. **search_codebase** - Search for code patterns, functions, classes, or concepts
   - Use when: Finding implementations, understanding patterns, locating features
   - Example: search_codebase("authentication", file_pattern="*.py")

6. **explore_file** - Read and analyze specific files with optional focus areas
   - Use when: Understanding module structure, analyzing implementations
   - Example: explore_file("src/auth/login.py", focus_area="class LoginHandler")

7. **find_symbol** - Find where classes, functions, or variables are defined and used
   - Use when: Tracking usage, understanding dependencies
   - Example: find_symbol("UserModel", symbol_type="class")

8. **trace_imports** - Trace import dependencies for files or modules
   - Use when: Understanding module coupling, finding circular imports
   - Example: trace_imports("src/api/routes.py")

9. **analyze_component** - Deep dive into component/module structure
   - Use when: Planning modifications, understanding architecture
   - Example: analyze_component("src/auth")

10. **map_relationships** - Map component relationships from an entry point
    - Use when: Understanding interactions, planning changes
    - Example: map_relationships("src/main.py", depth=3)

11. **find_patterns** - Identify design and architectural patterns
    - Use when: Understanding conventions, ensuring consistency
    - Example: find_patterns("architectural")

12. **assess_tech_stack** - Identify technologies and frameworks in use
    - Use when: Planning integrations, making architectural decisions
    - Example: assess_tech_stack()

13. **find_entry_points** - Locate application entry points
    - Use when: Understanding startup flow, debugging initialization
    - Example: find_entry_points()

14. **analyze_data_flow** - Trace data flow through the application
    - Use when: Understanding request handling, tracking transformations
    - Example: analyze_data_flow("handle_user_request")

## Best Practices

When creating tasks:
- Use codebase tools to understand existing implementation before planning
- Search for similar features to maintain consistency
- Analyze components that will be affected by changes
- Include relevant file paths in task descriptions
- Use clear, actionable titles
- Include time estimates (e.g., "2h", "3 days")
- Specify dependencies with "needs:" or "depends:"
- Set priorities: low, medium, high, critical
- Group related tasks hierarchically

Example workflow:
1. First understand the codebase: search_codebase("existing feature")
2. Analyze affected components: analyze_component("src/module")
3. Check patterns: find_patterns()
4. Then create informed tasks with specific file references

Example task creation:
```
Build Authentication System:
  - Setup database schema (high, 2h)
    Files: src/models/user.py, migrations/
  - Implement user model:
    - Define fields (1h)
    - Add validation (1h)
  - Create auth endpoints (medium, 3h, needs: Implement user model)
    Files: src/api/auth.py, src/middleware/auth.py
  - Add JWT support (high, 2h, needs: Create auth endpoints)
  - Write tests (medium, 2h, needs: Add JWT support)
    Files: tests/test_auth.py
```
"""
        else:
            base_prompt += """Create task structures that:
- Break down complex requirements into manageable tasks
- Define clear dependencies between tasks
- Assign appropriate priorities and agents
- Estimate effort and complexity
"""
        
        return base_prompt
    
    async def get_enhanced_task_context(self, project_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get enhanced context for a project or specific task.
        
        Args:
            project_id: Project identifier
            task_id: Optional specific task ID
            
        Returns:
            Enhanced context with task graph information
        """
        if not self.use_enhanced_task_graph or project_id not in self.task_graph_managers:
            # Fall back to standard context
            return await self.get_project_context(project_id, task_id)
            
        manager = self.task_graph_managers[project_id]
        
        if task_id:
            # Get expanded context for specific task
            return manager.expand_task_context(task_id)
        else:
            # Get abstracted state for whole project
            return manager.get_abstracted_state()
    
    async def save_enhanced_task_graph(self, project_id: str) -> Optional[Path]:
        """
        Save the enhanced task graph to disk.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Path to saved file or None
        """
        if not self.use_enhanced_task_graph or project_id not in self.task_graph_managers:
            return None
            
        manager = self.task_graph_managers[project_id]
        return manager.save_graph()
    
    async def load_enhanced_task_graph(self, project_id: str) -> bool:
        """
        Load an enhanced task graph from disk.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if loaded successfully
        """
        if not self.use_enhanced_task_graph:
            return False
            
        # Create context and manager
        context = TaskGraphContext(
            project_id=project_id,
            project_path=self.project_path,
            rag_client=self.rag_client
        )
        manager = TaskGraphManager(context)
        
        # Try to load
        if manager.load_graph():
            self.task_graph_managers[project_id] = manager
            # Also convert to standard graph for compatibility
            self.task_graphs[project_id] = self._convert_to_standard_graph(manager.graph, project_id)
            return True
            
        return False
    
    async def create_implementation_plan(self, requirements: str, project_type: str = "feature", scope: str = "medium") -> Any:
        """
        Create a detailed phased implementation plan.
        
        This creates a plan using the deep context passing system with
        phases, milestones, and context chunks.
        
        Args:
            requirements: Project requirements
            project_type: Type of project (feature, bugfix, refactor, infrastructure)
            scope: Project scope (small, medium, large, enterprise)
            
        Returns:
            ImplementationPlan object
        """
        # Initialize plan-aware architect if not done
        if not self.plan_aware_architect:
            # Get the first task manager or create one
            if self.task_graph_managers:
                task_manager = list(self.task_graph_managers.values())[0]
            else:
                # Create a default task manager
                context = TaskGraphContext(
                    project_id="default",
                    project_path=self.project_path,
                    rag_client=self.rag_client
                )
                task_manager = TaskGraphManager(context)
                self.task_graph_managers["default"] = task_manager
            
            self.plan_aware_architect = PlanAwareArchitect(
                project_path=str(self.project_path),
                task_manager=task_manager,
                plan_manager=self.plan_manager,
                llm_client=self.llm_client
            )
        
        # Create the implementation plan
        plan = await self.plan_aware_architect.create_implementation_plan(
            requirement=requirements,
            project_type=project_type,
            scope=scope
        )
        
        logger.info(f"Created implementation plan: {plan.name}")
        return plan