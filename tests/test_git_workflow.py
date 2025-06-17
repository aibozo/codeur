"""
Comprehensive tests for Git Workflow system.

Tests the GitWorkflow, GitSafetyGuard, and GitVisualizer components
to ensure proper functionality of the Git management system.
"""

import pytest
import tempfile
import shutil
import os
import subprocess
from pathlib import Path
from datetime import datetime
import json

from src.core.git_workflow import (
    GitWorkflow, BranchNamingConfig, CommitType, MergeStrategy,
    BranchType, CommitMetadata, Checkpoint
)
from src.core.git_safety_guard import (
    GitSafetyGuard, CheckType, CheckSeverity, CheckResult
)
from src.ui.git_visualizer import GitVisualizer, NodeType
from src.core.logging import get_logger

logger = get_logger(__name__)


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Initialize git repo
        subprocess.run(['git', 'init', '-b', 'main'], cwd=repo_path, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path)
        
        # Create initial commit
        readme = repo_path / "README.md"
        readme.write_text("# Test Project\n\nThis is a test project.")
        subprocess.run(['git', 'add', '.'], cwd=repo_path)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path)
        
        yield repo_path


@pytest.fixture
def git_workflow(temp_git_repo):
    """Create a GitWorkflow instance with a test repo."""
    return GitWorkflow(
        repo_path=str(temp_git_repo),
        naming_config=BranchNamingConfig()
    )


@pytest.fixture
def git_safety_guard(temp_git_repo):
    """Create a GitSafetyGuard instance with a test repo."""
    return GitSafetyGuard(str(temp_git_repo))


@pytest.fixture
def git_visualizer(temp_git_repo):
    """Create a GitVisualizer instance with a test repo."""
    return GitVisualizer(str(temp_git_repo))


