# GraphRAG查询重写技术实现解析

## 概述

GraphRAG查询重写模块是一个基于策略模式设计的智能查询优化系统，通过多种重写策略提升知识图谱检索的召回率和准确性。特别针对游戏数据分析场景进行了专门优化。

## 核心架构设计

### 数据结构定义

**RewriteResult数据类**
```python
@dataclass
class RewriteResult:
    """Query rewrite result."""
    original_query: str              # 原始查询
    rewritten_queries: List[str]     # 重写后的查询列表
    strategy: RewriteStrategy        # 使用的重写策略
    confidence: float                # 置信度分数(0-1)
    reasoning: str                   # 重写推理过程
    metadata: Optional[Dict[str, Any]] = None  # 额外元数据
```

**重写策略枚举**
```python
class RewriteStrategy(Enum):
    """Query rewriting strategies."""
    DECOMPOSITION = "decomposition"        # 查询分解
    EXPANSION = "expansion"               # 查询扩展
    CLARIFICATION = "clarification"       # 查询澄清
    SIMPLIFICATION = "simplification"     # 查询简化
    CONTEXTUALIZATION = "contextualization"  # 上下文化
    GAME_SPECIFIC = "game_specific"       # 游戏领域特化
```

### 抽象基类设计

```python
class QueryRewriterBase(ABC):
    """Base class for query rewriters."""
    
    @abstractmethod
    async def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> RewriteResult:
        """Rewrite a query using the specific strategy."""
        pass
    
    @abstractmethod
    def get_strategy(self) -> RewriteStrategy:
        """Get the rewrite strategy."""
        pass
```

**设计优势**：
- 统一接口设计，易于扩展新的重写策略
- 异步支持，提升并发处理性能
- 策略模式实现，符合开闭原则

## 具体重写策略实现

### 1. 查询分解策略 (DecompositionRewriter)

**实现原理**：使用LLM的推理能力将复杂查询分解为简单子查询

**核心实现逻辑**：
```python
async def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> RewriteResult:
    """Decompose a complex query into sub-queries."""
    
    prompt = f"""
分析以下查询并将其分解为更简单的子查询。每个子查询应该：
1. 聚焦于一个特定方面
2. 能够独立回答
3. 组合起来能完整回答原始问题

原始查询: {query}

请以JSON格式返回结果：
{{
    "sub_queries": ["子查询1", "子查询2", ...],
    "reasoning": "分解的原因和逻辑",
    "confidence": 0.9
}}
"""
```

**技术要点**：
- **Prompt Engineering**：使用结构化中文提示词
- **JSON约束**：强制LLM输出标准JSON格式
- **异步调用**：`await self.model.achat(prompt, **self.model_params)`
- **错误降级**：JSON解析失败时返回原查询，confidence设为0.1

### 2. 查询扩展策略 (ExpansionRewriter)

**实现原理**：基于实体库匹配 + LLM语义扩展

**实体匹配算法**：
```python
def _find_relevant_entities(self, query: str) -> List[Entity]:
    """Find entities relevant to the query."""
    if not self.entities:
        return []
    
    query_lower = query.lower()
    relevant = []
    
    for entity in self.entities:
        # Simple keyword matching - can be improved with embeddings
        if (entity.title.lower() in query_lower or 
            (entity.description and any(word in entity.description.lower() 
                                      for word in query_lower.split()))):
            relevant.append(entity)
    
    return relevant[:10]  # Limit to top 10
```

**技术要点**：
- **关键词匹配**：`entity.title.lower() in query_lower` 简单但有效
- **描述匹配**：对实体描述进行分词匹配
- **数量控制**：限制最多10个相关实体，避免context过长
- **实体上下文**：将匹配的实体信息作为LLM扩展的依据

**LLM扩展逻辑**：
```python
# Get relevant entities for expansion
relevant_entities = self._find_relevant_entities(query)
entity_context = "\n".join([f"- {e.title}: {e.description}" for e in relevant_entities[:5]])

prompt = f"""
扩展以下查询，使其更加详细和全面。考虑：
1. 添加同义词和相关术语
2. 包含相关的实体和概念
3. 考虑不同的表达方式

原始查询: {query}

相关实体信息:
{entity_context}
"""
```

