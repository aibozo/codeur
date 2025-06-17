#!/usr/bin/env python3
"""
Test fixing patch extraction to preserve context line spaces.
"""

import re

def extract_patch_original(llm_response: str) -> str:
    """Original extraction method that loses spaces."""
    # Look for diff blocks
    diff_pattern = r'```diff\n(.*?)```'
    matches = re.findall(diff_pattern, llm_response, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    # Try to find patch content without code blocks
    lines = llm_response.split('\n')
    patch_lines = []
    in_patch = False
    
    for line in lines:
        if line.strip() in ['```diff', '```']:
            continue
            
        if line.startswith(('---', '+++', '@@', 'diff --git')):
            in_patch = True
        
        if in_patch:
            if line.strip() and not line.startswith(('#', '//')):
                patch_lines.append(line)
            elif patch_lines and line.strip() == '':
                patch_lines.append(line)
    
    if patch_lines:
        return '\n'.join(patch_lines)
    
    return None


def extract_patch_fixed(llm_response: str) -> str:
    """Fixed extraction that preserves spaces."""
    # Look for diff blocks
    diff_pattern = r'```diff\n(.*?)```'
    matches = re.findall(diff_pattern, llm_response, re.DOTALL)
    
    if matches:
        # Don't strip - preserve exact content
        return matches[0].rstrip()  # Only remove trailing whitespace
    
    # Try to find patch content without code blocks
    lines = llm_response.split('\n')
    patch_lines = []
    in_patch = False
    
    for line in lines:
        # Skip code block markers
        if line.strip() in ['```diff', '```']:
            continue
            
        if line.startswith(('---', '+++', '@@', 'diff --git')):
            in_patch = True
        
        if in_patch:
            # Critical: preserve the line exactly as is, including space prefixes
            # Only skip comment lines
            if line.startswith(('#', '//')):
                continue
            patch_lines.append(line)
    
    if patch_lines:
        # Join and ensure trailing newline
        result = '\n'.join(patch_lines)
        if not result.endswith('\n'):
            result += '\n'
        return result
    
    return None


def fix_patch_context_lines(patch_content: str) -> str:
    """Fix patches that are missing space prefixes on context lines."""
    if not patch_content:
        return patch_content
    
    lines = patch_content.split('\n')
    fixed_lines = []
    in_hunk = False
    
    for line in lines:
        if line.startswith(('---', '+++', 'diff --git', 'index ')):
            # Header lines - keep as is
            fixed_lines.append(line)
            in_hunk = False
        elif line.startswith('@@'):
            # Hunk header - keep as is
            fixed_lines.append(line)
            in_hunk = True
        elif in_hunk:
            # Inside a hunk
            if line.startswith(('+', '-')):
                # Add/remove lines - keep as is
                fixed_lines.append(line)
            elif line == '':
                # Empty line might be context
                fixed_lines.append(' ')
            elif not line.startswith(' '):
                # Context line missing space prefix
                fixed_lines.append(' ' + line)
            else:
                # Already has proper prefix
                fixed_lines.append(line)
        else:
            # Outside hunk - keep as is
            fixed_lines.append(line)
    
    result = '\n'.join(fixed_lines)
    if not result.endswith('\n'):
        result += '\n'
    return result


# Test with example patches
test_response = '''Here's the patch to add a multiply function:

```diff
--- a/math_utils.py
+++ b/math_utils.py
@@ -3,4 +3,7 @@
 def subtract(a, b):
     return a - b
 
+def multiply(a, b):
+    return a * b
+
```

This adds the multiply function after the subtract function.'''

print("=== Testing Patch Extraction ===\n")

print("Original extraction:")
original = extract_patch_original(test_response)
print(repr(original))

print("\n\nFixed extraction:")
fixed = extract_patch_fixed(test_response)
print(repr(fixed))

print("\n\nWith context line fix:")
fixed_context = fix_patch_context_lines(fixed)
print(repr(fixed_context))

# Test the fix function on a problematic patch
problematic_patch = """--- a/math_utils.py
+++ b/math_utils.py
@@ -3,4 +3,7 @@
def subtract(a, b):
    return a - b

+def multiply(a, b):
+    return a * b
+"""

print("\n\n=== Fixing Problematic Patch ===")
print("Before:")
print(repr(problematic_patch))

print("\nAfter:")
fixed_patch = fix_patch_context_lines(problematic_patch)
print(repr(fixed_patch))

# Check each line
print("\nLine by line analysis:")
for i, line in enumerate(fixed_patch.split('\n')):
    if line.startswith('+'):
        print(f"Line {i}: ADD: {repr(line)}")
    elif line.startswith('-'):
        print(f"Line {i}: DEL: {repr(line)}")
    elif line.startswith(' '):
        print(f"Line {i}: CTX: {repr(line)}")
    elif line.startswith(('@', '---', '+++')):
        print(f"Line {i}: HDR: {repr(line)}")
    else:
        print(f"Line {i}: ???: {repr(line)}")