class TestGitWorkflow:
    """Test GitWorkflow functionality."""
    
    def test_initialize_session(self, git_workflow):
        """Test session initialization creates working branch."""
        working_branch = git_workflow.initialize_session(user_id="test-user")
        
        assert working_branch is not None
        assert working_branch.startswith("working/session-")
        assert "test-user" in working_branch
        assert git_workflow.session_id is not None
        assert git_workflow.working_branch == working_branch
        
        # Check that we're on the working branch
        current_branch = git_workflow.git_ops.get_current_branch()
        assert current_branch == working_branch
        
        # Check that initial checkpoint was created
        assert len(git_workflow.checkpoints) == 1
        assert git_workflow.checkpoints[0].description == "session-start"
        
    def test_create_task_branch(self, git_workflow):
        """Test task branch creation."""
        # Initialize session first
        git_workflow.initialize_session()
        
        # Create task branch
        task_id = "test-123"
        description = "Add user authentication"
        task_branch = git_workflow.create_task_branch(task_id, description)
        
        assert task_branch is not None
        assert task_branch.startswith(f"task/{task_id}/")
        assert "add-user-authentication" in task_branch
        assert task_id in git_workflow.active_tasks
        
        # Check that we're on the task branch
        current_branch = git_workflow.git_ops.get_current_branch()
        assert current_branch == task_branch
        
    def test_commit_task(self, git_workflow, temp_git_repo):
        """Test atomic commit creation."""
        # Initialize and create task branch
        git_workflow.initialize_session()
        task_id = "test-456"
        git_workflow.create_task_branch(task_id, "Test task")
        
        # Make changes
        test_file = temp_git_repo / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")
        
        # Create commit metadata
        metadata = CommitMetadata(
            task_id=task_id,
            agent_type="test_agent",
            description="Added hello function",
            files_modified=["test.py"],
            test_status="passed"
        )
        
        # Commit the task
        commit_sha = git_workflow.commit_task(task_id, metadata)
        
        assert commit_sha is not None
        
        # Verify commit message format
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=%B'],
            cwd=temp_git_repo,
            capture_output=True,
            text=True
        )
        commit_message = result.stdout.strip()
        
        assert f"[TASK-{task_id}]" in commit_message
        assert "Agent: test_agent" in commit_message
        assert "Files: test.py" in commit_message
        assert "Tests: passed" in commit_message
        
    def test_merge_task_to_working(self, git_workflow, temp_git_repo):
        """Test merging task branch back to working branch."""
        # Initialize and create task
        git_workflow.initialize_session()
        task_id = "test-789"
        git_workflow.create_task_branch(task_id, "Test merge")
        
        # Make changes and commit
        test_file = temp_git_repo / "merge_test.py"
        test_file.write_text("# Merge test file\n")
        
        metadata = CommitMetadata(
            task_id=task_id,
            agent_type="test_agent",
            description="Test merge",
            files_modified=["merge_test.py"]
        )
        git_workflow.commit_task(task_id, metadata)
        
        # Merge back to working
        success, message = git_workflow.merge_task_to_working(task_id)
        
        assert success is True
        assert "Successfully merged" in message
        assert task_id not in git_workflow.active_tasks  # Task should be removed
        
        # Verify we're on working branch
        current_branch = git_workflow.git_ops.get_current_branch()
        assert current_branch == git_workflow.working_branch
        
        # Verify file exists on working branch
        assert test_file.exists()
        
    def test_checkpoint_creation_and_restoration(self, git_workflow, temp_git_repo):
        """Test checkpoint creation and restoration."""
        # Initialize session
        git_workflow.initialize_session()
        
        # Make some changes
        file1 = temp_git_repo / "checkpoint_test.txt"
        file1.write_text("Before checkpoint")
        subprocess.run(['git', 'add', '.'], cwd=temp_git_repo)
        subprocess.run(['git', 'commit', '-m', 'Before checkpoint'], cwd=temp_git_repo)
        
        # Create checkpoint
        checkpoint = git_workflow.create_checkpoint("test-checkpoint")
        
        assert checkpoint is not None
        assert checkpoint.description == "test-checkpoint"
        assert checkpoint.branch_name.startswith("checkpoint/")
        
        # Make more changes
        file1.write_text("After checkpoint")
        subprocess.run(['git', 'add', '.'], cwd=temp_git_repo)
        subprocess.run(['git', 'commit', '-m', 'After checkpoint'], cwd=temp_git_repo)
        
        # Restore checkpoint
        success = git_workflow.restore_checkpoint(checkpoint.id)
        
        assert success is True
        
        # Verify content was restored
        assert file1.read_text() == "Before checkpoint"
        
    def test_task_reversion(self, git_workflow, temp_git_repo):
        """Test reverting a task."""
        # Initialize and create task
        git_workflow.initialize_session()
        task_id = "revert-test"
        git_workflow.create_task_branch(task_id, "Test revert")
        
        # Make changes and commit
        test_file = temp_git_repo / "revert_test.py"
        test_file.write_text("# This will be reverted\n")
        
        metadata = CommitMetadata(
            task_id=task_id,
            agent_type="test_agent",
            description="Test revert",
            files_modified=["revert_test.py"]
        )
        git_workflow.commit_task(task_id, metadata)
        
        # Merge to working
        git_workflow.merge_task_to_working(task_id)
        
        # Revert the task
        success = git_workflow.revert_task(task_id, cascade=False)
        
        assert success is True
        
        # Verify file was reverted
        assert not test_file.exists()
        
    def test_selective_file_reversion(self, git_workflow, temp_git_repo):
        """Test reverting specific files from a task."""
        # Initialize and create task
        git_workflow.initialize_session()
        task_id = "selective-revert"
        git_workflow.create_task_branch(task_id, "Test selective revert")
        
        # Make changes to multiple files
        file1 = temp_git_repo / "keep_this.py"
        file2 = temp_git_repo / "revert_this.py"
        
        file1.write_text("# Keep this file\n")
        file2.write_text("# Revert this file\n")
        
        metadata = CommitMetadata(
            task_id=task_id,
            agent_type="test_agent",
            description="Multiple files",
            files_modified=["keep_this.py", "revert_this.py"]
        )
        git_workflow.commit_task(task_id, metadata)
        git_workflow.merge_task_to_working(task_id)
        
        # Selectively revert one file
        success = git_workflow.revert_task_files(task_id, ["revert_this.py"])
        
        assert success is True
        assert file1.exists()  # Should still exist
        assert not file2.exists()  # Should be reverted
        
    def test_get_task_history(self, git_workflow, temp_git_repo):
        """Test retrieving task history."""
        # Initialize and create some tasks
        git_workflow.initialize_session()
        
        # Create multiple tasks
        for i in range(3):
            task_id = f"task-{i}"
            git_workflow.create_task_branch(task_id, f"Task {i}")
            
            file = temp_git_repo / f"file{i}.py"
            file.write_text(f"# Task {i}\n")
            
            metadata = CommitMetadata(
                task_id=task_id,
                agent_type="test_agent",
                description=f"Task {i} implementation",
                files_modified=[f"file{i}.py"]
            )
            git_workflow.commit_task(task_id, metadata)
            git_workflow.merge_task_to_working(task_id)
        
        # Get history
        history = git_workflow.get_task_history()
        
        assert len(history) >= 3
        
        # Verify task IDs are in history
        task_ids = [h["task_id"] for h in history]
        assert "task-0" in task_ids
        assert "task-1" in task_ids
        assert "task-2" in task_ids
        
    def test_gitless_mode(self):
        """Test that gitless mode skips all git operations."""
        workflow = GitWorkflow(
            repo_path="/tmp/fake",
            gitless_mode=True
        )
        
        # All operations should return success/None without doing anything
        assert workflow.initialize_session() is None
        assert workflow.create_task_branch("test", "desc") is None
        assert workflow.commit_task("test", CommitMetadata(
            task_id="test",
            agent_type="test",
            description="test",
            files_modified=[]
        )) is None
        
        success, msg = workflow.merge_task_to_working("test")
        assert success is True
        
    @pytest.mark.asyncio
    async def test_async_methods(self, git_workflow, temp_git_repo):
        """Test async wrapper methods."""
        # Test async session start
        session_id = "async-test"
        branch = await git_workflow.start_session(session_id, "test-user")
        assert branch is not None
        assert git_workflow.session_id == session_id
        
        # Test async task branch creation
        task_branch = await git_workflow.create_task_branch_async("async-task", "Async test")
        assert task_branch is not None
        
        # Make a commit on the task branch before merging
        test_file = temp_git_repo / "async_test.py"
        test_file.write_text("# Async test file\n")
        
        metadata = CommitMetadata(
            task_id="async-task",
            agent_type="test_agent",
            description="Async test commit",
            files_modified=["async_test.py"]
        )
        commit_sha = git_workflow.commit_task("async-task", metadata)
        assert commit_sha is not None
        
        # Test async merge - should now succeed
        success, msg = await git_workflow.merge_task_to_working_async("async-task")
        assert success is True
        assert isinstance(msg, str)
        assert "Successfully merged" in msg