### 3. 游戏领域特化策略 (GameSpecificRewriter)

**实现原理**：硬编码术语映射 + 游戏分析专家Persona

**术语映射表设计**：
```python
# Game-specific terminology mapping
self.game_terminology = {
    "用户": ["玩家", "用户", "player"],
    "收入": ["付费", "充值", "收益", "revenue", "LTV"],
    "活跃": ["留存", "在线时长", "游戏频次"],
    "流失": ["离开", "不活跃", "churn"],
    "付费": ["充值", "购买", "消费", "IAP"],
    "关卡": ["level", "stage", "房间", "场次"],
    "道具": ["item", "皮肤", "装备"],
}
```

**专家Persona提示词**：
```python
prompt = f"""
你是一个游戏数据分析专家。请将以下查询改写为更适合游戏分析的表达方式。考虑：

1. 使用游戏行业标准术语
2. 明确分析维度（玩家、付费、留存、活动等）
3. 考虑游戏业务指标（LTV、ARPU、留存率等）
4. 适合知识图谱检索的表达方式

游戏术语映射：
{terminology_context}

原始查询: {query}

请以JSON格式返回结果：
{{
    "game_queries": ["游戏化查询1", "游戏化查询2", ...],
    "analysis_dimensions": ["维度1", "维度2", ...],
    "suggested_metrics": ["指标1", "指标2", ...],
    "reasoning": "改写的原因和策略",
    "confidence": 0.9
}}
"""
```

**技术亮点**：
- **领域知识编码**：将游戏分析经验编码为术语映射
- **多维度输出**：不仅重写查询，还提供分析维度和建议指标
- **专业Persona**：让LLM扮演游戏分析专家角色

### 4. 查询澄清策略 (ClarificationRewriter)

**实现原理**：歧义识别 + 明确化处理

**歧义识别提示词**：
```python
prompt = f"""
分析以下查询的歧义性，并提供更明确的表达方式。考虑：
1. 时间范围的明确化
2. 主体和对象的具体化
3. 分析目标的清晰化
4. 条件和约束的添加

原始查询: {query}

请以JSON格式返回结果：
{{
    "clarified_queries": ["明确查询1", "明确查询2", ...],
    "ambiguities_resolved": ["解决的歧义1", "解决的歧义2", ...],
    "reasoning": "澄清的原因和方法",
    "confidence": 0.8
}}
"""
```

## 引擎层核心逻辑

### QueryRewriteEngine主引擎

**初始化策略注册**：
```python
def __init__(
    self,
    model: ChatModel,
    entities: Optional[List[Entity]] = None,
    model_params: Optional[Dict[str, Any]] = None,
    enable_strategies: Optional[List[RewriteStrategy]] = None
):
    # 默认启用策略顺序
    if enable_strategies is None:
        enable_strategies = [
            RewriteStrategy.GAME_SPECIFIC,
            RewriteStrategy.EXPANSION,
            RewriteStrategy.CLARIFICATION,
            RewriteStrategy.DECOMPOSITION
        ]
    
    # 动态注册重写器
    for strategy in enable_strategies:
        if strategy == RewriteStrategy.DECOMPOSITION:
            self.rewriters[strategy] = DecompositionRewriter(model, model_params)
        # ... 其他策略
```

### 自动策略选择算法

```python
def _auto_select_strategy(self, query: str) -> RewriteStrategy:
    """Automatically select the best rewrite strategy for a query."""
    
    query_lower = query.lower()
    
    # 游戏术语检测
    game_terms = ["玩家", "付费", "充值", "关卡", "道具", "流失", "留存", "LTV", "ARPU"]
    if any(term in query_lower for term in game_terms):
        return RewriteStrategy.GAME_SPECIFIC
    
    # 复杂查询检测（连词、长度）
    complex_indicators = ["和", "或", "以及", "同时", "另外", "此外", "而且"]
    if any(indicator in query_lower for indicator in complex_indicators) or len(query.split()) > 10:
        return RewriteStrategy.DECOMPOSITION
    
    # 模糊查询检测（代词、模糊词）
    ambiguous_terms = ["这个", "那个", "它", "他们", "怎么样", "如何"]
    if any(term in query_lower for term in ambiguous_terms):
        return RewriteStrategy.CLARIFICATION
    
    # 默认扩展策略
    return RewriteStrategy.EXPANSION
```

