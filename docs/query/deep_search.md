# Deep Search

Deep Search is GraphRAG's most advanced search method that combines multiple search strategies with intelligent path control and comprehensive visualization of the reasoning process.

## Overview

Deep Search represents a significant advancement in knowledge graph querying by providing:

- **Multi-layered search execution** combining local and global search strategies
- **Intelligent path control** with dynamic depth adjustment
- **Complete reasoning transparency** through visualization logic chains
- **Confidence-based evaluation** for result quality assessment

## How Deep Search Works

Deep Search operates through a sophisticated multi-step process:

### 1. Query Analysis and Planning
The system first analyzes your query to determine:
- Query complexity level (1-5 scale)
- Recommended search depth
- Optimal search strategy combination
- Key entities and concepts to focus on

### 2. Multi-layered Search Execution
Deep Search executes searches in multiple layers:

**Local Search Layer:**
- Focuses on specific entities and relationships
- Provides detailed, granular information
- High precision for factual queries

**Global Search Layer:**
- Analyzes high-level patterns and community structures
- Provides broader context and thematic insights
- Excellent for conceptual and analytical queries

### 3. Intelligent Path Control
- **Dynamic Depth Adjustment**: Automatically determines when to stop based on confidence thresholds
- **Adaptive Strategy Selection**: Chooses the best search combination for each query type
- **Iterative Refinement**: Uses results from previous layers to improve subsequent searches

### 4. Result Integration and Reasoning
- Combines results from all search layers
- Resolves conflicts and identifies complementary information
- Provides comprehensive, well-reasoned final answers

## Key Features

### 🎯 Path Control
Deep Search intelligently controls the search process:
- **Maximum Depth**: Configurable limit (default: 3 layers)
- **Confidence Threshold**: Stops when results are sufficiently confident (default: 0.7)
- **Strategy Selection**: Automatically chooses optimal search combinations

### 🔍 Logic Chain Visualization
Every Deep Search provides complete transparency through:
- **Step-by-step process tracking** with timestamps
- **Confidence scoring** for each search step
- **Reasoning documentation** for decision making
- **Interactive visualizations** showing search paths

### 📊 Confidence Assessment
Sophisticated confidence evaluation includes:
- **Individual step confidence** scoring
- **Overall confidence** calculation
- **Quality indicators** for result reliability
- **Uncertainty quantification** where applicable

## Configuration

### Basic Configuration
```yaml
deep_search:
  max_depth: 3
  confidence_threshold: 0.7
  use_local_search: true
  use_global_search: true
  enable_path_visualization: true
  enable_logic_chain: true
```

### Advanced Configuration
```yaml
deep_search:
  # Search behavior
  max_depth: 5
  confidence_threshold: 0.8
  
  # Search strategy
  use_local_search: true
  use_global_search: true
  
  # Visualization
  enable_path_visualization: true
  enable_logic_chain: true
  
  # Local search parameters
  local_search_text_unit_prop: 0.9
  local_search_community_prop: 0.1
  local_search_top_k_mapped_entities: 10
  local_search_top_k_relationships: 10
  local_search_max_data_tokens: 12000
  
  # Global search parameters
  global_search_max_data_tokens: 8000
  global_search_map_max_length: 1000
  global_search_reduce_max_length: 2000
  
  # LLM settings
  max_tokens: 8000
  temperature: 0.0
  top_p: 1.0
```

## Usage Examples

### Command Line Interface

```bash
# Basic deep search
graphrag query --method deep --query "What are the main themes in this dataset?"

# Deep search with streaming output
graphrag query --method deep --query "How do entities relate to each other?" --streaming

# Deep search with custom response type
graphrag query --method deep --query "Summarize key findings" --response-type "Executive Summary"
```

### Python API

```python
import asyncio
import graphrag.api as api
from graphrag.config.load_config import load_config

async def run_deep_search():
    # Load configuration
    config = load_config("./")
    
    # Load your data
    entities = pd.read_parquet("output/entities.parquet")
    communities = pd.read_parquet("output/communities.parquet") 
    community_reports = pd.read_parquet("output/community_reports.parquet")
    text_units = pd.read_parquet("output/text_units.parquet")
    relationships = pd.read_parquet("output/relationships.parquet")
    
    # Perform deep search
    response, context_data = await api.deep_search(
        config=config,
        entities=entities,
        communities=communities,
        community_reports=community_reports,
        text_units=text_units,
        relationships=relationships,
        query="What patterns emerge from the data?",
        response_type="Detailed Analysis"
    )
    
    print("Response:", response)
    print("Logic Chain:", context_data.get("logic_chain", {}))
    print("Search Depth:", context_data.get("search_depth", 0))
    print("Confidence:", context_data.get("total_confidence", 0))

# Run the search
asyncio.run(run_deep_search())
```