class TestGitSafetyGuard:
    """Test GitSafetyGuard functionality."""
    
    def test_secret_detection(self, git_safety_guard, temp_git_repo):
        """Test detection of secrets in files."""
        # Create file with secret
        secret_file = temp_git_repo / "config.py"
        secret_file.write_text("""
API_KEY = "sk1234567890abcdef1234567890abcdef"
PASSWORD = "super_secret_password_123"
normal_var = "this is fine"
""")
        
        # Run checks
        results = git_safety_guard._check_secrets([str(secret_file)])
        
        # Should find secrets
        failed_checks = [r for r in results if not r.passed]
        assert len(failed_checks) >= 2
        
        # Verify detected secrets
        for result in failed_checks:
            assert result.check_type == CheckType.SECRET_SCAN
            assert result.severity == CheckSeverity.CRITICAL
            assert "secret" in result.message.lower() or "api" in result.message.lower()
            
    def test_file_size_check(self, git_safety_guard, temp_git_repo):
        """Test detection of large files."""
        # Create large file
        large_file = temp_git_repo / "large.bin"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))  # 11MB
        
        # Create normal file
        normal_file = temp_git_repo / "normal.txt"
        normal_file.write_text("Normal size file")
        
        # Run checks
        results = git_safety_guard._check_file_sizes([
            str(large_file),
            str(normal_file)
        ])
        
        # Should flag large file
        failed_checks = [r for r in results if not r.passed]
        assert len(failed_checks) == 1
        assert "too large" in failed_checks[0].message
        
    def test_syntax_check(self, git_safety_guard, temp_git_repo):
        """Test Python syntax checking."""
        # Create file with syntax error
        bad_file = temp_git_repo / "bad_syntax.py"
        bad_file.write_text("""
def broken_function(
    print("missing closing paren"
""")
        
        # Create file with good syntax
        good_file = temp_git_repo / "good_syntax.py"
        good_file.write_text("""
def working_function():
    print("all good")
""")
        
        # Run checks
        results = git_safety_guard._check_syntax([
            str(bad_file),
            str(good_file)
        ])
        
        # Should find syntax error
        failed_checks = [r for r in results if not r.passed]
        assert len(failed_checks) == 1
        assert "syntax error" in failed_checks[0].message.lower()
        
    def test_forbidden_extensions(self, git_safety_guard, temp_git_repo):
        """Test detection of forbidden file extensions."""
        # Create forbidden file
        exe_file = temp_git_repo / "malware.exe"
        exe_file.write_bytes(b"fake exe")
        
        # Run checks
        results = git_safety_guard._check_file_sizes([str(exe_file)])
        
        # Should flag forbidden extension
        failed_checks = [r for r in results if not r.passed]
        assert len(failed_checks) == 1
        assert "forbidden file type" in failed_checks[0].message.lower()
        
    def test_run_pre_commit_checks(self, git_safety_guard, temp_git_repo):
        """Test full pre-commit check suite."""
        # Create test files
        python_file = temp_git_repo / "test.py"
        python_file.write_text("""
def hello():
    return "world"
""")
        
        # Run all pre-commit checks
        results = git_safety_guard.run_pre_commit_checks([str(python_file)])
        
        # Should have multiple check results
        assert len(results) > 0
        
        # Group by check type
        by_type = {}
        for result in results:
            by_type.setdefault(result.check_type, []).append(result)
        
        # Verify we ran different types of checks
        assert CheckType.SECRET_SCAN in by_type
        assert CheckType.FILE_SIZE in by_type
        assert CheckType.SYNTAX_CHECK in by_type
        
    def test_format_results(self, git_safety_guard):
        """Test result formatting."""
        # Create sample results
        results = [
            CheckResult(
                check_type=CheckType.SECRET_SCAN,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message="Found API key in config.py",
                fixable=False
            ),
            CheckResult(
                check_type=CheckType.SYNTAX_CHECK,
                passed=True,
                severity=CheckSeverity.INFO,
                message="Syntax check passed"
            ),
            CheckResult(
                check_type=CheckType.CODE_QUALITY,
                passed=False,
                severity=CheckSeverity.WARNING,
                message="Line too long",
                fixable=True,
                fix_command="ruff check --fix"
            )
        ]
        
        # Format results
        formatted = git_safety_guard.format_results(results)
        
        # Verify formatting
        assert "Git Safety Check Results" in formatted
        assert "CRITICAL:" in formatted
        assert "WARNING:" in formatted
        assert "INFO:" in formatted
        assert "1/3 checks passed" in formatted
        assert "Fix: ruff check --fix" in formatted