**规则设计逻辑**：
1. **优先级排序**：游戏特化 > 查询分解 > 查询澄清 > 查询扩展
2. **关键词匹配**：基于简单但有效的关键词规则
3. **长度阈值**：超过10个词的查询认为是复杂查询
4. **降级机制**：无法匹配时默认使用扩展策略

### 并行多策略处理

```python
async def rewrite_multi_strategy(
    self,
    query: str,
    strategies: Optional[List[RewriteStrategy]] = None,
    context: Optional[Dict[str, Any]] = None
) -> List[RewriteResult]:
    """Apply multiple rewrite strategies to a query."""
    
    if strategies is None:
        strategies = list(self.rewriters.keys())
    
    # 构建并行任务
    tasks = []
    for strategy in strategies:
        if strategy in self.rewriters:
            tasks.append(self.rewriters[strategy].rewrite(query, context))
    
    if not tasks:
        return []
    
    # 并行执行所有重写任务
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 过滤异常，只保留成功结果
    valid_results = []
    for result in results:
        if isinstance(result, RewriteResult):
            valid_results.append(result)
        else:
            logger.warning(f"Rewrite task failed: {result}")
    
    return valid_results
```

**并发优势**：
- **asyncio.gather()**：并行执行多个异步任务
- **异常隔离**：单个策略失败不影响其他策略
- **return_exceptions=True**：异常作为结果返回而非抛出

## GraphRAG优化函数

```python
async def rewrite_for_graphrag(
    query: str,
    rewrite_engine: QueryRewriteEngine,
    max_rewrites: int = 3
) -> List[str]:
    """
    Rewrite a query specifically for GraphRAG search optimization.
    """
    
    # 固定策略组合：游戏特化 + 查询扩展
    game_result = await rewrite_engine.rewrite_query(
        query, RewriteStrategy.GAME_SPECIFIC
    )
    
    expansion_result = await rewrite_engine.rewrite_query(
        query, RewriteStrategy.EXPANSION
    )
    
    # 合并去重
    all_queries = [query]  # 保留原查询
    all_queries.extend(game_result.rewritten_queries)
    all_queries.extend(expansion_result.rewritten_queries)
    
    # 去重并限制数量
    unique_queries = []
    seen = set()
    for q in all_queries:
        if q not in seen and len(unique_queries) < max_rewrites:
            unique_queries.append(q)
            seen.add(q)
    
    return unique_queries
```

**优化策略**：
- **固定组合**：针对GraphRAG特点选择最优策略组合
- **原查询保留**：保证至少有原始查询可用
- **去重逻辑**：使用set()避免重复查询
- **数量控制**：防止查询数量过多影响性能

## 错误处理机制

**统一降级策略**：
```python
except Exception as e:
    logger.warning(f"Query rewrite failed: {e}")
    return RewriteResult(
        original_query=query,
        rewritten_queries=[query],  # 降级返回原查询
        strategy=self.get_strategy(),
        confidence=0.1,             # 低置信度标记
        reasoning=f"Rewrite failed: {str(e)}",
        metadata={"error": str(e)}
    )
```

**关键特点**：
- **优雅降级**：任何策略失败都返回原查询
- **置信度标记**：失败时confidence=0.1，便于下游判断
- **错误追踪**：在metadata中保存错误信息
- **日志记录**：使用logger记录警告，便于调试

## 总结

GraphRAG查询重写模块通过精心设计的多策略架构，实现了智能化的查询优化。其核心价值在于：

1. **模块化设计**：策略模式确保高扩展性
2. **游戏特化**：针对游戏分析场景的专门优化
3. **智能选择**：基于规则的自动策略选择
4. **并发处理**：asyncio支持高性能并行处理
5. **错误容忍**：完整的降级和异常处理机制

这种设计既保证了系统的稳定性，又提供了足够的灵活性来适应不同的查询场景和业务需求。
