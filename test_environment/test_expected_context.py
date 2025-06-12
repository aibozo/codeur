#!/usr/bin/env python3
"""
Show what context the coding agent SHOULD be getting.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service import RAGService


def show_expected_context():
    """Show what RAG should be providing."""
    
    print("=== Expected Context for Coding Agent ===\n")
    
    # 1. What RAG chunks should look like
    print("1. EXPECTED RAG CHUNKS:")
    print("-" * 50)
    print("""
Expected chunk for get_user method:
{
    "file_path": "src/api_client.py",
    "start_line": 12,
    "end_line": 15,
    "chunk_type": "method",
    "symbol_name": "get_user",  # <-- SHOULD HAVE ACTUAL NAME
    "class_name": "APIClient",
    "content": "def get_user(self, user_id):\\n    \\"\\"\\"Get user by ID.\\"\\"\\"\\n    response = requests.get(f\\"{self.base_url}/users/{user_id}\\")\\n    return response.json()"
}
""")
    
    # 2. What tool responses should include
    print("\n2. EXPECTED TOOL RESPONSES:")
    print("-" * 50)
    print("""
Tool: find_symbol('get_user')
Expected response:
{
    "file_path": "src/api_client.py", 
    "start_line": 12,
    "end_line": 15,
    "content_with_line_numbers": "  12: def get_user(self, user_id):\\n  13:     \\"\\"\\"Get user by ID.\\"\\"\\"\\n  14:     response = requests.get(f\\"{self.base_url}/users/{user_id}\\")\\n  15:     return response.json()"
}

Tool: search_code('requests.exceptions')
Expected results:
- Examples of error handling from other files
- Import statements showing how to import RequestException
""")
    
    # 3. What the final context should include
    print("\n3. EXPECTED FINAL CONTEXT:")
    print("-" * 50)
    print("""
Should include:
1. The target file WITH line numbers ✓ (working)
2. Related functions WITH proper symbol names ✗ (broken - shows '    ')
3. Tool results showing:
   - The exact get_user method ✗ (tool not executed)
   - Examples of error handling ✗ (no relevant examples)
   - Import patterns ✗ (search returned 0 results)
4. Nearby code context (other methods in same class) ✓ (included)
""")
    
    # 4. Show actual RAG indexing
    print("\n4. CHECKING ACTUAL RAG INDEXING:")
    print("-" * 50)
    
    repo_path = Path(__file__).parent / "test_repo"
    rag_dir = repo_path / ".rag"
    
    if rag_dir.exists():
        rag_service = RAGService(persist_directory=str(rag_dir))
        
        # Check what's actually indexed
        results = rag_service.search_code("get_user", k=3)
        
        print("RAG search for 'get_user':")
        for i, result in enumerate(results):
            chunk = result.chunk
            print(f"\n{i+1}. {chunk.file_path}:{chunk.start_line}")
            print(f"   Type: {chunk.chunk_type}")
            print(f"   Symbol: '{chunk.symbol_name}'" + (" <-- BROKEN!" if chunk.symbol_name.strip() == "" else ""))
            print(f"   Content preview: {chunk.content[:50]}...")
            
    # 5. Why it matters
    print("\n\n5. WHY THIS MATTERS:")
    print("-" * 50)
    print("""
Without proper context:
- LLM doesn't know which method is get_user (multiple methods at lines 9, 11, 16, 26)
- Can't find examples of error handling patterns
- Doesn't know how to import RequestException
- Has to guess at implementation details

With proper context:
- Clear identification of get_user method
- Examples of try/except patterns from codebase
- Correct import statements
- Consistent error handling style
""")


if __name__ == "__main__":
    show_expected_context()