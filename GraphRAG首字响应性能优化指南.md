# GraphRAG 首字响应性能优化指南

## 概述

在ToB场景中，特别是游戏智能分析平台，**首字响应时间**直接影响用户体验和业务价值。大客户在测试时往往会有**所有人同时使用**的场景，这对系统并发能力提出了极高要求。传统的**同步+多节点**方案在高并发下容易产生阻塞，无法满足企业级应用需求。

本指南从四个核心维度提供系统性的性能优化方案：
1. **异步调用架构** - 彻底避免同步阻塞
2. **多层缓存体系** - 减少重复计算开销
3. **Milvus向量检索优化** - 加速召回阶段
4. **硬件与基础设施加速** - 底层性能提升

### 性能目标

| 场景 | 首字响应时间 | 并发支持 | 可用性 |
|------|-------------|----------|--------|
| 单用户查询 | ≤ 200ms | - | 99.9% |
| 中等并发 (≤50用户) | ≤ 500ms | 50 QPS | 99.9% |
| 高并发 (≤200用户) | ≤ 1000ms | 200 QPS | 99.5% |
| 峰值并发 (≤500用户) | ≤ 2000ms | 500 QPS | 99% |

---

## 1. 异步调用架构

### 1.1 问题分析

**传统同步架构的问题**：
- 请求串行处理，一个慢查询阻塞整个队列
- 资源利用率低，大量线程等待I/O
- 在大客户测试时容易出现雪崩效应

**解决方案**：全链路异步化 + 事件驱动架构

### 1.2 异步架构设计

```python
# graphrag/async_engine/async_query_processor.py

import asyncio
import aiohttp
from typing import AsyncGenerator, Dict, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import uvloop  # 高性能事件循环

@dataclass
class QueryTask:
    """异步查询任务"""
    query_id: str
    query: str
    user_id: str
    priority: int = 1  # 1-5, 5为最高优先级
    timestamp: float = 0.0

class AsyncQueryProcessor:
    """异步查询处理器 - 支持高并发非阻塞处理"""
    
    def __init__(self, 
                 max_concurrent_queries: int = 100,
                 max_workers: int = 50):
        # 使用高性能事件循环
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        
        self.max_concurrent = max_concurrent_queries
        self.semaphore = asyncio.Semaphore(max_concurrent_queries)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 任务队列 - 支持优先级
        self.task_queue = asyncio.PriorityQueue()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # 性能监控
        self.metrics = {
            "total_queries": 0,
            "concurrent_queries": 0,
            "average_response_time": 0.0,
            "queue_depth": 0
        }
        
        # 启动后台任务处理器
        asyncio.create_task(self._start_task_processor())
    
    async def submit_query(self, query_task: QueryTask) -> str:
        """提交查询任务 - 立即返回任务ID"""
        await self.task_queue.put((
            -query_task.priority,  # 负数实现高优先级先处理
            query_task.timestamp,
            query_task
        ))
        
        self.metrics["queue_depth"] = self.task_queue.qsize()
        return query_task.query_id
    
    async def _start_task_processor(self):
        """后台任务处理器 - 持续处理队列中的任务"""
        while True:
            try:
                # 从队列获取任务
                _, _, task = await self.task_queue.get()
                
                # 创建异步处理任务
                async_task = asyncio.create_task(
                    self._process_single_query(task)
                )
                self.active_tasks[task.query_id] = async_task
                
                # 不等待任务完成，继续处理下一个
                asyncio.create_task(self._cleanup_completed_task(task.query_id))
                
            except Exception as e:
                logger.error(f"Task processor error: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_single_query(self, task: QueryTask) -> Dict:
        """处理单个查询任务"""
        async with self.semaphore:  # 控制并发数
            start_time = time.time()
            self.metrics["concurrent_queries"] += 1
            
            try:
                # 1. 异步查询改写
                rewrite_task = asyncio.create_task(
                    self._async_query_rewrite(task.query)
                )
                
                # 2. 异步向量检索 (并行执行)
                retrieval_task = asyncio.create_task(
                    self._async_vector_retrieval(task.query)
                )
                
                # 3. 等待前两步完成
                rewritten_query, retrieved_contexts = await asyncio.gather(
                    rewrite_task, retrieval_task
                )
                
                # 4. 异步LLM生成
                response = await self._async_llm_generation(
                    rewritten_query, retrieved_contexts
                )
                
                # 5. 记录性能指标
                response_time = time.time() - start_time
                self._update_metrics(response_time)
                
                return {
                    "query_id": task.query_id,
                    "response": response,
                    "response_time": response_time,
                    "status": "completed"
                }
                
            except Exception as e:
                logger.error(f"Query processing error for {task.query_id}: {e}")
                return {
                    "query_id": task.query_id,
                    "error": str(e),
                    "status": "failed"
                }
            finally:
                self.metrics["concurrent_queries"] -= 1
    
    async def _async_query_rewrite(self, query: str) -> str:
        """异步查询改写"""
        # 使用异步HTTP客户端调用改写服务
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.rewrite_service_url}/rewrite",
                json={"query": query},
                timeout=aiohttp.ClientTimeout(total=2.0)
            ) as response:
                result = await response.json()
                return result.get("rewritten_query", query)
    
    async def _async_vector_retrieval(self, query: str) -> List[str]:
        """异步向量检索"""
        # 使用线程池处理CPU密集型的向量计算
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_vector_search,
            query
        )
    
    async def _async_llm_generation(self, query: str, contexts: List[str]) -> str:
        """异步LLM生成 - 支持流式输出"""
        # 使用异步生成器实现流式响应
        async def stream_generator():
            async for chunk in self._stream_llm_response(query, contexts):
                yield chunk
        
        # 收集完整响应
        full_response = ""
        async for chunk in stream_generator():
            full_response += chunk
        
        return full_response

# 流式响应处理
class StreamingResponseHandler:
    """流式响应处理器 - 实现首字响应优化"""
    
    async def handle_streaming_query(self, query: str) -> AsyncGenerator[str, None]:
        """处理流式查询，优化首字响应时间"""
        
        # 1. 立即返回处理状态
        yield json.dumps({
            "type": "status",
            "message": "查询处理中...",
            "timestamp": time.time()
        }) + "\n"
        
        # 2. 并行启动多个处理流程
        tasks = [
            asyncio.create_task(self._fast_cache_lookup(query)),
            asyncio.create_task(self._quick_similarity_search(query)),
            asyncio.create_task(self._intent_recognition(query))
        ]
        
        # 3. 有结果就立即返回
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    yield json.dumps({
                        "type": "partial_result",
                        "data": result,
                        "timestamp": time.time()
                    }) + "\n"
            except Exception as e:
                continue
        
        # 4. 完整处理流程
        full_result = await self._full_processing_pipeline(query)
        yield json.dumps({
            "type": "final_result",
            "data": full_result,
            "timestamp": time.time()
        }) + "\n"
```