### Streaming API

```python
async def run_streaming_deep_search():
    async for chunk in api.deep_search_streaming(
        config=config,
        entities=entities,
        communities=communities,
        community_reports=community_reports,
        text_units=text_units,
        relationships=relationships,
        query="Analyze the relationship patterns",
    ):
        print(chunk, end="", flush=True)

asyncio.run(run_streaming_deep_search())
```

## Logic Chain Visualization

Deep Search provides comprehensive visualization of the reasoning process:

### Search Path Graph
Interactive flow chart showing:
- Each search step as a node
- Connections between steps
- Color coding by search type
- Size indicating confidence level

### Confidence Analysis
Detailed confidence tracking including:
- Step-by-step confidence trends
- Average and peak confidence scores
- Confidence threshold visualization
- Quality indicators

### Detailed Information
Complete transparency with:
- Step-by-step reasoning
- Context used at each step
- Time stamps and performance metrics
- Raw logic chain data

## Best Practices

### Query Formulation
- **Be specific** about what you want to learn
- **Provide context** when asking complex questions  
- **Use clear language** that the LLM can understand
- **Consider multiple aspects** that might be relevant

### Configuration Tuning
- **Start with defaults** and adjust based on results
- **Lower confidence threshold** for broader exploration
- **Increase max depth** for complex analytical questions
- **Adjust token limits** based on your data size

### Result Interpretation
- **Review the logic chain** to understand reasoning
- **Check confidence scores** for reliability assessment
- **Examine different search paths** for completeness
- **Consider multiple perspectives** in the results

## Performance Considerations

### Computational Cost
Deep Search is more resource-intensive than single-method searches:
- Uses multiple LLM calls per query
- Requires additional processing for logic chain construction
- Benefits from caching and efficient vector stores

### Optimization Tips
- Use appropriate **confidence thresholds** to avoid unnecessary depth
- Configure **token limits** based on your use case
- Consider **streaming** for long-running queries
- Monitor **LLM usage** and costs

## Troubleshooting

### Common Issues

**Low Confidence Scores:**
- Check if your data has sufficient coverage for the query
- Consider lowering the confidence threshold
- Verify that entities and relationships are well-connected

**Slow Performance:**
- Reduce max_depth or token limits
- Optimize your vector store configuration
- Consider using smaller language models for faster responses

**Incomplete Results:**
- Increase max_depth for more thorough exploration
- Check that both local and global search are enabled
- Verify that your query is specific enough

## Advanced Features

### Custom Logic Chain Processing
```python
def analyze_logic_chain(context_data):
    logic_chain = context_data.get("logic_chain", {})
    paths = logic_chain.get("paths", [])
    
    # Analyze search strategy effectiveness
    strategy_performance = {}
    for path in paths:
        search_type = path.get("search_type")
        confidence = path.get("confidence", 0)
        
        if search_type not in strategy_performance:
            strategy_performance[search_type] = []
        strategy_performance[search_type].append(confidence)
    
    return strategy_performance
```

### Integration with Other Tools
Deep Search works seamlessly with:
- **Jupyter notebooks** for interactive analysis
- **Streamlit apps** for web interfaces
- **Custom applications** via the Python API
- **CI/CD pipelines** for automated analysis

## Future Enhancements

We're continuously improving Deep Search with:
- **Enhanced confidence models** for better reliability assessment
- **Custom search strategies** for domain-specific use cases
- **Performance optimizations** for large-scale deployments
- **Advanced visualization** options for complex logic chains

## Related Documentation

- [Query Overview](./overview.md) - General querying concepts
- [Local Search](./local_search.md) - Detailed local search documentation
- [Global Search](./global_search.md) - Global search methodology
- [DRIFT Search](./drift_search.md) - Dynamic search approach 