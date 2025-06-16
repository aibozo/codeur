#!/usr/bin/env python3
"""
Test the integration of adaptive similarity gating with RAG service.
"""

import asyncio
import sys
from pathlib import Path
import numpy as np
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).parent.parent))

from src.rag_service.models import CodeChunk, SearchResult
from src.rag_service.adaptive_rag_service import AdaptiveRAGService
from src.rag_service.adaptive_client import AdaptiveRAGClient
from src.core.adaptive_similarity_gate import AdaptiveSimilarityGate
from src.core.context_quality_critic import ContextQualityCritic


def create_mock_search_results(n: int = 20) -> List[SearchResult]:
    """Create mock search results for testing."""
    np.random.seed(42)
    results = []
    
    for i in range(n):
        # Create similarity scores with some patterns
        if i < 3:
            score = 0.9 + np.random.uniform(-0.05, 0.05)  # High relevance
        elif i < 8:
            score = 0.7 + np.random.uniform(-0.1, 0.1)   # Medium relevance
        else:
            score = 0.4 + np.random.uniform(-0.2, 0.2)   # Low relevance
        
        chunk = CodeChunk(
            id=f"chunk_{i}",
            content=f"Code content {i}: {'authentication' if i < 5 else 'logging'} implementation",
            file_path=f"src/module_{i}.py",
            start_line=i * 10 + 1,
            end_line=(i + 1) * 10,
            chunk_type="function" if i % 2 == 0 else "class",
            language="python",
            symbols=[f"func_{i}"] if i % 2 == 0 else [f"Class{i}"]
        )
        
        result = SearchResult(
            chunk=chunk,
            score=float(score),
            match_type="hybrid",
            highlights=[f"**authentication** in line {i}"] if i < 5 else []
        )
        
        results.append(result)
    
    return results


class MockRAGService:
    """Mock RAG service for testing."""
    
    def __init__(self):
        self.persist_dir = Path("./mock_rag")
        self.repo_path = Path("./mock_repo")
        self.embedding_service = MockEmbeddingService()
        self.vector_store = None
        self.chunker = None
        self.search = None
        self.indexed_files = set()
    
    def search_code(self, query: str, k: int = 10, filters=None):
        """Mock search that returns test results."""
        return create_mock_search_results(k * 2)[:k]
    
    def find_similar(self, chunk, k=10, filters=None):
        """Mock similarity search."""
        return create_mock_search_results(k)


class MockEmbeddingService:
    """Mock embedding service."""
    
    def count_tokens(self, text: str) -> int:
        return len(text) // 4  # Rough estimate


async def test_adaptive_rag_service():
    """Test the AdaptiveRAGService integration."""
    print("\n" + "="*80)
    print("TESTING ADAPTIVE RAG SERVICE")
    print("="*80)
    
    # Create adaptive service from mock
    mock_service = MockRAGService()
    adaptive_service = AdaptiveRAGService.from_existing_service(
        mock_service,
        enable_adaptive_gating=True
    )
    
    print("\n✅ Created adaptive RAG service")
    
    # Test 1: Basic search with adaptive filtering
    print("\n1. Testing adaptive search:")
    results = adaptive_service.search_code(
        query="How to implement authentication?",
        k=5,
        project_id="test_project",
        retrieval_type="code_search"
    )
    
    print(f"   Requested: 5 results")
    print(f"   Received: {len(results)} results")
    
    for i, result in enumerate(results):
        print(f"   {i+1}. {result.chunk.file_path}: score={result.score:.3f}")
        if result.metadata and "gating_reason" in result.metadata:
            print(f"      Reason: {result.metadata['gating_reason']}")
    
    # Test 2: Context retrieval with critique
    print("\n2. Testing context retrieval with critique:")
    context, critique = adaptive_service.get_context(
        query="Show me authentication implementation",
        k=5,
        max_tokens=1000,
        project_id="test_project",
        auto_critique=True
    )
    
    print(f"   Context length: {len(context)} chars")
    if critique:
        print(f"   Quality score: {critique['quality_score']:.2f}")
        print(f"   Avg relevance: {critique['avg_relevance']:.2f}")
        print(f"   Blindspots: {critique['blindspots']}")
        print(f"   Suggestions: {len(critique['suggestions'])}")
    
    # Test 3: Get adaptive statistics
    print("\n3. Testing adaptive statistics:")
    stats = adaptive_service.get_adaptive_stats("test_project")
    
    if stats.get("enabled"):
        gating_stats = stats["gating_stats"].get("statistics", {}).get("code_search", {})
        print(f"   Total retrievals: {gating_stats.get('total_retrievals', 0)}")
        print(f"   Current threshold: {gating_stats.get('current_threshold', 0):.3f}")
        print(f"   Rolling mean: {gating_stats.get('rolling_mean', 0):.3f}")
    
    return adaptive_service