### 1.3 事件驱动架构

```python
# graphrag/async_engine/event_driven_system.py

from dataclasses import dataclass
from typing import Callable, Dict, List
import asyncio

@dataclass
class QueryEvent:
    """查询事件"""
    event_type: str  # "query_start", "retrieval_complete", "llm_start", "response_ready"
    query_id: str
    data: Dict
    timestamp: float

class EventDrivenQueryEngine:
    """事件驱动查询引擎"""
    
    def __init__(self):
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.event_queue = asyncio.Queue()
        
        # 启动事件处理器
        asyncio.create_task(self._process_events())
    
    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def publish(self, event: QueryEvent):
        """发布事件"""
        await self.event_queue.put(event)
    
    async def _process_events(self):
        """处理事件队列"""
        while True:
            event = await self.event_queue.get()
            
            # 并行处理所有订阅者
            if event.event_type in self.event_handlers:
                tasks = [
                    asyncio.create_task(handler(event))
                    for handler in self.event_handlers[event.event_type]
                ]
                await asyncio.gather(*tasks, return_exceptions=True)

# 事件处理器示例
async def on_query_start(event: QueryEvent):
    """查询开始事件处理器"""
    # 预热缓存
    await cache_service.warm_up(event.data["query"])

async def on_retrieval_complete(event: QueryEvent):
    """检索完成事件处理器"""
    # 预处理上下文
    await context_processor.preprocess(event.data["contexts"])

# 注册事件处理器
engine = EventDrivenQueryEngine()
engine.subscribe("query_start", on_query_start)
engine.subscribe("retrieval_complete", on_retrieval_complete)
```

---

## 2. 多层缓存体系

### 2.1 缓存架构设计

```python
# graphrag/cache/multi_layer_cache.py

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
import redis
import pickle
import hashlib
import json
import time

class CacheLayer(ABC):
    """缓存层抽象基类"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

class MemoryCache(CacheLayer):
    """内存缓存 - L1缓存"""
    
    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry["expire_time"]:
                self.access_times[key] = time.time()
                return entry["value"]
            else:
                await self.delete(key)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        # LRU淘汰策略
        if len(self.cache) >= self.max_size:
            await self._evict_lru()
        
        self.cache[key] = {
            "value": value,
            "expire_time": time.time() + ttl
        }
        self.access_times[key] = time.time()
        return True
    
    async def _evict_lru(self):
        """淘汰最近最少使用的条目"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
        await self.delete(lru_key)

class RedisCache(CacheLayer):
    """Redis缓存 - L2缓存"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        try:
            serialized = pickle.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

class MultiLayerCache:
    """多层缓存管理器"""
    
    def __init__(self):
        self.layers = [
            MemoryCache(max_size=5000),     # L1: 内存缓存
            RedisCache(),                   # L2: Redis缓存
        ]
        
        # 缓存预热策略
        self.preload_patterns = {
            "frequent_queries": self._preload_frequent_queries,
            "user_context": self._preload_user_context,
            "game_entities": self._preload_game_entities
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """多层缓存查找"""
        for i, layer in enumerate(self.layers):
            value = await layer.get(key)
            if value is not None:
                # 回填到更快的缓存层
                for j in range(i):
                    await self.layers[j].set(key, value)
                return value
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """写入所有缓存层"""
        tasks = [
            layer.set(key, value, ttl) for layer in self.layers
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _generate_cache_key(self, query: str, context: Dict = None) -> str:
        """生成缓存键"""
        content = query
        if context:
            content += json.dumps(context, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _preload_frequent_queries(self):
        """预加载频繁查询"""
        frequent_queries = [
            "今日DAU趋势",
            "付费转化率分析", 
            "新手留存情况",
            "热门道具排行"
        ]
        
        for query in frequent_queries:
            cache_key = self._generate_cache_key(query)
            # 预计算并缓存结果
            result = await self._compute_query_result(query)
            await self.set(cache_key, result, ttl=7200)  # 2小时
```

### 2.2 智能缓存策略

