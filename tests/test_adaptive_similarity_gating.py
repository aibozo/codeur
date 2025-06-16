#!/usr/bin/env python3
"""
Test and demonstrate the adaptive similarity gating system.
"""

import asyncio
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.adaptive_similarity_gate import AdaptiveSimilarityGate, GatingStatistics
from src.core.context_quality_critic import ContextQualityCritic, ContextChunk
from src.architect.context_graph_rag_enhancer import ContextGraphRAGEnhancer
from src.architect.context_graph import ContextGraph
from src.architect.context_graph_models import ResolutionConfig


async def demo_adaptive_gating():
    """Demonstrate adaptive similarity gating with feedback loop."""
    
    print("\n" + "="*80)
    print("ADAPTIVE SIMILARITY GATING DEMO")
    print("="*80)
    
    # Create adaptive similarity gate
    gate = AdaptiveSimilarityGate(
        adaptation_rate=0.2,  # Faster adaptation for demo
        outlier_method="mad"  # Median Absolute Deviation
    )
    
    print("\n✅ Created adaptive similarity gate")
    
    # Simulate retrieval results with varying quality
    print("\n📊 Simulating retrieval scenarios...")
    
    # Scenario 1: Good distribution of similarities
    print("\n1. Well-distributed similarities:")
    results1 = [
        {"id": f"chunk_{i}", "content": f"Content {i}", "similarity": score}
        for i, score in enumerate([0.95, 0.88, 0.82, 0.75, 0.71, 0.65, 0.58, 0.45, 0.38, 0.25])
    ]
    
    filtered1 = gate.filter_results(
        results=results1,
        project_id="demo_project",
        retrieval_type="code_search",
        target_chunks=5
    )
    
    included1 = [r for r in filtered1 if r.included]
    print(f"   Included: {len(included1)}/{len(results1)} chunks")
    print(f"   Threshold: {gate.profiles['demo_project'].statistics['code_search'].current_threshold:.3f}")
    for r in included1:
        print(f"   - {r.chunk_id}: {r.similarity_score:.3f} ({r.reason})")
    
    # Scenario 2: Results with outliers
    print("\n2. Results with outliers:")
    results2 = [
        {"id": f"chunk_{i}", "content": f"Content {i}", "similarity": score}
        for i, score in enumerate([0.92, 0.90, 0.89, 0.88, 0.35, 0.33, 0.30, 0.28, 0.25, 0.20])
    ]
    
    filtered2 = gate.filter_results(
        results=results2,
        project_id="demo_project",
        retrieval_type="code_search",
        target_chunks=4
    )
    
    included2 = [r for r in filtered2 if r.included]
    print(f"   Included: {len(included2)}/{len(results2)} chunks")
    print(f"   Outliers detected: {sum(1 for r in filtered2 if r.reason == 'not_outlier')}")
    
    # Scenario 3: Provide feedback and adapt
    print("\n3. Feedback loop demonstration:")
    
    # Simulate negative feedback (too many irrelevant chunks)
    feedback = {
        "chunk_ids": [r.chunk_id for r in included1],
        "useful": [True, True, True, False, False],  # Last 2 were not useful
        "unnecessary_chunks": [included1[-2].chunk_id, included1[-1].chunk_id]
    }
    
    print("   Providing feedback: 2 unnecessary chunks")
    gate.record_feedback(
        project_id="demo_project",
        retrieval_type="code_search",
        feedback=feedback
    )
    
    # Run same query again to see adaptation
    filtered3 = gate.filter_results(
        results=results1,  # Same results
        project_id="demo_project",
        retrieval_type="code_search",
        target_chunks=5
    )
    
    included3 = [r for r in filtered3 if r.included]
    new_threshold = gate.profiles['demo_project'].statistics['code_search'].current_threshold
    print(f"   New threshold: {new_threshold:.3f} (adapted based on feedback)")
    print(f"   Now included: {len(included3)} chunks")
    
    # Show statistics
    print("\n📈 Gating Statistics:")
    stats = gate.get_statistics("demo_project", "code_search")
    print(f"   Total retrievals: {stats['total_retrievals']}")
    print(f"   Rolling mean similarity: {stats['rolling_mean']:.3f}")
    print(f"   Rolling median: {stats['rolling_median']:.3f}")
    print(f"   MAD (spread): {stats['mad']:.3f}")
    print(f"   Precision: {stats['precision']:.3f}")
    
    return gate


async def demo_quality_critic():
    """Demonstrate context quality critic."""
    
    print("\n\n" + "="*80)
    print("CONTEXT QUALITY CRITIC DEMO")
    print("="*80)
    
    critic = ContextQualityCritic()
    print("\n✅ Created context quality critic")
    
    # Create sample context chunks
    query = "How do I implement user authentication in FastAPI?"
    
    context_chunks = [
        ContextChunk(
            chunk_id="1",
            content="""from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext""",
            similarity_score=0.92,
            metadata={"file": "auth.py", "type": "imports"}
        ),
        ContextChunk(
            chunk_id="2",
            content="""def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt""",
            similarity_score=0.88,
            metadata={"file": "auth.py", "type": "function"}
        ),
        ContextChunk(
            chunk_id="3",
            content="""# This is a general utility function for logging
def log_request(request: Request):
    logger.info(f"Request: {request.method} {request.url}")""",
            similarity_score=0.45,
            metadata={"file": "utils.py", "type": "logging"}
        ),
        ContextChunk(
            chunk_id="4",
            content="""@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}""",
            similarity_score=0.95,
            metadata={"file": "main.py", "type": "endpoint"}
        ),
        ContextChunk(
            chunk_id="5",
            content="""# Database models for the application
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)""",
            similarity_score=0.65,
            metadata={"file": "models.py", "type": "database"}
        )
    ]
    
    print("\n🔍 Critiquing context quality...")
    critique = await critic.critique_context(
        query=query,
        context_chunks=context_chunks,
        task_type="code"
    )
    
    print(f"\n📊 Critique Results:")
    print(f"   Overall Quality: {critique.overall_quality:.2f}/1.0")
    print(f"\n   Relevance Scores:")
    for chunk_id, score in critique.relevance_scores.items():
        chunk = next(c for c in context_chunks if c.chunk_id == chunk_id)
        print(f"   - Chunk {chunk_id} ({chunk.metadata.get('type', 'unknown')}): {score:.2f}")
    
    print(f"\n   🚫 Unnecessary Chunks: {critique.unnecessary_chunks}")
    print(f"\n   ⚠️  Blindspots Detected:")
    for blindspot in critique.blindspots:
        print(f"   - {blindspot}")
    
    print(f"\n   💡 Suggestions:")
    for suggestion in critique.suggestions:
        print(f"   - {suggestion}")
    
    print(f"\n   📈 Quality Metrics:")
    for metric, value in critique.metrics.items():
        print(f"   - {metric}: {value:.3f}")
    
    return critic


