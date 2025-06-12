"""
Main Coding Agent implementation.

Orchestrates the process of:
1. Receiving CodingTasks
2. Gathering context
3. Generating patches
4. Validating changes
5. Creating commits
6. Emitting results
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import uuid
import json

from ..proto_gen import messages_pb2
from .models import CommitStatus, CommitResult, CodeContext
from .context_gatherer import ContextGatherer
from .patch_generator import PatchGenerator
from .file_rewriter import FileRewriter
from .validator import PatchValidator
from .git_operations import GitOperations

logger = logging.getLogger(__name__)


class CodingAgent:
    """
    Main Coding Agent that converts CodingTasks into Git commits.
    
    Follows the workflow:
    receive task -> gather context -> draft patch -> validate -> commit
    """
    
    def __init__(
        self,
        repo_path: str,
        rag_client=None,
        llm_client=None,
        max_retries: int = 2
    ):
        """
        Initialize the Coding Agent.
        
        Args:
            repo_path: Path to the repository
            rag_client: Optional RAG client for context
            llm_client: Optional LLM client for generation
            max_retries: Maximum patch generation retries
        """
        self.repo_path = Path(repo_path)
        self.max_retries = max_retries
        self.llm_client = llm_client
        self.rag_client = rag_client
        
        # Initialize components
        self.context_gatherer = ContextGatherer(repo_path, rag_client)
        self.patch_generator = PatchGenerator(llm_client)
        self.file_rewriter = FileRewriter(llm_client, repo_path)
        self.validator = PatchValidator(repo_path)
        self.git_ops = GitOperations(repo_path)
        
        logger.info(f"Initialized Coding Agent for {repo_path}")
    
    def process_task(self, task: messages_pb2.CodingTask) -> CommitResult:
        """
        Process a coding task and produce a commit.
        
        Args:
            task: The CodingTask to process
            
        Returns:
            CommitResult with the outcome
        """
        logger.info(f"Processing task {task.id}: {task.goal}")
        
        result = CommitResult(
            task_id=task.id,
            status=CommitStatus.HARD_FAIL  # Pessimistic default
        )
        
        try:
            # 1. Create feature branch
            branch_name = self._create_branch_name(task)
            if not self._setup_branch(branch_name, task.base_commit_sha):
                result.add_note("Failed to create feature branch")
                return result
            
            result.branch_name = branch_name
            
            # 2. Gather context
            logger.info("Gathering context...")
            context = self.context_gatherer.gather_context(task)
            result.add_note(f"Gathered context: {context.token_count} tokens")
            
            # 2.5 Let agent refine context with tools
            logger.info("Refining context with tools...")
            context = self._refine_context_with_tools(task, context)
            result.add_note(f"Refined context: {context.token_count} tokens")
            
            # 3. Generate and validate patch (with retries)
            patch_content = None
            validation_result = None
            use_file_rewriter = False
            
            for attempt in range(self.max_retries + 1):
                logger.info(f"Patch generation attempt {attempt + 1}")
                
                if use_file_rewriter and task.paths:
                    # Use file rewriter for specific files
                    logger.info("Using file rewriter approach...")
                    rewrite_success = False
                    
                    for file_path in task.paths:
                        rewrite_result = self.file_rewriter.rewrite_file(
                            context,
                            file_path,
                            temperature=0.1 + (attempt * 0.1)
                        )
                        
                        result.llm_tokens_used += rewrite_result.tokens_used
                        
                        if rewrite_result.success:
                            patch_content = rewrite_result.patch_content
                            rewrite_success = True
                            result.add_note(f"Rewrote file: {file_path}")
                        else:
                            result.add_note(f"Failed to rewrite {file_path}: {rewrite_result.error_message}")
                    
                    if not rewrite_success:
                        continue
                        
                    # File rewriter succeeded, skip to validation
                    patch_result = rewrite_result
                    
                else:
                    # Traditional patch generation
                    if attempt == 0:
                        # First attempt - generate new patch
                        patch_result = self.patch_generator.generate_patch(context)
                    else:
                        # Retry - refine based on errors
                        if patch_content and validation_result and validation_result.errors:
                            error_msg = "\n".join(validation_result.errors[:5])
                            patch_result = self.patch_generator.refine_patch(
                                patch_content,
                                error_msg,
                                context
                            )
                        else:
                            # No specific errors, try again with higher temperature
                            patch_result = self.patch_generator.generate_patch(
                                context,
                                temperature=0.3 + (attempt * 0.1)
                            )
                    
                    result.llm_tokens_used += patch_result.tokens_used
                    
                    if not patch_result.success:
                        result.add_note(f"Patch generation failed: {patch_result.error_message}")
                        # Switch to file rewriter after first failure
                        if attempt >= 0 and task.paths:
                            use_file_rewriter = True
                            result.add_note("Switching to file rewriter approach...")
                        continue
                    
                    patch_content = patch_result.patch_content
                
                # 4. Apply patch (skip if using file rewriter - changes already made)
                if use_file_rewriter:
                    # File rewriter already modified the files
                    applied = True
                else:
                    logger.info("Applying patch...")
                    applied, error = self.git_ops.apply_patch(patch_content)
                    
                    if not applied:
                        # Analyze the error and provide feedback
                        feedback = self._analyze_patch_error(error, patch_content)
                        result.add_note(f"Failed to apply patch: {feedback}")
                        
                        # Suggest reading the file for better context
                        if "line" in error.lower() or "corrupt" in error.lower():
                            self._suggest_file_reading(context, task.paths, feedback)
                        
                        # Reset for next attempt
                        self.git_ops.reset_changes(hard=True)
                        
                        # Switch to file rewriter if patches keep failing
                        if "corrupt patch" in error.lower() and task.paths:
                            use_file_rewriter = True
                            result.add_note("Switching to file rewriter due to patch format issues...")
                        continue
                
                # 5. Validate changes
                logger.info("Validating changes...")
                validation_result = self.validator.validate_patch(
                    patch_result.files_modified,
                    run_tests=True,
                    test_pattern="fast"
                )
                
                if validation_result.is_valid:
                    # Success!
                    result.add_note("Validation passed")
                    break
                else:
                    # Validation failed
                    result.add_note(f"Validation failed on attempt {attempt + 1}")
                    for error in validation_result.errors[:5]:
                        result.add_note(f"  - {error}")
                    logger.info(f"All validation errors: {validation_result.errors}")
                    
                    # Reset for next attempt
                    self.git_ops.reset_changes(hard=True)
                    
                    if attempt < self.max_retries:
                        result.retries = attempt + 1
            
            # Check if we succeeded
            if patch_content and validation_result and validation_result.is_valid:
                # 6. Commit changes
                logger.info("Creating commit...")
                commit_message = self._generate_commit_message(task)
                
                # Stage changes
                if not self.git_ops.stage_changes():
                    result.add_note("Failed to stage changes")
                    result.status = CommitStatus.HARD_FAIL
                    return result
                
                # Create commit
                commit_sha = self.git_ops.commit(
                    message=commit_message,
                    author="Coding Agent <agent@ai-system.local>"
                )
                
                if commit_sha:
                    result.commit_sha = commit_sha
                    result.status = CommitStatus.SUCCESS
                    result.add_note(f"Successfully created commit {commit_sha[:8]}")
                    
                    # Push branch (optional, could be done later)
                    # self.git_ops.push_branch(branch_name)
                else:
                    result.add_note("Failed to create commit")
                    result.status = CommitStatus.HARD_FAIL
            else:
                # Failed after all retries
                if result.retries > 0:
                    result.status = CommitStatus.SOFT_FAIL  # Retryable
                    result.add_note(f"Failed after {result.retries} retries")
                else:
                    result.status = CommitStatus.HARD_FAIL
                    result.add_note("Failed to generate valid patch")
            
        except Exception as e:
            logger.error(f"Error processing task: {e}", exc_info=True)
            result.status = CommitStatus.HARD_FAIL
            result.add_note(f"Exception: {str(e)}")
        
        finally:
            # Always try to go back to original branch
            try:
                self.git_ops.checkout_branch("main")
            except:
                pass
        
        logger.info(f"Task {task.id} completed with status: {result.status.value}")
        return result
    
    def _create_branch_name(self, task: messages_pb2.CodingTask) -> str:
        """Create a branch name for the task."""
        # Sanitize goal for branch name
        goal_slug = task.goal.lower()
        goal_slug = re.sub(r'[^a-z0-9-]', '-', goal_slug)
        goal_slug = re.sub(r'-+', '-', goal_slug)
        goal_slug = goal_slug.strip('-')[:30]
        
        # Add task ID suffix
        task_suffix = task.id.split('-')[-1][:8]
        
        return f"coding/{goal_slug}-{task_suffix}"
    
    def _setup_branch(self, branch_name: str, base_commit: Optional[str]) -> bool:
        """Setup the working branch."""
        try:
            # First, ensure we're on main/master
            try:
                self.git_ops.checkout_branch("main")
            except:
                try:
                    self.git_ops.checkout_branch("master")
                except:
                    logger.warning("Could not checkout main/master branch")
            
            # Create new branch
            return self.git_ops.create_branch(branch_name, base_commit)
            
        except Exception as e:
            logger.error(f"Failed to setup branch: {e}")
            return False
    
    def _generate_commit_message(self, task: messages_pb2.CodingTask) -> str:
        """Generate a commit message for the task."""
        lines = []
        
        # Main commit message
        lines.append(task.goal)
        lines.append("")
        
        # Body with details
        lines.append(f"Task ID: {task.id}")
        lines.append(f"Plan ID: {task.parent_plan_id}")
        
        if task.paths:
            lines.append("")
            lines.append("Modified files:")
            for path in task.paths:
                lines.append(f"- {path}")
        
        lines.append("")
        lines.append("Generated by Coding Agent")
        
        return "\n".join(lines)
    
    def _refine_context_with_tools(self, task: messages_pb2.CodingTask, context: CodeContext) -> CodeContext:
        """Let the agent refine context using tools."""
        
        if not self.llm_client:
            return context
        
        # Build a prompt asking what additional context is needed
        refinement_prompt = f"""
