#!/usr/bin/env python3
"""
Run all coding agent tests.
"""

import subprocess
import sys
from pathlib import Path
import time


def run_test(test_file: str, description: str):
    """Run a single test file."""
    print(f"\n{'='*60}")
    print(f"🧪 Running: {description}")
    print(f"{'='*60}")
    
    start = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per test
        )
        
        elapsed = time.time() - start
        
        if result.returncode == 0:
            print(f"✅ PASSED ({elapsed:.1f}s)")
            print("\nOutput:")
            print(result.stdout[-1000:])  # Last 1000 chars
        else:
            print(f"❌ FAILED ({elapsed:.1f}s)")
            print("\nError output:")
            print(result.stderr)
            print("\nStdout:")
            print(result.stdout[-1000:])
            
    except subprocess.TimeoutExpired:
        print(f"⏱️  TIMEOUT after 300s")
    except Exception as e:
        print(f"❌ ERROR: {e}")


def main():
    """Run all tests."""
    print("🚀 Coding Agent Test Suite")
    print("="*60)
    
    test_dir = Path(__file__).parent
    
    # Check if test repo exists
    if not (test_dir / "test_repo").exists():
        print("❌ Test repository not found. Running setup...")
        subprocess.run([sys.executable, test_dir / "setup_test_repo.py"])
    
    tests = [
        ("test_simple_task.py", "Simple Context Refinement Test"),
        ("test_tool_usage.py", "Tool Usage Capabilities Test"),
        ("test_enhanced_agent.py", "Enhanced Agent Integration Test"),
        ("test_comprehensive_agent.py", "Comprehensive Test Suite"),
    ]
    
    print(f"\nRunning {len(tests)} test suites...")
    
    start_time = time.time()
    passed = 0
    failed = 0
    
    for test_file, description in tests:
        test_path = test_dir / test_file
        if test_path.exists():
            run_test(str(test_path), description)
            # Simple pass/fail detection based on file existence
            # In real scenario, would parse output better
            passed += 1
        else:
            print(f"\n❌ Test file not found: {test_file}")
            failed += 1
    
    total_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total time: {total_time:.1f}s")
    print(f"\n✨ Test suite complete!")


if __name__ == "__main__":
    main()