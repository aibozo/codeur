# Context Graph System Design

**Status: ✅ IMPLEMENTED** - The context graph system is fully implemented and integrated with the Architect agent as `ContextAwareArchitect`.

## Overview
A dynamic context management system that builds a graph of conversation nodes, using summarization and embeddings to intelligently manage context length while preserving access to detailed historical information.

## Core Concepts

### 1. Message Node Structure
```python
@dataclass
class MessageNode:
    id: str
    timestamp: datetime
    role: str  # "user" or "assistant"
    content: str
    summary: Optional[str] = None
    embedding: Optional[List[float]] = None
    token_count: int = 0
    
    # Graph relationships
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    # Task association
    task_ids: List[str] = field(default_factory=list)
    
    # Community membership
    community_id: Optional[str] = None
    
    # Metadata
    importance_score: float = 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
```

### 2. Context Resolution Levels
- **FULL**: Complete original message
- **SUMMARY**: AI-generated summary
- **TITLE**: One-line description
- **HIDDEN**: Not included in context

### 3. Distance-Based Resolution (Configurable)
```python
@dataclass
class ResolutionConfig:
    """Configurable thresholds for context resolution."""
    # Distance thresholds
    full_context_distance: int = 5
    summary_distance: int = 20
    title_distance: int = 50
    
    # Token thresholds
    max_full_tokens_per_node: int = 500
    max_summary_tokens: int = 100
    max_title_tokens: int = 20
    
    # Community thresholds
    min_nodes_for_community: int = 5
    max_community_summary_tokens: int = 200
    community_inclusion_distance: int = 100
    
    # Performance tuning
    batch_size: int = 10
    summarization_delay_seconds: int = 60
    cache_ttl_seconds: int = 3600
    
    # Cost controls
    daily_summarization_budget: float = 1.0  # USD
    enable_embedding_generation: bool = True
    embedding_batch_size: int = 50

# Default configurations
AGGRESSIVE_COMPRESSION = ResolutionConfig(
    full_context_distance=3,
    summary_distance=10,
    title_distance=25,
    max_summary_tokens=50
)

BALANCED = ResolutionConfig()  # Uses defaults

CONTEXT_RICH = ResolutionConfig(
    full_context_distance=10,
    summary_distance=40,
    title_distance=100,
    max_summary_tokens=150
)
```

## Key Components

### 1. Graph Builder
- Automatically creates nodes from conversation
- Maintains parent-child relationships
- Tracks conversation flow

### 2. Summarization Service
- Uses GPT-4o-mini or similar for cost-effective summarization
- Batch processing for efficiency
- Caches summaries to avoid recomputation

### 3. Embedding Service
- Generates embeddings for summaries
- Enables semantic search across conversation history
- Supports clustering for community detection

### 4. Community Management
- Groups related message nodes
- Creates hierarchical summaries
- Task-based communities (all messages for task X)
- Topic-based communities (detected via embeddings)

### 5. Context Compiler
- Assembles context based on current position
- Applies resolution rules
- Optimizes token usage

### 6. History Tool
- LLM-accessible tool for fetching detailed history
- Supports queries like:
  - "Show me all messages about authentication"
  - "What did we discuss about task X?"
  - "Retrieve messages from nodes [id1, id2, id3]"

## Implementation Phases

### Phase 1: Core Graph Structure
- [ ] MessageNode data model
- [ ] ContextGraph class with basic operations
- [ ] Sequential node addition
- [ ] Parent-child relationships

### Phase 2: Summarization Pipeline
- [ ] Integration with GPT-4o-mini
- [ ] Async batch summarization
- [ ] Summary caching
- [ ] Token counting

### Phase 3: Embedding Integration
- [ ] Embedding generation for summaries
- [ ] Vector storage
- [ ] Similarity search
- [ ] Clustering algorithms

### Phase 4: Community System
- [ ] Community detection algorithms
- [ ] Task-based community creation
- [ ] Community summarization
- [ ] Hierarchical summary structures

### Phase 5: Context Compilation
- [ ] Distance calculation
- [ ] Resolution rules engine
- [ ] Token optimization
- [ ] Context assembly

### Phase 6: RAG Enhancement
- [ ] Intelligent resolution enhancement
- [ ] Relevance-based detail injection
- [ ] Dynamic context adjustment

### Phase 7: History Tool
- [ ] Tool interface for LLMs
- [ ] Query language
- [ ] Efficient retrieval
- [ ] Response formatting

## Usage Example

```python
# Building the graph during conversation
async def handle_message(user_message: str, architect: Architect):
    # Create node for user message
    user_node = await context_graph.add_message(
        role="user",
        content=user_message,
        task_ids=current_task_ids
    )
    
    # Get compiled context
    context = await context_graph.compile_context(
        current_node_id=user_node.id,
        max_tokens=8000,
        include_communities=True
    )
    
    # Send to architect with compiled context
    response = await architect.process_with_context(
        message=user_message,
        context=context
    )
    
    # Create node for assistant response
    assistant_node = await context_graph.add_message(
        role="assistant",
        content=response,
        parent_id=user_node.id,
        task_ids=current_task_ids
    )
    
    # Trigger async summarization
    await context_graph.summarize_old_nodes()
```