class TestGitVisualizer:
    """Test GitVisualizer functionality."""
    
    def test_generate_graph(self, git_visualizer, git_workflow, temp_git_repo):
        """Test graph generation."""
        # Create some commits
        git_workflow.initialize_session()
        
        # Create a task
        task_id = "viz-test"
        git_workflow.create_task_branch(task_id, "Viz test")
        
        file = temp_git_repo / "viz_test.py"
        file.write_text("# Visualization test\n")
        
        metadata = CommitMetadata(
            task_id=task_id,
            agent_type="test_agent",
            description="Viz test",
            files_modified=["viz_test.py"]
        )
        git_workflow.commit_task(task_id, metadata)
        git_workflow.merge_task_to_working(task_id)
        
        # Generate graph
        graph = git_visualizer.generate_graph(max_commits=10)
        
        assert graph is not None
        assert len(graph.nodes) > 0
        assert graph.current_branch is not None
        
        # Verify we have the task commit
        task_nodes = [n for n in graph.nodes.values() if n.task_id == task_id]
        assert len(task_nodes) > 0
        
    def test_get_graph_data_json(self, git_visualizer, git_workflow, temp_git_repo):
        """Test JSON data generation for frontend."""
        # Create some activity
        git_workflow.initialize_session()
        git_workflow.create_checkpoint("test-checkpoint")
        
        # Get JSON data
        data = git_visualizer.get_graph_data_json(max_commits=10)
        
        assert "nodes" in data
        assert "edges" in data
        assert "branches" in data
        assert "checkpoints" in data
        assert "stats" in data
        
        # Verify stats
        assert data["stats"]["totalCommits"] > 0
        assert data["stats"]["totalCheckpoints"] > 0
        
        # Verify JSON serializable
        json_str = json.dumps(data)
        assert len(json_str) > 0
        
    def test_get_compact_history(self, git_visualizer, git_workflow, temp_git_repo):
        """Test compact history generation."""
        # Create some activity
        git_workflow.initialize_session()
        
        # Get history
        history = git_visualizer.get_compact_history(max_items=10)
        
        assert isinstance(history, list)
        assert len(history) > 0
        
        # Verify history items
        for item in history:
            assert "id" in item
            assert "type" in item
            assert "icon" in item
            assert "title" in item
            assert "timestamp" in item
            assert "relativeTime" in item
            
    def test_render_terminal(self, git_visualizer, git_workflow):
        """Test terminal rendering."""
        # Create simple graph
        git_workflow.initialize_session()
        
        graph = git_visualizer.generate_graph(max_commits=5)
        
        # Render to terminal
        output = git_visualizer.render_terminal(graph)
        
        assert isinstance(output, str)
        assert len(output) > 0
        assert "Git History Visualization" in output
        assert "Current:" in output
        
    def test_render_html(self, git_visualizer, git_workflow):
        """Test HTML rendering."""
        # Create simple graph
        git_workflow.initialize_session()
        
        graph = git_visualizer.generate_graph(max_commits=5)
        
        # Render to HTML
        html = git_visualizer.render_html(graph)
        
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "vis.min.js" in html
        assert "gitGraph" in html
        
    def test_node_type_detection(self, git_visualizer, git_workflow, temp_git_repo):
        """Test correct detection of node types."""
        # Initialize
        git_workflow.initialize_session()
        
        # Create checkpoint
        checkpoint = git_workflow.create_checkpoint("test-checkpoint")
        
        # Create task
        task_id = "type-test"
        git_workflow.create_task_branch(task_id, "Type test")
        
        file = temp_git_repo / "type_test.py"
        file.write_text("# Type test\n")
        
        metadata = CommitMetadata(
            task_id=task_id,
            agent_type="test_agent",
            description="Type test",
            files_modified=["type_test.py"]
        )
        git_workflow.commit_task(task_id, metadata)
        
        # Generate graph
        graph = git_visualizer.generate_graph(max_commits=20)
        
        # Find checkpoint node
        checkpoint_nodes = [n for n in graph.nodes.values() if n.is_checkpoint]
        assert len(checkpoint_nodes) > 0
        
        # Find task node
        task_nodes = [n for n in graph.nodes.values() if n.task_id == task_id]
        assert len(task_nodes) > 0
        assert task_nodes[0].node_type == NodeType.TASK