```python
# graphrag/cache/intelligent_cache.py

class IntelligentCacheManager:
    """智能缓存管理器 - 基于使用模式优化缓存策略"""
    
    def __init__(self, cache: MultiLayerCache):
        self.cache = cache
        self.usage_stats = {}
        self.cache_hit_rates = {}
        
        # 启动缓存分析任务
        asyncio.create_task(self._analyze_cache_patterns())
    
    async def get_with_intelligence(self, query: str, user_context: Dict) -> Any:
        """智能缓存获取"""
        
        # 1. 生成多个候选缓存键
        cache_keys = self._generate_candidate_keys(query, user_context)
        
        # 2. 并行查找所有候选键
        tasks = [self.cache.get(key) for key in cache_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. 返回第一个有效结果
        for result in results:
            if result is not None and not isinstance(result, Exception):
                return result
        
        return None
    
    def _generate_candidate_keys(self, query: str, user_context: Dict) -> List[str]:
        """生成候选缓存键 - 支持模糊匹配"""
        keys = []
        
        # 精确匹配
        exact_key = self.cache._generate_cache_key(query, user_context)
        keys.append(exact_key)
        
        # 忽略用户上下文的通用匹配
        generic_key = self.cache._generate_cache_key(query)
        keys.append(generic_key)
        
        # 语义相似查询匹配
        similar_queries = self._find_similar_queries(query)
        for similar_query in similar_queries:
            similar_key = self.cache._generate_cache_key(similar_query)
            keys.append(similar_key)
        
        return keys
    
    async def _analyze_cache_patterns(self):
        """分析缓存使用模式"""
        while True:
            await asyncio.sleep(300)  # 每5分钟分析一次
            
            # 分析热点查询
            hot_queries = self._identify_hot_queries()
            
            # 预加载热点查询结果
            for query in hot_queries:
                await self._preload_query_variants(query)
    
    def _identify_hot_queries(self) -> List[str]:
        """识别热点查询"""
        # 基于访问频率和响应时间分析
        return sorted(
            self.usage_stats.items(),
            key=lambda x: x[1]["frequency"] / x[1]["avg_response_time"],
            reverse=True
        )[:20]  # 返回top 20热点查询
```

### 2.3 游戏场景专用缓存

```python
# graphrag/cache/game_specific_cache.py

class GameAnalyticsCacheManager:
    """游戏分析专用缓存管理器"""
    
    def __init__(self):
        self.base_cache = MultiLayerCache()
        
        # 游戏数据特定的缓存策略
        self.cache_strategies = {
            "real_time_metrics": {
                "ttl": 60,      # 1分钟过期
                "preload": True,
                "priority": "high"
            },
            "daily_reports": {
                "ttl": 3600,    # 1小时过期
                "preload": True,
                "priority": "medium"
            },
            "historical_analysis": {
                "ttl": 86400,   # 24小时过期
                "preload": False,
                "priority": "low"
            }
        }
    
    async def get_game_metric(self, metric_type: str, query: str, **kwargs) -> Any:
        """获取游戏指标 - 根据指标类型使用不同缓存策略"""
        
        strategy = self.cache_strategies.get(metric_type, {})
        
        # 生成带类型前缀的缓存键
        cache_key = f"game:{metric_type}:{self._generate_key(query, kwargs)}"
        
        # 尝试从缓存获取
        result = await self.base_cache.get(cache_key)
        if result is not None:
            return result
        
        # 缓存未命中，计算结果
        result = await self._compute_game_metric(metric_type, query, **kwargs)
        
        # 根据策略缓存结果
        ttl = strategy.get("ttl", 3600)
        await self.base_cache.set(cache_key, result, ttl)
        
        return result
    
    async def warm_up_daily_cache(self):
        """预热每日缓存 - 在低峰期预计算"""
        daily_metrics = [
            ("real_time_metrics", "当前在线玩家数"),
            ("real_time_metrics", "实时付费转化率"),
            ("daily_reports", "今日新增用户"),
            ("daily_reports", "今日收入统计"),
            ("daily_reports", "热门关卡分析")
        ]
        
        tasks = []
        for metric_type, query in daily_metrics:
            task = asyncio.create_task(
                self.get_game_metric(metric_type, query)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
```

---

## 3. Milvus向量检索优化

### 3.1 Milvus集群架构优化

