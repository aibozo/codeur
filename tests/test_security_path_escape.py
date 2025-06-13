"""Test path escape scenarios for SecurityManager.

This module tests various path traversal and escape attempts to ensure
the SecurityManager properly prevents access outside the project root.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.security import SecurityManager, SecurityException


class TestSecurityManagerPathEscape:
    """Test cases for path escape prevention in SecurityManager."""
    
    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project root directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir()
            
            # Create some test files and directories
            (project_root / "src").mkdir()
            (project_root / "src" / "main.py").write_text("# Main file")
            (project_root / "README.md").write_text("# Project")
            (project_root / ".git").mkdir()
            
            yield project_root
    
    @pytest.fixture
    def security_manager(self, temp_project_root):
        """Create a SecurityManager instance with temp project root."""
        return SecurityManager(temp_project_root)
    
    def test_simple_parent_directory_escape(self, security_manager, temp_project_root):
        """Test that simple ../ escapes are prevented."""
        # Try to access parent directory
        assert not security_manager.is_safe_path("../")
        assert not security_manager.is_safe_path("..")
        assert not security_manager.is_safe_path("../secret.txt")
        
        # These should raise SecurityException
        with pytest.raises(SecurityException):
            security_manager.validate_path("../")
        
        with pytest.raises(SecurityException):
            security_manager.validate_path("../secret.txt")
    
    def test_nested_parent_directory_escape(self, security_manager, temp_project_root):
        """Test that nested ../ escapes are prevented."""
        # Multiple levels of parent directory access
        assert not security_manager.is_safe_path("../../")
        assert not security_manager.is_safe_path("../../../etc/passwd")
        assert not security_manager.is_safe_path("src/../../")
        assert not security_manager.is_safe_path("src/../../../outside.txt")
        
        # Hidden in the middle of path
        assert not security_manager.is_safe_path("src/../../../hidden/file.txt")
    
    def test_absolute_path_escape(self, security_manager, temp_project_root):
        """Test that absolute paths outside project are prevented."""
        # Try to access system directories
        assert not security_manager.is_safe_path("/etc/passwd")
        assert not security_manager.is_safe_path("/home/user/.ssh/id_rsa")
        assert not security_manager.is_safe_path("C:\\Windows\\System32\\config")
        
        # Absolute path to project is OK
        assert security_manager.is_safe_path(temp_project_root / "src" / "main.py")
    
    def test_symlink_escape(self, security_manager, temp_project_root):
        """Test that symlinks pointing outside project are prevented."""
        # Create a symlink pointing outside
        outside_file = temp_project_root.parent / "outside.txt"
        outside_file.write_text("Secret data")
        
        symlink_path = temp_project_root / "link_to_outside"
        
        # Handle different OS behaviors for symlinks
        try:
            symlink_path.symlink_to(outside_file)
            
            # The symlink itself might be in project, but resolves outside
            assert not security_manager.is_safe_path(symlink_path)
            
            with pytest.raises(SecurityException):
                security_manager.read_file(symlink_path)
        except OSError:
            # Skip test if symlinks not supported (e.g., Windows without admin)
            pytest.skip("Symlinks not supported on this system")
    
    def test_path_normalization_escape(self, security_manager, temp_project_root):
        """Test various path normalization attempts."""
        # Double slashes
        assert not security_manager.is_safe_path("src//..//..//secret.txt")
        
        # Backslashes (Windows-style)
        assert not security_manager.is_safe_path("src\\..\\..\\secret.txt")
        
        # Mixed slashes
        assert not security_manager.is_safe_path("src/../\\../secret.txt")
        
        # Current directory references
        assert not security_manager.is_safe_path("./../../secret.txt")
        assert not security_manager.is_safe_path("src/./../../secret.txt")
        
        # URL encoding attempts (these should be handled by Path.resolve)
        assert not security_manager.is_safe_path("..%2F..%2Fsecret.txt")
        assert not security_manager.is_safe_path("..%252F..%252Fsecret.txt")
    
    def test_null_byte_injection(self, security_manager, temp_project_root):
        """Test null byte injection attempts."""
        # Null bytes should be handled properly
        paths_with_null = [
            "src/main.py\x00.txt",
            "src/main.py\x00../../secret.txt",
            "\x00/../secret.txt",
        ]
        
        for path in paths_with_null:
            # These should either be rejected or the null byte stripped
            # Either way, they shouldn't allow escape
            result = security_manager.is_safe_path(path)
            if result:
                # If accepted, ensure it doesn't escape
                resolved = Path(path).resolve()
                assert resolved.is_relative_to(temp_project_root)
    
    def test_unicode_normalization_escape(self, security_manager, temp_project_root):
        """Test Unicode normalization attacks."""
        # Unicode characters that might normalize to dots or slashes
        unicode_escapes = [
            "src/\u2024\u2024/secret.txt",  # One dot leader
            "src/\u2025\u2025/secret.txt",  # Two dot leader
            "src/\uff0e\uff0e/secret.txt",  # Fullwidth full stop
            "src/\u2215\u2215secret.txt",   # Division slash
        ]
        
        for path in unicode_escapes:
            # These should not allow escape
            if security_manager.is_safe_path(path):
                resolved = Path(path).resolve()
                assert resolved.is_relative_to(temp_project_root)
    
    def test_case_sensitivity_escape(self, security_manager, temp_project_root):
        """Test case sensitivity issues."""
        # On case-insensitive filesystems, these might be issues
        if os.name == 'nt':  # Windows
            # Test forbidden patterns with different cases
            test_files = [
                ".ENV",
                ".Env",
                "SECRET.KEY",
                "Id_Rsa",
            ]
            
            for filename in test_files:
                file_path = temp_project_root / filename
                # These should be caught by forbidden patterns
                assert not security_manager.is_safe_path(file_path)
    
    def test_long_path_escape(self, security_manager, temp_project_root):
        """Test very long paths that might cause buffer issues."""
        # Create a very long path with escape attempts
        long_segment = "a" * 200
        escape_path = f"{long_segment}/../" * 10 + "secret.txt"
        
        assert not security_manager.is_safe_path(escape_path)
        
        # Very long legitimate path should work
        legitimate_long = "src/" + "/".join([long_segment[:50]] * 5) + "/file.txt"
        # This might fail due to OS path length limits, but shouldn't escape
        try:
            result = security_manager.is_safe_path(legitimate_long)
            if result:
                resolved = Path(legitimate_long).resolve()
                assert resolved.is_relative_to(temp_project_root)
        except OSError:
            # Path too long for OS is OK, as long as it doesn't escape
            pass
    
    def test_special_files_escape(self, security_manager, temp_project_root):
        """Test access to special files and devices."""
        special_files = [
            "/dev/null",
            "/dev/zero",
            "/dev/random",
            "CON",  # Windows special file
            "PRN",  # Windows special file
            "AUX",  # Windows special file
            "NUL",  # Windows special file
            "COM1", # Windows special file
            "LPT1", # Windows special file
        ]
        
        for special in special_files:
            assert not security_manager.is_safe_path(special)
    
    def test_environment_variable_escape(self, security_manager, temp_project_root):
        """Test environment variable expansion attempts."""
        # These should not expand environment variables
        env_paths = [
            "$HOME/.ssh/id_rsa",
            "${HOME}/.ssh/id_rsa",
            "%USERPROFILE%\\.ssh\\id_rsa",
            "~/.ssh/id_rsa",
            "~/../../etc/passwd",
        ]
        
        for path in env_paths:
            # Path.resolve() doesn't expand env vars or ~, so these should fail
            assert not security_manager.is_safe_path(path)
    
    def test_race_condition_escape(self, security_manager, temp_project_root):
        """Test TOCTOU (Time-of-check to time-of-use) scenarios."""
        # Create a legitimate file
        safe_file = temp_project_root / "safe.txt"
        safe_file.write_text("Safe content")
        
        # First check should pass
        assert security_manager.is_safe_path(safe_file)
        
        # In a real TOCTOU attack, the file would be replaced with a symlink
        # between check and use. We simulate by checking the path is resolved
        # at validation time
        validated_path = security_manager.validate_path(safe_file)
        assert validated_path.resolve() == safe_file.resolve()
    
    def test_path_injection_in_operations(self, security_manager, temp_project_root):
        """Test path injection in file operations."""
        # Test read_file with escape attempts
        with pytest.raises(SecurityException):
            security_manager.read_file("../../../etc/passwd")
        
        # Test write_file with escape attempts
        with pytest.raises(SecurityException):
            security_manager.write_file("../../../tmp/evil.txt", "evil content")
        
        # Test list_files with escape attempts
        with pytest.raises(SecurityException):
            security_manager.list_files("../../../")
    
    def test_relative_symlink_escape(self, security_manager, temp_project_root):
        """Test relative symlinks that might escape."""
        try:
            # Create a subdirectory
            subdir = temp_project_root / "subdir"
            subdir.mkdir()
            
            # Create a relative symlink that goes up too far
            escape_link = subdir / "escape_link"
            escape_link.symlink_to("../../../../../../etc")
            
            # This should be caught
            assert not security_manager.is_safe_path(escape_link)
            
            # Create a safe relative symlink
            safe_link = subdir / "safe_link"
            safe_link.symlink_to("../src")
            
            # This should be allowed as it stays within project
            assert security_manager.is_safe_path(safe_link)
            
        except OSError:
            pytest.skip("Symlinks not supported on this system")
    
    def test_directory_traversal_in_list_files(self, security_manager, temp_project_root):
        """Test directory traversal in list_files pattern."""
        # These patterns should not allow escape
        with pytest.raises(SecurityException):
            security_manager.list_files(".", "../*")
        
        with pytest.raises(SecurityException):
            security_manager.list_files("src", "../../*")
        
        # Safe patterns should work
        files = security_manager.list_files(".", "*.md")
        assert len(files) == 1
        assert files[0].name == "README.md"
    
    def test_path_combination_attacks(self, security_manager, temp_project_root):
        """Test combinations of different escape techniques."""
        complex_escapes = [
            "src/./../../../etc/passwd",  # Hidden parent refs
            "./src/../.././../etc/passwd",  # Multiple techniques
            "src//../..//../..//etc/passwd",  # Double slashes
            "src/subdir/../../../../../../etc/passwd",  # Deep escape
            "./../project/../../../etc/passwd",  # Legitimate + escape
        ]
        
        for path in complex_escapes:
            assert not security_manager.is_safe_path(path)
            with pytest.raises(SecurityException):
                security_manager.validate_path(path)
    
    def test_forbidden_patterns_with_paths(self, security_manager, temp_project_root):
        """Test that forbidden patterns work with path traversal."""
        # Even if the path would be within project, forbidden patterns apply
        test_cases = [
            "src/../.env",  # Forbidden file via traversal
            "src/../.ssh/id_rsa",  # Forbidden directory
            "src/../config/.aws/credentials",  # Nested forbidden
        ]
        
        for path in test_cases:
            # Create the file to ensure path exists
            full_path = temp_project_root / Path(path).resolve().relative_to(temp_project_root)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("test")
            
            # Should still be forbidden
            assert not security_manager.is_safe_path(path)
    
    def test_get_relative_path_escape(self, security_manager, temp_project_root):
        """Test get_relative_path with escape attempts."""
        # Should raise for paths outside project
        with pytest.raises(SecurityException):
            security_manager.get_relative_path("../../../etc/passwd")
        
        with pytest.raises(SecurityException):
            security_manager.get_relative_path("/etc/passwd")
        
        # Should work for valid paths
        valid_path = temp_project_root / "src" / "main.py"
        relative = security_manager.get_relative_path(valid_path)
        assert relative == Path("src/main.py")
    
    def test_windows_specific_escapes(self, security_manager, temp_project_root):
        """Test Windows-specific path escape attempts."""
        if os.name != 'nt':
            pytest.skip("Windows-specific test")
        
        windows_escapes = [
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "\\\\server\\share\\file.txt",  # UNC path
            "src\\..\\..\\..\\Windows\\System32",
            ".\\..\\..\\..\\Windows\\System32",
            "CON.txt",  # Reserved name with extension
            "PRN.config",  # Reserved name with extension
        ]
        
        for path in windows_escapes:
            assert not security_manager.is_safe_path(path)
    
    def test_path_edge_cases(self, security_manager, temp_project_root):
        """Test edge cases in path handling."""
        # Empty path
        assert not security_manager.is_safe_path("")
        
        # Just dots
        assert security_manager.is_safe_path(".")  # Current dir is OK
        assert not security_manager.is_safe_path("..")  # Parent is not
        assert not security_manager.is_safe_path("...")  # Three dots
        
        # Paths with spaces
        space_path = temp_project_root / "path with spaces" / "file.txt"
        space_path.parent.mkdir(parents=True, exist_ok=True)
        space_path.write_text("content")
        assert security_manager.is_safe_path(space_path)
        
        # Paths with special characters (but not escape sequences)
        special_path = temp_project_root / "path-with_special.chars!" / "file.txt"
        special_path.parent.mkdir(parents=True, exist_ok=True)
        special_path.write_text("content")
        assert security_manager.is_safe_path(special_path)