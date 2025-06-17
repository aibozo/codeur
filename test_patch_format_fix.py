#!/usr/bin/env python3
"""
Test to identify and fix patch format issues.
"""

import tempfile
from pathlib import Path
import subprocess

def test_patch_formats():
    """Test different patch format issues."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create test file
        test_file = repo_path / "math_utils.py"
        test_file.write_text("""def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
""")
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True)
        
        print("=== Testing Different Patch Formats ===\n")
        
        # Test 1: Patch from the LLM (problematic)
        print("Test 1: LLM-generated patch (missing newline at end)")
        patch1 = """--- a/math_utils.py
+++ b/math_utils.py
@@ -3,4 +3,7 @@
 def subtract(a, b):
     return a - b
 
+def multiply(a, b):
+    return a * b
+"""  # Note: no trailing newline after last +
        
        test_patch(repo_path, patch1, "patch1_no_final_newline.patch")
        
        # Test 2: Add trailing newline
        print("\nTest 2: With trailing newline")
        patch2 = patch1 + "\n"
        test_patch(repo_path, patch2, "patch2_with_newline.patch")
        
        # Test 3: Add space after @@ line
        print("\nTest 3: With context after @@ line")
        patch3 = """--- a/math_utils.py
+++ b/math_utils.py
@@ -3,4 +3,7 @@ def subtract(a, b):
     return a - b
 
+def multiply(a, b):
+    return a * b
+
"""
        test_patch(repo_path, patch3, "patch3_with_context.patch")
        
        # Test 4: Proper git diff format
        print("\nTest 4: Full git diff format")
        patch4 = """diff --git a/math_utils.py b/math_utils.py
index 1234567..abcdef0 100644
--- a/math_utils.py
+++ b/math_utils.py
@@ -3,4 +3,7 @@
 def subtract(a, b):
     return a - b
 
+def multiply(a, b):
+    return a * b
+
"""
        test_patch(repo_path, patch4, "patch4_full_git.patch")
        
        # Test 5: Context lines must have space prefix
        print("\nTest 5: Proper context line prefixes")
        patch5 = """--- a/math_utils.py
+++ b/math_utils.py
@@ -3,4 +3,7 @@
 def subtract(a, b):
     return a - b
 
+def multiply(a, b):
+    return a * b
+
"""
        test_patch(repo_path, patch5, "patch5_space_prefix.patch")
        
        # Generate real patch for comparison
        print("\nTest 6: Real git-generated patch")
        
        # Make the change
        new_content = test_file.read_text() + "\ndef multiply(a, b):\n    return a * b\n"
        test_file.write_text(new_content)
        
        # Generate patch with git
        result = subprocess.run(
            ["git", "diff", "math_utils.py"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        real_patch = result.stdout
        print("Real git patch:")
        print(real_patch)
        print("\nAnalyzing real patch...")
        analyze_patch_details(real_patch)


def test_patch(repo_path, patch_content, filename):
    """Test applying a patch."""
    patch_file = repo_path / filename
    patch_file.write_text(patch_content)
    
    result = subprocess.run(
        ["git", "apply", "--check", filename],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✓ {filename}: Valid patch")
    else:
        print(f"✗ {filename}: {result.stderr.strip()}")
        
        # Try verbose for more info
        result2 = subprocess.run(
            ["git", "apply", "--verbose", "--check", filename],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if result2.stderr and result2.stderr != result.stderr:
            print(f"  Details: {result2.stderr.strip()}")


def analyze_patch_details(patch):
    """Analyze patch character by character."""
    lines = patch.split('\n')
    print(f"Total lines: {len(lines)}")
    print(f"Last line empty: {lines[-1] == ''}")
    
    # Check each line
    for i, line in enumerate(lines[:10]):  # First 10 lines
        if line.startswith(('---', '+++', '@@', 'diff')):
            print(f"Line {i}: Header: {repr(line)}")
        elif line.startswith('+'):
            print(f"Line {i}: Add: {repr(line)}")
        elif line.startswith('-'):
            print(f"Line {i}: Remove: {repr(line)}")
        elif line.startswith(' '):
            print(f"Line {i}: Context: {repr(line)}")
        else:
            print(f"Line {i}: Other: {repr(line)}")


if __name__ == "__main__":
    test_patch_formats()