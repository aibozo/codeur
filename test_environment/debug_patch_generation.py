#!/usr/bin/env python3
"""
Debug patch generation to see what's being produced.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

from src.llm import LLMClient
from src.coding_agent.models import CodeContext
from src.coding_agent.patch_generator import PatchGenerator
from src.coding_agent.patch_generator_v2 import ImprovedPatchGenerator


def test_patch_generation():
    """Test and debug patch generation."""
    
    print("=== Debugging Patch Generation ===\n")
    
    # Create a simple context
    context = CodeContext(
        task_goal="Add a docstring to the get_user method that says 'Fetch user data from the API endpoint.'",
        file_snippets={
            "src/api_client.py": '''class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_user(self, user_id):
        """Get user by ID."""
        response = requests.get(f"{self.base_url}/users/{user_id}")
        return response.json()'''
        }
    )
    
    # Test with different models
    models = ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"]
    
    for model in models:
        print(f"\n{'='*60}")
        print(f"Testing with {model}")
        print('='*60)
        
        try:
            llm = LLMClient(model=model)
            
            # Test original generator
            print("\n1. Original PatchGenerator:")
            gen1 = PatchGenerator(llm)
            result1 = gen1.generate_patch(context, temperature=0.1)
            
            if result1.success:
                print("✓ Generated patch")
                print("\n--- PATCH START ---")
                print(result1.patch_content)
                print("--- PATCH END ---\n")
            else:
                print(f"✗ Failed: {result1.error_message}")
            
            # Test improved generator
            print("\n2. ImprovedPatchGenerator:")
            gen2 = ImprovedPatchGenerator(llm)
            result2 = gen2.generate_patch(context, temperature=0.1)
            
            if result2.success:
                print("✓ Generated patch")
                print("\n--- PATCH START ---")
                print(result2.patch_content)
                print("--- PATCH END ---\n")
                
                # Show line-by-line analysis
                print("Line-by-line analysis:")
                for i, line in enumerate(result2.patch_content.split('\n'), 1):
                    print(f"{i:3}: {repr(line)}")
            else:
                print(f"✗ Failed: {result2.error_message}")
                
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()


def test_simple_prompt():
    """Test with a very simple, direct prompt."""
    print("\n\n=== Testing Simple Direct Prompt ===\n")
    
    llm = LLMClient(model="gpt-4-turbo-preview")
    
    prompt = """Generate a git diff patch that adds a docstring to this Python method:

```python
def get_user(self, user_id):
    '''Get user by ID.'''
    response = requests.get(f"{self.base_url}/users/{user_id}")
    return response.json()
```

The new docstring should say: "Fetch user data from the API endpoint."

Output ONLY a valid git diff in this exact format:
--- a/src/api_client.py
+++ b/src/api_client.py
@@ -5,4 +5,4 @@
     def get_user(self, user_id):
-        """Get user by ID."""
+        """Fetch user data from the API endpoint."""
         response = requests.get(f"{self.base_url}/users/{user_id}")
         return response.json()"""
    
    response = llm.generate(
        prompt=prompt,
        temperature=0.1,
        system_prompt="You are a git diff generator. Output ONLY valid unified diff format."
    )
    
    print("LLM Response:")
    print("--- RESPONSE START ---")
    print(response)
    print("--- RESPONSE END ---")


if __name__ == "__main__":
    test_patch_generation()
    test_simple_prompt()