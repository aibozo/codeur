#!/usr/bin/env python3
"""
Comprehensive Demo: Git Workflow Integration

This example demonstrates the complete git workflow system integrated
with the multi-agent framework, showing:

1. Automatic session startup with working branch creation
2. Task branch creation for agent work
3. Atomic commits with safety checks
4. Branch merging and checkpoint creation
5. Visual git history and branch management

Run this example to see the full workflow in action.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.agent_factory import create_integrated_agent_system
from src.core.git_workflow import CommitType
from src.coding_agent.git_operations import GitOperations

async def setup_demo_repository():
    """Set up a demo git repository with some initial content."""
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="git_workflow_demo_"))
    print(f"📁 Created demo repository at: {temp_dir}")
    
    # Initialize git repository
    git_ops = GitOperations(str(temp_dir))
    git_ops._run_git(["init"])
    git_ops._run_git(["config", "user.name", "Demo User"])
    git_ops._run_git(["config", "user.email", "demo@example.com"])
    
    # Create initial project structure
    (temp_dir / "src").mkdir()
    (temp_dir / "tests").mkdir()
    
    # Create initial files
    (temp_dir / "README.md").write_text("""# Git Workflow Demo Project

This is a demonstration project for the integrated git workflow system.

## Features
- Automatic working branch management
- Task-based branching
- Atomic commits with safety checks
- Visual git history
""")
    
    (temp_dir / "src" / "__init__.py").write_text("")
    (temp_dir / "src" / "calculator.py").write_text("""
class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def add(self, a, b):
        \"\"\"Add two numbers.\"\"\"
        return a + b
    
    def subtract(self, a, b):
        \"\"\"Subtract two numbers.\"\"\"
        return a - b
""")
    
    (temp_dir / "tests" / "__init__.py").write_text("")
    (temp_dir / "tests" / "test_calculator.py").write_text("""
import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from calculator import Calculator

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()
    
    def test_add(self):
        self.assertEqual(self.calc.add(2, 3), 5)
    
    def test_subtract(self):
        self.assertEqual(self.calc.subtract(5, 3), 2)

if __name__ == '__main__':
    unittest.main()
""")
    
    # Create initial commit
    git_ops.stage_changes()
    git_ops.commit("Initial project setup")
    
    print("✅ Initial repository setup complete")
    return temp_dir

async def demonstrate_git_workflow():
    """Demonstrate the complete git workflow integration."""
    
    print("🚀 Git Workflow Integration Demo")
    print("=" * 50)
    
    # Step 1: Set up demo repository
    repo_path = await setup_demo_repository()
    
    try:
        # Step 2: Create integrated agent system
        print("\n📋 Step 2: Creating integrated agent system...")
        system = await create_integrated_agent_system(str(repo_path))
        
        factory = system["factory"]
        git_workflow = system["git_workflow"]
        agents = system["agents"]
        
        print(f"✅ Created {len(agents)} agents with git workflow integration")
        
        # Step 3: Start a working session
        print("\n🌿 Step 3: Starting working session...")
        working_branch = await factory.start_session(user_id="demo_user")
        print(f"✅ Started working session on branch: {working_branch}")
        
        # Show initial git status
        print("\n📊 Initial Git Status:")
        history = git_workflow.get_visual_history(5)
        print(history)
        
        # Step 4: Simulate coding agent work
        print("\n💻 Step 4: Simulating coding agent work...")
        coding_agent = agents.get("coding_agent")
        
        if coding_agent:
            # Create a task branch for new feature
            task_id = "calc_multiply_001"
            branch_name = await coding_agent.create_task_branch(
                task_id=task_id,
                description="Add multiply method to calculator"
            )
            print(f"✅ Created task branch: {branch_name}")
            
            # Simulate code changes
            calc_file = repo_path / "src" / "calculator.py"
            current_content = calc_file.read_text()
            new_content = current_content + """
    def multiply(self, a, b):
        \"\"\"Multiply two numbers.\"\"\"
        return a * b
"""
            calc_file.write_text(new_content)
            
            # Update test file
            test_file = repo_path / "tests" / "test_calculator.py"
            test_content = test_file.read_text()
            test_content = test_content.replace(
                "if __name__ == '__main__':",
                """    def test_multiply(self):
        self.assertEqual(self.calc.multiply(3, 4), 12)

