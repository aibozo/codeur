# Context Graph Implementation Roadmap

## Phase 1: Core Foundation (Week 1)

### 1.1 Data Models
```python
# src/architect/context_graph_models.py
- MessageNode class
- ContextGraph class
- ResolutionLevel enum
- ContextWindow dataclass
```

### 1.2 Basic Graph Operations
```python
# src/architect/context_graph.py
- add_message()
- get_node()
- get_ancestors()
- get_descendants()
- calculate_distance()
```

### 1.3 Integration with Architect
```python
# src/architect/architect.py modifications
- Add context_graph attribute
- Hook into message flow
- Maintain current_node reference
```

## Phase 2: Summarization System (Week 1-2)

### 2.1 Summarizer Service
```python
# src/core/summarizer.py
- SummarizerService class
- Async batch processing
- Cost tracking
- Error handling
```

### 2.2 Summary Generation
```python
# src/architect/context_summarizer.py
- generate_summary()
- batch_summarize()
- should_summarize() logic
- summary_cache management
```

### 2.3 Background Processing
```python
# src/core/background_tasks.py
- SummarizationQueue
- Background worker
- Progress tracking
```

## Phase 3: Embedding System (Week 2)

### 3.1 Embedding Service
```python
# src/core/embeddings.py
- EmbeddingService updates
- Batch embedding generation
- Cost-optimized processing
```

### 3.2 Vector Operations
```python
# src/architect/context_embeddings.py
- generate_node_embedding()
- find_similar_nodes()
- cluster_nodes()
```

## Phase 4: Context Compilation (Week 2-3)

### 4.1 Resolution Engine
```python
# src/architect/context_compiler.py
- ContextCompiler class
- apply_resolution_rules()
- optimize_token_usage()
- compile_context()
```

### 4.2 Resolution Strategies
```python
# src/architect/resolution_strategies.py
- DistanceBasedStrategy
- ImportanceBasedStrategy
- TokenBudgetStrategy
- HybridStrategy
```

## Phase 5: Community System (Week 3)

### 5.1 Community Detection
```python
# src/architect/context_communities.py
- CommunityDetector class
- detect_communities()
- create_task_community()
- merge_communities()
```

### 5.2 Community Summarization
```python
# src/architect/community_summarizer.py
- summarize_community()
- hierarchical_summary()
- update_community_summary()
```

## Phase 6: History Tool (Week 3-4)

### 6.1 Tool Interface
```python
# src/architect/history_tool.py
- HistoryTool class
- search_history()
- retrieve_nodes()
- format_results()
```

### 6.2 Query Language
```python
# src/architect/history_query.py
- QueryParser
- Natural language queries
- Structured queries
- Time-based queries
```

## Phase 7: RAG Integration (Week 4)

### 7.1 Context Enhancement
```python
# src/architect/context_enhancer.py
- enhance_with_rag()
- find_relevant_context()
- inject_details()
```

### 7.2 Adaptive Resolution
```python
# src/architect/adaptive_resolution.py
- calculate_relevance()
- adjust_resolution()
- optimize_details()
```

## Key Classes Overview

