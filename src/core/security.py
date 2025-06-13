"""Security utilities for the Agent System.

This module provides security features to ensure the agent system
operates safely within the project boundaries.
"""

import os
import sys
from pathlib import Path
from typing import Union, List, Optional
import fnmatch
from functools import wraps

from src.core.logging import setup_logging

logger = setup_logging(__name__)


class SecurityException(Exception):
    """Exception raised for security violations."""
    pass


class SecurityManager:
    """Manages security policies for file system access.
    
    This class ensures that all file operations are restricted to the
    project root directory and prevents access to sensitive files.
    """
    
    def __init__(self, project_root: Path):
        """Initialize the security manager.
        
        Args:
            project_root: The root directory of the project
        """
        self.project_root = project_root.resolve()
        
        # Default patterns for files that should never be accessed
        self.forbidden_patterns = [
            '.env',
            '.env.*',
            '*.key',
            '*.pem',
            '*.pfx',
            '*.p12',
            'id_rsa*',
            'id_dsa*',
            'id_ecdsa*',
            'id_ed25519*',
            '.ssh/*',
            '.gnupg/*',
            '.password*',
            '.secret*',
            '*.secret',
            '*.credentials',
            '.aws/credentials',
            '.config/gcloud/*',
            '.kube/config',
        ]
        
        # Patterns for directories that should be skipped
        self.excluded_dirs = [
            '.git',
            '__pycache__',
            'node_modules',
            '.venv',
            'venv',
            'env',
            '.env',
            '.tox',
            '.pytest_cache',
            '.mypy_cache',
            '.coverage',
            'htmlcov',
            'dist',
            'build',
            '*.egg-info',
        ]
    
    def is_safe_path(self, path: Union[str, Path]) -> bool:
        """Check if a path is safe to access.
        
        Args:
            path: The path to check
            
        Returns:
            True if the path is safe, False otherwise
        """
        try:
            # Convert to Path object and resolve
            target_path = Path(path).resolve()
            
            # Check if path is within project root
            if not self._is_subpath(target_path, self.project_root):
                logger.warning(f"Path '{path}' is outside project root")
                return False
            
            # Check against forbidden patterns
            relative_path = target_path.relative_to(self.project_root)
            for pattern in self.forbidden_patterns:
                if fnmatch.fnmatch(str(relative_path), pattern):
                    logger.warning(f"Path '{path}' matches forbidden pattern '{pattern}'")
                    return False
                if fnmatch.fnmatch(target_path.name, pattern):
                    logger.warning(f"Filename '{target_path.name}' matches forbidden pattern '{pattern}'")
                    return False
            
            # Check if any parent directory is excluded
            for parent in relative_path.parents:
                if str(parent) in self.excluded_dirs:
                    logger.warning(f"Path '{path}' is within excluded directory '{parent}'")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking path safety: {str(e)}")
            return False
    
    def _is_subpath(self, child: Path, parent: Path) -> bool:
        """Check if child is a subpath of parent.
        
        Args:
            child: The potential child path
            parent: The parent path
            
        Returns:
            True if child is under parent
        """
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False
    
    def validate_path(self, path: Union[str, Path]) -> Path:
        """Validate and return a safe path.
        
        Args:
            path: The path to validate
            
        Returns:
            The validated Path object
            
        Raises:
            SecurityException: If the path is not safe
        """
        if not self.is_safe_path(path):
            raise SecurityException(f"Access to path '{path}' is not allowed")
        return Path(path).resolve()
    
    def is_valid_project_root(self) -> bool:
        """Check if the current directory is a valid project root.
        
        Returns:
            True if this appears to be a valid project directory
        """
        # Check for common project indicators
        indicators = [
            '.git',
            'setup.py',
            'pyproject.toml',
            'package.json',
            'Cargo.toml',
            'go.mod',
            'pom.xml',
            'build.gradle',
            'CMakeLists.txt',
            'Makefile',
            'requirements.txt',
            'README.md',
            'readme.md',
            'README.MD',
        ]
        
        for indicator in indicators:
            if (self.project_root / indicator).exists():
                return True
        
        # Check if there are any source files
        extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']
        for ext in extensions:
            if list(self.project_root.glob(f'*{ext}')):
                return True
            if list(self.project_root.glob(f'**/*{ext}')):
                return True
        
        return False
    
    def read_file(self, path: Union[str, Path]) -> str:
        """Safely read a file.
        
        Args:
            path: Path to the file to read
            
        Returns:
            The file contents
            
        Raises:
            SecurityException: If the path is not safe
            FileNotFoundError: If the file doesn't exist
        """
        safe_path = self.validate_path(path)
        
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_file(self, path: Union[str, Path], content: str) -> None:
        """Safely write to a file.
        
        Args:
            path: Path to the file to write
            content: Content to write
            
        Raises:
            SecurityException: If the path is not safe
        """
        safe_path = self.validate_path(path)
        
        # Ensure parent directory exists
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def list_files(self, directory: Union[str, Path], pattern: str = '*') -> List[Path]:
        """Safely list files in a directory.
        
        Args:
            directory: Directory to list
            pattern: Glob pattern for files
            
        Returns:
            List of file paths
            
        Raises:
            SecurityException: If the directory is not safe
        """
        safe_dir = self.validate_path(directory)
        
        if not safe_dir.is_dir():
            raise ValueError(f"'{safe_dir}' is not a directory")
        
        files = []
        for file_path in safe_dir.glob(pattern):
            if file_path.is_file() and self.is_safe_path(file_path):
                files.append(file_path)
        
        return files
    
    def get_relative_path(self, path: Union[str, Path]) -> Path:
        """Get the relative path from project root.
        
        Args:
            path: The path to convert
            
        Returns:
            The relative path
            
        Raises:
            SecurityException: If the path is not safe
        """
        safe_path = self.validate_path(path)
        return safe_path.relative_to(self.project_root)


def secure_path_access(func):
    """Decorator to ensure path arguments are validated.
    
    This decorator checks the first argument (assumed to be a path)
    for security before calling the function.
    """
    @wraps(func)
    def wrapper(self, path, *args, **kwargs):
        if hasattr(self, 'security_manager') and self.security_manager:
            path = self.security_manager.validate_path(path)
        return func(self, path, *args, **kwargs)
    return wrapper


def get_security_manager(project_root: Optional[Path] = None) -> SecurityManager:
    """Get a security manager instance.
    
    Args:
        project_root: The project root directory. If None, uses current directory.
        
    Returns:
        SecurityManager instance
    """
    if project_root is None:
        project_root = Path.cwd()
    return SecurityManager(project_root)