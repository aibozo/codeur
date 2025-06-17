"""
Patch generator using LLM for the Coding Agent.

Responsible for:
- Constructing prompts from context
- Calling LLM to generate patches
- Parsing and validating LLM responses
- Handling retries and refinements
"""

import logging
import re
from typing import Optional, Dict, Any, List
import json

from .models import CodeContext, PatchResult

logger = logging.getLogger(__name__)


class PatchGenerator:
    """
    Generates code patches using LLM.
    
    Uses the gathered context to construct prompts and
    generate unified diff patches.
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize patch generator.
        
        Args:
            llm_client: LLM client (will try to create one if None)
        """
        self.llm_client = llm_client
        
        if not self.llm_client:
            try:
                from src.llm import LLMClient
                self.llm_client = LLMClient(agent_name="coding")
                logger.info(f"Initialized LLM client for patch generation: {self.llm_client.model_card.display_name}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM client: {e}")
                self.llm_client = None
    
    def generate_patch(
        self,
        context: CodeContext,
        temperature: float = 0.2
    ) -> PatchResult:
        """
        Generate a patch from the given context.
        
        Args:
            context: The code context
            temperature: LLM temperature (lower = more focused)
            
        Returns:
            PatchResult with the generated patch
        """
        if not self.llm_client:
            return PatchResult(
                success=False,
                error_message="LLM client not available"
            )
        
        try:
            # Build the prompt
            prompt = self._build_prompt(context)
            
            # Call LLM
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=temperature,
                system_prompt=self._get_system_prompt()
            )
            
            # Parse the response
            patch_content = self._extract_patch(response)
            
            if patch_content:
                # Extract modified files
                files_modified = self._extract_modified_files(patch_content)
                
                return PatchResult(
                    success=True,
                    patch_content=patch_content,
                    files_modified=files_modified,
                    tokens_used=len(prompt) // 4 + len(response) // 4  # TODO: Use tiktoken for accurate tokenization
                )
            else:
                return PatchResult(
                    success=False,
                    error_message="Failed to extract valid patch from LLM response",
                    tokens_used=len(prompt) // 4  # TODO: Use tiktoken for accurate tokenization
                )
                
        except Exception as e:
            logger.error(f"Error generating patch: {e}")
            return PatchResult(
                success=False,
                error_message=str(e)
            )
    
    def refine_patch(
        self,
        original_patch: str,
        error_message: str,
        context: CodeContext
    ) -> PatchResult:
        """
        Refine a patch based on validation errors.
        
        Args:
            original_patch: The original patch that failed
            error_message: The validation error message
            context: The code context
            
        Returns:
            PatchResult with refined patch
        """
        if not self.llm_client:
            return PatchResult(
                success=False,
                error_message="LLM client not available"
            )
        
        try:
            # Build refinement prompt
            prompt = self._build_refinement_prompt(
                original_patch,
                error_message,
                context
            )
            
            # Call LLM with lower temperature for more focused fix
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                system_prompt=self._get_refinement_system_prompt()
            )
            
            # Parse the response
            patch_content = self._extract_patch(response)
            
            if patch_content:
                files_modified = self._extract_modified_files(patch_content)
                
                return PatchResult(
                    success=True,
                    patch_content=patch_content,
                    files_modified=files_modified,
                    tokens_used=len(prompt) // 4 + len(response) // 4  # TODO: Use tiktoken for accurate tokenization
                )
            else:
                return PatchResult(
                    success=False,
                    error_message="Failed to extract refined patch",
                    tokens_used=len(prompt) // 4  # TODO: Use tiktoken for accurate tokenization
                )
                
        except Exception as e:
            logger.error(f"Error refining patch: {e}")
            return PatchResult(
                success=False,
                error_message=str(e)
            )
    
    def _build_prompt(self, context: CodeContext) -> str:
        """Build the prompt for patch generation."""
        prompt_parts = []
        
        # Task description
        prompt_parts.append(f"Generate a unified diff patch to: {context.task_goal}")
        prompt_parts.append("")
        
        # Context
        context_str = context.to_prompt_context()
        prompt_parts.append("Context:")
        prompt_parts.append(context_str)
        prompt_parts.append("")
        
        # Instructions
        prompt_parts.append("Instructions:")
        prompt_parts.append("1. Generate a valid unified diff patch (git format)")
        prompt_parts.append("2. Only modify the files mentioned in the context")
        prompt_parts.append("3. Ensure the changes achieve the stated goal")
        prompt_parts.append("4. Follow the coding style of the existing code")
        prompt_parts.append("5. Include proper error handling where appropriate")
        prompt_parts.append("6. The patch should apply cleanly with 'git apply'")
        prompt_parts.append("7. IMPORTANT: Line numbers are shown in the format 'NNNN: content'")
        prompt_parts.append("   Use these line numbers for the @@ markers in your patch")
        prompt_parts.append("")
        prompt_parts.append("Generate the patch:")
        
        return "\n".join(prompt_parts)
    
    def _build_refinement_prompt(
        self,
        original_patch: str,
        error_message: str,
        context: CodeContext
    ) -> str:
        """Build prompt for patch refinement."""
        prompt_parts = []
        
        prompt_parts.append(f"Fix the following patch that failed validation.")
        prompt_parts.append(f"Task goal: {context.task_goal}")
        prompt_parts.append("")
        
        prompt_parts.append("Original patch that failed:")
        prompt_parts.append("```diff")
        prompt_parts.append(original_patch)
        prompt_parts.append("```")
        prompt_parts.append("")
        
        prompt_parts.append("Validation error:")
        prompt_parts.append(error_message)
        prompt_parts.append("")
        
        # Add relevant context
        if context.file_snippets:
            prompt_parts.append("Relevant code context:")
            for file_path, content in list(context.file_snippets.items())[:2]:
                prompt_parts.append(f"\n--- {file_path} ---")
                prompt_parts.append(content[:300])
        
        prompt_parts.append("")
        prompt_parts.append("Generate a corrected patch that fixes the validation errors:")
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for patch generation."""
        return """You are an expert software engineer generating code patches.

