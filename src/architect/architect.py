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
from src.core.logging import get_logger

# Optional import for RAG service
try:
    from src.rag_service import RAGService, RAGClient
    RAG_AVAILABLE = True
except ImportError:
    RAGService = None
    RAGClient = None
    RAG_AVAILABLE = False

# Optional import for LLM
try:
    from src.llm import LLMClient
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    LLMClient = None

logger = get_logger(__name__)


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
        elif LLM_AVAILABLE:
            try:
                # Use the new LLMClient with model card system
                model = os.getenv("ARCHITECT_MODEL")
                self.llm_client = LLMClient(model=model, agent_name="architect")
                logger.info(f"Architect using model: {self.llm_client.model_card.display_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client: {e}")
                self.llm_client = None
        else:
            self.llm_client = None
            logger.warning("Architect running without LLM - using mock responses")
        
        logger.info(f"Architect initialized for project: {self.project_path}")
        
        # Initialize architect tools if enhanced task graph is enabled
        self.architect_tools = None
        if self.use_enhanced_task_graph:
            logger.info("Enhanced task graph system enabled")
    
    def _index_project(self) -> None:
        """Index the project for RAG retrieval."""
        if not self.rag_client:
            return
            
        try:
            logger.info("Indexing project for RAG...")
            results = self.rag_client.index_directory(
                directory=str(self.project_path),
                extensions=[".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".hpp"],
                exclude_patterns=["**/node_modules/**", "**/.venv/**", "**/__pycache__/**", "**/.git/**"]
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
                    logger.info(f"Found {len(search_results)} relevant code chunks for analysis")
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")
        
        if self.llm_client:
            # Use LLM to analyze requirements with context
            try:
                system_prompt = """You are an expert software architect. Analyze the given requirements and provide a structured analysis including:
                - Project type (web app, API, CLI tool, etc.)
                - Complexity level (simple, medium, complex)
                - Key features list
                - Technical requirements
                - Suggested implementation phases
                - Estimated number of tasks
                Respond in JSON format.
                
                You have access to enhanced task management tools:
                - create_tasks: Create hierarchical task structures with dependencies
                - add_subtasks: Add subtasks to existing tasks
                - get_task_status: Check current task graph status
                - update_task_priority: Adjust task priorities
                
                When creating tasks, use natural language formats and be specific about dependencies and time estimates."""
                
                result = self.llm_client.generate_with_json(
                    prompt=f"Project requirements: {requirements}{rag_context}",
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                analysis = result
                
                # Ensure all expected fields exist
                analysis.setdefault('project_type', 'web_application')
                analysis.setdefault('complexity', 'medium')
                analysis.setdefault('estimated_tasks', 15)
                analysis.setdefault('key_features', [])
                analysis.setdefault('technical_requirements', [])
                analysis.setdefault('suggested_phases', ['Design', 'Implementation', 'Testing'])
                
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")
                # Fall back to mock response
                analysis = self._get_mock_analysis(requirements)
        else:
            # Use mock response
            analysis = self._get_mock_analysis(requirements)
        
        # Store analysis in RAG if available
        if self.rag_service:
            await self._store_in_rag(
                'project_analysis',
                f"Project Analysis\n\nRequirements: {requirements}\n\nAnalysis: {analysis}"
            )
        
        return analysis
    
    async def design_architecture(
        self,
        requirements: str,
        constraints: Optional[List[str]] = None
    ) -> ProjectStructure:
        """
        Design the overall system architecture based on requirements.
        
        Args:
            requirements: Project requirements
            constraints: Technical or business constraints
            
        Returns:
            ProjectStructure with component design
        """
        logger.info("Designing system architecture")
        
        # Update constraints
        if constraints:
            self.project_structure.constraints.extend(constraints)
        
        # Gather architectural context from RAG
        arch_context = ""
        if self.rag_client:
            try:
                # Search for existing architectural patterns
                patterns = self.rag_client.search(
                    query="class interface component service controller model architecture",
                    k=10,
                    filters={"chunk_type": {"$in": ["class", "module"]}}
                )
                
                # Search for configuration files
                configs = self.rag_client.search(
                    query="configuration settings config json yaml toml package dependencies",
                    k=5
                )
                
                if patterns or configs:
                    arch_context = "\n\nExisting architecture insights:\n"
                    
                    # Add pattern insights
                    if patterns:
                        arch_context += "\nCode patterns found:"
                        for p in patterns[:3]:
                            arch_context += f"\n- {p.get('file_path', '')}: {p.get('symbols', [])}"[:100]
                    
                    # Add config insights  
                    if configs:
                        arch_context += "\n\nConfiguration files:"
                        for c in configs[:2]:
                            arch_context += f"\n- {c.get('file_path', '')}"
                            
                    logger.info(f"Found {len(patterns)} patterns and {len(configs)} config files")
            except Exception as e:
                logger.warning(f"RAG architecture search failed: {e}")
        
        if self.llm_client:
            # Use LLM to design architecture with context
            try:
                system_prompt = """You are an expert software architect. Design a system architecture based on the requirements.
                Include:
                - Components (with name, type, technologies, responsibilities)
                - Interfaces between components (with name, from, to, protocol)
                - Technology stack recommendations
                - Key architectural decisions and patterns
                Respond in JSON format with 'components' and 'interfaces' arrays."""
                
                user_prompt = f"Requirements: {requirements}\nConstraints: {constraints or 'None'}{arch_context}"
                
                response_text = self.llm_client.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=1500
                )
                
                # Parse JSON from response
                try:
                    arch_design = json.loads(response_text)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    import re
                    json_match = re.search(r'```(?:json)?\n(.*?)\n```', response_text, re.DOTALL)
                    if json_match:
                        arch_design = json.loads(json_match.group(1))
                    else:
                        raise
                
                self.project_structure.components = arch_design.get('components', [])
                self.project_structure.interfaces = arch_design.get('interfaces', [])
                self.project_structure.technology_stack = arch_design.get('technology_stack', {})
                
                # Add any architectural patterns or decisions
                if 'patterns' in arch_design:
                    self.project_structure.assumptions.extend(arch_design['patterns'])
                
            except Exception as e:
                logger.error(f"LLM architecture design failed: {e}")
                # Fall back to simple architecture
                self._create_simple_architecture(requirements)
        else:
            # Use simple architecture
            self._create_simple_architecture(requirements)
        
        # Store architecture in RAG
        if self.rag_service:
            await self._store_in_rag(
                'system_architecture',
                self._format_architecture_doc()
            )
        
        return self.project_structure
    
    def _create_simple_architecture(self, requirements: str):
        """Create a simple fallback architecture when LLM fails."""
        self.project_structure.components = [
            {
                "name": "MainComponent",
                "type": "service",
                "technologies": ["python"],
                "responsibilities": ["Core functionality based on requirements"]
            }
        ]
        self.project_structure.interfaces = []
        self.project_structure.technology_stack = {
            "language": "python",
            "framework": "none"
        }
    
    async def create_task_graph(
        self,
        project_id: str,
        requirements: str,
        architecture: Optional[ProjectStructure] = None
    ) -> TaskGraph:
        """
        Create a task dependency graph for the project.
        
        Args:
            project_id: Unique project identifier
            requirements: Project requirements
            architecture: System architecture (uses self.project_structure if None)
            
        Returns:
            TaskGraph with all tasks and dependencies
        """
        logger.info(f"Creating task graph for project: {project_id}")
        
        if architecture is None:
            architecture = self.project_structure
        
        # Use enhanced task graph if enabled
        if self.use_enhanced_task_graph:
            return await self._create_enhanced_task_graph(project_id, requirements, architecture)
        
        # Create standard task graph
        graph = TaskGraph(project_id=project_id)
        
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
            self.architect_tools = ArchitectTools(manager)
            
        # Handle function calls
        if function_name == "create_tasks":
            return await self.architect_tools.create_tasks(**arguments)
        elif function_name == "add_subtasks":
            return await self.architect_tools.add_subtasks(**arguments)
        elif function_name == "get_task_status":
            return await self.architect_tools.get_task_status(**arguments)
        elif function_name == "update_task_priority":
            return await self.architect_tools.update_task_priority(**arguments)
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
- Creating and managing task dependency graphs
- Orchestrating the development workflow

"""
        
        if self.use_enhanced_task_graph:
            base_prompt += """You have access to enhanced task management tools:

1. **create_tasks** - Create hierarchical task structures using natural language formats:
   - List format (recommended): Simple bullet lists with time estimates and dependencies
   - Markdown format: Structured markdown with headers and task details
   - YAML format: Structured YAML for complex hierarchies

2. **add_subtasks** - Break down existing tasks into subtasks

3. **get_task_status** - Check current progress and task states

4. **update_task_priority** - Adjust task priorities as needed

When creating tasks:
- Use clear, actionable titles
- Include time estimates (e.g., "2h", "3 days")
- Specify dependencies with "needs:" or "depends:"
- Set priorities: low, medium, high, critical
- Group related tasks hierarchically

Example task creation:
```
Build Authentication System:
  - Setup database schema (high, 2h)
  - Implement user model:
    - Define fields (1h)
    - Add validation (1h)
  - Create auth endpoints (medium, 3h, needs: Implement user model)
  - Add JWT support (high, 2h, needs: Create auth endpoints)
  - Write tests (medium, 2h, needs: Add JWT support)
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
        
        # Store task graph
        self.task_graphs[project_id] = graph
        
        # Store task graph in RAG
        if self.rag_service:
            await self._store_in_rag(
                f'task_graph_{project_id}',
                self._format_task_graph_doc(graph)
            )
        
        return graph
    
    async def _create_enhanced_task_graph(
        self,
        project_id: str,
        requirements: str,
        architecture: ProjectStructure
    ) -> TaskGraph:
        """
        Create an enhanced task graph using the TaskGraphManager and LLM tools.
        
        Args:
            project_id: Unique project identifier
            requirements: Project requirements
            architecture: System architecture
            
        Returns:
            TaskGraph with all tasks and dependencies
        """
        logger.info(f"Creating enhanced task graph for project: {project_id}")
        
        # Create task graph context
        context = TaskGraphContext(
            project_id=project_id,
            project_path=self.project_path,
            rag_client=self.rag_client,
            agent_registry=None,  # Will be set by orchestrator
            scheduler=None  # Will be set by orchestrator
        )
        
        # Create task graph manager
        manager = TaskGraphManager(context)
        self.task_graph_managers[project_id] = manager
        
        # Initialize architect tools
        self.architect_tools = ArchitectTools(manager)
        
        if self.llm_client:
            # Use LLM to create tasks with function calling
            try:
                # Get available functions
                functions = self.architect_tools.get_tool_definitions()
                
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert software architect. Create a comprehensive task structure for the given requirements.
                            
                            Use the create_tasks function to build a hierarchical task structure. Consider:
                            - Breaking down the project into logical phases
                            - Creating clear dependencies between tasks
                            - Estimating time for each task
                            - Assigning appropriate priorities
                            
                            Use the 'list' format for clarity. Include time estimates and dependencies."""
                        },
                        {
                            "role": "user",
                            "content": f"Requirements: {requirements}\n\nArchitecture: {architecture.components[:3]}"
                        }
                    ],
                    functions=functions,
                    function_call="auto",
                    temperature=0.7,
                    max_tokens=2000
                )
                
                # Process function calls
                if response.choices[0].message.function_call:
                    function_name = response.choices[0].message.function_call.name
                    function_args = json.loads(response.choices[0].message.function_call.arguments)
                    
                    if function_name == "create_tasks":
                        result = await self.architect_tools.create_tasks(**function_args)
                        logger.info(f"Created {result.get('created_tasks', 0)} tasks via LLM")
                    
                    # Check if we need to add more details
                    if result.get("status") == "success" and result.get("created_tasks", 0) > 0:
                        # Get task status to see what was created
                        status = await self.architect_tools.get_task_status(detail_level="summary")
                        
                        # Store in RAG
                        if self.rag_service:
                            await self._store_in_rag(
                                f'enhanced_task_graph_{project_id}',
                                f"Enhanced Task Graph Created\n\nStatus: {status}"
                            )
                
            except Exception as e:
                logger.error(f"LLM task creation failed: {e}")
                # Fall back to manual creation
                await self._create_default_enhanced_tasks(manager, requirements)
        else:
            # Create default tasks without LLM
            await self._create_default_enhanced_tasks(manager, requirements)
        
        # Convert enhanced graph to standard TaskGraph for compatibility
        standard_graph = self._convert_to_standard_graph(manager.graph, project_id)
        self.task_graphs[project_id] = standard_graph
        
        return standard_graph
    
    async def _create_default_enhanced_tasks(self, manager: TaskGraphManager, requirements: str):
        """Create default enhanced tasks when LLM is not available."""
        # Create a simple task hierarchy
        await manager.create_task_hierarchy(
            epic_title="Project Implementation",
            epic_description=f"Implement project based on: {requirements[:200]}...",
            subtasks=[
                {
                    "title": "Setup Project Structure",
                    "description": "Initialize project with dependencies",
                    "agent_type": "request_planner",
                    "priority": "HIGH"
                },
                {
                    "title": "Implement Core Features",
                    "description": "Build main functionality",
                    "agent_type": "coding_agent",
                    "priority": "HIGH",
                    "dependencies": ["Setup Project Structure"]
                },
                {
                    "title": "Add Tests",
                    "description": "Write unit and integration tests",
                    "agent_type": "code_tester",
                    "priority": "MEDIUM",
                    "dependencies": ["Implement Core Features"]
                }
            ]
        )
        
        # Auto-detect communities
        manager.detect_and_create_communities(method="theme")
    
    def _convert_to_standard_graph(self, enhanced_graph, project_id: str) -> TaskGraph:
        """Convert enhanced graph to standard TaskGraph for compatibility."""
        standard_graph = TaskGraph(project_id=project_id)
        
        # Convert each enhanced task to standard task
        for task_id, enhanced_task in enhanced_graph.tasks.items():
            standard_task = TaskNode(
                id=enhanced_task.id,
                title=enhanced_task.title,
                description=enhanced_task.description,
                agent_type=enhanced_task.agent_type,
                priority=enhanced_task.priority,
                status=enhanced_task.status,
                dependencies=enhanced_task.dependencies,
                context=enhanced_task.context
            )
            
            # Copy timestamps
            standard_task.created_at = enhanced_task.created_at
            standard_task.started_at = enhanced_task.started_at
            standard_task.completed_at = enhanced_task.completed_at
            
            standard_graph.add_task(standard_task)
            
            # Mark completed if needed
            if enhanced_task.status == TaskStatus.COMPLETED:
                standard_graph.mark_completed(task_id)
        
        return standard_graph
    
    async def get_next_tasks(self, project_id: str) -> List[TaskNode]:
        """
        Get the next tasks that should be worked on.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of tasks ready for execution
        """
        if project_id not in self.task_graphs:
            return []
        
        graph = self.task_graphs[project_id]
        return graph.get_ready_tasks()
    
    async def update_task_status(
        self,
        project_id: str,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the status of a task in the graph.
        
        Args:
            project_id: Project identifier
            task_id: Task identifier
            status: New task status
            error_message: Error message if task failed
            
        Returns:
            True if update successful
        """
        if project_id not in self.task_graphs:
            return False
        
        graph = self.task_graphs[project_id]
        if task_id not in graph.tasks:
            return False
        
        task = graph.tasks[task_id]
        task.status = status
        
        if status == TaskStatus.IN_PROGRESS:
            task.started_at = datetime.utcnow()
        elif status == TaskStatus.COMPLETED:
            graph.mark_completed(task_id)
        elif status == TaskStatus.FAILED:
            task.error_message = error_message
        
        # Update RAG with new status
        if self.rag_service:
            await self._store_in_rag(
                f'task_status_{project_id}_{task_id}',
                f"Task: {task.title}\nStatus: {status.value}\nTimestamp: {datetime.utcnow().isoformat()}"
            )
        
        return True
    
    async def get_project_context(self, project_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get relevant context for a project or specific task.
        
        Args:
            project_id: Project identifier
            task_id: Optional specific task ID
            
        Returns:
            Dictionary with relevant context
        """
        context = {
            'project_id': project_id,
            'architecture': self.project_structure.to_dict() if hasattr(self.project_structure, 'to_dict') else {},
            'task_graph_stats': {}
        }
        
        if project_id in self.task_graphs:
            graph = self.task_graphs[project_id]
            context['task_graph_stats'] = graph.to_dict()['stats']
            
            if task_id and task_id in graph.tasks:
                task = graph.tasks[task_id]
                context['task'] = task.to_dict()
                context['dependencies'] = [
                    graph.tasks[dep_id].to_dict()
                    for dep_id in task.dependencies
                    if dep_id in graph.tasks
                ]
        
        return context
    
    async def _store_in_rag(self, doc_id: str, content: str) -> None:
        """Store document in RAG service."""
        if not self.rag_service:
            return
        
        try:
            # In real implementation, would use actual RAG storage
            logger.info(f"Storing document in RAG: {doc_id}")
            # await self.rag_service.store_document(doc_id, content)
        except Exception as e:
            logger.error(f"Failed to store in RAG: {e}")
    
    def _format_architecture_doc(self) -> str:
        """Format architecture as a document."""
        doc = "# System Architecture\n\n"
        
        doc += "## Components\n"
        for comp in self.project_structure.components:
            doc += f"\n### {comp['name']}\n"
            doc += f"- Type: {comp['type']}\n"
            doc += f"- Technologies: {', '.join(comp['technologies'])}\n"
            doc += f"- Responsibilities: {', '.join(comp['responsibilities'])}\n"
        
        doc += "\n## Interfaces\n"
        for intf in self.project_structure.interfaces:
            doc += f"\n### {intf['name']}\n"
            doc += f"- From: {intf['from']}\n"
            doc += f"- To: {intf['to']}\n"
            doc += f"- Protocol: {intf['protocol']}\n"
        
        return doc
    
    def _format_task_graph_doc(self, graph: TaskGraph) -> str:
        """Format task graph as a document."""
        doc = f"# Task Graph for Project {graph.project_id}\n\n"
        
        doc += f"## Summary\n"
        stats = graph.to_dict()['stats']
        doc += f"- Total Tasks: {stats['total_tasks']}\n"
        doc += f"- Critical Path Length: {stats['critical_path_length']}\n"
        
        doc += f"\n## Tasks\n"
        for task in graph.tasks.values():
            doc += f"\n### {task.title}\n"
            doc += f"- ID: {task.id}\n"
            doc += f"- Agent: {task.agent_type}\n"
            doc += f"- Priority: {task.priority.value}\n"
            doc += f"- Description: {task.description}\n"
            if task.dependencies:
                doc += f"- Dependencies: {len(task.dependencies)}\n"
        
        return doc
    
    async def analyze_existing_architecture(self) -> Dict[str, Any]:
        """Analyze the existing project architecture using RAG."""
        if not self.rag_client:
            return {"error": "RAG not available"}
        
        analysis = {
            "components": [],
            "patterns": [],
            "technologies": set(),
            "structure": {}
        }
        
        try:
            # Find main entry points
            entry_points = self.rag_client.search(
                query="main app application server index entry point start",
                k=10,
                filters={"chunk_type": {"$in": ["function", "module"]}}
            )
            
            # Find architectural patterns
            patterns = self.rag_client.search(
                query="controller service model view component factory singleton repository",
                k=15,
                filters={"chunk_type": "class"}
            )
            
            # Find configuration and dependencies
            configs = self.rag_client.search(
                query="package.json requirements.txt pyproject.toml cargo.toml pom.xml build.gradle",
                k=10
            )
            
            # Analyze results
            for entry in entry_points:
                file_path = entry.get('file_path', '')
                if 'server' in file_path.lower() or 'app' in file_path.lower():
                    analysis['components'].append({
                        'type': 'entry_point',
                        'file': file_path,
                        'purpose': 'Application entry'
                    })
            
            # Extract patterns
            pattern_types = set()
            for pattern in patterns:
                symbols = pattern.get('symbols', [])
                for symbol in symbols:
                    if 'Controller' in symbol:
                        pattern_types.add('MVC')
                    elif 'Service' in symbol:
                        pattern_types.add('Service Layer')
                    elif 'Repository' in symbol:
                        pattern_types.add('Repository Pattern')
            
            analysis['patterns'] = list(pattern_types)
            
            # Extract technologies from config files
            for config in configs:
                file_name = Path(config.get('file_path', '')).name
                if file_name == 'package.json':
                    analysis['technologies'].add('Node.js')
                elif file_name in ['requirements.txt', 'pyproject.toml']:
                    analysis['technologies'].add('Python')
                elif file_name == 'pom.xml':
                    analysis['technologies'].add('Java/Maven')
            
            analysis['technologies'] = list(analysis['technologies'])
            
            return analysis
            
        except Exception as e:
            logger.error(f"Architecture analysis failed: {e}")
            return {"error": str(e)}
    
    async def find_similar_implementations(self, feature_description: str) -> List[Dict[str, Any]]:
        """Find similar implementations in the codebase."""
        if not self.rag_client:
            return []
        
        try:
            # Search for similar features
            results = self.rag_client.search(
                query=feature_description,
                k=10,
                filters={"chunk_type": {"$in": ["function", "class", "method"]}}
            )
            
            # Format results
            similar_impls = []
            for result in results:
                similar_impls.append({
                    'file': result.get('file_path', ''),
                    'symbols': result.get('symbols', []),
                    'summary': result.get('content', '')[:200],
                    'relevance': result.get('score', 0)
                })
            
            return similar_impls
            
        except Exception as e:
            logger.error(f"Similar implementation search failed: {e}")
            return []
    
    async def get_component_dependencies(self, component_name: str) -> Dict[str, List[str]]:
        """Get dependencies for a specific component."""
        if not self.rag_client:
            return {}
        
        try:
            # Search for the component
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
            self.architect_tools = ArchitectTools(manager)
            
        # Handle function calls
        if function_name == "create_tasks":
            return await self.architect_tools.create_tasks(**arguments)
        elif function_name == "add_subtasks":
            return await self.architect_tools.add_subtasks(**arguments)
        elif function_name == "get_task_status":
            return await self.architect_tools.get_task_status(**arguments)
        elif function_name == "update_task_priority":
            return await self.architect_tools.update_task_priority(**arguments)
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
- Creating and managing task dependency graphs
- Orchestrating the development workflow

"""
        
        if self.use_enhanced_task_graph:
            base_prompt += """You have access to enhanced task management tools:

1. **create_tasks** - Create hierarchical task structures using natural language formats:
   - List format (recommended): Simple bullet lists with time estimates and dependencies
   - Markdown format: Structured markdown with headers and task details
   - YAML format: Structured YAML for complex hierarchies

2. **add_subtasks** - Break down existing tasks into subtasks

3. **get_task_status** - Check current progress and task states

4. **update_task_priority** - Adjust task priorities as needed

When creating tasks:
- Use clear, actionable titles
- Include time estimates (e.g., "2h", "3 days")
- Specify dependencies with "needs:" or "depends:"
- Set priorities: low, medium, high, critical
- Group related tasks hierarchically

Example task creation:
```
Build Authentication System:
  - Setup database schema (high, 2h)
  - Implement user model:
    - Define fields (1h)
    - Add validation (1h)
  - Create auth endpoints (medium, 3h, needs: Implement user model)
  - Add JWT support (high, 2h, needs: Create auth endpoints)
  - Write tests (medium, 2h, needs: Add JWT support)
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