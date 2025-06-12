#!/usr/bin/env python3
"""
Test patch generation with o3 model and line numbers.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load from parent .env
load_dotenv(Path(__file__).parent.parent / ".env")

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from src.llm import LLMClient
from src.coding_agent.models import CodeContext


def test_o3_patch_generation():
    """Test patch generation with o3."""
    
    print("=== Testing Patch Generation with o3 ===\n")
    
    # File content with line numbers
    file_content = """   1: \"\"\"
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
  14:         response = requests.get(f\"{self.base_url}/users/{user_id}\")
  15:         return response.json()
  16:     
  17:     def create_user(self, user_data):
  18:         \"\"\"Create a new user.\"\"\"
  19:         response = requests.post(f\"{self.base_url}/users\", json=user_data)
  20:         return response.json()"""
    
    # Create context
    context = CodeContext(
        task_goal="Update the docstring of the get_user method to say 'Fetch user data from the API endpoint.'",
        file_snippets={"src/api_client.py": file_content}
    )
    
    # Test with o3
    llm = LLMClient(model="o3")
    print(f"Using model: {llm.model}\n")
    
    prompt = f"""Generate a git diff patch to: {context.task_goal}

Current file content (with line numbers in format 'NNNN: content'):
{file_content}

Instructions:
1. Generate a valid unified diff patch in git format
2. The line numbers are shown before each line (e.g., "13: " means line 13)
3. Use these line numbers for the @@ markers in your patch
4. The docstring to change is on line 13
5. Include 3 lines of context before and after the change
6. Do NOT include the line numbers in the patch content itself

Example of correct patch format:
```diff
--- a/src/api_client.py
+++ b/src/api_client.py
@@ -10,7 +10,7 @@ class APIClient:
     def __init__(self, base_url):
         self.base_url = base_url
     
     def get_user(self, user_id):
-        "Get user by ID."
+        "Fetch user data from the API endpoint."
         response = requests.get(f"{{self.base_url}}/users/{{user_id}}")
         return response.json()
```

Generate ONLY the patch:"""

    try:
        response = llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=500,
            system_prompt="You are a git diff generator. Output ONLY valid unified diff format. Do not include any explanations."
        )
        
        print("Generated patch:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        
        # Save to file to test
        patch_file = Path("/tmp/test_o3_patch.diff")
        patch_file.write_text(response)
        print(f"\nPatch saved to: {patch_file}")
        
        # Test if it's valid
        import subprocess
        test_repo = Path(__file__).parent / "test_repo"
        result = subprocess.run(
            ["git", "apply", "--check", str(patch_file)],
            cwd=test_repo,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\n✓ Patch is valid and can be applied!")
        else:
            print(f"\n✗ Patch validation failed: {result.stderr}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_o3_patch_generation()