CRITICAL GUIDELINES:
1. ALWAYS verify line numbers match the actual file content
2. If unsure, ask to read the file first
3. Include at least 3 lines of context before and after changes
4. Use exact line numbers from the provided context (format: 'NNNN: content')
5. Generate valid unified diff patches in git format

If the context seems incomplete or line numbers are unclear, say so rather than guessing."""
    
    def _get_refinement_system_prompt(self) -> str:
        """Get system prompt for patch refinement."""
        return """You are debugging and fixing code patches.
Analyze the validation error carefully and fix the specific issue.
Maintain the original intent while ensuring the code is valid.
Generate a corrected unified diff patch that will pass validation."""
    
    def _extract_patch(self, llm_response: str) -> Optional[str]:
        """Extract patch content from LLM response."""
        # Look for diff blocks (handles o3 model output)
        diff_pattern = r'```diff\n(.*?)```'
        matches = re.findall(diff_pattern, llm_response, re.DOTALL)
        
        if matches:
            # Don't strip - preserve exact content
            patch = matches[0].rstrip()  # Only remove trailing whitespace
            return self._fix_patch_context_lines(patch)
        
        # Try to find patch content without code blocks
        lines = llm_response.split('\n')
        patch_lines = []
        in_patch = False
        
        for line in lines:
            # Skip code block markers
            if line.strip() in ['```diff', '```']:
                continue
                
            if line.startswith(('---', '+++', '@@', 'diff --git')):
                in_patch = True
            
            if in_patch:
                # Critical: preserve the line exactly as is, including space prefixes
                # Only skip comment lines
                if line.startswith(('#', '//')):
                    continue
                patch_lines.append(line)
        
        if patch_lines:
            # Join and ensure trailing newline
            result = '\n'.join(patch_lines)
            if not result.endswith('\n'):
                result += '\n'
            return self._fix_patch_context_lines(result)
        
        return None
    
    def _fix_patch_context_lines(self, patch_content: str) -> str:
        """Fix patches that are missing space prefixes on context lines."""
        if not patch_content:
            return patch_content
        
        lines = patch_content.split('\n')
        fixed_lines = []
        in_hunk = False
        
        for line in lines:
            if line.startswith(('---', '+++', 'diff --git', 'index ')):
                # Header lines - keep as is
                fixed_lines.append(line)
                in_hunk = False
            elif line.startswith('@@'):
                # Hunk header - keep as is
                fixed_lines.append(line)
                in_hunk = True
            elif in_hunk:
                # Inside a hunk
                if line.startswith(('+', '-')):
                    # Add/remove lines - keep as is
                    fixed_lines.append(line)
                elif line == '':
                    # Empty line might be context
                    fixed_lines.append(' ')
                elif not line.startswith(' '):
                    # Context line missing space prefix
                    fixed_lines.append(' ' + line)
                else:
                    # Already has proper prefix
                    fixed_lines.append(line)
            else:
                # Outside hunk - keep as is
                fixed_lines.append(line)
        
        result = '\n'.join(fixed_lines)
        if not result.endswith('\n'):
            result += '\n'
        return result
    
    def _extract_modified_files(self, patch_content: str) -> List[str]:
        """Extract list of modified files from patch."""
        files = []
        
        # Look for +++ b/filename patterns
        file_pattern = r'\+\+\+ b/(.+?)(?:\s|$)'
        matches = re.findall(file_pattern, patch_content)
        files.extend(matches)
        
        # Also look for diff --git patterns
        git_pattern = r'diff --git a/(.+?) b/(.+?)(?:\s|$)'
        git_matches = re.findall(git_pattern, patch_content)
        for _, file_b in git_matches:
            if file_b not in files:
                files.append(file_b)
        
        return files