### ResolutionConfig
```python
@dataclass
class ResolutionConfig:
    """Centralized configuration for all resolution parameters."""
    # Distance thresholds
    full_context_distance: int = 5
    summary_distance: int = 20
    title_distance: int = 50
    
    # Token limits
    max_full_tokens_per_node: int = 500
    max_summary_tokens: int = 100
    max_title_tokens: int = 20
    target_context_size: int = 8000
    
    # Community settings
    min_nodes_for_community: int = 5
    max_community_summary_tokens: int = 200
    community_inclusion_distance: int = 100
    community_detection_threshold: float = 0.7
    
    # Performance tuning
    batch_size: int = 10
    summarization_delay_seconds: int = 60
    cache_ttl_seconds: int = 3600
    parallel_workers: int = 3
    
    # Cost controls
    daily_summarization_budget: float = 1.0
    enable_embedding_generation: bool = True
    embedding_batch_size: int = 50
    cost_per_million_summary_tokens: float = 0.40
    cost_per_million_embedding_tokens: float = 0.10
    
    # Quality settings
    min_summary_quality_score: float = 0.8
    importance_threshold: float = 0.7
    preserve_code_blocks: bool = True
    preserve_decisions: bool = True
    
    def estimate_cost(self, num_messages: int, avg_message_length: int) -> float:
        """Estimate daily cost based on configuration."""
        total_tokens = num_messages * avg_message_length
        summary_tokens = total_tokens * (self.max_summary_tokens / avg_message_length)
        
        summary_cost = (summary_tokens / 1_000_000) * self.cost_per_million_summary_tokens
        embedding_cost = 0
        if self.enable_embedding_generation:
            embedding_cost = (summary_tokens / 1_000_000) * self.cost_per_million_embedding_tokens
            
        return summary_cost + embedding_cost

### ContextGraph
```python
class ContextGraph:
    def __init__(self, project_id: str, config: ResolutionConfig = None):
        self.project_id = project_id
        self.config = config or ResolutionConfig()
        self.nodes: Dict[str, MessageNode] = {}
        self.current_node_id: Optional[str] = None
        self.root_nodes: Set[str] = set()
        self.communities: Dict[str, MessageCommunity] = {}
        
    async def add_message(self, role: str, content: str, **kwargs) -> MessageNode:
        """Add a new message to the graph."""
        
    async def compile_context(self, current_node_id: str, max_tokens: int) -> ContextWindow:
        """Compile context for the current position."""
        
    def get_conversation_path(self, node_id: str) -> List[MessageNode]:
        """Get the path from root to specified node."""
```

### ContextCompiler
```python
class ContextCompiler:
    def __init__(self, graph: ContextGraph):
        self.graph = graph
        self.strategies: List[ResolutionStrategy] = []
        
    async def compile(self, current_node_id: str, budget: TokenBudget) -> ContextWindow:
        """Compile optimized context within token budget."""
        
    def calculate_resolution(self, node: MessageNode, current_id: str) -> ResolutionLevel:
        """Determine resolution level for a node."""
```

### MessageCommunity
```python
@dataclass
class MessageCommunity:
    id: str
    name: str
    node_ids: Set[str]
    summary: Optional[str] = None
    task_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_node(self, node_id: str):
        """Add a node to the community."""
        
    async def generate_summary(self, nodes: List[MessageNode]) -> str:
        """Generate community summary."""
```

## Integration Examples

### Architect Integration
```python
class Architect:
    def __init__(self, ...):
        self.context_graph = ContextGraph(project_id)
        self.context_compiler = ContextCompiler(self.context_graph)
        
    async def process_message(self, message: str) -> str:
        # Add to graph
        user_node = await self.context_graph.add_message(
            role="user",
            content=message,
            task_ids=self.current_task_ids
        )
        
        # Compile context
        context = await self.context_compiler.compile(
            current_node_id=user_node.id,
            budget=TokenBudget(max_tokens=8000)
        )
        
        # Process with context
        response = await self._generate_response(message, context)
        
        # Add response to graph
        await self.context_graph.add_message(
            role="assistant",
            content=response,
            parent_id=user_node.id
        )
        
        return response
```

### History Tool Usage
```python
# Tool available to LLM
async def search_conversation_history(query: str, limit: int = 10) -> List[Dict]:
    """Search through conversation history."""
    results = await history_tool.search(
        query=query,
        limit=limit,
        include_context=True
    )
    return [
        {
            "id": node.id,
            "role": node.role,
            "content": node.content if include_full else node.summary,
            "timestamp": node.timestamp,
            "distance": node.distance_from_current
        }
        for node in results
    ]