class TestIntegration:
    """Test integration between components."""
    
    def test_workflow_with_safety_checks(self, temp_git_repo):
        """Test workflow with safety checks enabled."""
        workflow = GitWorkflow(str(temp_git_repo))
        safety_guard = GitSafetyGuard(str(temp_git_repo))
        
        # Initialize
        workflow.initialize_session()
        
        # Create task
        task_id = "safety-test"
        workflow.create_task_branch(task_id, "Safety test")
        
        # Create file with potential issue
        test_file = temp_git_repo / "config.py"
        test_file.write_text("""
# This should pass safety checks
DATABASE_URL = "postgresql://localhost/mydb"
DEBUG = True
""")
        
        # Run safety checks before commit
        results = safety_guard.run_pre_commit_checks([str(test_file)])
        
        # Check results
        failed = [r for r in results if not r.passed and r.severity in [CheckSeverity.ERROR, CheckSeverity.CRITICAL]]
        
        # Should pass (no real secrets)
        assert len(failed) == 0
        
        # Commit if checks pass
        if len(failed) == 0:
            metadata = CommitMetadata(
                task_id=task_id,
                agent_type="test_agent",
                description="Config update",
                files_modified=["config.py"]
            )
            commit_sha = workflow.commit_task(task_id, metadata)
            assert commit_sha is not None
            
    def test_visualizer_with_workflow(self, temp_git_repo):
        """Test visualizer with actual workflow data."""
        workflow = GitWorkflow(str(temp_git_repo))
        visualizer = GitVisualizer(str(temp_git_repo))
        
        # Create some workflow activity
        workflow.initialize_session("test-user")
        
        # Create multiple tasks
        for i in range(3):
            task_id = f"task-{i}"
            workflow.create_task_branch(task_id, f"Feature {i}")
            
            file = temp_git_repo / f"feature{i}.py"
            file.write_text(f"# Feature {i} implementation\n")
            
            metadata = CommitMetadata(
                task_id=task_id,
                agent_type=f"agent_{i}",
                description=f"Implement feature {i}",
                files_modified=[f"feature{i}.py"]
            )
            workflow.commit_task(task_id, metadata)
            workflow.merge_task_to_working(task_id)
            
        # Create checkpoint
        workflow.create_checkpoint("after-features")
        
        # Get visualization data
        viz_data = visualizer.get_graph_data_json()
        
        # Verify data
        assert viz_data["stats"]["totalTasks"] >= 3
        assert viz_data["stats"]["totalCheckpoints"] >= 2  # Initial + created
        assert len(viz_data["tasks"]) >= 3
        
        # Verify task data
        task_ids = [t["id"] for t in viz_data["tasks"]]
        assert "task-0" in task_ids
        assert "task-1" in task_ids
        assert "task-2" in task_ids
        
        # Get activity history
        history = visualizer.get_compact_history()
        assert len(history) > 0
        
        # Verify different activity types
        activity_types = set(h["type"] for h in history)
        assert "checkpoint" in activity_types
        assert "task" in activity_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])