```python
# graphrag/vector_store/milvus_optimizer.py

from pymilvus import connections, Collection, utility
import numpy as np
from typing import List, Dict, Tuple
import asyncio
import concurrent.futures

class OptimizedMilvusClient:
    """优化的Milvus客户端 - 专为高并发场景设计"""
    
    def __init__(self, hosts: List[str], port: int = 19530):
        self.hosts = hosts
        self.port = port
        self.connections = {}
        self.connection_pool_size = len(hosts) * 4  # 每个节点4个连接
        
        # 初始化连接池
        asyncio.create_task(self._init_connection_pool())
        
        # 性能优化配置
        self.search_params = {
            "metric_type": "IP",           # 内积距离，比L2更快
            "params": {
                "nprobe": 32,              # 降低nprobe提升速度
                "max_empty_result_buckets": 2
            }
        }
        
        # 批量搜索配置
        self.batch_size = 100
        self.max_concurrent_searches = 50
    
    async def _init_connection_pool(self):
        """初始化连接池"""
        for i, host in enumerate(self.hosts):
            for j in range(4):  # 每个主机4个连接
                conn_name = f"conn_{i}_{j}"
                connections.connect(
                    alias=conn_name,
                    host=host,
                    port=self.port,
                    # 连接池优化配置
                    pool_size=20,
                    secure=False,
                    timeout=10
                )
                self.connections[conn_name] = {
                    "host": host,
                    "load": 0,
                    "last_used": time.time()
                }
    
    def _get_optimal_connection(self) -> str:
        """获取最优连接 - 负载均衡"""
        return min(
            self.connections.items(),
            key=lambda x: (x[1]["load"], x[1]["last_used"])
        )[0]
    
    async def parallel_search(self, 
                            collection_name: str,
                            query_vectors: List[List[float]],
                            top_k: int = 10) -> List[List[Dict]]:
        """并行向量搜索 - 支持大批量查询"""
        
        collection = Collection(collection_name)
        
        # 分批处理
        batches = [
            query_vectors[i:i + self.batch_size]
            for i in range(0, len(query_vectors), self.batch_size)
        ]
        
        # 创建并发搜索任务
        semaphore = asyncio.Semaphore(self.max_concurrent_searches)
        
        async def search_batch(batch: List[List[float]]) -> List[List[Dict]]:
            async with semaphore:
                conn_name = self._get_optimal_connection()
                self.connections[conn_name]["load"] += 1
                
                try:
                    # 使用线程池执行同步搜索
                    loop = asyncio.get_event_loop()
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            self._sync_search,
                            collection, batch, top_k, conn_name
                        )
                        result = await loop.run_in_executor(None, lambda: future.result())
                    
                    return result
                finally:
                    self.connections[conn_name]["load"] -= 1
                    self.connections[conn_name]["last_used"] = time.time()
        
        # 并行执行所有批次
        batch_tasks = [search_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # 合并结果
        final_results = []
        for batch_result in batch_results:
            final_results.extend(batch_result)
        
        return final_results
    
    def _sync_search(self, collection, vectors, top_k, conn_name):
        """同步搜索实现"""
        # 使用指定连接
        connections.connect(alias=conn_name)
        
        results = collection.search(
            data=vectors,
            anns_field="embedding",
            param=self.search_params,
            limit=top_k,
            output_fields=["id", "content", "metadata"]
        )
        
        return self._format_search_results(results)

class MilvusIndexOptimizer:
    """Milvus索引优化器"""
    
    def __init__(self, collection: Collection):
        self.collection = collection
    
    async def optimize_for_game_queries(self):
        """针对游戏查询优化索引"""
        
        # 1. 创建多个索引以支持不同查询模式
        index_configs = [
            {
                "field_name": "embedding",
                "index_type": "IVF_FLAT",
                "metric_type": "IP",
                "params": {"nlist": 1024}  # 适中的聚类数量
            },
            {
                "field_name": "embedding",
                "index_type": "HNSW",
                "metric_type": "IP", 
                "params": {
                    "M": 16,               # 连接数
                    "efConstruction": 200  # 构建时的候选数
                }
            }
        ]
        
        for config in index_configs:
            await self._create_index_async(config)
    
    async def _create_index_async(self, config: Dict):
        """异步创建索引"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.collection.create_index(
                field_name=config["field_name"],
                index_params=config
            )
        )
```

### 3.2 向量检索加速策略

