#!/usr/bin/env python3
"""
Test with a working patch approach.
"""

import sys
import os
import subprocess
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


def test_with_exact_content():
    """Test with exact file content."""
    
    setup_logging(logging.WARNING)
    
    print("=== Testing with Exact Content ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # Get exact content from file
    api_file = repo_path / "src" / "api_client.py"
    original_content = api_file.read_text()
    
    print("Original file content around get_user:")
    lines = original_content.split('\n')
    for i, line in enumerate(lines):
        if 'def get_user' in line:
            # Show context
            start = max(0, i - 2)
            end = min(len(lines), i + 5)
            for j in range(start, end):
                print(f"{j+1:3}: {lines[j]}")
            break
    
    # Create a manual patch that should work
    print("\n\nCreating manual patch...")
    
    manual_patch = """--- a/src/api_client.py
+++ b/src/api_client.py
@@ -11,7 +11,7 @@ class APIClient:
     
     def get_user(self, user_id):
-        \"\"\"Get user by ID.\"\"\"
+        \"\"\"Fetch user data from the API endpoint.\"\"\"
         response = requests.get(f"{self.base_url}/users/{user_id}")
         return response.json()
     """
    
    print("Manual patch:")
    print(manual_patch)
    
    # Test applying it
    print("\nTesting manual patch...")
    
    # Save patch to file
    patch_file = Path("/tmp/test.patch")
    patch_file.write_text(manual_patch)
    
    # Try to apply
    result = subprocess.run(
        ["git", "apply", "--check", str(patch_file)],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ Manual patch is valid!")
        
        # Actually apply it
        subprocess.run(["git", "checkout", "master"], cwd=repo_path)
        subprocess.run(["git", "checkout", "-b", "test-manual"], cwd=repo_path)
        
        apply_result = subprocess.run(
            ["git", "apply", str(patch_file)],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if apply_result.returncode == 0:
            print("✓ Successfully applied!")
            
            # Show the change
            diff = subprocess.run(
                ["git", "diff"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            print("\nResulting diff:")
            print(diff.stdout)
            
            # Clean up
            subprocess.run(["git", "checkout", "master"], cwd=repo_path)
            subprocess.run(["git", "branch", "-D", "test-manual"], cwd=repo_path)
    else:
        print(f"✗ Manual patch failed: {result.stderr}")


def create_file_rewrite_agent():
    """Create an alternative that rewrites files instead of patches."""
    
    print("\n\n=== Alternative: File Rewrite Approach ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    api_file = repo_path / "src" / "api_client.py"
    
    # Read current content
    content = api_file.read_text()
    
    # Simple string replacement
    new_content = content.replace(
        '"""Get user by ID."""',
        '"""Fetch user data from the API endpoint."""'
    )
    
    if new_content != content:
        print("✓ File rewrite approach works!")
        print("\nChange preview:")
        
        # Show diff
        import difflib
        diff = difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="a/src/api_client.py",
            tofile="b/src/api_client.py",
            n=3
        )
        print(''.join(diff))
        
        # This approach avoids patch parsing issues entirely
        print("\n💡 File rewrite approach avoids patch format issues!")
    else:
        print("✗ No changes made")


if __name__ == "__main__":
    test_with_exact_content()
    create_file_rewrite_agent()