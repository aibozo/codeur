"""
Demo script showing the Git workflow in action.

This demonstrates how the enhanced git workflow integrates with
the multi-agent system.
"""

import asyncio
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.git_workflow import GitWorkflow, CommitType, MergeStrategy
from src.core.git_safety_guard import GitSafetyGuard
from src.ui.git_visualizer import GitVisualizer
from src.core.logging import get_logger

logger = get_logger(__name__)


async def demo_git_workflow():
    """Demonstrate the complete git workflow."""
    
    # Create a temporary git repository for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Initialize git repo
        print(f"📁 Creating demo repository at {repo_path}")
        subprocess.run(['git', 'init'], cwd=repo_path, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Demo User'], cwd=repo_path)
        subprocess.run(['git', 'config', 'user.email', 'demo@example.com'], cwd=repo_path)
        
        # Create initial commit
        readme_file = repo_path / "README.md"
        readme_file.write_text("# Demo Project\n\nThis is a demo of the git workflow.")
        subprocess.run(['git', 'add', '.'], cwd=repo_path)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path)
        
        # Initialize our workflow components
        workflow = GitWorkflow(str(repo_path))
        safety_guard = GitSafetyGuard(str(repo_path))
        visualizer = GitVisualizer(str(repo_path))
        
        print("\n🚀 Starting Git Workflow Demo\n")
        
        # 1. Start a working session
        print("1️⃣ Starting a new working session...")
        session_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        working_branch = await workflow.start_session(session_id, "demo-user")
        print(f"   ✅ Created working branch: {working_branch}")
        
        # 2. Create task branches and make changes
        print("\n2️⃣ Creating task branches...")
        
        # Task 1: Add authentication
        task1_branch = await workflow.create_task_branch(
            "TASK-001",
            "add user authentication",
            "coding-agent"
        )
        print(f"   ✅ Created task branch: {task1_branch}")
        
        # Make changes for task 1
        auth_file = repo_path / "auth.py"
        auth_file.write_text("""
def authenticate(username, password):
    # Simple authentication
    return username == "admin" and password == "secret"
""")
        
        # Run safety checks
        print("\n3️⃣ Running pre-commit safety checks...")
        validation = await safety_guard.run_pre_commit_checks("coding-agent")
        print(f"   Checks passed: {validation.checks_passed}")
        print(f"   Checks failed: {validation.checks_failed}")
        print(f"   Can proceed: {validation.can_proceed}")
        
        # Commit task 1
        print("\n4️⃣ Creating atomic commit for task...")
        commit1 = await workflow.commit_atomic(
            "TASK-001",
            "coding-agent",
            "Add basic authentication module",
            CommitType.FEATURE
        )
        print(f"   ✅ Created commit: {commit1[:8]}")
        
        # Merge to working branch
        print("\n5️⃣ Merging task to working branch...")
        success, message = await workflow.merge_task_to_working(
            "TASK-001",
            "coding-agent",
            MergeStrategy.SQUASH
        )
        print(f"   ✅ Merge {'successful' if success else 'failed'}: {message}")
        
        # Create a checkpoint
        print("\n6️⃣ Creating checkpoint...")
        checkpoint = await workflow.create_checkpoint(
            "After authentication implementation"
        )
        print(f"   ✅ Created checkpoint: {checkpoint.id}")
        print(f"   Branch: {checkpoint.branch_name}")
        
        # Task 2: Add user management
        task2_branch = await workflow.create_task_branch(
            "TASK-002",
            "add user management",
            "coding-agent"
        )
        
        # Make changes for task 2
        users_file = repo_path / "users.py"
        users_file.write_text("""
class UserManager:
    def __init__(self):
        self.users = {}
    
    def add_user(self, username, password):
        self.users[username] = password
    
    def remove_user(self, username):
        del self.users[username]
""")
        
        # Commit task 2
        commit2 = await workflow.commit_atomic(
            "TASK-002",
            "coding-agent",
            "Add user management class",
            CommitType.FEATURE
        )
        
        # Merge task 2
        await workflow.merge_task_to_working("TASK-002", "coding-agent")
        
        # Visualize current state
        print("\n7️⃣ Visualizing git history...")
        graph = visualizer.generate_graph()
        visual = visualizer.render_terminal(graph)
        print(visual)
        
        # Demonstrate reversion
        print("\n8️⃣ Demonstrating task reversion...")
        print("   Reverting TASK-002...")
        revert_result = await workflow.revert_task("TASK-002", cascade=False)
        print(f"   ✅ Reversion {'successful' if revert_result.success else 'failed'}")
        print(f"   Affected files: {revert_result.affected_files}")
        
        # Show updated visualization
        print("\n9️⃣ Updated git history after reversion:")
        graph = visualizer.generate_graph()
        visual = visualizer.render_terminal(graph)
        print(visual)
        
        # Restore from checkpoint
        print("\n🔟 Restoring from checkpoint...")
        restore_success, restore_message = await workflow.restore_checkpoint(
            checkpoint.id,
            strategy="branch"
        )
        print(f"   ✅ Restore {'successful' if restore_success else 'failed'}: {restore_message}")
        
        # Generate HTML visualization
        print("\n📊 Generating HTML visualization...")
        html_path = repo_path / "git_history.html"
        html_content = visualizer.render_html(graph)
        html_path.write_text(html_content)
        print(f"   ✅ HTML visualization saved to: {html_path}")
        
        # Show agent activity
        print("\n📈 Agent Activity Summary:")
        activity = visualizer.get_agent_activity("coding-agent", days=1)
        print(f"   Total commits: {activity['total_commits']}")
        print(f"   Tasks completed: {activity['tasks_completed']}")
        print(f"   Checkpoints created: {activity['checkpoints_created']}")
        print(f"   Reverts: {activity['reverts']}")
        
        print("\n✨ Demo completed successfully!")


