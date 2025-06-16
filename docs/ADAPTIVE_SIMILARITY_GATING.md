# Adaptive Similarity Gating System

The adaptive similarity gating system provides intelligent, self-improving context retrieval for the agent system. It learns from feedback to optimize chunk selection and reduce noise in retrieved context.

## Overview

The system consists of three main components:

1. **Adaptive Similarity Gate** - Filters retrieval results with project-specific thresholds
2. **Context Quality Critic** - Analyzes context quality and identifies issues
3. **Context Graph RAG Enhancer** - Integrates both systems with the context graph

## Key Features

### 1. Outlier-Resistant Filtering

The system uses multiple statistical methods to identify relevant chunks:

- **MAD (Median Absolute Deviation)** - Robust to outliers, default method
- **IQR (Interquartile Range)** - Good for skewed distributions
- **Z-score** - Traditional method for normal distributions

```python
from src.core.adaptive_similarity_gate import AdaptiveSimilarityGate

# Create gate with MAD method
gate = AdaptiveSimilarityGate(
    adaptation_rate=0.1,  # How quickly to adapt (0-1)
    outlier_method="mad"  # Options: "mad", "iqr", "zscore"
)
```

### 2. Project-Specific Learning

Each project maintains its own gating profile that adapts over time:

```python
# Filter results for a specific project
filtered_results = gate.filter_results(
    results=search_results,
    project_id="my_project",
    retrieval_type="code_search",  # Different types can have different thresholds
    target_chunks=5,  # Desired number of chunks
    min_chunks=2,     # Minimum to include
    max_chunks=10     # Maximum to include
)
```

### 3. Quality Feedback Loop

The quality critic analyzes retrieved context and provides feedback:

```python
from src.core.context_quality_critic import ContextQualityCritic

critic = ContextQualityCritic(llm_client=openai_client)

# Critique context quality
critique = await critic.critique_context(
    query="How to implement authentication?",
    context_chunks=filtered_chunks,
    task_type="code"  # Options: "code", "documentation", "planning"
)

# Provide feedback to gate
gate.record_feedback(
    project_id="my_project",
    retrieval_type="code_search",
    feedback={
        "chunk_ids": chunk_ids,
        "useful": [True, True, False, False],  # Which chunks were useful
        "unnecessary_chunks": ["chunk_3", "chunk_4"],
        "missing_context": "Need user model definition"
    }
)
```

### 4. Intelligent Threshold Adaptation

The system adapts thresholds using multiple signals:

1. **Target-based** - Adjusts to retrieve desired number of chunks
2. **Statistical** - Uses rolling statistics to find natural cutoffs
3. **Quality-based** - Responds to precision/recall feedback

## Integration with Context Graph

The Context Graph RAG Enhancer brings everything together:

```python
from src.architect.context_graph_rag_enhancer import ContextGraphRAGEnhancer

# Create integrated system
enhancer = ContextGraphRAGEnhancer(
    context_graph=context_graph,
    rag_client=rag_client,
    similarity_gate=gate,
    quality_critic=critic
)

# Compile enhanced context with automatic optimization
enhanced_window = await enhancer.compile_enhanced_context(
    query="Show me authentication implementation",
    current_node_id=current_node.id,
    max_tokens=8000,
    include_rag=True,     # Include RAG results
    auto_critique=True    # Run quality analysis
)

# Access results
print(f"Quality score: {enhanced_window.quality_score}")
print(f"Blindspots: {enhanced_window.critique_summary['blindspots']}")
```

## Adaptive Strategies

### 1. Multiple Filtering Strategies

The gate combines multiple strategies for robust filtering:

- **Threshold-based** - Traditional similarity threshold
- **Outlier detection** - Removes statistical outliers
- **Elbow method** - Finds natural cutoff points
- **Minimum guarantee** - Ensures minimum chunks included

### 2. Context Quality Metrics

The critic evaluates context on multiple dimensions:

