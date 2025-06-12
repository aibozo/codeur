#!/usr/bin/env python3
"""
Fix the RAG system issues.
"""

import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service import RAGService
from src.rag_service.embeddings import EmbeddingService
import chromadb


def diagnose_rag_issues():
    """Diagnose all RAG issues."""
    
    print("\n=== RAG System Diagnosis ===\n")
    
    # 1. Check all vector stores
    print("1. Checking vector stores:")
    
    vector_stores = [
        Path("/home/riley/Programming/agent/.rag/vector_store"),
        Path("/home/riley/Programming/agent/test_environment/test_repo/.rag"),
        Path("/home/riley/Programming/agent/test_environment/.rag"),
    ]
    
    for vs_path in vector_stores:
        print(f"\n  {vs_path}:")
        if vs_path.exists():
            print(f"    Exists: Yes")
            try:
                client = chromadb.PersistentClient(path=str(vs_path))
                collections = client.list_collections()
                print(f"    Collections: {[c.name for c in collections]}")
                
                for collection in collections:
                    count = collection.count()
                    print(f"    {collection.name}: {count} items")
                    
                    # Check embedding dimension
                    if count > 0:
                        result = collection.peek(1)
                        if result and 'embeddings' in result and result['embeddings']:
                            dim = len(result['embeddings'][0])
                            print(f"    Embedding dimension: {dim}")
            except Exception as e:
                print(f"    Error: {e}")
        else:
            print(f"    Exists: No")
    
    # 2. Test embedding service
    print("\n\n2. Testing embedding service:")
    embedding_service = EmbeddingService()
    test_text = "def get_user(self, user_id):"
    embedding = embedding_service.embed_text(test_text)
    if embedding:
        print(f"   Embedding dimension: {len(embedding)}")
        print(f"   Model: {embedding_service.model}")
        print(f"   Expected dimension: {embedding_service.dimension}")
    else:
        print("   Failed to generate embedding")


def fix_test_repo_rag():
    """Fix the test repo RAG system."""
    
    print("\n\n=== Fixing Test Repo RAG ===\n")
    
    repo_path = Path(__file__).parent / "test_repo"
    rag_dir = repo_path / ".rag"
    
    # 1. Remove old RAG directory
    if rag_dir.exists():
        print("1. Removing old RAG directory...")
        shutil.rmtree(rag_dir)
    
    # 2. Create fresh RAG service
    print("2. Creating fresh RAG service...")
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # 3. Index all Python files
    print("3. Indexing Python files:")
    python_files = list(repo_path.glob("**/*.py"))
    
    for py_file in python_files:
        if ".rag" not in str(py_file) and "__pycache__" not in str(py_file):
            print(f"   Indexing {py_file.relative_to(repo_path)}...")
            try:
                chunks = rag_service.index_file(str(py_file))
                print(f"     -> {chunks} chunks")
            except Exception as e:
                print(f"     -> Error: {e}")
    
    # 4. Test search
    print("\n4. Testing search functionality:")
    
    test_queries = [
        "get_user",
        "APIClient", 
        "def get_user",
        "error handling"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        try:
            # Use search_code method instead of search
            results = rag_service.search_code(query, k=3)
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results[:3]):
                chunk = result.chunk
                print(f"     {i+1}. {chunk.file_path}:{chunk.start_line} ({chunk.chunk_type})")
                if chunk.symbol_name:
                    print(f"        Symbol: {chunk.symbol_name}")
                print(f"        Preview: {chunk.content[:60]}...")
        except Exception as e:
            print(f"   Error: {e}")


def test_with_proper_context():
    """Test the coding agent with proper context."""
    
    print("\n\n=== Testing with Fixed RAG ===\n")
    
    from src.coding_agent.context_gatherer import ContextGatherer
    from src.proto_gen import messages_pb2
    
    repo_path = Path(__file__).parent / "test_repo"
    rag_dir = repo_path / ".rag"
    
    # Create RAG client
    rag_service = RAGService(persist_directory=str(rag_dir))
    
    # Create context gatherer
    context_gatherer = ContextGatherer(
        repo_path=str(repo_path),
        rag_client=rag_service
    )
    
    # Create a task
    task = messages_pb2.CodingTask()
    task.goal = "Add error handling to the get_user method in src/api_client.py"
    task.paths.append("src/api_client.py")
    
    print(f"Task: {task.goal}")
    
    # Gather context
    print("\nGathering context...")
    context = context_gatherer.gather_context(task)
    
    print(f"\nContext summary:")
    print(f"  - File snippets: {len(context.file_snippets)}")
    print(f"  - Related functions: {len(context.related_functions)}")
    print(f"  - Token count: {context.token_count}")
    
    # Check file content
    if "src/api_client.py" in context.file_snippets:
        snippet = context.file_snippets["src/api_client.py"]
        lines = snippet.split('\n')
        
        print(f"\nFile snippet check:")
        print(f"  - Lines: {len(lines)}")
        print(f"  - Has line numbers: {any(':' in line and line.strip()[:4].strip().isdigit() for line in lines if line.strip())}")
        
        # Find get_user method
        get_user_lines = [line for line in lines if 'get_user' in line]
        if get_user_lines:
            print(f"  - Found get_user method:")
            for line in get_user_lines[:3]:
                print(f"    {line}")
    
    # Check related functions
    if context.related_functions:
        print(f"\nRelated functions found:")
        for func in context.related_functions[:3]:
            print(f"  - {func['file']}:{func['line']} - {func['symbol']}")


if __name__ == "__main__":
    diagnose_rag_issues()
    fix_test_repo_rag()
    test_with_proper_context()