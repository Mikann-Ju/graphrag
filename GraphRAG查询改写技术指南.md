# GraphRAG 查询改写技术指南

## 概述

查询改写(Query Rewriting)是GraphRAG系统中的关键预处理环节，通过智能化的查询转换技术，将用户的原始查询优化为更适合知识图谱检索的表达方式，从而显著提升搜索准确性和结果质量。

### 核心价值
- **提升检索精度**: 将模糊查询转换为精确的知识图谱查询
- **增强语义理解**: 通过扩展和澄清提高系统对用户意图的理解
- **优化游戏分析**: 针对游戏业务场景提供专业化的查询优化
- **多策略融合**: 支持多种改写策略的组合使用

## 改写策略

### 1. 查询分解 (Decomposition)
将复杂的多维度查询分解为可独立处理的子查询。

**适用场景**:
- 包含多个分析维度的复杂查询
- 需要分步骤回答的综合性问题

**示例**:
```
原始查询: "分析高付费玩家的流失原因和留存策略"
改写结果:
1. "识别高付费玩家群体的特征"
2. "分析高付费玩家的流失原因"
3. "制定高付费玩家的留存策略"
```

### 2. 查询扩展 (Expansion)
通过添加相关术语、同义词和上下文信息丰富查询内容。

**适用场景**:
- 关键词较少的简短查询
- 需要更全面覆盖的广泛性查询

**示例**:
```
原始查询: "玩家付费分析"
改写结果:
1. "玩家付费行为模式分析，包括充值频次、金额分布和付费转化路径"
2. "不同玩家群体的付费意愿、ARPU值和LTV分析"
3. "付费玩家的游戏偏好、道具购买和活动参与分析"
```

### 3. 查询澄清 (Clarification)
消除查询中的歧义，使表达更加明确和具体。

**适用场景**:
- 包含代词或模糊指代的查询
- 缺乏时间范围或具体条件的查询

**示例**:
```
原始查询: "这个活动效果怎么样？"
改写结果:
1. "最近一次促销活动对玩家参与度和付费转化率的影响分析"
2. "当前运营活动在不同玩家群体中的参与情况和效果评估"
```

### 4. 游戏专业化 (Game-Specific)
将通用表达转换为游戏行业的专业术语和分析框架。

**适用场景**:
- 使用通用商业术语的查询
- 需要游戏行业专业视角的分析

**示例**:
```
原始查询: "用户满意度调研"
改写结果:
1. "玩家游戏体验满意度分析，包括关卡设计、平衡性和社交功能评价"
2. "玩家留存率、活跃度和游戏内反馈的满意度指标分析"
```

## 技术实现

### 核心架构

```python
# 查询改写引擎的基本使用
from graphrag.query.rewrite.query_rewriter import (
    QueryRewriteEngine, 
    RewriteStrategy,
    create_query_rewrite_engine
)

# 创建改写引擎
rewrite_engine = create_query_rewrite_engine(
    model=chat_model,
    entities=entities,
    model_params={"temperature": 0.1}
)

# 单策略改写
result = await rewrite_engine.rewrite_query(
    query="分析玩家流失情况", 
    strategy=RewriteStrategy.GAME_SPECIFIC
)

# 多策略改写
results = await rewrite_engine.rewrite_multi_strategy(
    query="用户活跃度分析",
    strategies=[RewriteStrategy.GAME_SPECIFIC, RewriteStrategy.EXPANSION]
)
```

### 与GraphRAG集成

```python
# 在搜索前进行查询改写
async def enhanced_search_with_rewrite(query: str, search_engine, rewrite_engine):
    # 1. 查询改写
    rewritten_queries = await rewrite_for_graphrag(
        query=query,
        rewrite_engine=rewrite_engine,
        max_rewrites=3
    )
    
    # 2. 多查询搜索
    all_results = []
    for rewritten_query in rewritten_queries:
        result = await search_engine.search(rewritten_query)
        all_results.append(result)
    
    # 3. 结果融合
    final_result = combine_search_results(all_results)
    return final_result
```

## 配置指南

### 1. 基础配置

在`settings.yaml`中添加查询改写配置：

```yaml
query_rewrite:
  enabled: true
  strategies:
    - game_specific
    - expansion  
    - clarification
    - decomposition
  
  # LLM配置
  model_id: "openai"
  temperature: 0.1
  max_tokens: 2000
  
  # 改写参数
  max_rewrites: 3
  confidence_threshold: 0.6
  auto_strategy_selection: true
```

### 2. 高级配置

```yaml
query_rewrite:
  # 游戏术语映射
  game_terminology:
    用户: ["玩家", "用户", "player"]
    收入: ["付费", "充值", "收益", "revenue", "LTV"] 
    活跃: ["留存", "在线时长", "游戏频次"]
    
  # 策略权重
  strategy_weights:
    game_specific: 1.0
    expansion: 0.8
    clarification: 0.7
    decomposition: 0.6
    
  # 实体匹配配置
  entity_matching:
    similarity_threshold: 0.8
    max_entities: 10
    use_embedding: true
```

## 使用场景

### 1. 游戏运营分析

