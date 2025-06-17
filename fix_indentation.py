#!/usr/bin/env python3
"""Fix indentation in the test file."""

import re

# Read the file
with open('tests/test_e2e_calculator_pipeline.py', 'r') as f:
    lines = f.readlines()

# Fix specific indentation patterns
fixed_lines = []
for i, line in enumerate(lines):
    # Fix lines that should be indented 8 spaces inside try/for/if blocks
    if re.match(r'^        \w', line) and i > 0:
        prev_line = lines[i-1].strip()
        if prev_line.endswith(':') and not prev_line.startswith('def') and not prev_line.startswith('class'):
            # This line should be indented 12 spaces
            line = '    ' + line
    
    # Fix except blocks that are incorrectly indented
    if line.strip().startswith('except ') and not line.startswith('    except'):
        line = '    ' + line.strip() + '\n'
    
    # Fix lines inside if/elif/else blocks in functions
    if re.match(r'^        (if |elif |else:)', line):
        line = '    ' + line
    
    # Fix raise/return statements
    if re.match(r'^        (raise |return )', line):
        line = '    ' + line
    
    fixed_lines.append(line)

# Write the fixed file
with open('tests/test_e2e_calculator_pipeline.py', 'w') as f:
    f.writelines(fixed_lines)

print("Fixed indentation issues")