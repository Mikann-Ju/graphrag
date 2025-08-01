# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""GraphRAG智能缓存系统 - 基于查询向量相似性的缓存实现"""

import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import numpy as np

# 外部依赖的条件导入
try:
    import redis
except ImportError:
    redis = None

try:
    import faiss
except ImportError:
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

@dataclass
class CachedResult:
    """缓存结果数据结构"""
    query: str
    result: Dict[str, Any]
    timestamp: float
    hit_count: int = 0
    vector: Optional[np.ndarray] = None
    similar_queries: Optional[List[str]] = None

    def __post_init__(self):
        if self.similar_queries is None:
            self.similar_queries = []

class VectorSimilarityCache:
    """基于向量相似性的智能缓存系统"""
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 embedding_model: str = "all-MiniLM-L6-v2",
                 similarity_threshold: float = 0.85,
                 cache_ttl: int = 3600,
                 max_cache_size: int = 10000):
        
        # 检查依赖
        if redis is None:
            raise ImportError("请安装redis: pip install redis")
        if faiss is None:
            raise ImportError("请安装faiss: pip install faiss-cpu")
        if SentenceTransformer is None:
            raise ImportError("请安装sentence-transformers: pip install sentence-transformers")
        
        # Redis连接
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db,
            decode_responses=True
        )
        
        # 向量模型
        self.embedding_model = SentenceTransformer(embedding_model)
        self.vector_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # FAISS索引
        self.faiss_index = faiss.IndexFlatIP(self.vector_dim)
        self.query_vectors: List[np.ndarray] = []
        self.query_hashes: List[str] = []
        
        # 配置参数
        self.similarity_threshold = similarity_threshold
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        
        # 性能统计
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "similarity_hits": 0
        }
        
        # 从Redis恢复索引
        self._restore_index_from_redis()
    
    def _generate_query_hash(self, query: str) -> str:
        """生成查询hash"""
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def _encode_query(self, query: str) -> np.ndarray:
        """将查询转换为向量"""
        return self.embedding_model.encode([query])[0].astype('float32')
    
    def _restore_index_from_redis(self):
        """从Redis恢复FAISS索引"""
        try:
            # 获取所有缓存的查询
            cache_keys = self.redis_client.keys("query_cache:*")
            
            for key in cache_keys:
                cached_data = self.redis_client.hgetall(key)
                if cached_data and "vector" in cached_data:
                    # 恢复向量和hash
                    vector = np.frombuffer(
                        bytes.fromhex(cached_data["vector"]), 
                        dtype=np.float32
                    )
                    query_hash = key.split(":")[-1]
                    
                    self.query_vectors.append(vector)
                    self.query_hashes.append(query_hash)
            
            # 重建FAISS索引
            if self.query_vectors:
                vectors_array = np.vstack(self.query_vectors)
                self.faiss_index.add(vectors_array)
                logger.info(f"从Redis恢复了 {len(self.query_vectors)} 个查询向量到FAISS索引")
        
        except Exception as e:
            logger.warning(f"从Redis恢复索引失败: {e}")
    
    def _find_similar_query(self, query_vector: np.ndarray) -> Tuple[Optional[str], float]:
        """查找相似查询"""
        if self.faiss_index.ntotal == 0:
            return None, 0.0
        
        # FAISS搜索
        similarities, indices = self.faiss_index.search(
            query_vector.reshape(1, -1), k=1
        )
        
        if len(similarities[0]) > 0:
            similarity = float(similarities[0][0])
            if similarity >= self.similarity_threshold:
                index = int(indices[0][0])
                similar_query_hash = self.query_hashes[index]
                return similar_query_hash, similarity
        
        return None, 0.0
    
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        self.stats["total_queries"] += 1
        
        # 1. 生成查询向量
        query_vector = self._encode_query(query)
        query_hash = self._generate_query_hash(query)
        
        # 2. 首先检查精确匹配
        cache_key = f"query_cache:{query_hash}"
        cached_data = self.redis_client.hgetall(cache_key)
        
        if cached_data and "result" in cached_data:
            # 精确命中
            self.stats["cache_hits"] += 1
            self._update_hit_count(cache_key)
            
            logger.info(f"缓存精确命中: {query[:50]}...")
            return json.loads(cached_data["result"])
        
        # 3. 查找相似查询
        similar_hash, similarity = self._find_similar_query(query_vector)
        
        if similar_hash:
            similar_cache_key = f"query_cache:{similar_hash}"
            similar_data = self.redis_client.hgetall(similar_cache_key)
            
            if similar_data and "result" in similar_data:
                # 相似性命中
                self.stats["similarity_hits"] += 1
                self._update_hit_count(similar_cache_key)
                
                # 更新相似查询列表
                self._add_similar_query(similar_cache_key, query)
                
                logger.info(f"缓存相似性命中 (相似度: {similarity:.3f}): {query[:50]}...")
                return json.loads(similar_data["result"])
        
        # 4. 缓存未命中
        self.stats["cache_misses"] += 1
        logger.info(f"缓存未命中: {query[:50]}...")
        return None
    
    def set(self, query: str, result: Dict[str, Any]):
        """设置缓存"""
        try:
            # 生成查询向量和hash
            query_vector = self._encode_query(query)
            query_hash = self._generate_query_hash(query)
            
            # 检查缓存大小限制
            if len(self.query_vectors) >= self.max_cache_size:
                self._evict_old_cache()
            
            # 存储到Redis
            cache_key = f"query_cache:{query_hash}"
            cache_data = {
                "query": query,
                "result": json.dumps(result, ensure_ascii=False),
                "timestamp": time.time(),
                "hit_count": 0,
                "vector": query_vector.tobytes().hex(),
                "similar_queries": json.dumps([])
            }
            
            # 设置缓存和TTL
            self.redis_client.hset(cache_key, mapping=cache_data)
            self.redis_client.expire(cache_key, self.cache_ttl)
            
            # 更新FAISS索引
            self.faiss_index.add(query_vector.reshape(1, -1))
            self.query_vectors.append(query_vector)
            self.query_hashes.append(query_hash)
            
            logger.info(f"新查询已缓存: {query[:50]}...")
            
        except Exception as e:
            logger.error(f"缓存设置失败: {e}")
    
    def _update_hit_count(self, cache_key: str):
        """更新命中次数"""
        try:
            self.redis_client.hincrby(cache_key, "hit_count", 1)
            # 重新设置TTL
            self.redis_client.expire(cache_key, self.cache_ttl)
        except Exception as e:
            logger.error(f"更新命中次数失败: {e}")
    
    def _add_similar_query(self, cache_key: str, similar_query: str):
        """添加相似查询记录"""
        try:
            similar_queries_str = self.redis_client.hget(cache_key, "similar_queries")
            if similar_queries_str:
                similar_queries = json.loads(similar_queries_str)
                if similar_query not in similar_queries:
                    similar_queries.append(similar_query)
                    # 限制相似查询列表长度
                    if len(similar_queries) > 10:
                        similar_queries = similar_queries[-10:]
                    
                    self.redis_client.hset(
                        cache_key, 
                        "similar_queries", 
                        json.dumps(similar_queries, ensure_ascii=False)
                    )
        except Exception as e:
            logger.error(f"添加相似查询失败: {e}")
    
    def _evict_old_cache(self):
        """缓存淘汰策略"""
        try:
            # 获取所有缓存键和其统计信息
            cache_keys = self.redis_client.keys("query_cache:*")
            cache_stats = []
            
            for key in cache_keys:
                cached_data = self.redis_client.hgetall(key)
                if cached_data:
                    timestamp = float(cached_data.get("timestamp", 0))
                    hit_count = int(cached_data.get("hit_count", 0))
                    
                    # 计算淘汰分数 (综合考虑时间和命中次数)
                    age = time.time() - timestamp
                    eviction_score = age / (hit_count + 1)  # 年龄越大，命中越少，分数越高
                    
                    cache_stats.append((key, eviction_score))
            
            # 按淘汰分数排序，移除分数最高的10%
            cache_stats.sort(key=lambda x: x[1], reverse=True)
            evict_count = max(1, len(cache_stats) // 10)
            
            for i in range(evict_count):
                key_to_evict = cache_stats[i][0]
                query_hash = key_to_evict.split(":")[-1]
                
                # 从Redis删除
                self.redis_client.delete(key_to_evict)
                
                # 从内存索引删除 (FAISS不支持删除，需要重建)
                if query_hash in self.query_hashes:
                    index = self.query_hashes.index(query_hash)
                    self.query_hashes.pop(index)
                    self.query_vectors.pop(index)
            
            # 重建FAISS索引
            self._rebuild_faiss_index()
            
            logger.info(f"淘汰了 {evict_count} 个旧缓存项")
            
        except Exception as e:
            logger.error(f"缓存淘汰失败: {e}")
    
    def _rebuild_faiss_index(self):
        """重建FAISS索引"""
        try:
            self.faiss_index = faiss.IndexFlatIP(self.vector_dim)
            if self.query_vectors:
                vectors_array = np.vstack(self.query_vectors)
                self.faiss_index.add(vectors_array)
        except Exception as e:
            logger.error(f"重建FAISS索引失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_queries = self.stats["total_queries"]
        cache_hits = self.stats["cache_hits"]
        similarity_hits = self.stats["similarity_hits"]
        
        hit_rate = (cache_hits + similarity_hits) / max(total_queries, 1)
        similarity_rate = similarity_hits / max(total_queries, 1)
        
        return {
            "total_queries": total_queries,
            "cache_hits": cache_hits,
            "similarity_hits": similarity_hits,
            "cache_misses": self.stats["cache_misses"],
            "hit_rate": f"{hit_rate:.2%}",
            "similarity_rate": f"{similarity_rate:.2%}",
            "cached_items": self.faiss_index.ntotal,
            "similarity_threshold": self.similarity_threshold
        }
    
    def clear_cache(self):
        """清空所有缓存"""
        try:
            # 清空Redis
            cache_keys = self.redis_client.keys("query_cache:*")
            if cache_keys:
                self.redis_client.delete(*cache_keys)
            
            # 清空FAISS索引
            self.faiss_index = faiss.IndexFlatIP(self.vector_dim)
            self.query_vectors.clear()
            self.query_hashes.clear()
            
            # 重置统计
            self.stats = {
                "total_queries": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "similarity_hits": 0
            }
            
            logger.info("已清空所有缓存")
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

# 使用示例
def example_usage():
    """缓存使用示例"""
    
    # 初始化缓存
    cache = VectorSimilarityCache(
        similarity_threshold=0.8,
        cache_ttl=3600,
        max_cache_size=5000
    )
    
    # 模拟查询和结果
    queries_and_results = [
        ("分析玩家的付费行为模式", {"analysis": "高付费玩家倾向于...", "confidence": 0.95}),
        ("玩家付费行为分析", {"analysis": "高付费玩家倾向于...", "confidence": 0.95}),  # 相似查询
        ("如何提升玩家留存率", {"suggestions": "通过改善...", "confidence": 0.88}),
        ("提升玩家留存的方法", {"suggestions": "通过改善...", "confidence": 0.88}),  # 相似查询
    ]
    
    # 测试缓存功能
    for query, result in queries_and_results:
        print(f"\n查询: {query}")
        
        # 尝试从缓存获取
        cached_result = cache.get(query)
        
        if cached_result:
            print("✅ 缓存命中!")
            print(f"结果: {cached_result}")
        else:
            print("❌ 缓存未命中，执行新查询...")
            # 模拟执行实际查询
            time.sleep(0.1)  # 模拟查询延迟
            
            # 将结果存入缓存
            cache.set(query, result)
            print(f"结果: {result}")
    
    # 显示统计信息
    print(f"\n缓存统计: {cache.get_stats()}")

if __name__ == "__main__":
    example_usage() 