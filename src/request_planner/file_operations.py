"""
File operations for plan execution.

This module handles actual file modifications during plan execution,
including creating, editing, and deleting files with proper error handling
and rollback capabilities.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import difflib
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileBackup:
    """Backup information for a file."""
    original_path: Path
    backup_path: Path
    existed: bool
    content: Optional[str] = None
    
    
class FileOperations:
    """
    Handles file operations with backup and rollback support.
    
    Features:
    - Automatic backup before modifications
    - Rollback on failure
    - Diff generation
    - Safe file operations
    """
    
    def __init__(self, repo_path: Path):
        """Initialize file operations handler."""
        self.repo_path = Path(repo_path)
        self.backup_dir = self.repo_path / ".agent_backups"
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backups: List[FileBackup] = []
        
    def create_file(self, file_path: str, content: str) -> Tuple[bool, str]:
        """
        Create a new file.
        
        Args:
            file_path: Path relative to repo root
            content: File content
            
        Returns:
            Tuple of (success, message)
        """
        full_path = self.repo_path / file_path
        
        try:
            # Check if file already exists
            if full_path.exists():
                return False, f"File already exists: {file_path}"
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup entry (for rollback)
            backup = FileBackup(
                original_path=full_path,
                backup_path=None,
                existed=False
            )
            self.backups.append(backup)
            
            # Write file
            full_path.write_text(content, encoding='utf-8')
            
            logger.info(f"Created file: {file_path}")
            return True, f"Created {file_path}"
            
        except Exception as e:
            logger.error(f"Failed to create file {file_path}: {e}")
            return False, f"Error creating file: {str(e)}"
    
    def edit_file(self, file_path: str, content: str) -> Tuple[bool, str]:
        """
        Edit an existing file.
        
        Args:
            file_path: Path relative to repo root
            content: New file content
            
        Returns:
            Tuple of (success, message)
        """
        full_path = self.repo_path / file_path
        
        try:
            # Check if file exists
            if not full_path.exists():
                return False, f"File not found: {file_path}"
            
            # Create backup
            backup_path = self._create_backup(full_path)
            
            # Read original content
            original_content = full_path.read_text(encoding='utf-8')
            
            # Create backup entry
            backup = FileBackup(
                original_path=full_path,
                backup_path=backup_path,
                existed=True,
                content=original_content
            )
            self.backups.append(backup)
            
            # Write new content
            full_path.write_text(content, encoding='utf-8')
            
            logger.info(f"Edited file: {file_path}")
            return True, f"Modified {file_path}"
            
        except Exception as e:
            logger.error(f"Failed to edit file {file_path}: {e}")
            return False, f"Error editing file: {str(e)}"
    
    def apply_patch(self, file_path: str, patch: str) -> Tuple[bool, str]:
        """
        Apply a patch to a file.
        
        Args:
            file_path: Path relative to repo root
            patch: Unified diff patch
            
        Returns:
            Tuple of (success, message)
        """
        full_path = self.repo_path / file_path
        
        try:
            if not full_path.exists():
                return False, f"File not found: {file_path}"
            
            # Read current content
            current_content = full_path.read_text(encoding='utf-8')
            current_lines = current_content.splitlines(keepends=True)
            
            # Parse and apply patch
            # This is a simplified implementation
            # In production, use a proper patch library
            patched_content = self._apply_simple_patch(current_lines, patch)
            
            if patched_content is None:
                return False, "Failed to apply patch"
            
            # Use edit_file to handle backup
            return self.edit_file(file_path, patched_content)
            
        except Exception as e:
            logger.error(f"Failed to apply patch to {file_path}: {e}")
            return False, f"Error applying patch: {str(e)}"
    
    def delete_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Delete a file.
        
        Args:
            file_path: Path relative to repo root
            
        Returns:
            Tuple of (success, message)
        """
        full_path = self.repo_path / file_path
        
        try:
            if not full_path.exists():
                return False, f"File not found: {file_path}"
            
            # Create backup
            backup_path = self._create_backup(full_path)
            original_content = full_path.read_text(encoding='utf-8')
            
            # Create backup entry
            backup = FileBackup(
                original_path=full_path,
                backup_path=backup_path,
                existed=True,
                content=original_content
            )
            self.backups.append(backup)
            
            # Delete file
            full_path.unlink()
            
            logger.info(f"Deleted file: {file_path}")
            return True, f"Deleted {file_path}"
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False, f"Error deleting file: {str(e)}"
    
    def get_diff(self, file_path: str, new_content: str) -> str:
        """
        Get diff between current and new content.
        
        Args:
            file_path: Path relative to repo root
            new_content: New file content
            
        Returns:
            Unified diff string
        """
        full_path = self.repo_path / file_path
        
        if full_path.exists():
            current_content = full_path.read_text(encoding='utf-8')
            current_lines = current_content.splitlines(keepends=True)
        else:
            current_lines = []
        
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            current_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=''
        )
        
        return ''.join(diff)
    
    def rollback_all(self) -> Tuple[bool, str]:
        """
        Rollback all changes made in this session.
        
        Returns:
            Tuple of (success, message)
        """
        rolled_back = 0
        errors = []
        
        # Process backups in reverse order
        for backup in reversed(self.backups):
            try:
                if backup.existed:
                    # Restore from backup
                    if backup.backup_path and backup.backup_path.exists():
                        shutil.copy2(backup.backup_path, backup.original_path)
                    elif backup.content is not None:
                        backup.original_path.write_text(backup.content, encoding='utf-8')
                    rolled_back += 1
                else:
                    # File was created, delete it
                    if backup.original_path.exists():
                        backup.original_path.unlink()
                    rolled_back += 1
                    
            except Exception as e:
                errors.append(f"{backup.original_path}: {str(e)}")
        
        # Clear backups
        self.backups.clear()
        
        if errors:
            return False, f"Rolled back {rolled_back} files with {len(errors)} errors"
        else:
            return True, f"Successfully rolled back {rolled_back} files"
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file."""
        # Ensure backup directory exists
        session_backup_dir = self.backup_dir / self.current_session_id
        session_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup filename
        relative_path = file_path.relative_to(self.repo_path)
        backup_name = str(relative_path).replace('/', '_')
        backup_path = session_backup_dir / backup_name
        
        # Copy file
        shutil.copy2(file_path, backup_path)
        
        return backup_path
    
    def _apply_simple_patch(self, lines: List[str], patch: str) -> Optional[str]:
        """
        Apply a simple unified diff patch.
        
        This is a basic implementation for demonstration.
        In production, use a proper patch library.
        """
        # For now, just return None to indicate we need full content
        # A real implementation would parse and apply the patch
        return None
    
    def cleanup_backups(self, keep_days: int = 7):
        """Clean up old backup directories."""
        if not self.backup_dir.exists():
            return
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                try:
                    # Parse directory name as date
                    dir_date = datetime.strptime(backup_dir.name, "%Y%m%d_%H%M%S")
                    if dir_date < cutoff_date:
                        shutil.rmtree(backup_dir)
                        logger.info(f"Cleaned up old backup: {backup_dir.name}")
                except Exception:
                    # Skip directories that don't match date format
                    pass