#!/usr/bin/env python3
"""
Debug what o3 generates for patches.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.patch_generator import PatchGenerator
from src.coding_agent.models import CodeContext
from src.llm import LLMClient


def debug_o3_generation():
    """Debug o3 patch generation."""
    
    print("=== Debugging o3 Patch Generation ===\n")
    
    # Create context with line numbers
    context = CodeContext(
        task_goal="Update the docstring of the get_user method to say 'Fetch user data from the API endpoint.'",
        file_snippets={
            "src/api_client.py": """   1: \"\"\"
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
  15:         return response.json()"""
        }
    )
    
    # Test patch generator
    llm = LLMClient(model="o3")
    generator = PatchGenerator(llm)
    
    # Get the raw prompt
    prompt = generator._build_prompt(context)
    print("PROMPT SENT TO O3:")
    print("=" * 60)
    print(prompt)
    print("=" * 60)
    
    # Generate
    print("\nGenerating with o3...")
    result = generator.generate_patch(context, temperature=0.1)
    
    if result.success:
        print("\n✓ Patch generation reported success")
        print("\nEXTRACTED PATCH:")
        print("-" * 60)
        print(repr(result.patch_content))
        print("-" * 60)
        
        # Save raw patch
        patch_file = Path("/tmp/o3_debug_patch.diff") 
        patch_file.write_text(result.patch_content)
        print(f"\nSaved to: {patch_file}")
        
        # Hex dump first few bytes
        print("\nHEX DUMP (first 100 bytes):")
        content_bytes = result.patch_content.encode('utf-8')
        for i in range(min(100, len(content_bytes))):
            if i % 16 == 0:
                print(f"\n{i:04x}: ", end="")
            print(f"{content_bytes[i]:02x} ", end="")
        print()
        
    else:
        print(f"\n✗ Failed: {result.error_message}")


if __name__ == "__main__":
    debug_o3_generation()