```python
# graphrag/vector_store/retrieval_acceleration.py

class RetrievalAccelerator:
    """检索加速器 - 多种加速策略组合"""
    
    def __init__(self, milvus_client: OptimizedMilvusClient):
        self.milvus_client = milvus_client
        self.query_cache = {}
        self.embedding_cache = {}
        
        # 预计算常用查询的embedding
        asyncio.create_task(self._precompute_embeddings())
    
    async def fast_retrieval(self, 
                           query: str,
                           top_k: int = 10,
                           use_cache: bool = True) -> List[Dict]:
        """快速检索 - 组合多种加速策略"""
        
        # 1. 查询缓存检查
        if use_cache:
            cache_key = f"{query}_{top_k}"
            if cache_key in self.query_cache:
                return self.query_cache[cache_key]
        
        # 2. 并行执行embedding计算和相似查询查找
        embedding_task = asyncio.create_task(
            self._get_or_compute_embedding(query)
        )
        similar_queries_task = asyncio.create_task(
            self._find_similar_cached_queries(query)
        )
        
        embedding, similar_queries = await asyncio.gather(
            embedding_task, similar_queries_task
        )
        
        # 3. 如果有相似查询的缓存结果，直接返回
        for similar_query, similarity in similar_queries:
            if similarity > 0.95:  # 高相似度阈值
                cache_key = f"{similar_query}_{top_k}"
                if cache_key in self.query_cache:
                    return self.query_cache[cache_key]
        
        # 4. 执行向量搜索
        search_results = await self.milvus_client.parallel_search(
            collection_name="game_knowledge",
            query_vectors=[embedding],
            top_k=top_k
        )
        
        # 5. 缓存结果
        if use_cache:
            self.query_cache[cache_key] = search_results[0]
        
        return search_results[0]
    
    async def _get_or_compute_embedding(self, query: str) -> List[float]:
        """获取或计算embedding"""
        if query in self.embedding_cache:
            return self.embedding_cache[query]
        
        # 异步计算embedding
        embedding = await self._compute_embedding_async(query)
        self.embedding_cache[query] = embedding
        return embedding
    
    async def _compute_embedding_async(self, text: str) -> List[float]:
        """异步计算embedding"""
        # 使用线程池避免阻塞
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self._sync_embedding_compute, text)
            return await loop.run_in_executor(None, lambda: future.result())
    
    async def _precompute_embeddings(self):
        """预计算常用查询的embedding"""
        frequent_queries = [
            "玩家留存率分析",
            "付费转化率统计", 
            "新手引导效果",
            "关卡难度平衡",
            "道具使用情况",
            "活动参与度分析"
        ]
        
        tasks = [
            self._get_or_compute_embedding(query) 
            for query in frequent_queries
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

class HybridRetriever:
    """混合检索器 - 结合向量检索和传统检索"""
    
    def __init__(self, 
                 vector_retriever: RetrievalAccelerator,
                 keyword_retriever):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        
        # 检索权重配置
        self.retrieval_weights = {
            "vector": 0.7,
            "keyword": 0.3
        }
    
    async def hybrid_search(self, 
                          query: str,
                          top_k: int = 10) -> List[Dict]:
        """混合搜索 - 并行执行多种检索策略"""
        
        # 并行执行不同检索策略
        vector_task = asyncio.create_task(
            self.vector_retriever.fast_retrieval(query, top_k * 2)
        )
        keyword_task = asyncio.create_task(
            self.keyword_retriever.search(query, top_k * 2)
        )
        
        vector_results, keyword_results = await asyncio.gather(
            vector_task, keyword_task, return_exceptions=True
        )
        
        # 结果融合和重排序
        combined_results = self._merge_and_rerank(
            vector_results, keyword_results, query
        )
        
        return combined_results[:top_k]
    
    def _merge_and_rerank(self, 
                         vector_results: List[Dict],
                         keyword_results: List[Dict],
                         query: str) -> List[Dict]:
        """合并和重排序结果"""
        
        # 使用加权分数合并
        all_results = {}
        
        # 处理向量检索结果
        for i, result in enumerate(vector_results):
            doc_id = result["id"]
            vector_score = (len(vector_results) - i) / len(vector_results)
            
            if doc_id not in all_results:
                all_results[doc_id] = result.copy()
                all_results[doc_id]["combined_score"] = 0
            
            all_results[doc_id]["combined_score"] += (
                vector_score * self.retrieval_weights["vector"]
            )
        
        # 处理关键词检索结果
        for i, result in enumerate(keyword_results):
            doc_id = result["id"]
            keyword_score = (len(keyword_results) - i) / len(keyword_results)
            
            if doc_id not in all_results:
                all_results[doc_id] = result.copy()
                all_results[doc_id]["combined_score"] = 0
            
            all_results[doc_id]["combined_score"] += (
                keyword_score * self.retrieval_weights["keyword"]
            )
        
        # 按合并分数排序
        return sorted(
            all_results.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
```

---

## 4. 硬件与基础设施加速

### 4.1 GPU加速配置

```python
# graphrag/acceleration/gpu_optimizer.py

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import numpy as np
from typing import List, Dict
import asyncio

class GPUAcceleratedEmbedding:
    """GPU加速的embedding计算"""
    
    def __init__(self, 
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 batch_size: int = 32,
                 max_length: int = 512):
        
        # 检查GPU可用性
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        
        # 加载模型到GPU
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        
        self.batch_size = batch_size
        self.max_length = max_length
        
        # 启用混合精度计算
        self.scaler = torch.cuda.amp.GradScaler()
    
    async def encode_batch(self, texts: List[str]) -> np.ndarray:
        """批量编码文本 - GPU加速"""
        
        if not texts:
            return np.array([])
        
        # 分批处理
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            
            # 异步处理批次
            batch_embeddings = await self._encode_single_batch(batch_texts)
            all_embeddings.append(batch_embeddings)
        
        return np.vstack(all_embeddings)
    
    async def _encode_single_batch(self, texts: List[str]) -> np.ndarray:
        """处理单个批次"""
        loop = asyncio.get_event_loop()
        
        def _sync_encode():
            # Token化
            inputs = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt"
            )
            
            # 移动到GPU
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 前向传播 (使用混合精度)
            with torch.no_grad():
                with torch.cuda.amp.autocast():
                    outputs = self.model(**inputs)
                    
                    # Mean pooling
                    attention_mask = inputs['attention_mask']
                    token_embeddings = outputs.last_hidden_state
                    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                    
                    embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                    
                    # L2标准化
                    embeddings = F.normalize(embeddings, p=2, dim=1)
                    
                    return embeddings.cpu().numpy()
        
        return await loop.run_in_executor(None, _sync_encode)

class GPUAcceleratedReranker:
    """GPU加速的重排序器"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 加载重排序模型
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
    
    async def rerank_batch(self, 
                          query: str, 
                          documents: List[str],
                          top_k: int = 10) -> List[Dict]:
        """批量重排序"""
        
        if len(documents) <= top_k:
            return [{"text": doc, "score": 1.0} for doc in documents]
        
        # 构建查询-文档对
        pairs = [(query, doc) for doc in documents]
        
        # GPU加速评分
        scores = await self._compute_relevance_scores(pairs)
        
        # 排序并返回top-k
        scored_docs = [
            {"text": doc, "score": float(score)}
            for doc, score in zip(documents, scores)
        ]
        
        return sorted(scored_docs, key=lambda x: x["score"], reverse=True)[:top_k]
    
    async def _compute_relevance_scores(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """计算相关性分数"""
        loop = asyncio.get_event_loop()
        
        def _sync_score():
            scores = []
            batch_size = 16
            
            for i in range(0, len(pairs), batch_size):
                batch_pairs = pairs[i:i + batch_size]
                
                # Token化
                inputs = self.tokenizer(
                    batch_pairs,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                )
                
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    with torch.cuda.amp.autocast():
                        outputs = self.model(**inputs)
                        batch_scores = outputs.logits.squeeze().cpu().numpy()
                        
                        if batch_scores.ndim == 0:
                            batch_scores = [batch_scores.item()]
                        
                        scores.extend(batch_scores)
            
            return scores
        
        return await loop.run_in_executor(None, _sync_score)
```

