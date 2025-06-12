"""
Improved patch generator with better diff handling.
"""

import logging
import re
from typing import Optional, Dict, Any, List
import json

from .models import CodeContext, PatchResult

logger = logging.getLogger(__name__)


class ImprovedPatchGenerator:
    """
    Improved patch generator with better prompting for diffs.
    """
    
    def __init__(self, llm_client=None):
        """Initialize patch generator."""
        self.llm_client = llm_client
        
        if not self.llm_client:
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from llm import LLMClient
                self.llm_client = LLMClient()
                logger.info("Initialized LLM client for patch generation")
            except Exception as e:
                logger.error(f"Failed to initialize LLM client: {e}")
                self.llm_client = None
    
    def generate_patch(
        self,
        context: CodeContext,
        max_tokens: int = 2000,
        temperature: float = 0.1  # Lower temperature for more consistent formatting
    ) -> PatchResult:
        """Generate a patch from the given context."""
        if not self.llm_client:
            return PatchResult(
                success=False,
                error_message="LLM client not available"
            )
        
        try:
            # Build the improved prompt
            prompt = self._build_improved_prompt(context)
            
            # Call LLM with improved system prompt
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=self._get_improved_system_prompt()
            )
            
            # Extract and clean the patch
            patch_content = self._extract_and_clean_patch(response)
            
            if patch_content:
                # Validate patch format
                if self._validate_patch_format(patch_content):
                    files_modified = self._extract_modified_files(patch_content)
                    
                    return PatchResult(
                        success=True,
                        patch_content=patch_content,
                        files_modified=files_modified,
                        tokens_used=len(prompt) // 4 + max_tokens
                    )
                else:
                    # Try to fix common issues
                    fixed_patch = self._fix_common_patch_issues(patch_content)
                    if fixed_patch and self._validate_patch_format(fixed_patch):
                        files_modified = self._extract_modified_files(fixed_patch)
                        return PatchResult(
                            success=True,
                            patch_content=fixed_patch,
                            files_modified=files_modified,
                            tokens_used=len(prompt) // 4 + max_tokens
                        )
                    else:
                        return PatchResult(
                            success=False,
                            error_message="Generated patch has invalid format",
                            tokens_used=len(prompt) // 4 + max_tokens
                        )
            else:
                return PatchResult(
                    success=False,
                    error_message="Failed to extract valid patch from LLM response",
                    tokens_used=len(prompt) // 4 + max_tokens
                )
                
        except Exception as e:
            logger.error(f"Error generating patch: {e}")
            return PatchResult(
                success=False,
                error_message=str(e)
            )
    
    def _build_improved_prompt(self, context: CodeContext) -> str:
        """Build an improved prompt for patch generation."""
        prompt_parts = []
        
        # Clear task description
        prompt_parts.append(f"Task: {context.task_goal}")
        prompt_parts.append("")
        
        # Add file content for reference
        if context.file_snippets:
            prompt_parts.append("Current file content:")
            for file_path, content in list(context.file_snippets.items())[:1]:  # Focus on one file
                prompt_parts.append(f"File: {file_path}")
                prompt_parts.append("```python")
                prompt_parts.append(content)
                prompt_parts.append("```")
                prompt_parts.append("")
        
        # Very specific instructions
        prompt_parts.append("Generate a git unified diff patch that:")
        prompt_parts.append("1. Uses the exact format: --- a/path/to/file.py")
        prompt_parts.append("2. Has proper @@ -start,count +start,count @@ markers")
        prompt_parts.append("3. Includes context lines (unchanged lines) before and after changes")
        prompt_parts.append("4. Uses - for removed lines and + for added lines")
        prompt_parts.append("5. Has no trailing whitespace on any lines")
        prompt_parts.append("")
        
        # Example format
        prompt_parts.append("Example of correct format:")
        prompt_parts.append("```diff")
        prompt_parts.append("--- a/src/example.py")
        prompt_parts.append("+++ b/src/example.py")
        prompt_parts.append("@@ -10,4 +10,5 @@")
        prompt_parts.append(" def function():")
        prompt_parts.append("-    # old comment")
        prompt_parts.append("+    # new comment")
        prompt_parts.append("+    # additional line")
        prompt_parts.append("     return value")
        prompt_parts.append("```")
        prompt_parts.append("")
        
        prompt_parts.append("Now generate the patch:")
        
        return "\n".join(prompt_parts)
    
    def _get_improved_system_prompt(self) -> str:
        """Get improved system prompt for patch generation."""
        return """You are a git diff expert. Generate ONLY valid unified diff patches.

Rules:
1. Output MUST be a valid git unified diff
2. Use exact git diff format with --- a/ and +++ b/ prefixes
3. Include proper @@ line markers with correct line counts
4. Include 3 lines of context before and after changes
5. Never add trailing whitespace
6. Ensure line numbers in @@ markers match the actual content

Your output should be wrapped in ```diff blocks and contain ONLY the patch."""
    
    def _extract_and_clean_patch(self, llm_response: str) -> Optional[str]:
        """Extract and clean patch content from LLM response."""
        # First try to extract from diff blocks
        diff_pattern = r'```diff\n(.*?)```'
        matches = re.findall(diff_pattern, llm_response, re.DOTALL)
        
        if matches:
            patch = matches[0]
        else:
            # Try to find patch content without code blocks
            lines = llm_response.split('\n')
            patch_lines = []
            in_patch = False
            
            for line in lines:
                if line.startswith(('--- a/', 'diff --git')):
                    in_patch = True
                
                if in_patch:
                    # Skip markdown or comments
                    if not line.startswith(('```', '#', '//')):
                        patch_lines.append(line)
            
            if not patch_lines:
                return None
                
            patch = '\n'.join(patch_lines)
        
        # Clean the patch
        cleaned_lines = []
        for line in patch.split('\n'):
            # Remove trailing whitespace
            line = line.rstrip()
            
            # Skip empty lines at the end
            if not line and cleaned_lines and not cleaned_lines[-1]:
                continue
                
            cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
            
        return '\n'.join(cleaned_lines)
    
    def _validate_patch_format(self, patch: str) -> bool:
        """Validate that the patch has correct format."""
        lines = patch.split('\n')
        
        # Must have --- and +++ lines
        has_minus = any(line.startswith('--- ') for line in lines)
        has_plus = any(line.startswith('+++ ') for line in lines)
        has_at = any(line.startswith('@@') for line in lines)
        
        if not (has_minus and has_plus and has_at):
            return False
        
        # Check @@ format
        for line in lines:
            if line.startswith('@@'):
                # Should match @@ -start,count +start,count @@
                if not re.match(r'@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@', line):
                    return False
        
        return True
    
    def _fix_common_patch_issues(self, patch: str) -> Optional[str]:
        """Try to fix common patch formatting issues."""
        lines = patch.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix --- and +++ lines missing a/ b/ prefixes
            if line.startswith('--- ') and not line.startswith('--- a/'):
                line = line.replace('--- ', '--- a/')
            elif line.startswith('+++ ') and not line.startswith('+++ b/'):
                line = line.replace('+++ ', '+++ b/')
            
            # Fix @@ lines with wrong format
            if line.startswith('@@'):
                # Try to extract numbers and reformat
                match = re.search(r'-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?', line)
                if match:
                    old_start = match.group(1)
                    old_count = match.group(2) or '1'
                    new_start = match.group(3)
                    new_count = match.group(4) or '1'
                    line = f"@@ -{old_start},{old_count} +{new_start},{new_count} @@"
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
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