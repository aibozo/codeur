"""
File rewriter - Alternative to patch generation that rewrites entire files.
"""

import logging
import re
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from .models import CodeContext, PatchResult

logger = logging.getLogger(__name__)


class FileRewriter:
    """
    Rewrite files instead of generating patches.
    More reliable than patch generation.
    """
    
    def __init__(self, llm_client=None, repo_path: str = "."):
        """Initialize file rewriter."""
        self.llm_client = llm_client
        self.repo_path = Path(repo_path)
        
        if not self.llm_client:
            try:
                from src.llm import LLMClient
                self.llm_client = LLMClient(agent_name="coding")
                logger.info(f"Initialized LLM client for file rewriting: {self.llm_client.model_card.display_name}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM client: {e}")
                self.llm_client = None
    
    def rewrite_file(
        self,
        context: CodeContext,
        file_path: str,
        max_tokens: int = 3000,
        temperature: float = 0.1
    ) -> PatchResult:
        """Rewrite a file based on the context."""
        if not self.llm_client:
            return PatchResult(
                success=False,
                error_message="LLM client not available"
            )
        
        try:
            # Get current file content
            full_path = self.repo_path / file_path
            if not full_path.exists():
                return PatchResult(
                    success=False,
                    error_message=f"File not found: {file_path}"
                )
            
            original_content = full_path.read_text()
            
            # Build prompt for rewriting
            prompt = self._build_rewrite_prompt(context, file_path, original_content)
            
            # Call LLM
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=self._get_system_prompt()
            )
            
            # Extract new content
            new_content = self._extract_code(response)
            
            if new_content and new_content != original_content:
                # Generate diff for display
                import difflib
                diff_lines = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{file_path}",
                    tofile=f"b/{file_path}",
                    n=3
                ))
                
                patch_content = ''.join(diff_lines)
                
                # Write the new content
                full_path.write_text(new_content)
                
                return PatchResult(
                    success=True,
                    patch_content=patch_content,
                    files_modified=[file_path],
                    tokens_used=len(prompt) // 4 + max_tokens
                )
            else:
                return PatchResult(
                    success=False,
                    error_message="No changes generated or failed to extract code",
                    tokens_used=len(prompt) // 4 + max_tokens
                )
                
        except Exception as e:
            logger.error(f"Error rewriting file: {e}")
            return PatchResult(
                success=False,
                error_message=str(e)
            )
    
    def _build_rewrite_prompt(self, context: CodeContext, file_path: str, original_content: str) -> str:
        """Build prompt for file rewriting."""
        prompt_parts = []
        
        prompt_parts.append(f"Task: {context.task_goal}")
        prompt_parts.append(f"File: {file_path}")
        prompt_parts.append("")
        
        prompt_parts.append("Current file content:")
        prompt_parts.append("```python")
        prompt_parts.append(original_content)
        prompt_parts.append("```")
        prompt_parts.append("")
        
        # Add any additional context
        if context.blob_contents:
            prompt_parts.append("Additional context:")
            for blob_id, content in list(context.blob_contents.items())[:2]:
                prompt_parts.append(f"\n{blob_id}:")
                prompt_parts.append(content[:500])
        
        prompt_parts.append("")
        prompt_parts.append("Instructions:")
        prompt_parts.append("1. Make ONLY the changes necessary to accomplish the task")
        prompt_parts.append("2. Preserve all other code exactly as it is")
        prompt_parts.append("3. Maintain the same code style and formatting")
        prompt_parts.append("4. Output the complete modified file")
        prompt_parts.append("")
        prompt_parts.append("Output the modified file content:")
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for file rewriting."""
        return """You are a precise code editor. When asked to modify code:
1. Make ONLY the requested changes
2. Preserve everything else exactly as it is
3. Maintain consistent style and formatting
4. Output the complete file with modifications
5. Wrap the output in ```python code blocks"""
    
    def _extract_code(self, llm_response: str) -> Optional[str]:
        """Extract code from LLM response."""
        # Look for code blocks
        code_pattern = r'```(?:python)?\n(.*?)```'
        matches = re.findall(code_pattern, llm_response, re.DOTALL)
        
        if matches:
            # Return the first (hopefully only) code block
            return matches[0].strip()
        
        # If no code blocks, try to extract everything after a marker
        markers = [
            "Output:",
            "Modified file:",
            "Here is the modified",
            "Here's the modified",
        ]
        
        for marker in markers:
            if marker in llm_response:
                parts = llm_response.split(marker, 1)
                if len(parts) > 1:
                    code = parts[1].strip()
                    # Remove any trailing text
                    if "```" in code:
                        code = code.split("```")[0]
                    return code.strip()
        
        return None


class SmartFileRewriter(FileRewriter):
    """
    Smarter file rewriter that can handle specific change types.
    """
    
    def rewrite_for_docstring_change(
        self,
        file_path: str,
        function_name: str,
        new_docstring: str
    ) -> PatchResult:
        """Specialized rewriter for docstring changes."""
        try:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                return PatchResult(
                    success=False,
                    error_message=f"File not found: {file_path}"
                )
            
            original_content = full_path.read_text()
            lines = original_content.splitlines(keepends=True)
            
            # Find the function
            in_function = False
            docstring_start = -1
            docstring_end = -1
            indent = ""
            
            for i, line in enumerate(lines):
                if f"def {function_name}(" in line:
                    in_function = True
                    # Get indentation of next line
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        indent = len(next_line) - len(next_line.lstrip())
                        
                        # Check if next line is a docstring
                        stripped = next_line.strip()
                        if stripped.startswith('"""') or stripped.startswith("'''"):
                            docstring_start = i + 1
                            # Find end
                            if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                                # Single line docstring
                                docstring_end = i + 1
                            else:
                                # Multi-line docstring
                                for j in range(i + 2, len(lines)):
                                    if '"""' in lines[j] or "'''" in lines[j]:
                                        docstring_end = j
                                        break
                            break
            
            if docstring_start >= 0 and docstring_end >= 0:
                # Replace the docstring
                new_docstring_line = ' ' * indent + f'"""{new_docstring}"""\n'
                
                # Build new content
                new_lines = lines[:docstring_start] + [new_docstring_line] + lines[docstring_end + 1:]
                new_content = ''.join(new_lines)
                
                # Generate diff
                import difflib
                diff_lines = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{file_path}",
                    tofile=f"b/{file_path}",
                    n=3
                ))
                
                patch_content = ''.join(diff_lines)
                
                # Write the new content
                full_path.write_text(new_content)
                
                return PatchResult(
                    success=True,
                    patch_content=patch_content,
                    files_modified=[file_path],
                    tokens_used=0  # No LLM used
                )
            else:
                return PatchResult(
                    success=False,
                    error_message=f"Could not find docstring for function {function_name}"
                )
                
        except Exception as e:
            logger.error(f"Error in specialized rewrite: {e}")
            return PatchResult(
                success=False,
                error_message=str(e)
            )