### 4.2 基础设施优化

```python
# graphrag/infrastructure/cluster_manager.py

class HighPerformanceCluster:
    """高性能集群管理器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.nodes = self._initialize_nodes()
        self.load_balancer = LoadBalancer(self.nodes)
        
        # 监控和自动扩缩容
        asyncio.create_task(self._monitor_cluster_health())
    
    def _initialize_nodes(self) -> List[Dict]:
        """初始化集群节点"""
        nodes = []
        
        # GPU节点 - 专门处理embedding和重排序
        for i in range(self.config["gpu_nodes"]):
            nodes.append({
                "id": f"gpu-{i}",
                "type": "gpu",
                "capabilities": ["embedding", "reranking"],
                "load": 0,
                "max_load": 100,
                "endpoint": f"http://gpu-{i}:8000"
            })
        
        # CPU节点 - 处理检索和缓存
        for i in range(self.config["cpu_nodes"]):
            nodes.append({
                "id": f"cpu-{i}",
                "type": "cpu", 
                "capabilities": ["retrieval", "caching", "postprocessing"],
                "load": 0,
                "max_load": 80,
                "endpoint": f"http://cpu-{i}:8000"
            })
        
        # 向量数据库节点
        for i in range(self.config["vector_db_nodes"]):
            nodes.append({
                "id": f"milvus-{i}",
                "type": "vector_db",
                "capabilities": ["vector_search"],
                "load": 0,
                "max_load": 90,
                "endpoint": f"http://milvus-{i}:19530"
            })
        
        return nodes
    
    async def process_query_distributed(self, query: str) -> Dict:
        """分布式查询处理"""
        
        # 1. 查询预处理 - 路由到CPU节点
        preprocessing_node = self.load_balancer.get_best_node("cpu")
        preprocessed_query = await self._call_node(
            preprocessing_node,
            "preprocess",
            {"query": query}
        )
        
        # 2. Embedding计算 - 路由到GPU节点
        embedding_node = self.load_balancer.get_best_node("gpu")
        embedding_task = asyncio.create_task(
            self._call_node(
                embedding_node,
                "compute_embedding",
                {"query": preprocessed_query["cleaned_query"]}
            )
        )
        
        # 3. 向量检索 - 路由到向量数据库节点
        vector_db_node = self.load_balancer.get_best_node("vector_db")
        
        # 等待embedding完成后进行检索
        embedding_result = await embedding_task
        retrieval_result = await self._call_node(
            vector_db_node,
            "vector_search",
            {
                "embedding": embedding_result["embedding"],
                "top_k": 20
            }
        )
        
        # 4. 重排序 - 路由到GPU节点 (可以与embedding并行)
        rerank_node = self.load_balancer.get_best_node("gpu", exclude=[embedding_node["id"]])
        reranked_results = await self._call_node(
            rerank_node,
            "rerank",
            {
                "query": query,
                "documents": retrieval_result["documents"]
            }
        )
        
        # 5. 后处理 - 路由到CPU节点
        postprocess_node = self.load_balancer.get_best_node("cpu", exclude=[preprocessing_node["id"]])
        final_result = await self._call_node(
            postprocess_node,
            "postprocess",
            {
                "query": query,
                "documents": reranked_results["documents"]
            }
        )
        
        return final_result
    
    async def _monitor_cluster_health(self):
        """监控集群健康状态"""
        while True:
            await asyncio.sleep(30)  # 每30秒检查一次
            
            for node in self.nodes:
                try:
                    health = await self._call_node(node, "health", {})
                    node["load"] = health["load"]
                    node["status"] = health["status"]
                    
                    # 自动扩缩容逻辑
                    if health["load"] > 85:
                        await self._scale_up(node["type"])
                    elif health["load"] < 20:
                        await self._scale_down(node["type"])
                        
                except Exception as e:
                    logger.error(f"Node {node['id']} health check failed: {e}")
                    node["status"] = "unhealthy"

class LoadBalancer:
    """智能负载均衡器"""
    
    def __init__(self, nodes: List[Dict]):
        self.nodes = nodes
        self.routing_strategy = "least_loaded"
    
    def get_best_node(self, 
                     capability: str, 
                     exclude: List[str] = None) -> Dict:
        """获取最佳节点"""
        exclude = exclude or []
        
        # 筛选具备指定能力的节点
        capable_nodes = [
            node for node in self.nodes
            if capability in node["capabilities"]
            and node["id"] not in exclude
            and node.get("status", "healthy") == "healthy"
        ]
        
        if not capable_nodes:
            raise Exception(f"No healthy nodes available for capability: {capability}")
        
        # 根据策略选择节点
        if self.routing_strategy == "least_loaded":
            return min(capable_nodes, key=lambda x: x["load"])
        elif self.routing_strategy == "round_robin":
            return self._round_robin_select(capable_nodes)
        else:
            return capable_nodes[0]
```

### 4.3 网络优化

