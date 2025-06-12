#!/usr/bin/env python3
"""
Simple test to verify line numbers help with patch generation.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

from src.llm import LLMClient
from src.coding_agent.models import CodeContext


def test_patch_with_line_numbers():
    """Test patch generation with line numbers."""
    
    print("=== Testing Patch Generation with Line Numbers ===\n")
    
    # Create context with line numbers
    context = CodeContext(
        task_goal="Update the docstring of the get_user method to say 'Fetch user data from the API endpoint.'",
        file_snippets={
            "src/api_client.py": '''   1: """
   2: Simple API client that needs error handling.
   3: """
   4: 
   5: import requests
   6: 
   7: 
   8: class APIClient:
   9:     def __init__(self, base_url):
  10:         self.base_url = base_url
  11:     
  12:     def get_user(self, user_id):
  13:         """Get user by ID."""
  14:         response = requests.get(f"{self.base_url}/users/{user_id}")
  15:         return response.json()
  16:     
  17:     def create_user(self, user_data):
  18:         """Create a new user."""
  19:         response = requests.post(f"{self.base_url}/users", json=user_data)
  20:         return response.json()'''
        }
    )
    
    # Test with LLM
    llm = LLMClient()
    
    prompt = f"""Generate a git diff patch to: {context.task_goal}

Current file content (with line numbers):
{context.file_snippets['src/api_client.py']}

Instructions:
1. Generate a valid unified diff patch
2. Use the line numbers shown (format: 'NNNN: content') for @@ markers
3. The docstring to change is on line 13
4. Include 3 lines of context before and after the change

Example format:
```diff
--- a/src/api_client.py
+++ b/src/api_client.py
@@ -10,7 +10,7 @@ class APIClient:
     def __init__(self, base_url):
         self.base_url = base_url
     
     def get_user(self, user_id):
-        "Get user by ID."
+        "Fetch user data from the API endpoint."
         response = requests.get(f"{self.base_url}/users/{user_id}")
         return response.json()
```

Generate ONLY the patch in the above format:"""

    try:
        response = llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=500
        )
        
        print("Generated patch:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_patch_with_line_numbers()