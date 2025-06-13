"""Security utilities for the Agent System.

This module provides security features to ensure the agent system
operates safely within the project boundaries.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Union, List, Optional, Dict, Any
import fnmatch
from functools import wraps

from src.core.logging import get_logger

logger = get_logger(__name__)


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
        
        # Import settings
        from src.core.settings import get_settings
        settings = get_settings()
        
        # Load security config from settings
        self.forbidden_patterns = settings.security.forbidden_patterns.copy()
        self.excluded_dirs = settings.security.excluded_dirs.copy()
        self.enable_symlink_checks = settings.security.enable_symlink_checks
        self.allowed_symlinks = set(settings.security.allowed_symlinks)
        
        # Load additional config from .agent-security.yml if it exists
        self._load_security_config()
    
    def is_safe_path(self, path: Union[str, Path]) -> bool:
        """Check if a path is safe to access.
        
        Args:
            path: The path to check
            
        Returns:
            True if the path is safe, False otherwise
        """
        try:
            # Convert to Path object
            original_path = Path(path)
            target_path = original_path.resolve()
            
            # Check for symlink traversal
            if self._check_symlink_traversal(original_path, target_path):
                return False
            
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
    
    def _check_symlink_traversal(self, original_path: Path, resolved_path: Path) -> bool:
        """Check if a path involves unsafe symlink traversal.
        
        Args:
            original_path: The original path before resolution
            resolved_path: The resolved (absolute) path
            
        Returns:
            True if the path involves unsafe symlink traversal
        """
        if not self.enable_symlink_checks:
            return False
        
        # Check each component of the path for symlinks
        current = self.project_root
        for part in original_path.parts:
            if part in ['.', '..']:
                continue
                
            current = current / part
            
            try:
                if current.is_symlink():
                    # Check if this symlink is allowed
                    link_target = current.resolve()
                    
                    # Allow symlinks that stay within project root
                    if self._is_subpath(link_target, self.project_root):
                        continue
                    
                    # Check against allowed symlinks
                    if str(current) in self.allowed_symlinks:
                        continue
                    
                    logger.warning(f"Blocked symlink traversal: {current} -> {link_target}")
                    return True
                    
            except (OSError, RuntimeError):
                # Handle broken symlinks or permission errors
                logger.warning(f"Error checking symlink: {current}")
                return True
        
        return False
    
    def _load_security_config(self):
        """Load additional security configuration from .agent-security.yml."""
        config_path = self.project_root / ".agent-security.yml"
        
        if not config_path.exists():
            return
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                return
            
            # Add additional forbidden patterns
            if 'forbidden_patterns' in config:
                additional_patterns = config['forbidden_patterns']
                if isinstance(additional_patterns, list):
                    self.forbidden_patterns.extend(additional_patterns)
            
            # Add additional excluded directories
            if 'excluded_dirs' in config:
                additional_dirs = config['excluded_dirs']
                if isinstance(additional_dirs, list):
                    self.excluded_dirs.extend(additional_dirs)
            
            # Add allowed symlinks
            if 'allowed_symlinks' in config:
                allowed = config['allowed_symlinks']
                if isinstance(allowed, list):
                    self.allowed_symlinks.update(allowed)
            
            logger.info(f"Loaded security config from {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading security config: {e}")
    
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