```yaml
# docker-compose.yml - 网络优化配置

version: '3.8'

services:
  nginx-lb:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - graphrag-api-1
      - graphrag-api-2
      - graphrag-api-3

  # API服务集群
  graphrag-api-1:
    image: graphrag:latest
    environment:
      - NODE_ID=api-1
      - REDIS_URL=redis://redis-cluster:6379
      - MILVUS_HOST=milvus-cluster
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    networks:
      - graphrag-network

  # GPU加速节点
  graphrag-gpu-1:
    image: graphrag:gpu
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - NODE_TYPE=gpu
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Milvus集群
  milvus-cluster:
    image: milvusdb/milvus:v2.3.0
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - milvus_data:/var/lib/milvus
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G

  # Redis集群
  redis-cluster:
    image: redis:7-alpine
    command: redis-server --appendonly yes --cluster-enabled yes
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

networks:
  graphrag-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

```nginx
# nginx.conf - 高性能负载均衡配置

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    # 连接池优化
    upstream graphrag_api {
        least_conn;
        server graphrag-api-1:8000 max_fails=3 fail_timeout=30s;
        server graphrag-api-2:8000 max_fails=3 fail_timeout=30s;
        server graphrag-api-3:8000 max_fails=3 fail_timeout=30s;
        keepalive 100;
    }
    
    upstream graphrag_gpu {
        least_conn;
        server graphrag-gpu-1:8000 max_fails=2 fail_timeout=30s;
        server graphrag-gpu-2:8000 max_fails=2 fail_timeout=30s;
        keepalive 50;
    }
    
    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 1000;
    
    # 缓存配置
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;
    
    server {
        listen 80;
        
        # API路由 - 普通查询
        location /api/query {
            proxy_pass http://graphrag_api;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            
            # 超时设置
            proxy_connect_timeout 5s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            
            # 缓存设置
            proxy_cache api_cache;
            proxy_cache_valid 200 5m;
            proxy_cache_key "$scheme$request_method$host$request_uri";
        }
        
        # GPU加速路由 - embedding和重排序
        location /api/embedding {
            proxy_pass http://graphrag_gpu;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            
            # GPU任务通常较重，延长超时
            proxy_connect_timeout 10s;
            proxy_send_timeout 120s;
            proxy_read_timeout 120s;
        }
        
        # 流式响应
        location /api/stream {
            proxy_pass http://graphrag_api;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_buffering off;
            proxy_cache off;
        }
    }
}
```

---

## 5. 性能监控与调优

### 5.1 实时性能监控

```python
# graphrag/monitoring/performance_monitor.py

import time
import psutil
import asyncio
from typing import Dict, List
import logging
from dataclasses import dataclass
from collections import deque
import numpy as np

@dataclass
class PerformanceMetrics:
    """性能指标数据结构"""
    timestamp: float
    response_time: float
    concurrent_queries: int
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    cache_hit_rate: float
    error_rate: float