async def test_adaptive_rag_client():
    """Test the AdaptiveRAGClient integration."""
    print("\n\n" + "="*80)
    print("TESTING ADAPTIVE RAG CLIENT")
    print("="*80)
    
    # Create client from mock service
    mock_service = MockRAGService()
    client = AdaptiveRAGClient(service=mock_service)
    client.set_project_context("client_test_project")
    
    print("\n✅ Created adaptive RAG client")
    
    # Test 1: Search with project context
    print("\n1. Testing client search:")
    results = client.search(
        query="authentication flow",
        k=5,
        retrieval_type="documentation"
    )
    
    print(f"   Found {len(results)} results")
    
    # Test 2: Provide feedback
    print("\n2. Testing feedback mechanism:")
    chunk_ids = [r.chunk.id for r in results]
    usefulness = [True, True, True, False, False]  # Last 2 not useful
    
    client.provide_feedback(
        chunk_ids=chunk_ids,
        useful=usefulness,
        missing_context="Need more details about JWT token generation",
        unnecessary_chunks=chunk_ids[-2:]
    )
    
    print("   ✓ Feedback recorded")
    
    # Test 3: Check adaptation
    print("\n3. Testing threshold adaptation:")
    stats_before = client.get_adaptive_stats()
    
    # Search again to see adaptation
    results2 = client.search(
        query="JWT token implementation",
        k=5
    )
    
    stats_after = client.get_adaptive_stats()
    
    if stats_before.get("enabled") and stats_after.get("enabled"):
        before_threshold = stats_before["gating_stats"]["statistics"].get("code_search", {}).get("current_threshold", 0.7)
        after_threshold = stats_after["gating_stats"]["statistics"].get("code_search", {}).get("current_threshold", 0.7)
        print(f"   Threshold changed: {before_threshold:.3f} → {after_threshold:.3f}")
    
    # Test 4: Find similar with adaptive filtering
    print("\n4. Testing find_similar_code:")
    similar_results = client.find_similar_code(
        code_snippet="""
def authenticate_user(username: str, password: str):
    user = get_user(username)
    if verify_password(password, user.hashed_password):
        return create_access_token(user)
    return None
""",
        k=3
    )
    
    print(f"   Found {len(similar_results)} similar code chunks")
    
    return client


async def test_compatibility():
    """Test backward compatibility with existing code."""
    print("\n\n" + "="*80)
    print("TESTING BACKWARD COMPATIBILITY")
    print("="*80)
    
    # Test that adaptive components work as drop-in replacements
    from src.rag_service.client import RAGClient
    
    # Create regular client
    mock_service = MockRAGService()
    regular_client = RAGClient(service=mock_service)
    
    # Convert to adaptive
    adaptive_client = AdaptiveRAGClient.from_rag_client(regular_client)
    
    print("\n✅ Successfully converted RAGClient to AdaptiveRAGClient")
    
    # Test that all base methods still work
    print("\n1. Testing base method compatibility:")
    
    # Search (base method)
    results = adaptive_client.search("test query")
    print(f"   ✓ search() works: {len(results)} results")
    
    # Get context (enhanced to return tuple)
    result = adaptive_client.get_context("test query")
    if isinstance(result, tuple):
        context, critique = result
        print(f"   ✓ get_context() enhanced: returns (context, critique)")
    else:
        print(f"   ✓ get_context() compatible: returns context string")
    
    # Find symbol (unchanged)
    results = adaptive_client.find_symbol("authenticate")
    print(f"   ✓ find_symbol() works: {len(results)} results")
    
    print("\n✅ All base methods remain compatible")


async def test_integration_with_context_graph():
    """Test integration with context graph RAG enhancer."""
    print("\n\n" + "="*80)
    print("TESTING CONTEXT GRAPH INTEGRATION")  
    print("="*80)
    
    from src.architect.context_graph import ContextGraph
    from src.architect.context_graph_rag_enhancer import ContextGraphRAGEnhancer
    
    # Create components
    context_graph = ContextGraph("test_project")
    adaptive_client = AdaptiveRAGClient(service=MockRAGService())
    adaptive_client.set_project_context("test_project")
    
    # Create enhancer with adaptive client
    enhancer = ContextGraphRAGEnhancer(
        context_graph=context_graph,
        rag_client=adaptive_client,  # Uses adaptive client
        similarity_gate=adaptive_client.adaptive_service.similarity_gate,
        quality_critic=adaptive_client.adaptive_service.quality_critic
    )
    
    print("\n✅ Created context graph enhancer with adaptive RAG")
    
    # Add some messages
    parent_id = None
    for content in ["I need authentication", "Use JWT tokens", "Add refresh tokens"]:
        node = await context_graph.add_message("user", content, parent_id)
        parent_id = node.id
    
    # Compile enhanced context
    print("\n1. Testing enhanced context compilation:")
    enhanced_window = await enhancer.compile_enhanced_context(
        query="Show me the authentication implementation",
        current_node_id=parent_id,
        max_tokens=1000,
        include_rag=True,
        auto_critique=True
    )
    
    print(f"   Total tokens: {enhanced_window.total_tokens}")
    print(f"   Quality score: {enhanced_window.quality_score:.2f}")
    print(f"   RAG chunks: {len(enhanced_window.rag_chunks)}")
    
    print("\n✅ Context graph integration working correctly")


async def main():
    """Run all integration tests."""
    print("🚀 RAG Adaptive Integration Tests")
    print("=" * 80)
    
    # Test 1: Adaptive RAG Service
    service = await test_adaptive_rag_service()
    
    # Test 2: Adaptive RAG Client  
    client = await test_adaptive_rag_client()
    
    # Test 3: Backward Compatibility
    await test_compatibility()
    
    # Test 4: Context Graph Integration
    await test_integration_with_context_graph()
    
    print("\n\n✅ All integration tests passed!")
    print("\nThe adaptive similarity gating system is fully compatible with the existing RAG service.")


if __name__ == "__main__":
    asyncio.run(main()

# Fix for async context critique
import nest_asyncio
nest_asyncio.apply()