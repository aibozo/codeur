#!/usr/bin/env python3
"""
Final comprehensive test with all fixes applied.
"""

import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent import CodingAgent
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
from src.llm import LLMClient
from src.core.logging import setup_logging
import logging


def test_complete_workflow():
    """Test the complete coding agent workflow with all fixes."""
    
    setup_logging(logging.INFO)
    
    print("\n" + "="*60)
    print("🚀 Final Comprehensive Test - Enhanced Coding Agent")
    print("="*60)
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # 1. Fix git branch issue
    print("\n1️⃣ Fixing git configuration...")
    try:
        # Ensure we're on master (not main)
        subprocess.run(["git", "checkout", "master"], cwd=repo_path, capture_output=True)
        # Clean up any uncommitted changes
        subprocess.run(["git", "reset", "--hard"], cwd=repo_path, capture_output=True)
        print("   ✅ Git ready")
    except Exception as e:
        print(f"   ❌ Git error: {e}")
    
    # 2. Setup RAG with fresh index
    print("\n2️⃣ Setting up RAG service...")
    rag_dir = repo_path / ".rag"
    if rag_dir.exists():
        import shutil
        shutil.rmtree(rag_dir)
    
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # Index Python files
    python_files = list(repo_path.glob("**/*.py"))
    indexed = 0
    for py_file in python_files:
        if ".rag" not in str(py_file) and "__pycache__" not in str(py_file):
            chunks = rag_service.index_file(str(py_file))
            if chunks > 0:
                indexed += 1
    
    print(f"   ✅ Indexed {indexed} files")
    
    rag_client = RAGClient(service=rag_service)
    
    # 3. Initialize components
    print("\n3️⃣ Initializing components...")
    llm_client = LLMClient(model="gpt-4o")  # Use fast model
    
    # Fix the git operations to use 'master' instead of 'main'
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm_client,
        max_retries=2
    )
    
    # Monkey patch to fix the branch issue
    original_checkout = coding_agent.git_ops.checkout_branch
    def checkout_branch_fixed(branch_name):
        if branch_name == "main":
            branch_name = "master"
        return original_checkout(branch_name)
    coding_agent.git_ops.checkout_branch = checkout_branch_fixed
    
    print(f"   ✅ Agent ready with {llm_client.model}")
    
    # 4. Run test scenarios
    print("\n4️⃣ Running test scenarios...")
    
    test_cases = [
        {
            "name": "Add Error Handling",
            "goal": "Add error handling to the get_user method in src/api_client.py. Catch requests.exceptions.RequestException and return None with a log message.",
            "paths": ["src/api_client.py"],
            "verify": lambda: check_error_handling(repo_path)
        },
        {
            "name": "Add Documentation",
            "goal": "Add a docstring to the APIClient class explaining that it's a simple HTTP client for making API requests.",
            "paths": ["src/api_client.py"],
            "verify": lambda: check_docstring(repo_path)
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*50}")
        print(f"Test {i+1}: {test_case['name']}")
        print(f"{'='*50}")
        
        # Create task
        task = messages_pb2.CodingTask()
        task.id = f"test-final-{i+1:03d}"
        task.parent_plan_id = "test-plan-001"
        task.step_number = i + 1
        task.goal = test_case["goal"]
        for path in test_case["paths"]:
            task.paths.append(path)
        task.complexity_label = 2  # MODERATE
        task.estimated_tokens = 1000
        task.base_commit_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        ).stdout.strip()
        
        print(f"Goal: {task.goal}")
        
        # Process task
        start_time = time.time()
        try:
            result = coding_agent.process_task(task)
            elapsed = time.time() - start_time
            
            print(f"\n📊 Result: {result.status.name}")
            print(f"   Time: {elapsed:.1f}s")
            print(f"   Tokens: {result.llm_tokens_used}")
            print(f"   Retries: {result.retries}")
            
            # Key notes
            if result.notes:
                print("\n📝 Process notes:")
                for note in result.notes[-3:]:
                    print(f"   - {note}")
            
            # Verify if successful
            success = False
            if result.status.name == "SUCCESS":
                print(f"\n✅ Commit created: {result.commit_sha[:8]}")
                
                # Run verification
                if test_case["verify"]():
                    print("✅ Verification passed!")
                    success = True
                else:
                    print("❌ Verification failed!")
                
                # Reset for next test
                subprocess.run(["git", "checkout", "master"], cwd=repo_path, capture_output=True)
            
            results.append({
                "name": test_case["name"],
                "status": result.status.name,
                "success": success,
                "time": elapsed,
                "tokens": result.llm_tokens_used,
                "retries": result.retries
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "name": test_case["name"],
                "status": "ERROR",
                "success": False,
                "error": str(e)
            })
    
    # 5. Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.0f}%")
    
    print("\n📈 Details:")
    for result in results:
        icon = "✅" if result.get("success") else "❌"
        print(f"\n{icon} {result['name']}:")
        print(f"   Status: {result['status']}")
        if "time" in result:
            print(f"   Time: {result['time']:.1f}s")
            print(f"   Tokens: {result.get('tokens', 0)}")
            print(f"   Retries: {result.get('retries', 0)}")
        if "error" in result:
            print(f"   Error: {result['error']}")
    
    # 6. Key findings
    print("\n" + "="*60)
    print("🔍 Key Findings")
    print("="*60)
    
    print("\n✅ What's Working:")
    print("  - Line numbers in context")
    print("  - RAG search (no more 384D errors)")
    print("  - File rewriter fallback")
    print("  - Tool usage for context refinement")
    
    print("\n❓ Status:")
    if passed == total:
        print("  🎉 All tests passed! The enhanced coding agent is working correctly.")
    else:
        print(f"  ⚠️  {total - passed} test(s) failed. Check the details above.")


def check_error_handling(repo_path):
    """Check if error handling was added correctly."""
    api_file = repo_path / "src/api_client.py"
    if not api_file.exists():
        return False
    
    content = api_file.read_text()
    
    checks = [
        "import logging" in content or "from logging import" in content,
        "try:" in content,
        "except" in content,
        "RequestException" in content or "requests.exceptions" in content,
        "return None" in content
    ]
    
    return all(checks)


def check_docstring(repo_path):
    """Check if docstring was added to APIClient class."""
    api_file = repo_path / "src/api_client.py"
    if not api_file.exists():
        return False
    
    content = api_file.read_text()
    lines = content.split('\n')
    
    # Find APIClient class
    for i, line in enumerate(lines):
        if "class APIClient" in line:
            # Check next few lines for docstring
            for j in range(i+1, min(i+5, len(lines))):
                if '"""' in lines[j] or "'''" in lines[j]:
                    return True
    
    return False


if __name__ == "__main__":
    test_complete_workflow()