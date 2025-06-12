#!/usr/bin/env python3
"""
Test with a simpler task to see the agent working.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.models import CodeContext
from src.llm import LLMClient
import json


def test_context_refinement():
    """Test the context refinement with tools."""
    
    print("=== Testing Context Refinement ===\n")
    
    # Simulate what the agent would do
    llm = LLMClient(model="gpt-4o")  # Use gpt-4o for faster response
    
    refinement_prompt = """
You are about to implement this task: Add error handling to the get_user method in src/api_client.py. It should catch requests.exceptions.RequestException and return None with a log message when the request fails.

Initial context provided:
- 0 code chunks from search
- 1 file snippets
- Target files: src/api_client.py

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
        
        print("\nLLM requested these tool calls:")
        print(json.dumps(response, indent=2))
        
        # Show what each tool would return
        print("\n\nSimulating tool responses:")
        
        # Handle both single dict and list responses
        tool_calls = response if isinstance(response, list) else [response]
        
        for tool_call in tool_calls:
            tool = tool_call.get("tool")
            args = tool_call.get("args", {})
            
            print(f"\n{tool}({args}):")
            
            if tool == "read_file" and args.get("path") == "src/api_client.py":
                print("""
   1: \"\"\"
   2: Simple API client that needs error handling.
   3: \"\"\"
   4: 
   5: import requests
   6: 
   7: 
   8: class APIClient:
   9:     def __init__(self, base_url):
  10:         self.base_url = base_url
  11:     
  12:     def get_user(self, user_id):
  13:         \"\"\"Get user by ID.\"\"\"
  14:         response = requests.get(f"{self.base_url}/users/{user_id}")
  15:         return response.json()
""")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_context_refinement()