#!/usr/bin/env python3
"""
Simple debug of patch generation.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

from src.llm import LLMClient
from src.coding_agent.models import CodeContext
from src.coding_agent.patch_generator_v2 import ImprovedPatchGenerator


def test_direct_llm():
    """Test LLM directly to see what it generates."""
    
    print("=== Direct LLM Test ===\n")
    
    llm = LLMClient(model="gpt-4-turbo-preview")
    
    # Very simple prompt
    prompt = """I need a git diff patch. Current code:

def get_user(self, user_id):
    '''Get user by ID.'''
    response = requests.get(f"{self.base_url}/users/{user_id}")
    return response.json()

Change the docstring from 'Get user by ID.' to 'Fetch user data from the API endpoint.'

Generate ONLY the git diff patch. Use proper unified diff format."""
    
    response = llm.generate(
        prompt=prompt,
        temperature=0.1,
        max_tokens=500
    )
    
    print("LLM Response:")
    print("-" * 60)
    print(response)
    print("-" * 60)
    
    # Check each line
    print("\nLine by line analysis:")
    for i, line in enumerate(response.split('\n'), 1):
        print(f"{i:3}: {repr(line)}")


def test_with_context():
    """Test with proper context."""
    
    print("\n\n=== Test with Context ===\n")
    
    context = CodeContext(
        task_goal="Change the docstring of get_user method to say 'Fetch user data from the API endpoint.'",
        file_snippets={
            "src/api_client.py": """    def get_user(self, user_id):
        '''Get user by ID.'''
        response = requests.get(f"{self.base_url}/users/{user_id}")
        return response.json()"""
        }
    )
    
    llm = LLMClient(model="gpt-4-turbo-preview")
    generator = ImprovedPatchGenerator(llm)
    
    result = generator.generate_patch(context)
    
    if result.success:
        print("✓ Generated patch successfully")
        print("\nPatch content:")
        print("-" * 60)
        print(result.patch_content)
        print("-" * 60)
        
        print("\nHex dump of first 200 chars:")
        for i, char in enumerate(result.patch_content[:200]):
            print(f"{ord(char):02x} ", end="")
            if (i + 1) % 16 == 0:
                print()
    else:
        print(f"✗ Failed: {result.error_message}")


if __name__ == "__main__":
    test_direct_llm()
    test_with_context()