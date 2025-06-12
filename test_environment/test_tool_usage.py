#!/usr/bin/env python3
"""
Test the tool usage capabilities of the enhanced coding agent.
"""

import sys
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.models import CodeContext
from src.llm import LLMClient
from src.coding_agent import CodingAgent
from src.proto_gen import messages_pb2
from src.rag_service import RAGClient, RAGService
import logging
from src.core.logging import setup_logging


def test_tool_usage():
    """Test that the agent uses tools appropriately."""
    
    setup_logging(logging.DEBUG)  # More verbose for tool debugging
    
    print("\n=== Testing Tool Usage Capabilities ===\n")
    
    # Test 1: Context refinement with tools
    print("📝 Test 1: Context Refinement")
    print("-" * 40)
    
    llm = LLMClient(model="gpt-4o")
    
    # Create a task that should trigger tool usage
    refinement_prompt = """
You are about to implement this task: Fix the bug in the parse_date function that causes it to crash on invalid dates.

Initial context provided:
- 0 code chunks from search
- 0 file snippets  
- Target files: src/date_utils.py

You have access to these tools:
1. read_file(path, start_line=None, end_line=None) - Read a file or specific lines
2. search_code(query) - Search for code patterns
3. find_symbol(symbol_name) - Find a function/class definition

What additional context do you need? Respond with a JSON list of tool calls.

Example:
[
  {"tool": "read_file", "args": {"path": "src/api.py", "start_line": 10, "end_line": 30}},
  {"tool": "search_code", "args": {"query": "def get_user"}}
]
"""
    
    print("Asking LLM what context it needs...")
    
    try:
        response = llm.generate_with_json(
            prompt=refinement_prompt,
            system_prompt="You are a coding assistant. Always read files before making changes to verify content and line numbers.",
            max_tokens=500,
            temperature=0.1
        )
        
        print("\n✅ LLM requested these tool calls:")
        print(json.dumps(response, indent=2))
        
        # Verify the response makes sense
        if isinstance(response, list):
            for tool_call in response:
                assert "tool" in tool_call, "Missing 'tool' field"
                assert "args" in tool_call, "Missing 'args' field"
                print(f"\n  Tool: {tool_call['tool']}")
                print(f"  Args: {tool_call['args']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 2: Full agent with tool usage
    print("\n\n📝 Test 2: Full Agent Tool Usage")
    print("-" * 40)
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # Initialize RAG
    rag_dir = repo_path / ".rag"
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # Index repository
    print("Indexing repository...")
    for py_file in repo_path.glob("**/*.py"):
        if ".rag" not in str(py_file):
            rag_service.index_file(str(py_file))
    
    rag_client = RAGClient(service=rag_service)
    
    # Create agent
    coding_agent = CodingAgent(
        repo_path=str(repo_path),
        rag_client=rag_client,
        llm_client=llm,
        max_retries=1
    )
    
    # Create a task that requires reading files
    task = messages_pb2.CodingTask()
    task.id = "test-tool-001"
    task.parent_plan_id = "test-plan-001" 
    task.step_number = 1
    task.goal = "Add a docstring to the process_data function in src/data_processor.py explaining what it does"
    task.paths.append("src/data_processor.py")
    task.complexity_label = messages_pb2.COMPLEXITY_SIMPLE
    task.estimated_tokens = 500
    task.base_commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    print(f"Task: {task.goal}")
    print(f"Target: {task.paths[0]}")
    
    # Enable detailed logging to see tool usage
    print("\n🔍 Processing (watch for tool usage)...")
    
    try:
        # Clean up branches first
        subprocess.run(["git", "checkout", "master"], cwd=repo_path, capture_output=True)
        
        result = coding_agent.process_task(task)
        
        print(f"\n📊 Result: {result.status.name}")
        
        # Check if tools were used
        tool_usage_notes = [n for n in result.notes if "tool" in n.lower() or "read" in n.lower()]
        
        if tool_usage_notes:
            print("\n✅ Tool usage detected:")
            for note in tool_usage_notes:
                print(f"  - {note}")
        else:
            print("\n⚠️  No explicit tool usage detected in notes")
        
        # Check if refined context was mentioned
        if "Refined context" in str(result.notes):
            print("\n✅ Context refinement occurred")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Direct tool testing
    print("\n\n📝 Test 3: Direct Tool Testing")
    print("-" * 40)
    
    # Test the individual tool methods
    print("Testing _tool_read_file...")
    content = coding_agent._tool_read_file("src/calculator.py", start_line=1, end_line=10)
    if content:
        print("✅ File reading works:")
        print(content[:200] + "...")
    else:
        print("❌ File reading failed")
    
    print("\n\nTesting _tool_search_code...")
    results = coding_agent._tool_search_code("def calculate")
    if results:
        print(f"✅ Code search found {len(results)} results")
        if results:
            print("First result preview:")
            print(results[0][:200] + "...")
    else:
        print("❌ Code search failed")
    
    print("\n\nTesting _tool_find_symbol...")
    result = coding_agent._tool_find_symbol("Calculator")
    if result:
        print("✅ Symbol search works:")
        print(result[:200] + "...")
    else:
        print("⚠️  Symbol not found (may be expected)")
    
    print("\n✨ Tool usage tests complete!")


def test_tool_error_handling():
    """Test how the agent handles tool errors."""
    
    print("\n\n=== Testing Tool Error Handling ===\n")
    
    llm = LLMClient(model="gpt-4o")
    
    # Test with invalid tool calls
    refinement_prompt = """
You need to implement a feature but the file doesn't exist yet.

You have access to these tools:
1. read_file(path, start_line=None, end_line=None) - Read a file or specific lines
2. search_code(query) - Search for code patterns
3. find_symbol(symbol_name) - Find a function/class definition

What additional context do you need? Respond with a JSON list of tool calls.
"""
    
    print("Testing error handling with non-existent files...")
    
    try:
        # Create a mock context
        context = CodeContext(task_goal="Test error handling")
        
        # Simulate tool calls that will fail
        tool_calls = [
            {"tool": "read_file", "args": {"path": "non_existent.py"}},
            {"tool": "search_code", "args": {"query": ""}},  # Empty query
            {"tool": "find_symbol", "args": {}}  # Missing required arg
        ]
        
        repo_path = Path(__file__).parent / "test_repo"
        coding_agent = CodingAgent(
            repo_path=str(repo_path),
            llm_client=llm
        )
        
        for tool_call in tool_calls:
            print(f"\nTrying: {tool_call}")
            try:
                coding_agent._execute_tool_call(tool_call, context)
                print("  ✅ Handled gracefully")
            except Exception as e:
                print(f"  ❌ Exception: {e}")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    print("\n✨ Error handling tests complete!")


if __name__ == "__main__":
    test_tool_usage()
    test_tool_error_handling()