```

## Configuration Examples

### Development Mode
```python
# Maximum context, minimal compression for debugging
DEV_CONFIG = ResolutionConfig(
    full_context_distance=20,
    summary_distance=50,
    max_summary_tokens=200,
    enable_embedding_generation=False,  # Save costs in dev
    daily_summarization_budget=0.10
)
```

### Production Modes
```python
# Cost-optimized for high-volume usage
PRODUCTION_CHEAP = ResolutionConfig(
    full_context_distance=3,
    summary_distance=10,
    title_distance=20,
    max_summary_tokens=50,
    max_community_summary_tokens=100,
    batch_size=50,  # Larger batches for efficiency
    daily_summarization_budget=0.50
)

# Quality-optimized for important projects
PRODUCTION_QUALITY = ResolutionConfig(
    full_context_distance=8,
    summary_distance=30,
    max_summary_tokens=150,
    max_full_tokens_per_node=1000,
    preserve_code_blocks=True,
    preserve_decisions=True,
    min_summary_quality_score=0.9,
    daily_summarization_budget=2.00
)
```

### Dynamic Configuration
```python
class AdaptiveContextGraph(ContextGraph):
    """Context graph that adapts configuration based on usage."""
    
    def __init__(self, project_id: str, base_config: ResolutionConfig = None):
        super().__init__(project_id, base_config)
        self.usage_monitor = UsageMonitor()
        
    async def adapt_configuration(self):
        """Adjust configuration based on recent performance."""
        metrics = self.usage_monitor.get_metrics()
        
        # Adjust for cost
        if metrics.daily_cost > self.config.daily_summarization_budget:
            scale = self.config.daily_summarization_budget / metrics.daily_cost
            self.config.max_summary_tokens = int(self.config.max_summary_tokens * scale)
            self.config.full_context_distance = max(2, int(self.config.full_context_distance * scale))
            
        # Adjust for quality
        if metrics.user_satisfaction < 0.7:
            self.config.full_context_distance += 2
            self.config.max_summary_tokens += 25
            
        # Adjust for performance
        if metrics.avg_compilation_time > 200:  # ms
            self.config.batch_size = min(100, self.config.batch_size * 2)
            self.config.parallel_workers = min(10, self.config.parallel_workers + 1)
```

### Environment-Based Configuration
```python
def get_config_for_environment() -> ResolutionConfig:
    """Get configuration based on environment variables."""
    env = os.environ.get('CONTEXT_GRAPH_MODE', 'balanced')
    
    configs = {
        'development': DEV_CONFIG,
        'production': PRODUCTION_CHEAP,
        'premium': PRODUCTION_QUALITY,
        'balanced': ResolutionConfig(),  # Defaults
        'aggressive': ResolutionConfig(
            full_context_distance=2,
            summary_distance=8,
            max_summary_tokens=40
        )
    }
    
    config = configs.get(env, ResolutionConfig())
    
    # Override with environment variables
    if daily_budget := os.environ.get('CONTEXT_GRAPH_DAILY_BUDGET'):
        config.daily_summarization_budget = float(daily_budget)
    if max_tokens := os.environ.get('CONTEXT_GRAPH_MAX_SUMMARY_TOKENS'):
        config.max_summary_tokens = int(max_tokens)
        
    return config
```

## Testing Strategy

### Unit Tests
- Graph operations
- Summarization accuracy
- Resolution rules
- Community detection
- Configuration validation

### Integration Tests
- End-to-end conversation flow
- Context compilation performance
- Token budget compliance
- Tool functionality

### Performance Tests
- Large conversation graphs (1000+ nodes)
- Concurrent operations
- Memory usage
- API call optimization

## Monitoring & Analytics

### Metrics to Track
- Average context size reduction
- Summarization costs
- API call frequency
- Context quality scores
- User satisfaction

### Debugging Tools
- Graph visualizer
- Context preview
- Token counter
- Cost calculator

## Migration Path

### For Existing Conversations
1. Create root node
2. Import message history
3. Generate summaries in background
4. Build communities
5. Enable context compilation

### Rollout Strategy
1. Enable for new conversations
2. Test with power users
3. Gradual rollout
4. Full deployment

This implementation plan provides a clear path to building a sophisticated context management system that will dramatically improve the Architect's ability to handle long conversations efficiently.