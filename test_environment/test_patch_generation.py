#!/usr/bin/env python3
"""
Test patch generation capabilities with line numbers and proper context.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.models import CodeContext
from src.coding_agent.patch_generator import PatchGenerator
from src.coding_agent.context_gatherer import ContextGatherer
from src.llm import LLMClient
from src.proto_gen import messages_pb2


def test_patch_with_line_numbers():
    """Test that patches use correct line numbers from context."""
    
    print("\n=== Testing Patch Generation with Line Numbers ===\n")
    
    # Setup
    repo_path = Path(__file__).parent / "test_repo"
    llm = LLMClient(model="gpt-4o")
    patch_gen = PatchGenerator(llm)
    context_gatherer = ContextGatherer(str(repo_path))
    
    # Create a simple task
    task = messages_pb2.CodingTask()
    task.goal = "Add a comment above the calculate_total function explaining what it does"
    task.paths.append("src/calculator.py")
    
    print("📝 Task:", task.goal)
    print("📁 File:", task.paths[0])
    
    # Gather context with line numbers
    print("\n1️⃣ Gathering context with line numbers...")
    context = context_gatherer.gather_context(task)
    
    # Show the context
    print("\n📄 Context preview:")
    context_str = context.to_prompt_context()
    lines = context_str.split('\n')
    for i, line in enumerate(lines[:30]):  # First 30 lines
        print(f"  {line}")
    
    # Check that line numbers are present
    has_line_numbers = any(':' in line and line.strip()[0:4].strip().isdigit() 
                          for line in lines if line.strip())
    
    print(f"\n✅ Context has line numbers: {has_line_numbers}")
    
    # Generate patch
    print("\n2️⃣ Generating patch...")
    result = patch_gen.generate_patch(context, max_tokens=1000)
    
    if result.success:
        print("\n✅ Patch generated successfully!")
        print("\n📄 Generated patch:")
        print("-" * 60)
        print(result.patch_content)
        print("-" * 60)
        
        # Analyze the patch
        patch_lines = result.patch_content.split('\n')
        hunk_lines = [l for l in patch_lines if l.startswith('@@')]
        
        print(f"\n📊 Patch analysis:")
        print(f"  - Total lines: {len(patch_lines)}")
        print(f"  - Hunks: {len(hunk_lines)}")
        print(f"  - Files modified: {result.files_modified}")
        
        # Check if line numbers look reasonable
        import re
        for hunk in hunk_lines:
            match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', hunk)
            if match:
                old_start = int(match.group(1))
                print(f"  - Hunk starts at line {old_start}")
                
    else:
        print(f"\n❌ Patch generation failed: {result.error_message}")
    
    # Test refinement capability
    if result.success and result.patch_content:
        print("\n\n3️⃣ Testing patch refinement...")
        
        # Simulate an error
        fake_error = "error: patch fragment without header at line 5"
        
        print(f"Simulating error: {fake_error}")
        
        refined = patch_gen.refine_patch(
            result.patch_content,
            fake_error,
            context,
            max_tokens=1000
        )
        
        if refined.success:
            print("\n✅ Refinement succeeded!")
            print("\n📄 Refined patch preview:")
            print(refined.patch_content[:500] + "...")
        else:
            print(f"\n❌ Refinement failed: {refined.error_message}")


def test_context_quality():
    """Test the quality of context provided to patch generator."""
    
    print("\n\n=== Testing Context Quality ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    context_gatherer = ContextGatherer(str(repo_path))
    
    # Create a task that touches multiple files
    task = messages_pb2.CodingTask()
    task.goal = "Add logging to all public methods"
    task.paths.extend(["src/calculator.py", "src/data_processor.py"])
    
    print("📝 Task:", task.goal)
    print("📁 Files:", ", ".join(task.paths))
    
    # Gather context
    context = context_gatherer.gather_context(task)
    
    print(f"\n📊 Context statistics:")
    print(f"  - File snippets: {len(context.file_snippets)}")
    print(f"  - Blob contents: {len(context.blob_contents)}")
    print(f"  - Token count: {context.token_count}")
    
    # Check each file snippet
    print("\n📄 File snippets analysis:")
    for file_path, content in context.file_snippets.items():
        lines = content.split('\n')
        numbered_lines = [l for l in lines if l.strip() and ':' in l]
        
        print(f"\n  {file_path}:")
        print(f"    - Total lines: {len(lines)}")
        print(f"    - Lines with numbers: {len(numbered_lines)}")
        print(f"    - Full content: {'Yes' if len(content) > 500 else 'No'}")
        
        # Show first few lines
        print("    - Preview:")
        for line in lines[:5]:
            print(f"      {line}")
    
    # Test prompt generation
    print("\n\n📝 Testing prompt generation:")
    prompt = context.to_prompt_context(max_tokens=5000)
    
    print(f"Prompt length: {len(prompt)} chars")
    print(f"Prompt preview:")
    print("-" * 60)
    print(prompt[:1000] + "...")
    print("-" * 60)


def test_file_rewriter_fallback():
    """Test the file rewriter as a fallback."""
    
    print("\n\n=== Testing File Rewriter Fallback ===\n")
    
    from src.coding_agent.file_rewriter import FileRewriter
    
    repo_path = Path(__file__).parent / "test_repo"
    llm = LLMClient(model="gpt-4o")
    rewriter = FileRewriter(llm, str(repo_path))
    
    # Create context
    context = CodeContext(
        task_goal="Add a helpful comment to the Calculator class"
    )
    
    # Add the file content
    calc_file = repo_path / "src/calculator.py"
    if calc_file.exists():
        content = calc_file.read_text()
        # Add with line numbers
        lines = content.split('\n')
        numbered = []
        for i, line in enumerate(lines, 1):
            numbered.append(f"{i:4d}: {line}")
        context.add_snippet("src/calculator.py", '\n'.join(numbered))
    
    print("📝 Task:", context.task_goal)
    print("📁 File: src/calculator.py")
    
    # Rewrite the file
    print("\n🔧 Rewriting file...")
    result = rewriter.rewrite_file(context, "src/calculator.py")
    
    if result.success:
        print("\n✅ File rewrite succeeded!")
        print("\n📄 Generated patch:")
        print("-" * 60)
        print(result.patch_content[:1000] + "..." if len(result.patch_content) > 1000 else result.patch_content)
        print("-" * 60)
    else:
        print(f"\n❌ File rewrite failed: {result.error_message}")


if __name__ == "__main__":
    test_patch_with_line_numbers()
    test_context_quality()
    test_file_rewriter_fallback()