- **Relevance** - How well chunks match the query
- **Coverage** - Breadth of information covered
- **Redundancy** - Duplicate or similar content
- **Completeness** - Missing information detection
- **Noise ratio** - Proportion of irrelevant content

### 3. Blindspot Detection

The system identifies missing context through:

- **Code analysis** - Missing imports, undefined references
- **Pattern matching** - Common missing elements
- **LLM analysis** - Sophisticated gap detection

## Performance Characteristics

### Adaptation Speed

- **Fast adaptation** (rate=0.2-0.3): Good for experimentation
- **Moderate adaptation** (rate=0.1-0.15): Balanced approach
- **Slow adaptation** (rate=0.05-0.1): Stable production use

### Statistical Methods

| Method | Best For | Outlier Sensitivity | Computation |
|--------|----------|-------------------|-------------|
| MAD | General use | Low (robust) | Fast |
| IQR | Skewed data | Medium | Fast |
| Z-score | Normal data | High | Fastest |

### Quality Feedback Impact

- **Precision < 0.8**: Threshold increases (fewer chunks)
- **Recall < 0.8**: Threshold decreases (more chunks)
- **Missing context**: Lower threshold by 5%
- **>30% unnecessary**: Raise threshold by 5%

## Best Practices

### 1. Initialize with Representative Queries

Run a few typical queries to establish baseline statistics:

```python
# Warm up the system
for query in training_queries:
    results = gate.filter_results(...)
    critique = await critic.critique_context(...)
    gate.record_feedback(...)
```

### 2. Monitor Adaptation

Track how thresholds evolve:

```python
stats = gate.get_statistics("my_project")
print(f"Current threshold: {stats['statistics']['code_search']['current_threshold']}")
print(f"Adaptation from base: {stats['statistics']['code_search']['base_threshold']}")
```

### 3. Use Appropriate Retrieval Types

Different content needs different handling:

- `"code_search"` - Source code retrieval
- `"documentation"` - Documentation and comments
- `"context_graph"` - Conversation history
- `"planning"` - Architecture and design docs

### 4. Analyze Patterns

Use built-in analysis tools:

```python
analysis = await enhancer.analyze_retrieval_patterns()

for recommendation in analysis["recommendations"]:
    print(f"- {recommendation}")
```

## Troubleshooting

### High False Positive Rate

- Check if outlier method matches data distribution
- Consider increasing adaptation rate temporarily
- Review feedback quality

### Missing Important Context

- Lower minimum threshold in config
- Check if retrieval is too narrow
- Consider different retrieval types

### Slow Adaptation

- Increase adaptation rate
- Provide more explicit feedback
- Check if statistics have enough data (20+ retrievals)

### Threshold Oscillation

- Decrease adaptation rate
- Check for conflicting feedback
- Consider separate profiles for different query types

## Example: Complete Integration

```python
# 1. Setup components
gate = AdaptiveSimilarityGate(
    adaptation_rate=0.1,
    outlier_method="mad"
)

critic = ContextQualityCritic(
    llm_client=openai_client
)

enhancer = ContextGraphRAGEnhancer(
    context_graph=architect.context_graph,
    rag_client=rag_service,
    similarity_gate=gate,
    quality_critic=critic
)

# 2. Process query with enhancement
enhanced_context = await enhancer.compile_enhanced_context(
    query=user_query,
    current_node_id=current_node.id,
    max_tokens=8000
)

# 3. Use enhanced context
response = await llm.generate(
    prompt=enhanced_context.get_formatted_context(),
    query=user_query
)

# 4. System automatically adapts based on quality
# No manual intervention needed!
```

## Benefits

1. **Reduced Noise** - Filters out irrelevant chunks automatically
2. **Better Recall** - Identifies and addresses context gaps
3. **Cost Efficiency** - Retrieves optimal amount of context
4. **Self-Improving** - Gets better with use
5. **Project-Specific** - Adapts to each project's patterns