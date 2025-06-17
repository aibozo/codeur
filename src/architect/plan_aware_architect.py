"""
Plan-aware architect that creates detailed phased implementation plans.

This module extends the architect's capabilities to generate comprehensive
implementation plans with rich context for downstream agents.
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from .models import TaskNode, TaskStatus, TaskPriority
from .task_graph_manager import TaskGraphManager
from .plan_manager import PlanManager
from .plan_models import (
    ImplementationPlan, PhaseType, PlanStatus,
    ImplementationPhase, PlanMilestone, PlanChunk
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class PlanAwareArchitect:
    """
    Enhanced architect that creates detailed implementation plans.
    
    This architect generates phased plans with rich context chunks that
    get passed to execution agents throughout the development pipeline.
    """
    
    def __init__(self,
                 project_path: str,
                 task_manager: TaskGraphManager,
                 plan_manager: PlanManager,
                 llm_client: Optional[Any] = None):
        """
        Initialize the plan-aware architect.
        
        Args:
            project_path: Root path of the project
            task_manager: Task graph manager
            plan_manager: Plan manager for storing plans
            llm_client: Optional LLM client for enhanced planning
        """
        self.project_path = Path(project_path)
        self.task_manager = task_manager
        self.plan_manager = plan_manager
        self.llm_client = llm_client
        
        # Plan templates for common scenarios
        self.plan_templates = self._load_plan_templates()
    
    def _load_plan_templates(self) -> Dict[str, Any]:
        """Load predefined plan templates."""
        return {
            "feature_development": {
                "phases": [
                    {"type": "research", "name": "Research & Analysis"},
                    {"type": "design", "name": "Design & Architecture"},
                    {"type": "implementation", "name": "Implementation"},
                    {"type": "testing", "name": "Testing & Quality"},
                    {"type": "documentation", "name": "Documentation"}
                ]
            },
            "bug_fix": {
                "phases": [
                    {"type": "research", "name": "Issue Analysis"},
                    {"type": "implementation", "name": "Fix Implementation"},
                    {"type": "testing", "name": "Testing & Validation"}
                ]
            },
            "refactoring": {
                "phases": [
                    {"type": "research", "name": "Code Analysis"},
                    {"type": "design", "name": "Refactoring Design"},
                    {"type": "implementation", "name": "Incremental Refactoring"},
                    {"type": "testing", "name": "Regression Testing"}
                ]
            },
            "infrastructure": {
                "phases": [
                    {"type": "research", "name": "Requirements Analysis"},
                    {"type": "design", "name": "Infrastructure Design"},
                    {"type": "implementation", "name": "Setup & Configuration"},
                    {"type": "testing", "name": "Integration Testing"},
                    {"type": "deployment", "name": "Deployment & Migration"}
                ]
            }
        }
    
    async def create_implementation_plan(self,
                                       requirement: str,
                                       project_type: str = "feature",
                                       scope: str = "medium") -> ImplementationPlan:
        """
        Create a detailed implementation plan from a requirement.
        
        Args:
            requirement: The requirement or feature description
            project_type: Type of project (feature, bugfix, refactor, etc.)
            scope: Project scope (small, medium, large, enterprise)
            
        Returns:
            A detailed implementation plan with phases and context chunks
        """
        logger.info(f"Creating implementation plan for: {requirement}")
        
        # Create base plan
        plan_name = self._generate_plan_name(requirement)
        plan = self.plan_manager.create_plan(
            name=plan_name,
            description=requirement,
            project_type=project_type,
            scope=scope
        )
        
        # Generate plan details using LLM if available
        if self.llm_client:
            await self._enhance_plan_with_llm(plan, requirement)
        else:
            # Use template-based approach
            self._create_plan_from_template(plan, project_type, requirement)
        
        # Save and index the plan
        self.plan_manager.save_plan(plan)
        
        # Create corresponding task graph
        await self._create_task_graph_from_plan(plan)
        
        logger.info(f"Created implementation plan '{plan.name}' with {len(plan.phases)} phases")
        return plan
    
    def _generate_plan_name(self, requirement: str) -> str:
        """Generate a concise plan name from requirement."""
        # Simple heuristic: take first few words
        words = requirement.split()[:5]
        return " ".join(words)
    
    async def _enhance_plan_with_llm(self, plan: ImplementationPlan, requirement: str):
        """Use LLM to generate detailed plan content."""
        prompt = f"""
        Create a detailed implementation plan for the following requirement:
        
        Requirement: {requirement}
        Project Type: {plan.project_type}
        Scope: {plan.scope}
        
        Generate a comprehensive plan with:
        1. Business objectives (2-3 clear objectives)
        2. Technical requirements (3-5 specific requirements)
        3. Technology stack (list of technologies needed)
        4. Architectural patterns (relevant patterns to use)
        5. Constraints (technical or business constraints)
        6. Phases with milestones and detailed context
        
        For each phase, include:
        - Phase objectives
        - Key decisions to make
        - Specific milestones with deliverables
        - Implementation details as context chunks
        
        Format the response as JSON.
        """
        
        try:
            response = await self.llm_client.generate(prompt)
            plan_data = json.loads(response)
            
            # Update plan with LLM-generated content
            plan.business_objectives = plan_data.get("business_objectives", [])
            plan.technical_requirements = plan_data.get("technical_requirements", [])
            plan.technology_stack = plan_data.get("technology_stack", [])
            plan.architectural_patterns = plan_data.get("architectural_patterns", [])
            plan.constraints = plan_data.get("constraints", [])
            
            # Create phases
            for phase_data in plan_data.get("phases", []):
                phase = self._create_phase_from_data(plan, phase_data)
                
                # Create milestones
                for milestone_data in phase_data.get("milestones", []):
                    milestone = self._create_milestone_from_data(phase, milestone_data)
                    
                    # Create context chunks
                    for chunk_data in milestone_data.get("chunks", []):
                        self._create_chunk_from_data(milestone, chunk_data)
        
        except Exception as e:
            logger.error(f"Failed to enhance plan with LLM: {e}")
            # Fall back to template
            self._create_plan_from_template(plan, plan.project_type, requirement)
    
    def _create_plan_from_template(self, plan: ImplementationPlan, project_type: str, requirement: str):
        """Create plan using predefined templates."""
        template = self.plan_templates.get(project_type, self.plan_templates["feature_development"])
        
        # Set default objectives and requirements based on type
        if project_type == "feature":
            plan.business_objectives = [
                f"Deliver {requirement} functionality",
                "Ensure scalability and maintainability",
                "Maintain backward compatibility"
            ]
            plan.technical_requirements = [
                "Implement core functionality",
                "Add comprehensive error handling",
                "Include unit and integration tests",
                "Document API and usage"
            ]
        elif project_type == "bugfix":
            plan.business_objectives = [
                f"Resolve {requirement}",
                "Prevent regression",
                "Minimize user impact"
            ]
            plan.technical_requirements = [
                "Identify root cause",
                "Implement targeted fix",
                "Add regression tests",
                "Verify fix in production-like environment"
            ]
        
        # Create phases from template
        for idx, phase_template in enumerate(template["phases"]):
            phase = self.plan_manager.add_phase(
                plan=plan,
                name=phase_template["name"],
                phase_type=PhaseType(phase_template["type"]),
                description=f"{phase_template['name']} for {requirement}",
                objectives=self._generate_phase_objectives(phase_template["type"], requirement),
                estimated_days=self._estimate_phase_duration(phase_template["type"], plan.scope)
            )
            
            # Add milestones based on phase type
            self._add_phase_milestones(phase, requirement)
    
    def _generate_phase_objectives(self, phase_type: str, requirement: str) -> List[str]:
        """Generate phase objectives based on type."""
        objectives_map = {
            "research": [
                f"Understand requirements for {requirement}",
                "Analyze existing codebase and patterns",
                "Identify potential challenges and risks"
            ],
            "design": [
                "Create architectural design",
                "Define component interfaces",
                "Plan data models and flows"
            ],
            "implementation": [
                "Implement core functionality",
                "Follow coding standards",
                "Ensure modularity and reusability"
            ],
            "testing": [
                "Achieve comprehensive test coverage",
                "Validate all requirements",
                "Ensure performance meets standards"
            ],
            "documentation": [
                "Document API and usage",
                "Create user guides",
                "Update system documentation"
            ]
        }
        
        return objectives_map.get(phase_type, ["Complete phase objectives"])
    
    def _estimate_phase_duration(self, phase_type: str, scope: str) -> float:
        """Estimate phase duration based on type and scope."""
        base_durations = {
            "research": {"small": 1, "medium": 2, "large": 3, "enterprise": 5},
            "design": {"small": 1, "medium": 3, "large": 5, "enterprise": 10},
            "implementation": {"small": 3, "medium": 10, "large": 20, "enterprise": 40},
            "testing": {"small": 1, "medium": 3, "large": 5, "enterprise": 10},
            "documentation": {"small": 0.5, "medium": 1, "large": 2, "enterprise": 3}
        }
        
        durations = base_durations.get(phase_type, {"small": 1, "medium": 2, "large": 3, "enterprise": 5})
        return durations.get(scope, 2)
    
    def _add_phase_milestones(self, phase: ImplementationPhase, requirement: str):
        """Add appropriate milestones to a phase."""
        if phase.phase_type == PhaseType.RESEARCH:
            milestone = self.plan_manager.add_milestone(
                phase=phase,
                title="Requirements Analysis Complete",
                description="Complete understanding of requirements and constraints",
                deliverables=[
                    "Requirements document",
                    "Technical constraints analysis",
                    "Risk assessment"
                ],
                success_criteria=[
                    "All stakeholder requirements documented",
                    "Technical feasibility confirmed",
                    "Risks identified and mitigation planned"
                ]
            )
            
            # Add context chunks
            self._add_research_chunks(milestone, requirement)
            
        elif phase.phase_type == PhaseType.DESIGN:
            milestone = self.plan_manager.add_milestone(
                phase=phase,
                title="Architecture Design Complete",
                description="Complete system design and component architecture",
                deliverables=[
                    "Architecture diagram",
                    "Component specifications",
                    "API design document"
                ],
                success_criteria=[
                    "Design reviewed and approved",
                    "All components clearly defined",
                    "Integration points documented"
                ]
            )
            
            self._add_design_chunks(milestone, requirement)
            
        elif phase.phase_type == PhaseType.IMPLEMENTATION:
            # Multiple milestones for implementation
            milestone1 = self.plan_manager.add_milestone(
                phase=phase,
                title="Core Implementation Complete",
                description="Core functionality implemented and working",
                deliverables=[
                    "Core feature code",
                    "Unit tests",
                    "Integration with existing system"
                ],
                success_criteria=[
                    "All core features working",
                    "Unit tests passing",
                    "Code review completed"
                ]
            )
            self._add_implementation_chunks(milestone1, requirement, "core")
            
            milestone2 = self.plan_manager.add_milestone(
                phase=phase,
                title="Full Implementation Complete",
                description="All features implemented with edge cases handled",
                deliverables=[
                    "Complete feature implementation",
                    "Error handling",
                    "Performance optimization"
                ],
                success_criteria=[
                    "All requirements implemented",
                    "Error scenarios handled",
                    "Performance benchmarks met"
                ]
            )
            self._add_implementation_chunks(milestone2, requirement, "full")
    
    def _add_research_chunks(self, milestone: PlanMilestone, requirement: str):
        """Add research phase context chunks."""
        chunks = [
            {
                "title": "Requirement Analysis",
                "content": f"""
                Analyze the requirement: {requirement}
                
                Key areas to investigate:
                1. User needs and use cases
                2. Technical requirements and constraints
                3. Integration points with existing system
                4. Performance and scalability needs
                5. Security considerations
                
                Look for:
                - Similar existing implementations
                - Potential code reuse opportunities
                - Third-party libraries or services
                - Architectural patterns that fit
                """,
                "type": "research",
                "priority": 10
            },
            {
                "title": "Codebase Analysis",
                "content": f"""
                Analyze existing codebase for {requirement} implementation:
                
                1. Search for related functionality
                2. Identify integration points
                3. Find reusable components
                4. Understand current architecture
                5. Locate relevant tests
                
                Key files to examine:
                - Controllers/handlers for similar features
                - Data models and schemas
                - Service layers and business logic
                - Configuration and infrastructure
                """,
                "type": "technical",
                "priority": 9
            }
        ]
        
        for chunk_data in chunks:
            chunk = self.plan_manager.add_chunk(
                milestone=milestone,
                title=chunk_data["title"],
                content=chunk_data["content"],
                chunk_type=chunk_data["type"],
                priority=chunk_data["priority"]
            )
            chunk.tags = {"research", "analysis", requirement.lower().replace(" ", "-")}
    
    def _add_design_chunks(self, milestone: PlanMilestone, requirement: str):
        """Add design phase context chunks."""
        chunks = [
            {
                "title": "Architecture Design",
                "content": f"""
                Design architecture for {requirement}:
                
                1. Component Structure:
                   - Define main components and their responsibilities
                   - Establish clear interfaces between components
                   - Plan for extensibility and maintainability
                
                2. Data Flow:
                   - Input/output data formats
                   - Processing pipeline
                   - State management approach
                
                3. Integration Points:
                   - API endpoints needed
                   - Database schema changes
                   - External service integrations
                
                4. Design Patterns:
                   - Choose appropriate patterns (MVC, Repository, etc.)
                   - Define abstraction layers
                   - Plan for dependency injection
                """,
                "type": "architectural",
                "priority": 10
            },
            {
                "title": "API Design",
                "content": f"""
                Design APIs for {requirement}:
                
                1. RESTful Endpoints:
                   - Define resource paths
                   - HTTP methods and status codes
                   - Request/response formats
                
                2. Data Models:
                   - Input validation schemas
                   - Response DTOs
                   - Error response formats
                
                3. Authentication/Authorization:
                   - Required permissions
                   - Access control rules
                   - Rate limiting needs
                
                4. Documentation:
                   - OpenAPI/Swagger specs
                   - Example requests/responses
                   - Error scenarios
                """,
                "type": "technical",
                "priority": 9
            }
        ]
        
        for chunk_data in chunks:
            chunk = self.plan_manager.add_chunk(
                milestone=milestone,
                title=chunk_data["title"],
                content=chunk_data["content"],
                chunk_type=chunk_data["type"],
                priority=chunk_data["priority"]
            )
            chunk.tags = {"design", "architecture", requirement.lower().replace(" ", "-")}
    
    def _add_implementation_chunks(self, milestone: PlanMilestone, requirement: str, phase: str):
        """Add implementation phase context chunks."""
        if phase == "core":
            chunks = [
                {
                    "title": "Core Implementation Guide",
                    "content": f"""
                    Implement core functionality for {requirement}:
                    
                    1. Start with data models:
                       - Create/update database schemas
                       - Implement model classes
                       - Add validation logic
                    
                    2. Implement business logic:
                       - Create service classes
                       - Implement core algorithms
                       - Handle main use cases
                    
                    3. Add API endpoints:
                       - Implement controllers/handlers
                       - Add request validation
                       - Return appropriate responses
                    
                    4. Basic error handling:
                       - Catch expected exceptions
                       - Return meaningful errors
                       - Log appropriately
                    """,
                    "type": "implementation",
                    "priority": 10
                },
                {
                    "title": "Testing Strategy",
                    "content": f"""
                    Test the core implementation of {requirement}:
                    
                    1. Unit tests:
                       - Test individual functions/methods
                       - Mock external dependencies
                       - Cover happy path and edge cases
                    
                    2. Integration tests:
                       - Test API endpoints
                       - Verify database operations
                       - Check service interactions
                    
                    3. Test data:
                       - Create realistic test fixtures
                       - Cover various scenarios
                       - Include edge cases
                    """,
                    "type": "testing",
                    "priority": 9
                }
            ]
        else:  # full implementation
            chunks = [
                {
                    "title": "Complete Implementation",
                    "content": f"""
                    Complete the implementation of {requirement}:
                    
                    1. Edge case handling:
                       - Identify all edge cases
                       - Implement proper handling
                       - Add specific tests
                    
                    2. Performance optimization:
                       - Profile critical paths
                       - Optimize database queries
                       - Add caching where beneficial
                    
                    3. Security hardening:
                       - Input sanitization
                       - Access control verification
                       - Audit logging
                    
                    4. Production readiness:
                       - Configuration management
                       - Monitoring/metrics
                       - Documentation updates
                    """,
                    "type": "implementation",
                    "priority": 8
                }
            ]
        
        for chunk_data in chunks:
            chunk = self.plan_manager.add_chunk(
                milestone=milestone,
                title=chunk_data["title"],
                content=chunk_data["content"],
                chunk_type=chunk_data["type"],
                priority=chunk_data["priority"]
            )
            chunk.tags = {"implementation", phase, requirement.lower().replace(" ", "-")}
    
    async def _create_task_graph_from_plan(self, plan: ImplementationPlan):
        """Create a task graph from the implementation plan."""
        graph_id = f"plan_{plan.id}"
        description = f"Task graph for plan: {plan.name}"
        
        # Create task graph
        self.task_manager.create_graph(graph_id, description)
        
        # Create tasks for each milestone
        task_map = {}  # milestone_id -> task_node
        
        for phase_idx, phase in enumerate(plan.phases):
            for milestone_idx, milestone in enumerate(phase.milestones):
                # Create task for milestone
                task_title = f"{phase.name}: {milestone.title}"
                task_description = milestone.description
                
                # Add context from chunks to description
                if milestone.chunks:
                    chunk_summaries = [f"- {chunk.title}" for chunk in milestone.chunks[:3]]
                    task_description += "\n\nContext chunks:\n" + "\n".join(chunk_summaries)
                
                # Determine task type based on phase
                task_type = self._get_task_type_for_phase(phase.phase_type)
                
                # Create task node
                task_node = TaskNode(
                    title=task_title,
                    description=task_description,
                    priority=TaskPriority.HIGH if phase_idx == 0 else TaskPriority.MEDIUM,
                    agent_type=task_type
                )
                
                # Add to graph
                self.task_manager.add_task(graph_id, task_node)
                task_map[milestone.id] = task_node
                
                # Map task to plan chunks
                chunk_ids = [chunk.id for chunk in milestone.chunks]
                if chunk_ids:
                    self.plan_manager.map_task_to_chunks(task_node.id, chunk_ids)
        
        # Add dependencies based on milestone dependencies
        for phase in plan.phases:
            for milestone in phase.milestones:
                if milestone.id in task_map:
                    task_node = task_map[milestone.id]
                    for dep_milestone_id in milestone.depends_on_milestones:
                        if dep_milestone_id in task_map:
                            dep_task = task_map[dep_milestone_id]
                            self.task_manager.add_dependency(graph_id, dep_task.id, task_node.id)
        
        # Update plan with task graph ID
        plan.task_graph_id = graph_id
        self.plan_manager.save_plan(plan)
        
        logger.info(f"Created task graph '{graph_id}' from plan '{plan.name}'")
    
    def _get_task_type_for_phase(self, phase_type: PhaseType) -> str:
        """Map phase type to agent type."""
        mapping = {
            PhaseType.RESEARCH: "coding_agent",  # Research involves code analysis
            PhaseType.DESIGN: "coding_agent",    # Design may involve prototyping
            PhaseType.IMPLEMENTATION: "coding_agent",
            PhaseType.TESTING: "test_agent",
            PhaseType.DOCUMENTATION: "coding_agent",  # Docs are code too
            PhaseType.DEPLOYMENT: "coding_agent",
            PhaseType.OPTIMIZATION: "coding_agent"
        }
        
        return mapping.get(phase_type, "coding_agent")
    
    def _create_phase_from_data(self, plan: ImplementationPlan, data: Dict[str, Any]) -> ImplementationPhase:
        """Create phase from LLM-generated data."""
        phase_type = PhaseType(data.get("type", "implementation"))
        
        return self.plan_manager.add_phase(
            plan=plan,
            name=data.get("name", "Phase"),
            phase_type=phase_type,
            description=data.get("description", ""),
            objectives=data.get("objectives", []),
            estimated_days=data.get("estimated_days", 1.0)
        )
    
    def _create_milestone_from_data(self, phase: ImplementationPhase, data: Dict[str, Any]) -> PlanMilestone:
        """Create milestone from LLM-generated data."""
        return self.plan_manager.add_milestone(
            phase=phase,
            title=data.get("title", "Milestone"),
            description=data.get("description", ""),
            deliverables=data.get("deliverables", []),
            success_criteria=data.get("success_criteria", [])
        )
    
    def _create_chunk_from_data(self, milestone: PlanMilestone, data: Dict[str, Any]) -> PlanChunk:
        """Create chunk from LLM-generated data."""
        chunk = self.plan_manager.add_chunk(
            milestone=milestone,
            title=data.get("title", "Context"),
            content=data.get("content", ""),
            chunk_type=data.get("type", "general"),
            priority=data.get("priority", 5)
        )
        
        # Add additional fields if present
        if "technologies" in data:
            chunk.technologies = data["technologies"]
        if "dependencies" in data:
            chunk.dependencies = data["dependencies"]
        if "relevant_files" in data:
            chunk.relevant_files = data["relevant_files"]
        if "test_requirements" in data:
            chunk.test_requirements = data["test_requirements"]
        if "acceptance_criteria" in data:
            chunk.acceptance_criteria = data["acceptance_criteria"]
        
        return chunk