async def demo_safety_checks():
    """Demonstrate safety guard features."""
    print("\n🛡️ Safety Guard Demo\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=repo_path, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Demo User'], cwd=repo_path)
        subprocess.run(['git', 'config', 'user.email', 'demo@example.com'], cwd=repo_path)
        
        safety_guard = GitSafetyGuard(str(repo_path))
        
        # Test 1: Secret detection
        print("1️⃣ Testing secret detection...")
        secret_file = repo_path / "config.py"
        secret_file.write_text("""
API_KEY = "sk-1234567890abcdef1234567890abcdef"
PASSWORD = "super_secret_password"
""")
        subprocess.run(['git', 'add', '.'], cwd=repo_path)
        
        validation = await safety_guard.run_pre_commit_checks("test-agent")
        for result in validation.results:
            if result.check_name == "no_secrets":
                print(f"   ❌ {result.message}")
                if result.details:
                    for secret in result.details.get('secrets', [])[:2]:
                        print(f"      - {secret['file']}:{secret['line']} - {secret['pattern']}")
        
        # Test 2: Large file detection
        print("\n2️⃣ Testing large file detection...")
        large_file = repo_path / "large_data.bin"
        large_file.write_bytes(b'0' * (6 * 1024 * 1024))  # 6MB file
        subprocess.run(['git', 'add', 'large_data.bin'], cwd=repo_path)
        
        validation = await safety_guard.run_pre_commit_checks("test-agent")
        for result in validation.results:
            if result.check_name == "file_sizes":
                print(f"   ⚠️  {result.message}")
                if result.details:
                    for file_info in result.details.get('warning_files', []):
                        print(f"      - {file_info['file']}: {file_info['size_mb']}MB")
        
        # Test 3: Code quality
        print("\n3️⃣ Testing code quality checks...")
        bad_code = repo_path / "bad_code.py"
        bad_code.write_text("""
import os
import sys

def process_data(data):
    print("Debug: processing data")  # TODO: Remove this
    result = data * 2
    return result

# Missing docstring, unused imports
""")
        subprocess.run(['git', 'add', 'bad_code.py'], cwd=repo_path)
        
        validation = await safety_guard.run_pre_commit_checks("test-agent")
        for result in validation.results:
            if result.check_name in ["no_debug_code", "code_quality"]:
                print(f"   ⚠️  {result.message}")
                if result.auto_fixable:
                    print(f"      💡 Auto-fixable with: {result.fix_command}")


import subprocess

if __name__ == "__main__":
    print("🎯 Git Workflow Demo for Multi-Agent System\n")
    
    # Run main workflow demo
    asyncio.run(demo_git_workflow())
    
    # Run safety checks demo
    asyncio.run(demo_safety_checks())
    
    print("\n🎉 All demos completed!")