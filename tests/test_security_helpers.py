"""Test security helper functions and decorators."""

import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.security import (
    SecurityManager,
    SecurityException,
    secure_path_access,
    get_security_manager
)


class TestSecurityHelpers:
    """Test helper functions and decorators in the security module."""
    
    def test_get_security_manager_default(self):
        """Test get_security_manager with default project root."""
        with patch('src.core.security.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/fake/project")
            
            manager = get_security_manager()
            assert isinstance(manager, SecurityManager)
            assert manager.project_root == Path("/fake/project")
    
    def test_get_security_manager_custom_root(self):
        """Test get_security_manager with custom project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = get_security_manager(project_root)
            
            assert isinstance(manager, SecurityManager)
            assert manager.project_root == project_root
    
    def test_secure_path_access_decorator(self):
        """Test the secure_path_access decorator."""
        
        class MockService:
            def __init__(self, security_manager=None):
                self.security_manager = security_manager
                self.calls = []
            
            @secure_path_access
            def read_file(self, path):
                self.calls.append(('read_file', path))
                return f"Content of {path}"
            
            @secure_path_access
            def write_file(self, path, content):
                self.calls.append(('write_file', path, content))
                return True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            
            # Test with security manager
            service = MockService(security_manager=manager)
            
            # Valid path should work
            valid_path = project_root / "test.txt"
            valid_path.write_text("test")
            
            result = service.read_file(str(valid_path))
            assert len(service.calls) == 1
            assert service.calls[0][0] == 'read_file'
            assert service.calls[0][1] == valid_path  # Should be resolved Path
            
            # Invalid path should raise exception
            with pytest.raises(SecurityException):
                service.read_file("../../../etc/passwd")
            
            # Test without security manager (should pass through)
            service_no_security = MockService()
            result = service_no_security.read_file("/any/path")
            assert result == "Content of /any/path"
    
    def test_secure_path_access_decorator_with_multiple_args(self):
        """Test decorator with methods that have multiple arguments."""
        
        class MockService:
            def __init__(self, security_manager=None):
                self.security_manager = security_manager
            
            @secure_path_access
            def copy_file(self, source_path, dest_path):
                # Only first path is validated by decorator
                return f"Copy {source_path} to {dest_path}"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            service = MockService(security_manager=manager)
            
            # First path is validated
            with pytest.raises(SecurityException):
                service.copy_file("../../../etc/passwd", "safe.txt")
            
            # If first path is safe, call proceeds
            valid_path = project_root / "source.txt"
            valid_path.write_text("content")
            
            result = service.copy_file(str(valid_path), "../../../etc/passwd")
            # Note: decorator only validates first path argument
            assert "Copy" in result
    
    def test_security_manager_is_valid_project_root(self):
        """Test project root validation with various indicators."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            
            # Initially not valid (empty directory)
            assert not manager.is_valid_project_root()
            
            # Test various project indicators
            indicators = [
                ".git",
                "setup.py",
                "pyproject.toml",
                "package.json",
                "Cargo.toml",
                "go.mod",
                "pom.xml",
                "build.gradle",
                "CMakeLists.txt",
                "Makefile",
                "requirements.txt",
                "README.md",
            ]
            
            for indicator in indicators:
                # Create indicator
                if indicator == ".git":
                    (project_root / indicator).mkdir()
                else:
                    (project_root / indicator).write_text("test")
                
                # Should now be valid
                assert manager.is_valid_project_root()
                
                # Clean up for next test
                if (project_root / indicator).is_dir():
                    (project_root / indicator).rmdir()
                else:
                    (project_root / indicator).unlink()
            
            # Test with source files
            (project_root / "main.py").write_text("print('hello')")
            assert manager.is_valid_project_root()
            (project_root / "main.py").unlink()
            
            # Test with nested source files
            (project_root / "src").mkdir()
            (project_root / "src" / "app.js").write_text("console.log('hello')")
            assert manager.is_valid_project_root()
    
    def test_security_manager_excluded_dirs(self):
        """Test that excluded directories are properly handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            
            # Create excluded directories
            excluded = [
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
                ".pytest_cache",
            ]
            
            for dir_name in excluded:
                excluded_dir = project_root / dir_name
                excluded_dir.mkdir()
                
                # Files in excluded directories should not be safe
                test_file = excluded_dir / "test.py"
                test_file.write_text("test")
                
                assert not manager.is_safe_path(test_file)
                
                # Even with subdirectories
                subdir = excluded_dir / "subdir"
                subdir.mkdir()
                sub_file = subdir / "file.txt"
                sub_file.write_text("test")
                
                assert not manager.is_safe_path(sub_file)
    
    def test_security_manager_list_files_filtering(self):
        """Test that list_files properly filters unsafe files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            
            # Create various files
            (project_root / "safe.py").write_text("# Safe")
            (project_root / ".env").write_text("SECRET=123")
            (project_root / "config.json").write_text("{}")
            (project_root / "private.key").write_text("key")
            
            # Create excluded directory with files
            cache_dir = project_root / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "module.pyc").write_text("bytecode")
            
            # List all files
            all_files = manager.list_files(project_root, "*")
            file_names = [f.name for f in all_files]
            
            # Should include safe files
            assert "safe.py" in file_names
            assert "config.json" in file_names
            
            # Should exclude forbidden patterns
            assert ".env" not in file_names
            assert "private.key" not in file_names
            
            # Should exclude files in excluded dirs
            assert "module.pyc" not in file_names
            
            # Test with specific patterns
            py_files = manager.list_files(project_root, "*.py")
            assert len(py_files) == 1
            assert py_files[0].name == "safe.py"
    
    def test_security_exception_messages(self):
        """Test that security exceptions have helpful messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            
            # Test various invalid paths
            test_cases = [
                ("../../../etc/passwd", "Access to path"),
                ("/etc/passwd", "Access to path"),
                (".env", "Access to path"),
            ]
            
            for path, expected_in_message in test_cases:
                with pytest.raises(SecurityException) as exc_info:
                    manager.validate_path(path)
                
                assert expected_in_message in str(exc_info.value)
                assert path in str(exc_info.value)
    
    def test_security_manager_write_file_creates_directories(self):
        """Test that write_file creates parent directories safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            
            # Write to nested path that doesn't exist
            nested_file = project_root / "new" / "sub" / "dir" / "file.txt"
            manager.write_file(nested_file, "content")
            
            assert nested_file.exists()
            assert nested_file.read_text() == "content"
            
            # Try to create directories outside project (should fail)
            with pytest.raises(SecurityException):
                manager.write_file("../new_dir/file.txt", "content")
    
    def test_forbidden_patterns_case_variations(self):
        """Test that forbidden patterns handle case variations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            
            # Test case variations of forbidden files
            forbidden_variations = [
                ".env", ".ENV", ".Env",
                "secret.key", "SECRET.KEY", "Secret.Key",
                "id_rsa", "ID_RSA", "Id_Rsa",
                ".aws/credentials", ".AWS/credentials", ".Aws/Credentials",
            ]
            
            for path in forbidden_variations:
                # Create parent directories if needed
                file_path = project_root / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text("forbidden")
                
                # Should be caught regardless of case
                assert not manager.is_safe_path(file_path)
    
    def test_path_resolution_edge_cases(self):
        """Test edge cases in path resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            manager = SecurityManager(project_root)
            
            # Test empty string
            assert not manager.is_safe_path("")
            
            # Test None (should raise appropriate error)
            with pytest.raises((TypeError, AttributeError)):
                manager.is_safe_path(None)
            
            # Test bytes path (Path should handle this)
            try:
                bytes_path = str(project_root / "test.txt").encode('utf-8')
                # This might work or raise TypeError depending on Path implementation
                manager.is_safe_path(bytes_path)
            except TypeError:
                # Expected on some Python versions
                pass