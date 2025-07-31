# DeepSearch 快速入门指南

## 🚀 什么是 DeepSearch

DeepSearch 是 GraphRAG 项目的最新高级搜索功能，具备以下核心特性：

- **🎯 路径控制**: 智能规划和控制搜索的深度与方向
- **🔍 逻辑链可视化**: 完整的搜索过程透明化
- **🚀 多搜索融合**: 结合本地搜索和全局搜索的优势
- **📊 置信度评估**: 动态评估搜索质量和结果可靠性
- **⚡ 自适应深度**: 根据置信度阈值自动调整搜索深度

## 📦 安装要求

确保您已经安装了 GraphRAG 项目：

```bash
git clone https://github.com/microsoft/graphrag.git
cd graphrag
pip install -e .
```

## 🔧 快速配置

### 1. 基础配置

在您的 `settings.yaml` 中添加 DeepSearch 配置：

```yaml
deep_search:
  max_depth: 3                    # 最大搜索深度
  confidence_threshold: 0.7       # 置信度阈值
  use_local_search: true         # 启用本地搜索
  use_global_search: true        # 启用全局搜索
  enable_path_visualization: true # 启用路径可视化
  enable_logic_chain: true       # 启用逻辑链
```

### 2. 高级配置

```yaml
deep_search:
  # 搜索行为
  max_depth: 5
  confidence_threshold: 0.8
  
  # 本地搜索参数
  local_search_text_unit_prop: 0.9
  local_search_community_prop: 0.1
  local_search_top_k_mapped_entities: 10
  local_search_top_k_relationships: 10
  local_search_max_data_tokens: 12000
  
  # 全局搜索参数
  global_search_max_data_tokens: 8000
  global_search_map_max_length: 1000
  global_search_reduce_max_length: 2000
  
  # LLM 设置
  max_tokens: 8000
  temperature: 0.0
  top_p: 1.0
```

## 🎯 使用方法

### 命令行使用

```bash
# 基础深度搜索
graphrag query --method deep --query "数据中的主要主题是什么？"

# 流式深度搜索
graphrag query --method deep --query "实体之间如何关联？" --streaming

# 自定义响应类型
graphrag query --method deep --query "总结关键发现" --response-type "执行摘要"
```

### Python API 使用

```python
import asyncio
import pandas as pd
import graphrag.api as api
from graphrag.config.load_config import load_config

async def run_deep_search_example():
    # 加载配置
    config = load_config("./")
    
    # 加载数据
    entities = pd.read_parquet("output/entities.parquet")
    communities = pd.read_parquet("output/communities.parquet")
    community_reports = pd.read_parquet("output/community_reports.parquet")
    text_units = pd.read_parquet("output/text_units.parquet")
    relationships = pd.read_parquet("output/relationships.parquet")
    
    # 执行深度搜索
    response, context_data = await api.deep_search(
        config=config,
        entities=entities,
        communities=communities,
        community_reports=community_reports,
        text_units=text_units,
        relationships=relationships,
        query="数据中出现的主要模式是什么？",
        response_type="详细分析"
    )
    
    print("响应:", response)
    print("搜索深度:", context_data.get("search_depth", 0))
    print("路径数量:", context_data.get("path_count", 0))
    print("总体置信度:", context_data.get("total_confidence", 0))
    
    # 分析逻辑链
    logic_chain = context_data.get("logic_chain", {})
    if logic_chain:
        print("\n逻辑链摘要:")
        paths = logic_chain.get("paths", [])
        for i, path in enumerate(paths):
            print(f"  步骤 {i+1}: {path.get('search_type')} 搜索 "
                  f"(置信度: {path.get('confidence', 0):.2f})")

# 运行示例
asyncio.run(run_deep_search_example())
```

### 流式搜索

```python
async def stream_search_example():
    async for chunk in api.deep_search_streaming(
        config=config,
        entities=entities,
        communities=communities,
        community_reports=community_reports,
        text_units=text_units,
        relationships=relationships,
        query="分析关系模式",
    ):
        print(chunk, end="", flush=True)

asyncio.run(stream_search_example())
```

## 🌐 Web 界面使用

### 1. 启动 Unified Search App

```bash
cd unified-search-app
streamlit run app.py
```

### 2. 启用 Deep Search

在侧边栏中勾选 "Include deep search" 选项

### 3. 可视化功能

启用后您将看到：

- **搜索路径图**: 显示搜索步骤和策略
- **置信度分析**: 实时置信度变化趋势
- **详细信息**: 每个步骤的详细推理过程

## 📊 理解结果

### 搜索路径示例

```json
{
  "paths": [
    {
      "step": 1,
      "search_type": "local",
      "query": "您的查询",
      "context_used": ["entities", "relationships", "text_units"],
      "reasoning": "深度1的本地搜索，关注具体实体和关系",
      "confidence": 0.8,
      "timestamp": 1234567890
    },
    {
      "step": 2,
      "search_type": "global",
      "query": "您的查询",
      "context_used": ["communities", "community_reports"],
      "reasoning": "深度2的全局搜索，关注高层次模式和社区结构",
      "confidence": 0.75,
      "timestamp": 1234567891
    }
  ],
  "final_reasoning": "基于2个搜索结果的综合分析",
  "total_confidence": 0.775
}
```

