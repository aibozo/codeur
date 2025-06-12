#!/usr/bin/env python3
"""
Test file rewriter directly to see what it generates.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

from src.coding_agent.file_rewriter import FileRewriter
from src.coding_agent.models import CodeContext


def test_direct_rewriter():
    """Test file rewriter directly."""
    
    print("=== Direct File Rewriter Test ===\n")
    
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
    
    # Create rewriter
    rewriter = FileRewriter(repo_path=str(repo_path))
    
    # Test rewriting
    result = rewriter.rewrite_file(context, "src/api_client.py")
    
    if result.success:
        print("✓ File rewrite succeeded!")
        print("\nGenerated diff:")
        print(result.patch_content)
        
        # Check the actual file
        api_file = repo_path / "src/api_client.py"
        if api_file.exists():
            print("\nNew file content:")
            print(api_file.read_text())
    else:
        print(f"✗ Failed: {result.error_message}")


if __name__ == "__main__":
    test_direct_rewriter()