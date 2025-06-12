#!/usr/bin/env python3
"""
Test file rewriter with o3 model.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.file_rewriter import FileRewriter
from src.coding_agent.models import CodeContext
from src.llm import LLMClient


def test_o3_file_rewriter():
    """Test file rewriter with o3."""
    
    print("=== Testing File Rewriter with o3 ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # Create context
    context = CodeContext(
        task_goal="Update the docstring of the get_user method to say 'Fetch user data from the API endpoint.'",
        file_snippets={
            "src/api_client.py": """class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_user(self, user_id):
        \"\"\"Get user by ID.\"\"\"
        response = requests.get(f"{self.base_url}/users/{user_id}")
        return response.json()"""
        }
    )
    
    # Create rewriter with o3
    llm = LLMClient(model="o3")
    rewriter = FileRewriter(llm_client=llm, repo_path=str(repo_path))
    
    print(f"Using model: {llm.model}")
    
    # Test rewriting
    result = rewriter.rewrite_file(context, "src/api_client.py")
    
    if result.success:
        print("\n✓ File rewrite succeeded!")
        print("\nGenerated diff:")
        print("-" * 60)
        print(result.patch_content)
        print("-" * 60)
        
        print("\nTokens used:", result.tokens_used)
        
        # Check the actual file
        api_file = repo_path / "src/api_client.py"
        if api_file.exists():
            new_content = api_file.read_text()
            if 'Fetch user data from the API endpoint' in new_content:
                print("\n✅ Successfully updated the docstring!")
            else:
                print("\n❌ Docstring was not updated correctly")
    else:
        print(f"\n✗ Failed: {result.error_message}")


if __name__ == "__main__":
    test_o3_file_rewriter()