class RealTimeMonitor:
    """实时性能监控器"""
    
    def __init__(self, window_size: int = 1000):
        self.metrics_history = deque(maxlen=window_size)
        self.current_queries = {}
        self.alert_thresholds = {
            "response_time": 2.0,      # 2秒
            "cpu_usage": 80.0,         # 80%
            "memory_usage": 85.0,      # 85%
            "error_rate": 5.0,         # 5%
            "cache_hit_rate": 70.0     # 70%
        }
        
        # 启动监控任务
        asyncio.create_task(self._continuous_monitoring())
    
    async def track_query_start(self, query_id: str, query: str):
        """跟踪查询开始"""
        self.current_queries[query_id] = {
            "start_time": time.time(),
            "query": query,
            "stage": "started"
        }
    
    async def track_query_end(self, query_id: str, success: bool = True):
        """跟踪查询结束"""
        if query_id in self.current_queries:
            query_info = self.current_queries[query_id]
            response_time = time.time() - query_info["start_time"]
            
            # 记录性能指标
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                response_time=response_time,
                concurrent_queries=len(self.current_queries),
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                gpu_usage=self._get_gpu_usage(),
                cache_hit_rate=self._get_cache_hit_rate(),
                error_rate=self._calculate_error_rate()
            )
            
            self.metrics_history.append(metrics)
            del self.current_queries[query_id]
            
            # 检查告警条件
            await self._check_alerts(metrics)
    
    async def _continuous_monitoring(self):
        """持续监控系统状态"""
        while True:
            await asyncio.sleep(10)  # 每10秒采集一次
            
            current_metrics = PerformanceMetrics(
                timestamp=time.time(),
                response_time=self._get_avg_response_time(),
                concurrent_queries=len(self.current_queries),
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                gpu_usage=self._get_gpu_usage(),
                cache_hit_rate=self._get_cache_hit_rate(),
                error_rate=self._calculate_error_rate()
            )
            
            self.metrics_history.append(current_metrics)
            await self._check_alerts(current_metrics)
    
    async def _check_alerts(self, metrics: PerformanceMetrics):
        """检查告警条件"""
        alerts = []
        
        if metrics.response_time > self.alert_thresholds["response_time"]:
            alerts.append(f"高响应时间告警: {metrics.response_time:.2f}s")
        
        if metrics.cpu_usage > self.alert_thresholds["cpu_usage"]:
            alerts.append(f"CPU使用率告警: {metrics.cpu_usage:.1f}%")
        
        if metrics.memory_usage > self.alert_thresholds["memory_usage"]:
            alerts.append(f"内存使用率告警: {metrics.memory_usage:.1f}%")
        
        if metrics.cache_hit_rate < self.alert_thresholds["cache_hit_rate"]:
            alerts.append(f"缓存命中率告警: {metrics.cache_hit_rate:.1f}%")
        
        for alert in alerts:
            logger.warning(alert)
            await self._send_alert(alert)
    
    def get_performance_summary(self) -> Dict:
        """获取性能摘要"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history)[-100:]  # 最近100条记录
        
        return {
            "avg_response_time": np.mean([m.response_time for m in recent_metrics]),
            "p95_response_time": np.percentile([m.response_time for m in recent_metrics], 95),
            "p99_response_time": np.percentile([m.response_time for m in recent_metrics], 99),
            "avg_cpu_usage": np.mean([m.cpu_usage for m in recent_metrics]),
            "avg_memory_usage": np.mean([m.memory_usage for m in recent_metrics]),
            "cache_hit_rate": np.mean([m.cache_hit_rate for m in recent_metrics]),
            "current_concurrent_queries": len(self.current_queries),
            "total_queries_processed": len(self.metrics_history)
        }
```

### 5.2 自动调优系统

```python
# graphrag/optimization/auto_tuner.py

class AutoTuner:
    """自动调优系统"""
    
    def __init__(self, monitor: RealTimeMonitor):
        self.monitor = monitor
        self.tuning_history = []
        self.current_config = self._load_default_config()
        
        # 启动自动调优
        asyncio.create_task(self._auto_tuning_loop())
    
    async def _auto_tuning_loop(self):
        """自动调优循环"""
        while True:
            await asyncio.sleep(300)  # 每5分钟评估一次
            
            # 获取性能指标
            performance = self.monitor.get_performance_summary()
            
            # 判断是否需要调优
            if await self._should_tune(performance):
                await self._apply_optimization(performance)
    
    async def _should_tune(self, performance: Dict) -> bool:
        """判断是否需要调优"""
        return (
            performance.get("avg_response_time", 0) > 1.0 or
            performance.get("cache_hit_rate", 100) < 70 or
            performance.get("avg_cpu_usage", 0) > 75
        )
    
    async def _apply_optimization(self, performance: Dict):
        """应用优化策略"""
        optimizations = []
        
        # 响应时间优化
        if performance.get("avg_response_time", 0) > 1.0:
            optimizations.extend(await self._optimize_response_time())
        
        # 缓存优化
        if performance.get("cache_hit_rate", 100) < 70:
            optimizations.extend(await self._optimize_cache())
        
        # CPU优化
        if performance.get("avg_cpu_usage", 0) > 75:
            optimizations.extend(await self._optimize_cpu_usage())
        
        # 应用优化
        for optimization in optimizations:
            await self._apply_single_optimization(optimization)
    
    async def _optimize_response_time(self) -> List[Dict]:
        """优化响应时间"""
        return [
            {
                "type": "increase_cache_size",
                "action": "memory_cache.increase_size",
                "params": {"multiplier": 1.5}
            },
            {
                "type": "adjust_batch_size",
                "action": "embedding.reduce_batch_size",
                "params": {"new_batch_size": 16}
            },
            {
                "type": "enable_more_connections", 
                "action": "milvus.increase_connections",
                "params": {"additional_connections": 2}
            }
        ]
    
    async def _optimize_cache(self) -> List[Dict]:
        """优化缓存策略"""
        return [
            {
                "type": "preload_frequent_queries",
                "action": "cache.preload_frequent",
                "params": {"query_count": 50}
            },
            {
                "type": "adjust_ttl",
                "action": "cache.increase_ttl", 
                "params": {"multiplier": 1.2}
            }
        ]
```

---

## 6. 部署建议

### 6.1 生产环境配置

**硬件配置建议**：
- **API服务器**: 32 Core CPU + 64GB RAM × 3台
- **GPU节点**: NVIDIA A100/V100 × 2台 (embedding和重排序)
- **向量数据库**: 16 Core CPU + 32GB RAM + SSD × 3台 (Milvus集群)
- **缓存集群**: 8 Core CPU + 16GB RAM × 3台 (Redis集群)

**网络配置**：
- 内网带宽: ≥10Gbps
- 外网带宽: ≥1Gbps  
- CDN加速: 静态资源和API缓存

### 6.2 扩容策略

```python
# 自动扩容配置
AUTO_SCALING_CONFIG = {
    "triggers": {
        "cpu_usage": {"threshold": 75, "action": "scale_up"},
        "response_time": {"threshold": 2.0, "action": "scale_up"},
        "queue_depth": {"threshold": 100, "action": "scale_up"},
        "error_rate": {"threshold": 5.0, "action": "scale_up"}
    },
    "scaling_policies": {
        "scale_up": {"min_instances": 2, "max_instances": 10, "step": 2},
        "scale_down": {"cooldown": 300, "step": 1}
    }
}
```

## 总结

通过以上四个维度的优化：

1. **异步调用架构** - 解决了同步阻塞问题，支持高并发
2. **多层缓存体系** - 大幅减少重复计算，提升响应速度  
3. **Milvus向量检索优化** - 加速召回阶段，降低检索延迟
4. **硬件与基础设施加速** - 底层性能提升，支撑大规模并发

可以将首字响应时间从秒级优化到毫秒级，同时支持500+并发用户的大客户测试场景。这套方案特别适合ToB场景中"所有人一起测试"的高并发压力。 