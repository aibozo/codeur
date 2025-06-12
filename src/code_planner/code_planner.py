"""
Code Planner Agent - Main orchestrator.

Consumes Plans from the Request Planner and produces TaskBundles
containing detailed CodingTasks for the Coding Agents.
"""

import logging
from pathlib import Path
from typing import Optional
from ..proto_gen import messages_pb2
from .ast_analyzer import ASTAnalyzer
try:
    from .ast_analyzer_v2 import EnhancedASTAnalyzer
    ENHANCED_AST_AVAILABLE = True
except ImportError:
    ENHANCED_AST_AVAILABLE = False
from .task_generator import TaskGenerator
from ..git_integration import GitAdapter
from .rag_integration import CodePlannerRAGIntegration


logger = logging.getLogger(__name__)


class CodePlanner:
    """
    Main Code Planner agent that transforms Plans into CodingTasks.
    
    Responsibilities:
    - Consume Plans from message queue
    - Analyze code structure with AST
    - Generate detailed CodingTasks
    - Emit TaskBundles for Coding Agents
    """
    
    def __init__(self, repo_path: str, git_adapter: Optional[GitAdapter] = None, use_rag: bool = True):
        self.repo_path = Path(repo_path)
        self.git_adapter = git_adapter or GitAdapter(repo_path)
        
        # Use enhanced analyzer if available
        if ENHANCED_AST_AVAILABLE:
            self.ast_analyzer = EnhancedASTAnalyzer(repo_path)
            logger.info("Using enhanced AST analyzer with tree-sitter support")
        else:
            self.ast_analyzer = ASTAnalyzer(repo_path)
            logger.info("Using basic AST analyzer")
        
        # Initialize RAG integration
        self.rag_integration = None
        if use_rag:
            try:
                self.rag_integration = CodePlannerRAGIntegration(repo_path)
                if self.rag_integration.enabled:
                    logger.info("RAG integration enabled for Code Planner")
                    # Index repository if needed
                    self.rag_integration.index_repository()
                else:
                    logger.warning("RAG integration initialized but not enabled")
            except Exception as e:
                logger.error(f"Failed to initialize RAG integration: {e}")
                self.rag_integration = None
        
        # Initialize task generator with RAG integration
        self.task_generator = TaskGenerator(self.ast_analyzer, rag_service=self.rag_integration)
        
        logger.info(f"Initialized Code Planner for repo: {repo_path}")
    
    def process_plan(self, plan: messages_pb2.Plan) -> messages_pb2.TaskBundle:
        """
        Process a Plan and generate a TaskBundle.
        
        Args:
            plan: Plan from Request Planner
            
        Returns:
            TaskBundle containing CodingTasks
        """
        logger.info(f"Processing plan: {plan.id} with {len(plan.steps)} steps")
        
        # Get current commit SHA
        base_commit = self.git_adapter.get_current_commit()
        
        # Analyze affected files
        self._analyze_affected_files(plan)
        
        # Generate tasks
        task_bundle = self.task_generator.generate_tasks(plan, base_commit)
        
        logger.info(
            f"Generated TaskBundle {task_bundle.id} with {len(task_bundle.tasks)} tasks"
        )
        
        # Log task summary
        complexity_names = {
            messages_pb2.COMPLEXITY_UNKNOWN: "UNKNOWN",
            messages_pb2.COMPLEXITY_TRIVIAL: "TRIVIAL",
            messages_pb2.COMPLEXITY_MODERATE: "MODERATE",
            messages_pb2.COMPLEXITY_COMPLEX: "COMPLEX",
        }
        for task in task_bundle.tasks:
            complexity_name = complexity_names.get(task.complexity_label, "UNKNOWN")
            logger.debug(
                f"  Task {task.id}: {task.goal} "
                f"({len(task.paths)} files, {complexity_name})"
            )
        
        return task_bundle
    
    def _analyze_affected_files(self, plan: messages_pb2.Plan):
        """Pre-analyze all affected files for caching."""
        all_files = set(plan.affected_paths)
        
        # Extract files from step hints
        for step in plan.steps:
            for hint in step.hints:
                # Simple file extraction from hints
                words = hint.split()
                for word in words:
                    if '/' in word and '.' in word:
                        file_path = word.strip('.,;:()"\'')
                        if self._is_valid_file(file_path):
                            all_files.add(file_path)
        
        # Analyze all files
        logger.debug(f"Pre-analyzing {len(all_files)} files")
        for file_path in all_files:
            self.ast_analyzer.analyze_file(file_path)
        
        # Build call graph
        if all_files:
            call_graph = self.ast_analyzer.build_call_graph(list(all_files))
            logger.debug(f"Built call graph with {len(call_graph)} nodes")
    
    def _is_valid_file(self, path: str) -> bool:
        """Check if path is a valid source file."""
        # Skip common non-source patterns
        invalid_patterns = [
            'http://', 'https://', 
            '.git/', '__pycache__/',
            'node_modules/', '.env',
            '.log', '.tmp'
        ]
        
        if any(pattern in path for pattern in invalid_patterns):
            return False
        
        # Check if file exists
        full_path = self.repo_path / path
        return full_path.exists() and full_path.is_file()
    
    def validate_task_bundle(self, bundle: messages_pb2.TaskBundle) -> bool:
        """Validate that a TaskBundle is well-formed."""
        if not bundle.id or not bundle.parent_plan_id:
            logger.error("TaskBundle missing required IDs")
            return False
        
        if not bundle.tasks:
            logger.error("TaskBundle has no tasks")
            return False
        
        # Validate each task
        for task in bundle.tasks:
            if not task.id or not task.goal:
                logger.error(f"Task {task.id} missing required fields")
                return False
            
            if not task.paths:
                logger.warning(f"Task {task.id} has no file paths")
            
            # Check dependency references
            for dep_id in task.depends_on:
                if not any(t.id == dep_id for t in bundle.tasks):
                    logger.error(f"Task {task.id} has invalid dependency: {dep_id}")
                    return False
        
        return True
    
    def get_metrics(self) -> dict:
        """Get Code Planner metrics."""
        metrics = {
            "cache_size": len(self.ast_analyzer._symbol_cache),
            "call_graph_nodes": len(self.ast_analyzer._call_graph),
        }
        
        # Add analyzer info if available
        if ENHANCED_AST_AVAILABLE and hasattr(self.ast_analyzer, 'get_analyzer_info'):
            metrics["analyzer_info"] = self.ast_analyzer.get_analyzer_info()
        
        return metrics