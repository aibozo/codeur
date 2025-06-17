#!/usr/bin/env python3
"""
Test script to analyze patch generation issues and context handling.
Tests both patch generation and file creation scenarios.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.abspath('.'))

from src.coding_agent.patch_generator import PatchGenerator
from src.coding_agent.models import CodeContext
from src.llm import LLMClient

def test_patch_context():
    """Test patch generation with different context scenarios."""
    
    print("=== PATCH CONTEXT ANALYSIS TEST ===\n")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Test 1: Create new file (no existing content)
        print("Test 1: Creating new file")
        print("-" * 50)
        
        context = CodeContext(
            task_goal="Create a simple calculator.py file with an add function"
        )
        
        # No file snippets since file doesn't exist
        print(f"Context task goal: {context.task_goal}")
        print(f"File snippets: {len(context.file_snippets)}")
        print(f"Context string preview:\n{context.to_prompt_context()[:500]}")
        
        # Initialize patch generator
        generator = PatchGenerator()
        
        # Generate patch for new file
        result = generator.generate_patch(context)
        
        print(f"\nPatch generation success: {result.success}")
        if result.patch_content:
            print(f"Patch preview (first 500 chars):\n{result.patch_content[:500]}")
            print(f"\nFiles to be modified: {result.files_modified}")
            
            # Analyze patch format
            analyze_patch_format(result.patch_content)
        else:
            print(f"Error: {result.error_message}")
        
        print("\n" + "="*50 + "\n")
        
        # Test 2: Modify existing file
        print("Test 2: Modifying existing file")
        print("-" * 50)
        
        # Create a test file
        test_file = repo_path / "math_utils.py"
        test_file.write_text("""def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
""")
        
        # Create context with file content
        context = CodeContext(
            task_goal="Add a multiply function to math_utils.py"
        )
        
        # Add file content with line numbers
        numbered_content = add_line_numbers(test_file.read_text())
        context.add_snippet("math_utils.py", numbered_content)
        
        print(f"Context task goal: {context.task_goal}")
        print(f"File snippets: {len(context.file_snippets)}")
        print(f"File content with line numbers:\n{numbered_content}")
        print(f"\nContext string preview:\n{context.to_prompt_context()[:500]}")
        
        # Generate patch
        result = generator.generate_patch(context)
        
        print(f"\nPatch generation success: {result.success}")
        if result.patch_content:
            print(f"Patch content:\n{result.patch_content}")
            
            # Analyze patch format
            analyze_patch_format(result.patch_content)
            
            # Try to apply patch
            test_patch_application(repo_path, result.patch_content)
        else:
            print(f"Error: {result.error_message}")
        
        print("\n" + "="*50 + "\n")
        
        # Test 3: Complex context with multiple files
        print("Test 3: Complex multi-file context")
        print("-" * 50)
        
        # Create another file
        main_file = repo_path / "main.py"
        main_file.write_text("""from math_utils import add, subtract

def main():
    result = add(5, 3)
    print(f"5 + 3 = {result}")

if __name__ == "__main__":
    main()
""")
        
        context = CodeContext(
            task_goal="Update main.py to use the multiply function"
        )
        
        # Add both files to context
        context.add_snippet("math_utils.py", add_line_numbers(test_file.read_text()))
        context.add_snippet("main.py", add_line_numbers(main_file.read_text()))
        
        print(f"Context task goal: {context.task_goal}")
        print(f"File snippets: {len(context.file_snippets)}")
        print(f"Total context size: {len(context.to_prompt_context())} chars")
        
        # Generate patch
        result = generator.generate_patch(context)
        
        print(f"\nPatch generation success: {result.success}")
        if result.patch_content:
            print(f"Patch preview (first 800 chars):\n{result.patch_content[:800]}")
            
            # Analyze patch format
            analyze_patch_format(result.patch_content)
        else:
            print(f"Error: {result.error_message}")


def add_line_numbers(content: str) -> str:
    """Add line numbers to content."""
    lines = content.split('\n')
    numbered_lines = []
    for i, line in enumerate(lines, 1):
        numbered_lines.append(f"{i:4d}: {line}")
    return '\n'.join(numbered_lines)


def analyze_patch_format(patch_content: str):
    """Analyze patch format for common issues."""
    print("\n--- Patch Format Analysis ---")
    
    lines = patch_content.split('\n')
    
    # Check for diff headers
    has_diff_header = any(line.startswith('diff --git') for line in lines)
    has_file_headers = any(line.startswith('---') or line.startswith('+++') for line in lines)
    has_hunks = any(line.startswith('@@') for line in lines)
    
    print(f"Has diff header: {has_diff_header}")
    print(f"Has file headers (---/+++): {has_file_headers}")
    print(f"Has hunk headers (@@): {has_hunks}")
    
    # Check line numbers in hunks
    hunk_count = 0
    for i, line in enumerate(lines):
        if line.startswith('@@'):
            hunk_count += 1
            print(f"Hunk {hunk_count} at line {i+1}: {line}")
            
            # Check if line numbers look reasonable
            import re
            match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', line)
            if match:
                old_start, old_count, new_start, new_count = map(int, match.groups())
                print(f"  Old: line {old_start}, {old_count} lines")
                print(f"  New: line {new_start}, {new_count} lines")
                
                # Check if the hunk content matches the counts
                content_lines = 0
                j = i + 1
                while j < len(lines) and not lines[j].startswith(('@@', 'diff', '---', '+++')):
                    if lines[j].startswith(('+', '-', ' ')):
                        content_lines += 1
                    j += 1
                print(f"  Actual content lines: {content_lines}")
    
    # Check for common issues
    print("\n--- Common Issues Check ---")
    
    # Check for line number prefixes in content
    content_with_line_nums = any(
        re.match(r'^[+\- ]\s*\d+:', line) 
        for line in lines 
        if line and line[0] in ['+', '-', ' ']
    )
    if content_with_line_nums:
        print("⚠️  WARNING: Patch content may include line numbers from context")
    
    # Check for incomplete patches
    if has_hunks and not has_file_headers:
        print("⚠️  WARNING: Has hunks but missing file headers")
    
    # Check for truncated patches
    if lines and lines[-1].startswith(('+', '-')) and len(lines[-1]) > 100:
        print("⚠️  WARNING: Last line might be truncated")


def test_patch_application(repo_path: Path, patch_content: str):
    """Test if patch can be applied."""
    print("\n--- Testing Patch Application ---")
    
    # Save patch to file
    patch_file = repo_path / "test.patch"
    patch_file.write_text(patch_content)
    
    # Try to apply with git
    import subprocess
    
    # First init git if needed
    if not (repo_path / ".git").exists():
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True)
    
    # Try to apply patch
    result = subprocess.run(
        ["git", "apply", "--check", "test.patch"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ Patch format is valid and can be applied")
    else:
        print(f"✗ Patch application failed: {result.stderr}")
        
        # Try with more lenient options
        result2 = subprocess.run(
            ["git", "apply", "--check", "--whitespace=fix", "test.patch"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if result2.returncode == 0:
            print("✓ Patch can be applied with whitespace fixes")
        else:
            # Try to get more details
            result3 = subprocess.run(
                ["git", "apply", "--verbose", "--check", "test.patch"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            print(f"Detailed error:\n{result3.stderr}")


if __name__ == "__main__":
    test_patch_context()