### 置信度解读

- **0.8-1.0**: 非常可靠的结果
- **0.6-0.8**: 较为可靠的结果  
- **0.4-0.6**: 中等可靠性，建议谨慎使用
- **0.0-0.4**: 低可靠性，可能需要更多信息

## 🎨 游戏数据分析示例

### 玩家行为分析

```bash
# 分析付费转化路径
graphrag query --method deep --query "高价值玩家的付费转化路径是什么？"

# 分析流失原因
graphrag query --method deep --query "为什么玩家在第3关后容易流失？"
```

### 游戏平衡性分析

```bash
# 关卡难度分析
graphrag query --method deep --query "哪些关卡的难度设置可能影响玩家体验？"

# 道具使用模式
graphrag query --method deep --query "玩家如何使用游戏道具来通过困难关卡？"
```

### 运营策略优化

```bash
# 活动效果评估
graphrag query --method deep --query "促销活动对不同类型玩家的影响如何？"

# 个性化推荐
graphrag query --method deep --query "如何为不同玩家群体设计个性化的游戏体验？"
```

## ⚙️ 性能优化

### 1. 配置调优

```yaml
deep_search:
  # 对于快速查询，降低深度
  max_depth: 2
  confidence_threshold: 0.6
  
  # 对于详细分析，增加深度
  max_depth: 5
  confidence_threshold: 0.8
```

### 2. 监控指标

```python
# 监控搜索性能
def monitor_search_performance(context_data):
    print(f"完成时间: {context_data.get('completion_time', 0):.2f}秒")
    print(f"LLM 调用次数: {context_data.get('llm_calls', 0)}")
    print(f"输入 token: {context_data.get('prompt_tokens', 0)}")
    print(f"输出 token: {context_data.get('output_tokens', 0)}")
```

## 🔧 故障排除

### 常见问题

**Q: 置信度分数很低怎么办？**
A: 
- 检查数据覆盖范围是否充足
- 考虑降低置信度阈值
- 验证实体和关系连接是否良好

**Q: 搜索速度很慢怎么办？**
A:
- 减少 max_depth 或 token 限制
- 优化向量存储配置
- 考虑使用较小的语言模型

**Q: 结果不完整怎么办？**
A:
- 增加 max_depth 进行更深入探索
- 确保启用了本地和全局搜索
- 验证查询是否足够具体

### 调试模式

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 分析逻辑链
def debug_logic_chain(context_data):
    logic_chain = context_data.get("logic_chain", {})
    paths = logic_chain.get("paths", [])
    
    print("搜索路径分析:")
    for path in paths:
        print(f"- 步骤 {path.get('step')}: {path.get('search_type')} "
              f"(置信度: {path.get('confidence', 0):.2f})")
        print(f"  推理: {path.get('reasoning', 'N/A')}")
```

## 📚 进阶用法

### 自定义逻辑链处理

```python
def analyze_search_strategy_effectiveness(context_data):
    logic_chain = context_data.get("logic_chain", {})
    paths = logic_chain.get("paths", [])
    
    # 分析搜索策略效果
    strategy_performance = {}
    for path in paths:
        search_type = path.get("search_type")
        confidence = path.get("confidence", 0)
        
        if search_type not in strategy_performance:
            strategy_performance[search_type] = []
        strategy_performance[search_type].append(confidence)
    
    # 计算平均置信度
    for strategy, confidences in strategy_performance.items():
        avg_confidence = sum(confidences) / len(confidences)
        print(f"{strategy} 搜索平均置信度: {avg_confidence:.2f}")
    
    return strategy_performance
```

### 批量查询处理

```python
async def batch_deep_search(queries, config, data_frames):
    results = []
    
    for query in queries:
        print(f"处理查询: {query}")
        
        response, context_data = await api.deep_search(
            config=config,
            query=query,
            **data_frames
        )
        
        results.append({
            "query": query,
            "response": response,
            "confidence": context_data.get("total_confidence", 0),
            "search_depth": context_data.get("search_depth", 0),
            "logic_chain": context_data.get("logic_chain", {})
        })
    
    return results

# 使用示例
queries = [
    "玩家流失的主要原因是什么？",
    "哪些功能最受欢迎？",
    "如何提高玩家留存率？"
]

results = asyncio.run(batch_deep_search(queries, config, data_frames))
```

## 🔗 相关资源

- [Deep Search 详细文档](./docs/query/deep_search.md)
- [GraphRAG 官方文档](https://microsoft.github.io/graphrag)
- [API 参考文档](./docs/api/)
- [配置指南](./docs/config/)

## 💡 最佳实践

1. **查询设计**
   - 使用具体、明确的问题
   - 为复杂问题提供上下文
   - 考虑多个相关方面

2. **配置调优**
   - 从默认设置开始
   - 根据结果逐步调整
   - 监控性能和成本

3. **结果解读**
   - 查看逻辑链了解推理过程
   - 检查置信度评估可靠性
   - 考虑多个搜索路径的结果

4. **性能优化**
   - 使用适当的置信度阈值
   - 根据用例配置 token 限制
   - 对长时间查询考虑流式输出

Happy searching with DeepSearch! 🎉 