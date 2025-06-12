"""
Patch validation for Coding Agent.

Validates generated patches by:
- Syntax checking
- Running linters
- Executing tests
- Type checking
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import List, Optional, Tuple
import tempfile
import os

from .models import ValidationResult

logger = logging.getLogger(__name__)


class PatchValidator:
    """
    Validates patches before committing.
    
    Runs various checks to ensure code quality.
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize validator.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = Path(repo_path)
        
        # Detect available tools
        self.has_black = self._check_tool("black", "--version")
        self.has_ruff = self._check_tool("ruff", "--version")
        self.has_pylint = self._check_tool("pylint", "--version")
        self.has_mypy = self._check_tool("mypy", "--version")
        self.has_pytest = self._check_tool("pytest", "--version")
        
        logger.info(f"Validator initialized - black:{self.has_black}, "
                   f"ruff:{self.has_ruff}, pylint:{self.has_pylint}, "
                   f"mypy:{self.has_mypy}, pytest:{self.has_pytest}")
    
    def validate_patch(
        self,
        modified_files: List[str],
        run_tests: bool = True,
        test_pattern: str = "fast"
    ) -> ValidationResult:
        """
        Validate the current state after applying a patch.
        
        Args:
            modified_files: List of modified file paths
            run_tests: Whether to run tests
            test_pattern: Test pattern to run (e.g., "fast", "unit")
            
        Returns:
            ValidationResult with all findings
        """
        result = ValidationResult()
        
        # Filter to Python files for now
        py_files = [f for f in modified_files if f.endswith('.py')]
        
        if not py_files:
            logger.info("No Python files to validate")
            return result
        
        # 1. Syntax check
        logger.info("Checking syntax...")
        result.syntax_valid = self._check_syntax(py_files, result)
        
        if not result.syntax_valid:
            return result  # No point continuing if syntax is broken
        
        # 2. Format/lint check
        logger.info("Running linters...")
        result.lint_passed = self._run_linters(py_files, result)
        
        # 3. Type check (if available)
        if self.has_mypy:
            logger.info("Running type checker...")
            result.type_check_passed = self._run_type_check(py_files, result)
        
        # 4. Run tests (if requested)
        if run_tests and self.has_pytest:
            logger.info(f"Running tests (pattern: {test_pattern})...")
            result.tests_passed = self._run_tests(test_pattern, result)
        
        return result
    
    def _check_tool(self, tool_name: str, version_arg: str) -> bool:
        """Check if a tool is available."""
        try:
            subprocess.run(
                [tool_name, version_arg],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_syntax(self, files: List[str], result: ValidationResult) -> bool:
        """Check Python syntax."""
        all_valid = True
        
        for file_path in files:
            full_path = self.repo_path / file_path
            
            if not full_path.exists():
                continue
            
            try:
                # Compile the file to check syntax
                with open(full_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), file_path, 'exec')
                    
            except SyntaxError as e:
                all_valid = False
                result.add_error(f"Syntax error in {file_path}:{e.lineno}: {e.msg}")
            except Exception as e:
                all_valid = False
                result.add_error(f"Failed to check {file_path}: {str(e)}")
        
        return all_valid
    
    def _run_linters(self, files: List[str], result: ValidationResult) -> bool:
        """Run available linters."""
        all_passed = True
        
        # Try ruff first (fastest)
        if self.has_ruff:
            passed = self._run_ruff(files, result)
            all_passed = all_passed and passed
        
        # Try black for formatting
        elif self.has_black:
            passed = self._run_black(files, result)
            all_passed = all_passed and passed
        
        # Try pylint if no other linter available
        elif self.has_pylint:
            passed = self._run_pylint(files, result)
            all_passed = all_passed and passed
        
        return all_passed
    
    def _run_ruff(self, files: List[str], result: ValidationResult) -> bool:
        """Run ruff linter."""
        try:
            cmd = ["ruff", "check", "--output-format", "json"] + files
            
            proc = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if proc.returncode != 0 and proc.stdout:
                # Parse ruff JSON output
                try:
                    issues = json.loads(proc.stdout)
                    for issue in issues[:10]:  # Limit to first 10
                        location = f"{issue.get('filename', '')}:{issue.get('location', {}).get('row', '')}"
                        message = issue.get('message', '')
                        code = issue.get('code', '')
                        
                        if issue.get('fix'):
                            result.add_warning(f"{location}: {code} - {message} (fixable)")
                        else:
                            result.add_error(f"{location}: {code} - {message}")
                except:
                    result.add_error(f"Ruff found issues: {proc.stdout}")
                
                return False
            
            return True
            
        except Exception as e:
            result.add_warning(f"Failed to run ruff: {e}")
            return True  # Don't fail on linter errors
    
    def _run_black(self, files: List[str], result: ValidationResult) -> bool:
        """Run black formatter in check mode."""
        try:
            cmd = ["black", "--check", "--diff"] + files
            
            proc = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if proc.returncode != 0:
                result.add_warning("Code formatting issues found (run black to fix)")
                if proc.stdout:
                    # Add first few lines of diff
                    diff_lines = proc.stdout.split('\n')[:20]
                    result.add_warning("Formatting diff:\n" + '\n'.join(diff_lines))
                return False
            
            return True
            
        except Exception as e:
            result.add_warning(f"Failed to run black: {e}")
            return True
    
    def _run_pylint(self, files: List[str], result: ValidationResult) -> bool:
        """Run pylint."""
        try:
            cmd = ["pylint", "--output-format=json", "--errors-only"] + files
            
            proc = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if proc.stdout:
                try:
                    messages = json.loads(proc.stdout)
                    for msg in messages[:10]:  # Limit to first 10
                        location = f"{msg.get('path', '')}:{msg.get('line', '')}"
                        message = msg.get('message', '')
                        symbol = msg.get('symbol', '')
                        
                        result.add_error(f"{location}: {symbol} - {message}")
                except:
                    result.add_error(f"Pylint found issues")
                
                return False
            
            return True
            
        except Exception as e:
            result.add_warning(f"Failed to run pylint: {e}")
            return True
    
    def _run_type_check(self, files: List[str], result: ValidationResult) -> bool:
        """Run mypy type checker."""
        try:
            cmd = ["mypy", "--no-error-summary", "--show-error-codes"] + files
            
            proc = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if proc.returncode != 0 and proc.stdout:
                # Parse mypy output
                lines = proc.stdout.strip().split('\n')
                for line in lines[:10]:  # Limit to first 10
                    if ': error:' in line or ': note:' in line:
                        result.add_warning(f"Type check: {line}")
            
            # Type errors are warnings, not failures
            return True
            
        except Exception as e:
            result.add_warning(f"Failed to run mypy: {e}")
            return True
    
    def _run_tests(self, pattern: str, result: ValidationResult) -> bool:
        """Run pytest with specified pattern."""
        try:
            # Build pytest command
            cmd = ["pytest", "-xvs"]
            
            # Add pattern-based filtering
            if pattern == "fast":
                cmd.extend(["-m", "fast"])
            elif pattern == "unit":
                cmd.extend(["-m", "unit"])
            elif pattern:
                cmd.extend(["-k", pattern])
            
            # Add timeout
            cmd.extend(["--timeout=30"])
            
            proc = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60  # Overall timeout
            )
            
            result.test_output = proc.stdout + proc.stderr
            
            if proc.returncode != 0:
                # Extract failure summary
                output_lines = result.test_output.split('\n')
                for i, line in enumerate(output_lines):
                    if 'FAILED' in line:
                        # Get test name and next few lines
                        result.add_error(f"Test failed: {line}")
                        
                        # Look for assertion details
                        for j in range(i+1, min(i+10, len(output_lines))):
                            if output_lines[j].strip():
                                result.add_error(f"  {output_lines[j].strip()}")
                
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            result.add_error("Tests timed out after 60 seconds")
            return False
        except Exception as e:
            result.add_error(f"Failed to run tests: {e}")
            return False