if __name__ == '__main__':"""
            )
            test_file.write_text(test_content)
            
            print("✅ Simulated code changes (added multiply method)")
            
            # Commit the work with safety checks
            commit_sha = await coding_agent.commit_task_work(
                task_id=task_id,
                message="Add multiply method to Calculator class",
                commit_type="feature"
            )
            
            if commit_sha:
                print(f"✅ Created atomic commit: {commit_sha}")
            else:
                print("ℹ️ No changes to commit")
        
        # Step 5: Create another agent's work
        print("\n🧪 Step 5: Simulating test agent work...")
        
        # Create another task branch
        test_task_id = "calc_tests_002"
        test_branch = await git_workflow.create_task_branch(
            task_id=test_task_id,
            description="Add edge case tests",
            agent_id="test_agent"
        )
        print(f"✅ Created test task branch: {test_branch}")
        
        # Add more tests
        test_file = repo_path / "tests" / "test_calculator.py"
        test_content = test_file.read_text()
        test_content = test_content.replace(
            "if __name__ == '__main__':",
            """    def test_add_negative(self):
        self.assertEqual(self.calc.add(-1, 1), 0)
    
    def test_multiply_zero(self):
        self.assertEqual(self.calc.multiply(5, 0), 0)

if __name__ == '__main__':"""
        )
        test_file.write_text(test_content)
        
        # Commit test work
        test_commit = await git_workflow.commit_atomic(
            task_id=test_task_id,
            agent_id="test_agent",
            message="Add edge case tests for calculator",
            commit_type=CommitType.TEST
        )
        
        if test_commit:
            print(f"✅ Created test commit: {test_commit}")
        
        # Step 6: Create checkpoint
        print("\n📍 Step 6: Creating checkpoint...")
        checkpoint = await factory.create_checkpoint("Feature development complete")
        print(f"✅ Created checkpoint: {checkpoint['id']}")
        print(f"   Branch: {checkpoint['branch_name']}")
        print(f"   Description: {checkpoint['description']}")
        
        # Step 7: Show updated git history
        print("\n📊 Updated Git History:")
        history = git_workflow.get_visual_history(10)
        print(history)
        
        # Step 8: Demonstrate branch merging
        print("\n🔄 Step 8: Demonstrating branch merging...")
        
        # Merge the first task
        if coding_agent:
            merge_result = await git_workflow.merge_task_to_working(
                task_id=task_id,
                agent_id="coding_agent"
            )
            print(f"✅ Merge result for {task_id}: {merge_result}")
        
        # Step 9: Show final git state
        print("\n📊 Final Git State:")
        history = git_workflow.get_visual_history(15)
        print(history)
        
        # Step 10: Demonstrate safety checks
        print("\n🛡️ Step 10: Demonstrating safety checks...")
        
        # Create a file with syntax errors to test safety checks
        bad_file = repo_path / "src" / "bad_code.py"
        bad_file.write_text("""
# This file has syntax errors
def broken_function(
    # Missing closing parenthesis
    return "This will fail syntax check"
""")
        
        # Try to commit with safety checks
        safety_commit = await git_workflow.commit_atomic(
            task_id="safety_test_003",
            agent_id="demo_agent",
            message="Test commit with syntax errors",
            run_safety_checks=True
        )
        
        if safety_commit:
            print(f"⚠️ Commit created despite safety issues: {safety_commit}")
        else:
            print("ℹ️ No commit created due to safety checks")
        
        # Clean up bad file
        bad_file.unlink()
        
        print("\n🎉 Git Workflow Demo Complete!")
        print("=" * 50)
        
        print("\n📋 Summary of Demonstrated Features:")
        print("✅ Automatic working branch creation")
        print("✅ Task-based branching for agent work")
        print("✅ Atomic commits with rich metadata")
        print("✅ Safety checks (syntax validation, test detection)")
        print("✅ Branch merging and cleanup")
        print("✅ Checkpoint creation for save points")
        print("✅ Visual git history with task information")
        print("✅ Multi-agent coordination through git workflow")
        
        print(f"\n📁 Demo repository preserved at: {repo_path}")
        print("You can explore the git history with:")
        print(f"  cd {repo_path}")
        print("  git log --graph --oneline --all")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup would happen here in a real scenario
        # For demo purposes, we'll leave the repo for inspection
        pass

async def main():
    """Main demo function."""
    try:
        await demonstrate_git_workflow()
    except KeyboardInterrupt:
        print("\n\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())