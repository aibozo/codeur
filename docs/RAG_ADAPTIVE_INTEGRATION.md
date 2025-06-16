# RAG Service Adaptive Integration Guide

This guide explains how to integrate the adaptive similarity gating system with the existing RAG service.

## Overview

The adaptive similarity gating system enhances the existing RAG service with:
- Intelligent filtering of search results based on learned patterns
- Quality feedback loops for continuous improvement
- Project-specific threshold adaptation
- Blindspot detection and mitigation

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User Query                        │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│            Adaptive RAG Service                      │
│  ┌─────────────────────────────────────────────┐   │
│  │           Base RAG Service                   │   │
│  │  - Vector Search (ChromaDB)                  │   │
│  │  - Keyword Search                            │   │
│  │  - Hybrid Search (RRF)                       │   │
│  └──────────────────┬──────────────────────────┘   │
│                     │                               │
│                     ▼                               │
│  ┌─────────────────────────────────────────────┐   │
│  │      Adaptive Similarity Gate                │   │
│  │  - Rolling Statistics (MAD/IQR)              │   │
│  │  - Project Profiles                         │   │
│  │  - Outlier Detection                        │   │
│  └──────────────────┬──────────────────────────┘   │
│                     │                               │
│                     ▼                               │
│  ┌─────────────────────────────────────────────┐   │
│  │        Context Quality Critic                │   │
│  │  - Relevance Analysis                        │   │
│  │  - Blindspot Detection                       │   │
│  │  - Feedback Generation                       │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Migration Path

### Option 1: Drop-in Replacement (Recommended)

Replace `RAGClient` with `AdaptiveRAGClient`:

```python
# Before
from src.rag_service import RAGClient

client = RAGClient(service=rag_service)
results = client.search("authentication implementation", k=10)

# After
from src.rag_service import AdaptiveRAGClient

client = AdaptiveRAGClient(service=rag_service)
client.set_project_context("my_project")
results = client.search("authentication implementation", k=10)
```

### Option 2: Service-Level Integration

Replace `RAGService` with `AdaptiveRAGService`:

```python
# Before
from src.rag_service import RAGService

rag_service = RAGService(
    persist_directory="./rag_data",
    repo_path="./my_repo"
)

# After
from src.rag_service import AdaptiveRAGService

rag_service = AdaptiveRAGService(
    persist_directory="./rag_data",
    repo_path="./my_repo",
    enable_adaptive_gating=True
)
```

### Option 3: Upgrade Existing Instances

Convert existing services/clients:

```python
from src.rag_service import AdaptiveRAGService, AdaptiveRAGClient

# Upgrade existing service
adaptive_service = AdaptiveRAGService.from_existing_service(
    existing_rag_service,
    enable_adaptive_gating=True
)

# Or upgrade existing client
adaptive_client = AdaptiveRAGClient.from_rag_client(
    existing_client,
    enable_adaptive_gating=True
)
```

## Usage Examples

### Basic Search with Adaptive Filtering

```python
from src.rag_service import AdaptiveRAGClient

# Initialize client
client = AdaptiveRAGClient()
client.set_project_context("fastapi_project")

# Search with automatic filtering
results = client.search(
    query="How to implement JWT authentication?",
    k=10,
    retrieval_type="code_search"  # Specialized handling
)

# Results are automatically filtered based on learned patterns
for result in results:
    print(f"{result.chunk.file_path}: {result.score:.3f}")
    if "gating_reason" in result.metadata:
        print(f"  Included because: {result.metadata['gating_reason']}")
```

### Context Retrieval with Quality Analysis

```python
# Get context with automatic quality critique
context, critique = client.get_context(
    query="Show me the user authentication flow",
    k=10,
    max_tokens=3000,
    auto_critique=True
)

print(f"Context quality: {critique['quality_score']:.2f}")
print(f"Blindspots detected: {critique['blindspots']}")
print(f"Suggestions: {critique['suggestions']}")

# Use the context
response = llm.generate(prompt=context)
```

### Providing Feedback

```python
# After using search results, provide feedback
chunk_ids = [r.chunk.id for r in results]
usefulness = [True, True, True, False, False]  # Last 2 weren't useful

client.provide_feedback(
    chunk_ids=chunk_ids,
    useful=usefulness,
    missing_context="Need more details about token refresh",
    unnecessary_chunks=chunk_ids[-2:]  # Last 2 chunks
)

# The system will adapt thresholds for future queries
```

### Monitoring Adaptation

```python
# Get statistics about adaptive behavior
stats = client.get_adaptive_stats()

print(f"Current threshold: {stats['gating_stats']['statistics']['code_search']['current_threshold']}")
print(f"Precision: {stats['gating_stats']['statistics']['code_search']['precision']}")
print(f"Quality trend: {stats['critique_summary']['quality_trend']}")

# Reset if needed
client.reset_adaptive_profile()
```