## Cost Optimization

### Summarization Costs
- GPT-4o-mini: $0.40 per 1M output tokens
- Target summary length: 50-100 tokens per message
- Batch processing to minimize API calls

### Embedding Costs
- $0.10 per 1M tokens
- Only embed summaries, not full messages
- Cache embeddings permanently

### Estimated Monthly Costs
- 10K messages/month @ 100 tokens each = 1M tokens
- Summarization: $0.40
- Embeddings: $0.10
- Total: ~$0.50/month for heavy usage

## Configuration Management

### Dynamic Adjustment
```python
class ContextGraphManager:
    def __init__(self, config: ResolutionConfig = None):
        self.config = config or ResolutionConfig()
        self.metrics = PerformanceMetrics()
        
    def auto_adjust_thresholds(self):
        """Automatically adjust based on performance metrics."""
        if self.metrics.avg_context_size > self.config.target_context_size:
            # Compress more aggressively
            self.config.full_context_distance -= 1
            self.config.summary_distance -= 5
        elif self.metrics.context_quality_score < 0.7:
            # Provide more context
            self.config.full_context_distance += 1
            self.config.max_summary_tokens += 20
            
    def apply_cost_constraints(self, daily_budget: float):
        """Adjust parameters to stay within budget."""
        current_daily_cost = self.metrics.calculate_daily_cost()
        if current_daily_cost > daily_budget:
            ratio = daily_budget / current_daily_cost
            self.config.batch_size = int(self.config.batch_size * ratio)
            self.config.max_summary_tokens = int(self.config.max_summary_tokens * ratio)
```

### Profile-Based Configuration
```python
# Per-project or per-agent configurations
PROFILES = {
    "architect": ResolutionConfig(
        full_context_distance=8,  # Architects need more context
        max_summary_tokens=150,
        enable_embedding_generation=True
    ),
    "coding_agent": ResolutionConfig(
        full_context_distance=3,  # Coding agents need less conversation context
        max_summary_tokens=75,
        enable_embedding_generation=False  # Save costs
    ),
    "long_running": ResolutionConfig(
        full_context_distance=5,
        summary_distance=15,
        community_inclusion_distance=50,  # More aggressive community summarization
        max_community_summary_tokens=300
    )
}
```

### Real-time Monitoring
```python
@dataclass
class PerformanceMetrics:
    avg_context_size: int
    avg_response_time: float
    context_quality_score: float
    daily_api_calls: int
    daily_tokens_processed: int
    cache_hit_rate: float
    
    def calculate_daily_cost(self) -> float:
        summarization_cost = (self.daily_tokens_processed / 1_000_000) * 0.40
        embedding_cost = (self.daily_tokens_processed / 1_000_000) * 0.10
        return summarization_cost + embedding_cost
```

## Advanced Features

### 1. Importance Scoring
- Automatically detect important messages
- Preserve full content for critical decisions
- User-marked important messages
- Importance-based resolution override

### 2. Conversation Branching
- Support exploring multiple paths
- Maintain separate branches
- Merge conversations

### 3. Export/Import
- Save conversation graphs
- Share context between sessions
- Backup and restore

### 4. Visualization
- Graph visualization for debugging
- Community structure display
- Token usage analytics

## Integration Points

### With Task Graph
- Link message nodes to tasks
- Create task-specific communities
- Use task completion to trigger summarization

### With RAG System
- Store important decisions in RAG
- Use RAG to enhance old context
- Cross-reference with code changes

### With Event System
- Emit events for node creation
- Subscribe to task events
- Coordinate summarization

## Performance Considerations

### Memory Management
- Lazy loading of node content
- Streaming for large contexts
- Garbage collection for old nodes

### Processing Optimization
- Background summarization
- Batch API calls
- Parallel embedding generation

### Storage
- Efficient graph serialization
- Compressed storage for old nodes
- Indexed access patterns

## Future Enhancements

1. **Multi-Agent Context Sharing**
   - Shared context graphs between agents
   - Permission-based access
   - Context inheritance

2. **Learning System**
   - Learn optimal resolution distances
   - Personalized importance detection
   - Adaptive summarization

3. **Context Templates**
   - Reusable context patterns
   - Project-specific templates
   - Role-based contexts

4. **Advanced Queries**
   - Natural language history search
   - Complex graph traversals
   - Time-based queries

## Success Metrics

1. **Context Efficiency**
   - Average tokens saved: >50%
   - Context relevance score: >0.8
   - Response quality maintained

2. **Cost Reduction**
   - Per-conversation cost: <$0.01
   - Monthly cost: <$1 for typical usage

3. **Performance**
   - Context compilation: <100ms
   - Summarization latency: <2s
   - History retrieval: <500ms

## Implementation Priority

1. **High Priority**
   - Core graph structure
   - Basic summarization
   - Distance-based resolution
   - Task integration

2. **Medium Priority**
   - Community system
   - Embedding search
   - History tool
   - RAG enhancement

3. **Low Priority**
   - Advanced visualization
   - Multi-agent sharing
   - Learning system
   - Templates

This system will provide intelligent context management that scales to very long conversations while maintaining access to all historical information and keeping costs minimal.