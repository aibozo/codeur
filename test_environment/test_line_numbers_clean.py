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
    
    # Test with LLM
    llm = LLMClient()
    print(f"Using model: {llm.model}\n")
    
    prompt = f"""Generate a git diff patch to: {context.task_goal}

Current file content (with line numbers):
{file_content}

Instructions:
1. Generate a valid unified diff patch
2. Use the line numbers shown (format: 'NNNN: content') for @@ markers
3. The docstring to change is on line 13
4. Include 3 lines of context before and after the change
5. Do NOT include the line numbers in the patch content itself

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
        patch_file = Path("/tmp/test_patch.diff")
        patch_file.write_text(response)
        print(f"\nPatch saved to: {patch_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_patch_with_line_numbers()