## Integration with Existing Components

### Architect Integration

The Architect already has a placeholder for RAG enhancement:

```python
from src.architect.context_aware_architect import ContextAwareArchitect
from src.rag_service import AdaptiveRAGClient

# Create adaptive RAG client
rag_client = AdaptiveRAGClient()
rag_client.set_project_context(project_id)

# Use with architect
architect = ContextAwareArchitect(
    project_path="./project",
    rag_service=rag_client.service  # Pass adaptive service
)
```

### Code Planner Integration

Update the CodePlannerRAGIntegration:

```python
from src.code_planner.rag_integration import CodePlannerRAGIntegration
from src.rag_service import AdaptiveRAGClient

class AdaptiveCodePlannerRAG(CodePlannerRAGIntegration):
    def __init__(self, rag_client: AdaptiveRAGClient):
        super().__init__(rag_client)
        self.adaptive_client = rag_client
    
    async def get_relevant_code_for_task(self, task, spec):
        # Set project context
        self.adaptive_client.set_project_context(task.project_id)
        
        # Use enhanced search
        results = await super().get_relevant_code_for_task(task, spec)
        
        # Check quality if needed
        if len(results) < 3:
            stats = self.adaptive_client.get_adaptive_stats()
            if stats['critique_summary']['avg_blindspots'] > 2:
                # Adjust search parameters
                pass
        
        return results
```

## Configuration

### Environment Variables

```bash
# Enable/disable adaptive features
ADAPTIVE_RAG_ENABLED=true

# Adaptation parameters
ADAPTIVE_RATE=0.1  # How quickly to adapt (0-1)
OUTLIER_METHOD=mad  # mad, iqr, or zscore

# Quality thresholds
MIN_CONTEXT_QUALITY=0.7
MAX_BLINDSPOTS=3
```

### Project-Specific Configuration

```python
# Configure per-project settings
from src.core.adaptive_similarity_gate import GatingStatistics

# Get project profile
profile = rag_service.similarity_gate.profiles["my_project"]

# Adjust settings
profile.statistics["code_search"].base_threshold = 0.75
profile.statistics["code_search"].min_threshold = 0.5
profile.statistics["code_search"].max_threshold = 0.9
profile.target_chunks_per_retrieval = 7
```

## Performance Considerations

### Memory Usage

- Each project profile: ~10KB
- Embedding cache: ~1MB per 1000 embeddings
- Rolling statistics: ~100KB per retrieval type

### Processing Overhead

- Adaptive filtering: +5-10ms per search
- Quality critique: +50-100ms (if enabled)
- Feedback processing: +2-5ms

### Optimization Tips

1. **Batch Operations**: Process multiple queries together
2. **Selective Critique**: Only critique important retrievals
3. **Profile Cleanup**: Periodically clean old project profiles
4. **Cache Management**: Clear embedding cache periodically

## Troubleshooting

### Issue: Too Many Results Filtered Out

```python
# Check current statistics
stats = client.get_adaptive_stats()
print(f"Current threshold: {stats['gating_stats']['statistics']['code_search']['current_threshold']}")

# Lower the threshold temporarily
profile = rag_service.similarity_gate.profiles[project_id]
profile.statistics["code_search"].current_threshold *= 0.9

# Or reset the profile
client.reset_adaptive_profile()
```

### Issue: Poor Quality Results

```python
# Enable critique to understand issues
context, critique = client.get_context(query, auto_critique=True)

# Check for patterns
if critique['blindspots'] > 3:
    print("Missing important context")
elif critique['unnecessary_chunks'] > len(results) * 0.3:
    print("Too much noise in results")

# Provide explicit feedback
client.provide_feedback(
    chunk_ids=[...],
    useful=[...],
    missing_context="Need X, Y, Z"
)
```

### Issue: Slow Adaptation

```python
# Increase adaptation rate
rag_service.similarity_gate.adaptation_rate = 0.2  # Default is 0.1

# Or provide more feedback
for query, expected_useful in training_data:
    results = client.search(query)
    client.provide_feedback(
        chunk_ids=[r.chunk.id for r in results],
        useful=expected_useful
    )
```

## Best Practices

1. **Set Project Context**: Always set project context for better adaptation
2. **Use Retrieval Types**: Specify retrieval type for specialized handling
3. **Monitor Quality**: Check critique summaries periodically
4. **Provide Feedback**: Especially for poor results
5. **Profile Management**: Reset profiles when project scope changes significantly

## API Compatibility

The adaptive components maintain full API compatibility with the base RAG service:

| Method | Base Behavior | Adaptive Enhancement |
|--------|--------------|---------------------|
| `search()` | Returns k results | Filters to k best results |
| `get_context()` | Returns string | Returns (string, critique) |
| `find_similar()` | Basic similarity | Adaptive filtering |
| `find_symbol()` | Unchanged | Unchanged |

All enhancements are additive and backward compatible.