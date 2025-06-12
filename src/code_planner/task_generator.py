"""
Task Generator - Creates CodingTasks from Plans.

Responsible for:
- Breaking down plan steps into concrete tasks
- Analyzing dependencies between tasks
- Generating skeleton patches as hints
- Assigning complexity scores
- Pre-fetching RAG context
"""

import uuid
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from ..proto_gen import messages_pb2
from .ast_analyzer import ASTAnalyzer, FileAnalysis


@dataclass
class TaskDependency:
    """Represents a dependency between tasks."""
    task_id: str
    depends_on: str
    reason: str


@dataclass
class TaskContext:
    """Additional context for a coding task."""
    affected_symbols: List[str]
    related_files: List[str]
    test_files: List[str]
    complexity_factors: Dict[str, int]


class TaskGenerator:
    """Generates CodingTasks from Plans."""
    
    def __init__(self, ast_analyzer: ASTAnalyzer, rag_service=None):
        self.ast_analyzer = ast_analyzer
        self.rag_service = rag_service  # Optional RAG integration
    
    def generate_tasks(self, plan: messages_pb2.Plan, base_commit: str) -> messages_pb2.TaskBundle:
        """Generate a TaskBundle from a Plan."""
        tasks = []
        task_dependencies = self._analyze_dependencies(plan)
        
        for i, step in enumerate(plan.steps):
            task = self._generate_task_from_step(
                step=step,
                step_number=i,
                plan=plan,
                base_commit=base_commit,
                dependencies=task_dependencies
            )
            tasks.append(task)
        
        # Create TaskBundle
        bundle = messages_pb2.TaskBundle()
        bundle.id = f"bundle-{uuid.uuid4()}"
        bundle.parent_plan_id = plan.id
        bundle.tasks.extend(tasks)
        bundle.execution_strategy = self._determine_execution_strategy(tasks, task_dependencies)
        
        return bundle
    
    def _generate_task_from_step(
        self,
        step: messages_pb2.Step,
        step_number: int,
        plan: messages_pb2.Plan,
        base_commit: str,
        dependencies: Dict[int, Set[int]]
    ) -> messages_pb2.CodingTask:
        """Generate a single CodingTask from a Step."""
        task = messages_pb2.CodingTask()
        task.id = f"task-{uuid.uuid4()}"
        task.parent_plan_id = plan.id
        task.step_number = step_number
        task.goal = step.goal
        
        # Analyze which files are affected
        affected_files = self._identify_affected_files(step, plan)
        task.paths.extend(affected_files)
        
        # Analyze code structure
        context = self._analyze_task_context(affected_files, step)
        
        # Pre-fetch RAG chunks if available
        if self.rag_service:
            blob_ids = self._fetch_rag_context(step, context)
            task.blob_ids.extend(blob_ids)
        
        # Generate skeleton patches as hints
        skeleton_patches = self._generate_skeleton_patches(step, context, affected_files)
        task.skeleton_patch.extend(skeleton_patches)
        
        # Set dependencies
        for dep_idx in dependencies.get(step_number, []):
            dep_task_id = f"task-{plan.id}-{dep_idx}"  # Placeholder - would be actual IDs
            task.depends_on.append(dep_task_id)
        
        # Calculate complexity
        task.complexity_label = self._calculate_task_complexity(step, context)
        task.estimated_tokens = self._estimate_tokens(task)
        
        task.base_commit_sha = base_commit
        
        # Add metadata
        # Map step kind enum to string
        step_kind_map = {
            messages_pb2.STEP_KIND_UNKNOWN: "UNKNOWN",
            messages_pb2.STEP_KIND_ADD: "ADD",
            messages_pb2.STEP_KIND_EDIT: "EDIT",
            messages_pb2.STEP_KIND_REFACTOR: "REFACTOR",
            messages_pb2.STEP_KIND_REMOVE: "REMOVE",
            messages_pb2.STEP_KIND_REVIEW: "REVIEW",
            messages_pb2.STEP_KIND_TEST: "TEST",
        }
        task.metadata["step_kind"] = step_kind_map.get(step.kind, "UNKNOWN")
        task.metadata["affected_symbols"] = ",".join(context.affected_symbols)
        
        return task
    
    def _fetch_rag_context(self, step: messages_pb2.Step, context: TaskContext) -> List[str]:
        """Fetch relevant RAG context blobs for the step."""
        if not self.rag_service:
            return []
        
        try:
            # If rag_service is actually a CodePlannerRAGIntegration instance
            if hasattr(self.rag_service, 'prefetch_blobs_for_step'):
                return self.rag_service.prefetch_blobs_for_step(
                    step=step,
                    affected_files=context.related_files,
                    k=10
                )
            # Otherwise try to use it as a basic RAG client
            elif hasattr(self.rag_service, 'search'):
                # Build query from step
                query = f"{step.goal} {' '.join(step.hints[:2])}"
                results = self.rag_service.search(query, k=10)
                
                # Extract blob IDs
                blob_ids = []
                for result in results:
                    if isinstance(result, dict) and 'id' in result:
                        blob_ids.append(result['id'])
                return blob_ids
            else:
                return []
        except Exception as e:
            # Don't fail task generation if RAG fails
            return []
    
    def _identify_affected_files(self, step: messages_pb2.Step, plan: messages_pb2.Plan) -> List[str]:
        """Identify which files are affected by a step."""
        affected = []
        
        # Check step hints for file references
        for hint in step.hints:
            # Simple heuristic: look for file paths in hints
            words = hint.split()
            for word in words:
                if '/' in word and '.' in word:
                    # Might be a file path
                    affected.append(word.strip('.,;:'))
        
        # Check plan's affected paths
        goal_lower = step.goal.lower()
        for path in plan.affected_paths:
            # Match files mentioned in goal
            if any(part in goal_lower for part in path.split('/')):
                affected.append(path)
        
        # Deduplicate
        return list(set(affected))
    
    def _analyze_task_context(self, files: List[str], step: messages_pb2.Step) -> TaskContext:
        """Analyze code context for the task."""
        affected_symbols = []
        related_files = set()
        test_files = []
        complexity_factors = {}
        
        for file_path in files:
            analysis = self.ast_analyzer.analyze_file(file_path)
            if not analysis:
                continue
            
            # Find symbols mentioned in step goal
            goal_lower = step.goal.lower()
            for symbol in analysis.symbols:
                if symbol.name.lower() in goal_lower:
                    affected_symbols.append(f"{file_path}:{symbol.name}")
                    
                    # Add files that use this symbol
                    for other_path, other_analysis in self.ast_analyzer._symbol_cache.items():
                        for other_symbol in other_analysis.symbols:
                            if symbol.name in other_symbol.calls:
                                related_files.add(other_analysis.path)
            
            # Find test files
            if 'test' in file_path.lower():
                test_files.append(file_path)
            
            # Track complexity
            complexity_factors[file_path] = analysis.complexity
        
        # Find test files for affected code
        for file_path in files:
            test_variations = [
                f"test_{file_path}",
                file_path.replace('src/', 'tests/'),
                file_path.replace('.py', '_test.py'),
                file_path.replace('.js', '.test.js'),
            ]
            for test_path in test_variations:
                if self.ast_analyzer.analyze_file(test_path):
                    test_files.append(test_path)
        
        return TaskContext(
            affected_symbols=affected_symbols,
            related_files=list(related_files),
            test_files=list(set(test_files)),
            complexity_factors=complexity_factors
        )
    
    def _generate_skeleton_patches(
        self,
        step: messages_pb2.Step,
        context: TaskContext,
        files: List[str]
    ) -> List[str]:
        """Generate skeleton patches as hints for the Coding Agent."""
        patches = []
        
        # For each affected file, generate a simple patch template
        for file_path in files[:3]:  # Limit to first 3 files
            analysis = self.ast_analyzer.analyze_file(file_path)
            if not analysis:
                continue
            
            # Try to use RAG-enhanced skeleton generation first
            enhanced_patch = None
            if self.rag_service and hasattr(self.rag_service, 'enhance_skeleton_patch'):
                # Find target symbol
                target_symbol = None
                for symbol in analysis.symbols:
                    if symbol.name.lower() in step.goal.lower():
                        target_symbol = symbol.name
                        break
                
                if target_symbol:
                    enhanced_patch = self.rag_service.enhance_skeleton_patch(
                        file_path=file_path,
                        step=step,
                        target_symbol=target_symbol
                    )
            
            # If we got an enhanced patch, use it
            if enhanced_patch:
                patches.append(enhanced_patch)
            else:
                # Fall back to basic skeleton generation
                if step.kind == messages_pb2.STEP_KIND_REFACTOR:
                    patch = self._generate_refactor_skeleton(file_path, step, analysis)
                elif step.kind == messages_pb2.STEP_KIND_TEST:
                    patch = self._generate_test_skeleton(file_path, step, analysis)
                else:
                    patch = self._generate_generic_skeleton(file_path, step, analysis)
                
                if patch:
                    patches.append(patch)
        
        return patches
    
    def _generate_refactor_skeleton(
        self,
        file_path: str,
        step: messages_pb2.Step,
        analysis: FileAnalysis
    ) -> Optional[str]:
        """Generate skeleton for refactoring."""
        # Find the main symbol to refactor
        target_symbol = None
        for symbol in analysis.symbols:
            if symbol.name.lower() in step.goal.lower():
                target_symbol = symbol
                break
        
        if not target_symbol:
            return None
        
        # Generate a simple patch hint
        patch = f"""--- a/{file_path}
+++ b/{file_path}
@@ -{target_symbol.line_start},{target_symbol.line_end} @@
-# Original {target_symbol.name} implementation
+# TODO: Refactored {target_symbol.name} - {step.goal}
+# Consider: {', '.join(step.hints[:2])}"""
        
        return patch
    
    def _generate_test_skeleton(
        self,
        file_path: str,
        step: messages_pb2.Step,
        analysis: FileAnalysis
    ) -> Optional[str]:
        """Generate skeleton for test creation."""
        # Simple test template
        patch = f"""--- /dev/null
+++ b/test_{file_path}
@@ -0,0 +1,10 @@
+# Test for: {step.goal}
+def test_TODO():
+    # Arrange
+    
+    # Act
+    
+    # Assert
+    pass"""
        
        return patch
    
    def _generate_generic_skeleton(
        self,
        file_path: str,
        step: messages_pb2.Step,
        analysis: FileAnalysis
    ) -> Optional[str]:
        """Generate generic skeleton patch."""
        patch = f"""--- a/{file_path}
+++ b/{file_path}
@@ -1,1 +1,2 @@
+# TODO: {step.goal}"""
        
        return patch
    
    def _fetch_rag_context(self, step: messages_pb2.Step, context: TaskContext) -> List[str]:
        """Fetch relevant code chunks from RAG service."""
        if not self.rag_service:
            return []
        
        # This would query the RAG service
        # For now, return empty list
        return []
    
    def _analyze_dependencies(self, plan: messages_pb2.Plan) -> Dict[int, Set[int]]:
        """Analyze dependencies between steps."""
        dependencies = {}
        
        # Simple heuristic: steps that modify same files depend on earlier steps
        file_steps = {}  # file -> list of step indices
        
        for i, step in enumerate(plan.steps):
            # Extract files from step
            step_files = set()
            for hint in step.hints:
                words = hint.split()
                for word in words:
                    if '/' in word and '.' in word:
                        step_files.add(word.strip('.,;:'))
            
            # Check dependencies
            step_deps = set()
            for file in step_files:
                if file in file_steps:
                    # Depend on all previous steps that touched this file
                    step_deps.update(file_steps[file])
                file_steps.setdefault(file, []).append(i)
            
            if step_deps:
                dependencies[i] = step_deps
        
        return dependencies
    
    def _determine_execution_strategy(
        self,
        tasks: List[messages_pb2.CodingTask],
        dependencies: Dict[int, Set[int]]
    ) -> str:
        """Determine how tasks should be executed."""
        # If no dependencies, can run in parallel
        if not dependencies:
            return "parallel"
        
        # If fully sequential dependencies, run sequentially
        if all(i in dependencies and dependencies[i] == {i-1} for i in range(1, len(tasks))):
            return "sequential"
        
        # Otherwise, use topological ordering
        return "topological"
    
    def _calculate_task_complexity(
        self,
        step: messages_pb2.Step,
        context: TaskContext
    ) -> messages_pb2.ComplexityLevel:
        """Calculate complexity level for a task."""
        # Sum complexity factors
        total_complexity = sum(context.complexity_factors.values())
        
        # Factor in number of files and symbols
        file_count = len(context.complexity_factors)
        symbol_count = len(context.affected_symbols)
        
        # Simple scoring
        score = total_complexity + (file_count * 5) + (symbol_count * 3)
        
        if score < 10:
            return messages_pb2.COMPLEXITY_TRIVIAL
        elif score < 50:
            return messages_pb2.COMPLEXITY_MODERATE
        else:
            return messages_pb2.COMPLEXITY_COMPLEX
    
    def _estimate_tokens(self, task: messages_pb2.CodingTask) -> int:
        """Estimate tokens needed for the task."""
        # Simple estimation based on complexity and file count
        base_tokens = {
            messages_pb2.COMPLEXITY_TRIVIAL: 500,
            messages_pb2.COMPLEXITY_MODERATE: 2000,
            messages_pb2.COMPLEXITY_COMPLEX: 4000,
        }
        
        tokens = base_tokens.get(task.complexity_label, 2000)
        tokens += len(task.paths) * 500  # Extra for each file
        tokens += len(task.skeleton_patch) * 200  # Extra for patches
        
        return tokens