```python
# 场景：运营人员查询分析
queries = [
    "这个月收入情况",
    "玩家为什么流失", 
    "活动效果分析",
    "新玩家留存怎么样"
]

for query in queries:
    result = await rewrite_engine.rewrite_query(
        query, RewriteStrategy.GAME_SPECIFIC
    )
    print(f"原查询: {query}")
    print(f"改写后: {result.rewritten_queries}")
    print(f"置信度: {result.confidence}")
    print("---")
```

### 2. 数据分析师深度挖掘

```python
# 场景：复杂多维度分析
complex_query = "分析不同付费等级玩家的游戏行为差异和优化建议"

# 分解策略
decomp_result = await rewrite_engine.rewrite_query(
    complex_query, RewriteStrategy.DECOMPOSITION  
)

# 为每个子查询进行扩展
expanded_subqueries = []
for sub_query in decomp_result.rewritten_queries:
    expansion_result = await rewrite_engine.rewrite_query(
        sub_query, RewriteStrategy.EXPANSION
    )
    expanded_subqueries.extend(expansion_result.rewritten_queries)
```

### 3. 自然语言交互

```python
# 场景：用户自然语言提问
natural_queries = [
    "最近玩家们都在玩什么？",
    "哪些道具最受欢迎？", 
    "新版本效果如何？"
]

for query in natural_queries:
    # 自动策略选择
    result = await rewrite_engine.rewrite_query(query)
    print(f"选择策略: {result.strategy}")
    print(f"改写结果: {result.rewritten_queries}")
```

## 性能优化

### 1. 缓存机制

```python
class CachedQueryRewriter:
    def __init__(self, base_rewriter, cache_size=1000):
        self.base_rewriter = base_rewriter
        self.cache = {}
        self.cache_size = cache_size
    
    async def rewrite_query(self, query, strategy=None):
        cache_key = f"{query}:{strategy}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = await self.base_rewriter.rewrite_query(query, strategy)
        
        # LRU缓存管理
        if len(self.cache) >= self.cache_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            
        self.cache[cache_key] = result
        return result
```

### 2. 批量处理

```python
async def batch_rewrite(queries: List[str], rewrite_engine):
    """批量处理多个查询的改写"""
    tasks = []
    for query in queries:
        task = rewrite_engine.rewrite_query(query)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

## 质量评估

### 1. 改写质量指标

- **语义保持度**: 改写后查询与原查询的语义一致性
- **明确性提升**: 查询歧义消除程度  
- **覆盖性增强**: 相关概念和术语的扩展程度
- **专业性适配**: 游戏行业术语的适配程度

### 2. 评估方法

```python
async def evaluate_rewrite_quality(original_query, rewritten_queries, evaluator_model):
    """评估改写质量"""
    
    scores = {
        "semantic_preservation": 0.0,
        "clarity_improvement": 0.0, 
        "coverage_enhancement": 0.0,
        "domain_adaptation": 0.0
    }
    
    for rewritten_query in rewritten_queries:
        # 语义保持度评估
        semantic_score = await evaluate_semantic_similarity(
            original_query, rewritten_query, evaluator_model
        )
        scores["semantic_preservation"] += semantic_score
        
        # 明确性提升评估  
        clarity_score = await evaluate_clarity_improvement(
            original_query, rewritten_query, evaluator_model
        )
        scores["clarity_improvement"] += clarity_score
    
    # 计算平均分
    for key in scores:
        scores[key] /= len(rewritten_queries)
    
    return scores
```

## 最佳实践

### 1. 策略选择原则

- **游戏术语优先**: 对于包含游戏相关词汇的查询，优先使用游戏专业化策略
- **复杂查询分解**: 对于超过15个词的长查询，考虑使用分解策略
- **模糊查询澄清**: 对于包含代词和不明确指代的查询，使用澄清策略
- **简短查询扩展**: 对于少于5个词的查询，使用扩展策略

### 2. 性能优化建议

- **异步处理**: 使用异步方式处理多个改写任务
- **结果缓存**: 对常见查询的改写结果进行缓存
- **策略组合**: 根据查询特点智能组合多种策略
- **阈值控制**: 设置合适的置信度阈值过滤低质量改写

### 3. 监控与调优

```python
# 改写效果监控
class RewriteMonitor:
    def __init__(self):
        self.metrics = {
            "total_rewrites": 0,
            "strategy_usage": {},
            "average_confidence": 0.0,
            "error_rate": 0.0
        }
    
    def log_rewrite(self, result: RewriteResult):
        self.metrics["total_rewrites"] += 1
        
        strategy = result.strategy.value
        if strategy not in self.metrics["strategy_usage"]:
            self.metrics["strategy_usage"][strategy] = 0
        self.metrics["strategy_usage"][strategy] += 1
        
        # 更新平均置信度
        total = self.metrics["total_rewrites"]
        current_avg = self.metrics["average_confidence"]
        self.metrics["average_confidence"] = (
            (current_avg * (total - 1) + result.confidence) / total
        )
```

## 总结

查询改写技术作为GraphRAG系统的重要组成部分，通过多策略的智能化查询优化，显著提升了知识图谱检索的精度和用户体验。在游戏分析场景中，专业化的改写策略更是将通用查询转换为行业专业表达，为精准的数据分析提供了强有力的技术支撑。

通过合理配置和优化改写策略，GraphRAG系统能够更好地理解用户意图，提供更准确、更有价值的分析结果。 