You are about to implement this task: {task.goal}

Initial context provided:
- {len(context.blob_contents)} code chunks from search
- {len(context.file_snippets)} file snippets
- Target files: {', '.join(task.paths)}

You have access to these tools:
1. read_file(path, start_line=None, end_line=None) - Read a file or specific lines
2. search_code(query) - Search for code patterns
3. find_symbol(symbol_name) - Find a function/class definition

What additional context do you need? Respond with a JSON list of tool calls.

Example:
[
  {{"tool": "read_file", "args": {{"path": "src/api.py", "start_line": 10, "end_line": 30}}}},
  {{"tool": "search_code", "args": {{"query": "def get_user"}}}}
]
"""
        
        try:
            # Ask LLM what context it needs
            response = self.llm_client.generate_with_json(
                prompt=refinement_prompt,
                system_prompt="You are a coding assistant. Always read files before making changes to verify content and line numbers.",
                max_tokens=1000,
                temperature=0.1
            )
            
            if isinstance(response, dict):
                response = [response]

            if isinstance(response, list):
                # Execute the requested tool calls
                for tool_call in response[:5]:  # Limit to 5 calls
                    self._execute_tool_call(tool_call, context)
            
        except Exception as e:
            logger.warning(f"Context refinement failed: {e}")
        
        return context
    
    def _execute_tool_call(self, tool_call: Dict[str, Any], context: CodeContext):
        """Execute a tool call and add results to context."""
        tool = tool_call.get("tool")
        args = tool_call.get("args", {})
        
        try:
            if tool == "read_file":
                content = self._tool_read_file(**args)
                if content:
                    context.add_blob(f"tool_read:{args.get('path')}", content)
            
            elif tool == "search_code":
                results = self._tool_search_code(**args)
                for i, result in enumerate(results[:3]):
                    context.add_blob(f"tool_search_{i}", result)
            
            elif tool == "find_symbol":
                result = self._tool_find_symbol(**args)
                if result:
                    context.add_blob(f"tool_symbol:{args.get('symbol_name')}", result)
                    
        except Exception as e:
            logger.warning(f"Tool call failed: {tool} - {e}")
    
    def _tool_read_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Optional[str]:
        """Read a file with line numbers."""
        file_path = self.repo_path / path
        
        if not file_path.exists():
            return None
        
        try:
            content = file_path.read_text()
            lines = content.splitlines()
            
            # Apply line range if specified
            if start_line is not None:
                start_idx = max(0, start_line - 1)
                end_idx = end_line if end_line else len(lines)
                lines = lines[start_idx:end_idx]
                line_offset = start_line
            else:
                line_offset = 1
            
            # Add line numbers
            numbered_lines = []
            for i, line in enumerate(lines):
                numbered_lines.append(f"{line_offset + i:4d}: {line}")
            
            return '\n'.join(numbered_lines)
            
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return None
    
    def _tool_search_code(self, query: str) -> List[str]:
        """Search for code patterns."""
        results = []
        
        if self.rag_client:
            try:
                search_results = self.rag_client.search(query, k=5)
                
                for result in search_results:
                    # Format result with line numbers
                    formatted = self._format_search_result(result)
                    results.append(formatted)
                    
            except Exception as e:
                logger.error(f"Search failed: {e}")
        
        return results
    
    def _tool_find_symbol(self, symbol_name: str) -> Optional[str]:
        """Find a symbol definition."""
        if self.rag_client:
            try:
                results = self.rag_client.find_symbol(symbol_name)
                if results:
                    return self._format_search_result(results[0])
            except Exception as e:
                logger.error(f"Symbol search failed: {e}")
        
        return None
    
    def _format_search_result(self, result: Dict[str, Any]) -> str:
        """Format a search result with line numbers."""
        file_path = result.get("file_path", "unknown")
        start_line = result.get("start_line", 0)
        end_line = result.get("end_line", 0)
        content = result.get("content", "")
        
        # Add line numbers
        lines = content.splitlines()
        numbered_lines = []
        
        for i, line in enumerate(lines):
            line_num = start_line + i
            numbered_lines.append(f"{line_num:4d}: {line}")
        
        header = f"=== {file_path}:{start_line}-{end_line} ==="
        return f"{header}\n" + '\n'.join(numbered_lines)
    
    def _analyze_patch_error(self, error: str, patch_content: str) -> str:
        """Analyze patch error and provide specific feedback."""
        
        if "corrupt patch" in error.lower():
            # Check for common issues
            lines = patch_content.splitlines()
            
            # Check @@ markers
            hunk_pattern = r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@'
            hunks = [l for l in lines if l.startswith('@@')]
            
            if not hunks:
                return "Missing @@ hunk markers. Read the actual file to see correct line numbers."
            
            for hunk in hunks:
                if not re.match(hunk_pattern, hunk):
                    return f"Malformed hunk header: {hunk}. Should be '@@ -start,count +start,count @@'"
            
            return "Patch format is corrupt. Read the target file to verify line numbers and content."
        
        elif "does not apply" in error.lower():
            return "Patch doesn't match file content. Read the current file content to see what's actually there."
        
        elif "no such file" in error.lower():
            return "File not found. Check the correct path."
        
        return f"Patch error: {error}"
    
    def _suggest_file_reading(self, context: CodeContext, file_paths: List[str], error_feedback: str):
        """Suggest reading files when patches fail."""
        
        suggestion = f"\nPatch application failed: {error_feedback}\n"
        suggestion += "Suggested actions:\n"
        
        for path in file_paths[:2]:
            suggestion += f"- Read {path} to see current content and line numbers\n"
        
        context.error_patterns.append(suggestion)


# Import guard for re
import re