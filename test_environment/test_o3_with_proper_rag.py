#!/usr/bin/env python3
"""
Test o3 with proper RAG context (no truncation, with line numbers).
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service import RAGService, RAGClient
from src.llm import LLMClient
from src.coding_agent.models import CodeContext


def test_o3_with_rag_context():
    """Test o3 patch generation with proper RAG context."""
    
    print("=== Testing o3 with Proper RAG Context ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    
    # Initialize RAG and index the file
    rag_service = RAGService(persist_directory=str(repo_path / ".rag"))
    api_file = repo_path / "src" / "api_client.py"
    rag_service.index_file(str(api_file))
    
    rag_client = RAGClient(service=rag_service)
    
    # Search for relevant chunks
    task_goal = "Update the docstring of the get_user method to say 'Fetch user data from the API endpoint.'"
    results = rag_client.search(
        query="get_user method docstring",
        k=3
    )
    
    print(f"Found {len(results)} relevant chunks:\n")
    
    # Build context with actual RAG chunks
    context_parts = []
    context_parts.append(f"Task: {task_goal}\n")
    context_parts.append("Relevant code chunks from RAG search (with exact line numbers):\n")
    
    for i, result in enumerate(results):
        file_path = result.get('file_path', '')
        start_line = result.get('start_line', 0)
        end_line = result.get('end_line', 0)
        content = result.get('content', '')
        
        print(f"{i+1}. {file_path}:{start_line}-{end_line}")
        print(f"   Content: {content[:50]}...")
        
        # Add to context with line numbers
        context_parts.append(f"\n=== Chunk from {file_path} (lines {start_line}-{end_line}) ===")
        
        # Add line numbers to content
        lines = content.split('\n')
        for j, line in enumerate(lines):
            line_num = start_line + j
            context_parts.append(f"{line_num:4d}: {line}")
    
    full_context = '\n'.join(context_parts)
    
    print(f"\n\nFull context size: {len(full_context)} characters")
    print("=" * 60)
    print(full_context)
    print("=" * 60)
    
    # Generate patch with o3
    llm = LLMClient(model="o3")
    print(f"\nGenerating patch with {llm.model}...")
    
    prompt = f"""{full_context}

Instructions:
1. Generate a valid git unified diff patch
2. The line numbers shown above are the EXACT line numbers in the file
3. Use these line numbers for your @@ markers
4. Include proper context lines (3 before and after the change)
5. The change should update line 13's docstring

Generate ONLY the patch:"""

    try:
        response = llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=500,
            system_prompt="You are a git patch generator. Output ONLY valid unified diff format."
        )
        
        print("\nGenerated patch:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        
        # Extract patch if wrapped in code blocks
        import re
        if '```' in response:
            match = re.search(r'```(?:diff)?\n(.*?)```', response, re.DOTALL)
            if match:
                patch_content = match.group(1).strip()
            else:
                patch_content = response
        else:
            patch_content = response
        
        # Save and test
        patch_file = Path("/tmp/test_o3_rag_patch.diff")
        patch_file.write_text(patch_content)
        
        import subprocess
        result = subprocess.run(
            ["git", "apply", "--check", str(patch_file)],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\n✅ SUCCESS! Patch is valid and can be applied!")
        else:
            print(f"\n❌ Patch validation failed: {result.stderr}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_o3_with_rag_context()