async def demo_integrated_system():
    """Demonstrate the fully integrated RAG enhancement system."""
    
    print("\n\n" + "="*80)
    print("INTEGRATED RAG ENHANCEMENT DEMO")
    print("="*80)
    
    # Create components
    config = ResolutionConfig(
        full_context_distance=3,
        summary_distance=6,
        title_distance=10
    )
    
    context_graph = ContextGraph("demo_project", config)
    similarity_gate = AdaptiveSimilarityGate()
    quality_critic = ContextQualityCritic()
    
    # Create mock RAG client
    class MockRAGClient:
        def search(self, query, k=10, filters=None):
            # Simulate search results (synchronous for compatibility)
            np.random.seed(42)
            scores = np.random.beta(5, 2, k)  # Skewed towards higher scores
            scores.sort()
            scores = scores[::-1]  # Descending order
            
            return [
                {
                    "id": f"rag_{i}",
                    "content": f"RAG result {i}: Content related to {query[:20]}...",
                    "similarity": float(score),
                    "metadata": {"source": "documentation", "relevance": score > 0.7}
                }
                for i, score in enumerate(scores)
            ]
        
        async def get_embedding(self, text):
            # Simulate embeddings
            np.random.seed(hash(text) % 1000)
            return np.random.randn(384).tolist()
    
    # Create enhancer
    enhancer = ContextGraphRAGEnhancer(
        context_graph=context_graph,
        rag_client=MockRAGClient(),
        similarity_gate=similarity_gate,
        quality_critic=quality_critic
    )
    
    print("\n✅ Created integrated RAG enhancement system")
    
    # Add some messages to the graph
    print("\n💬 Building conversation context...")
    parent_id = None
    for i, (role, content) in enumerate([
        ("user", "I need to build a user authentication system"),
        ("assistant", "I'll help you design a user authentication system. What technology stack are you using?"),
        ("user", "I'm using FastAPI with PostgreSQL"),
        ("assistant", "Great choice! Here's how to implement authentication in FastAPI..."),
        ("user", "How do I handle password hashing?"),
        ("assistant", "Use passlib with bcrypt for secure password hashing..."),
    ]):
        node = await context_graph.add_message(role, content, parent_id=parent_id)
        parent_id = node.id
        print(f"   Added: {role} - {content[:50]}...")
    
    # Compile enhanced context
    print("\n🔧 Compiling enhanced context...")
    query = "Show me the complete authentication implementation with JWT tokens"
    
    enhanced_window = await enhancer.compile_enhanced_context(
        query=query,
        current_node_id=parent_id,
        max_tokens=2000,
        include_rag=True,
        auto_critique=True
    )
    
    print(f"\n📊 Enhanced Context Window:")
    print(f"   Total tokens: {enhanced_window.total_tokens}")
    print(f"   Graph nodes: {len(enhanced_window.nodes)}")
    print(f"   RAG chunks: {sum(1 for c in enhanced_window.rag_chunks if c.included)}")
    print(f"   Quality score: {enhanced_window.quality_score:.2f}")
    
    print(f"\n   Critique Summary:")
    for key, value in enhanced_window.critique_summary.items():
        print(f"   - {key}: {value}")
    
    # Analyze patterns
    print("\n📈 Retrieval Pattern Analysis:")
    analysis = await enhancer.analyze_retrieval_patterns()
    
    print(f"\n   Recommendations:")
    for rec in analysis["recommendations"]:
        print(f"   - {rec}")
    
    print(f"\n   Performance Stats:")
    for stat, value in analysis["retrieval_stats"].items():
        print(f"   - {stat}: {value}")
    
    return enhancer


async def main():
    """Run all demonstrations."""
    
    print("🚀 Adaptive Similarity Gating and Context Quality System")
    print("=" * 80)
    
    # Demo 1: Adaptive Gating
    gate = await demo_adaptive_gating()
    
    # Demo 2: Quality Critic
    critic = await demo_quality_critic()
    
    # Demo 3: Integrated System
    enhancer = await demo_integrated_system()
    
    print("\n\n✅ All demonstrations complete!")
    print("\nKey Takeaways:")
    print("1. Adaptive gating learns from feedback to improve chunk selection")
    print("2. Quality critic identifies blindspots and unnecessary context")
    print("3. Integrated system provides intelligent context compilation")
    print("4. Project-specific thresholds adapt over time")
    print("5. Multiple statistical methods ensure robustness to outliers")


if __name__ == "__main__":
    asyncio.run(main())