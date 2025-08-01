# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Query rewriting module for GraphRAG."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

from graphrag.language_model.protocol.base import ChatModel
from graphrag.data_model.entity import Entity
from graphrag.data_model.community_report import CommunityReport

logger = logging.getLogger(__name__)


class RewriteStrategy(Enum):
    """Query rewriting strategies."""
    DECOMPOSITION = "decomposition"        # 查询分解
    EXPANSION = "expansion"               # 查询扩展
    CLARIFICATION = "clarification"       # 查询澄清
    SIMPLIFICATION = "simplification"     # 查询简化
    CONTEXTUALIZATION = "contextualization"  # 上下文化
    GAME_SPECIFIC = "game_specific"       # 游戏领域特化


@dataclass
class RewriteResult:
    """Query rewrite result."""
    original_query: str
    rewritten_queries: List[str]
    strategy: RewriteStrategy
    confidence: float
    reasoning: str
    metadata: Optional[Dict[str, Any]] = None


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


class DecompositionRewriter(QueryRewriterBase):
    """Decomposes complex queries into simpler sub-queries."""
    
    def __init__(self, model: ChatModel, model_params: Optional[Dict[str, Any]] = None):
        self.model = model
        self.model_params = model_params or {}
    
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
        
        try:
            response = await self.model.achat(prompt, **self.model_params)
            result_text = response.output.content
            
            # Parse JSON response
            import json
            result = json.loads(result_text)
            
            return RewriteResult(
                original_query=query,
                rewritten_queries=result.get("sub_queries", [query]),
                strategy=self.get_strategy(),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", "Query decomposition completed"),
                metadata={"method": "llm_decomposition"}
            )
            
        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}")
            return RewriteResult(
                original_query=query,
                rewritten_queries=[query],
                strategy=self.get_strategy(),
                confidence=0.1,
                reasoning=f"Decomposition failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def get_strategy(self) -> RewriteStrategy:
        return RewriteStrategy.DECOMPOSITION


class ExpansionRewriter(QueryRewriterBase):
    """Expands queries with additional context and synonyms."""
    
    def __init__(
        self, 
        model: ChatModel, 
        entities: Optional[List[Entity]] = None,
        model_params: Optional[Dict[str, Any]] = None
    ):
        self.model = model
        self.entities = entities or []
        self.model_params = model_params or {}
    
    async def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> RewriteResult:
        """Expand query with related terms and concepts."""
        
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

请以JSON格式返回结果：
{{
    "expanded_queries": ["扩展查询1", "扩展查询2", ...],
    "reasoning": "扩展的原因和策略",
    "confidence": 0.8
}}
"""
        
        try:
            response = await self.model.achat(prompt, **self.model_params)
            result_text = response.output.content
            
            import json
            result = json.loads(result_text)
            
            return RewriteResult(
                original_query=query,
                rewritten_queries=result.get("expanded_queries", [query]),
                strategy=self.get_strategy(),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", "Query expansion completed"),
                metadata={
                    "method": "llm_expansion",
                    "relevant_entities": [e.title for e in relevant_entities[:5]]
                }
            )
            
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            return RewriteResult(
                original_query=query,
                rewritten_queries=[query],
                strategy=self.get_strategy(),
                confidence=0.1,
                reasoning=f"Expansion failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
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
    
    def get_strategy(self) -> RewriteStrategy:
        return RewriteStrategy.EXPANSION


class GameSpecificRewriter(QueryRewriterBase):
    """Game-specific query rewriter for gaming analytics context."""
    
    def __init__(self, model: ChatModel, model_params: Optional[Dict[str, Any]] = None):
        self.model = model
        self.model_params = model_params or {}
        
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
    
    async def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> RewriteResult:
        """Rewrite query with game-specific terminology and context."""
        
        # Build game terminology context
        terminology_context = "\n".join([
            f"{key}: {', '.join(values)}" 
            for key, values in self.game_terminology.items()
        ])
        
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
        
        try:
            response = await self.model.achat(prompt, **self.model_params)
            result_text = response.output.content
            
            import json
            result = json.loads(result_text)
            
            return RewriteResult(
                original_query=query,
                rewritten_queries=result.get("game_queries", [query]),
                strategy=self.get_strategy(),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", "Game-specific rewrite completed"),
                metadata={
                    "method": "game_specific_rewrite",
                    "analysis_dimensions": result.get("analysis_dimensions", []),
                    "suggested_metrics": result.get("suggested_metrics", [])
                }
            )
            
        except Exception as e:
            logger.warning(f"Game-specific rewrite failed: {e}")
            return RewriteResult(
                original_query=query,
                rewritten_queries=[query],
                strategy=self.get_strategy(),
                confidence=0.1,
                reasoning=f"Game-specific rewrite failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def get_strategy(self) -> RewriteStrategy:
        return RewriteStrategy.GAME_SPECIFIC


class ClarificationRewriter(QueryRewriterBase):
    """Clarifies ambiguous queries by making them more specific."""
    
    def __init__(self, model: ChatModel, model_params: Optional[Dict[str, Any]] = None):
        self.model = model
        self.model_params = model_params or {}
    
    async def rewrite(self, query: str, context: Optional[Dict[str, Any]] = None) -> RewriteResult:
        """Clarify ambiguous queries."""
        
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
        
        try:
            response = await self.model.achat(prompt, **self.model_params)
            result_text = response.output.content
            
            import json
            result = json.loads(result_text)
            
            return RewriteResult(
                original_query=query,
                rewritten_queries=result.get("clarified_queries", [query]),
                strategy=self.get_strategy(),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", "Query clarification completed"),
                metadata={
                    "method": "ambiguity_resolution",
                    "ambiguities_resolved": result.get("ambiguities_resolved", [])
                }
            )
            
        except Exception as e:
            logger.warning(f"Query clarification failed: {e}")
            return RewriteResult(
                original_query=query,
                rewritten_queries=[query],
                strategy=self.get_strategy(),
                confidence=0.1,
                reasoning=f"Clarification failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def get_strategy(self) -> RewriteStrategy:
        return RewriteStrategy.CLARIFICATION


class QueryRewriteEngine:
    """Main query rewrite engine that orchestrates multiple rewrite strategies."""
    
    def __init__(
        self,
        model: ChatModel,
        entities: Optional[List[Entity]] = None,
        model_params: Optional[Dict[str, Any]] = None,
        enable_strategies: Optional[List[RewriteStrategy]] = None
    ):
        self.model = model
        self.entities = entities or []
        self.model_params = model_params or {}
        
        # Initialize rewriters
        self.rewriters = {}
        
        # Default enabled strategies
        if enable_strategies is None:
            enable_strategies = [
                RewriteStrategy.GAME_SPECIFIC,
                RewriteStrategy.EXPANSION,
                RewriteStrategy.CLARIFICATION,
                RewriteStrategy.DECOMPOSITION
            ]
        
        for strategy in enable_strategies:
            if strategy == RewriteStrategy.DECOMPOSITION:
                self.rewriters[strategy] = DecompositionRewriter(model, model_params)
            elif strategy == RewriteStrategy.EXPANSION:
                self.rewriters[strategy] = ExpansionRewriter(model, entities, model_params)
            elif strategy == RewriteStrategy.CLARIFICATION:
                self.rewriters[strategy] = ClarificationRewriter(model, model_params)
            elif strategy == RewriteStrategy.GAME_SPECIFIC:
                self.rewriters[strategy] = GameSpecificRewriter(model, model_params)
    
    async def rewrite_query(
        self,
        query: str,
        strategy: Optional[RewriteStrategy] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> RewriteResult:
        """Rewrite a query using the specified strategy."""
        
        if strategy and strategy in self.rewriters:
            return await self.rewriters[strategy].rewrite(query, context)
        
        # Auto-select strategy based on query characteristics
        selected_strategy = self._auto_select_strategy(query)
        
        if selected_strategy in self.rewriters:
            return await self.rewriters[selected_strategy].rewrite(query, context)
        else:
            # Fallback to first available strategy
            first_strategy = next(iter(self.rewriters.keys()))
            return await self.rewriters[first_strategy].rewrite(query, context)
    
    async def rewrite_multi_strategy(
        self,
        query: str,
        strategies: Optional[List[RewriteStrategy]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[RewriteResult]:
        """Apply multiple rewrite strategies to a query."""
        
        if strategies is None:
            strategies = list(self.rewriters.keys())
        
        tasks = []
        for strategy in strategies:
            if strategy in self.rewriters:
                tasks.append(self.rewriters[strategy].rewrite(query, context))
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, RewriteResult):
                valid_results.append(result)
            else:
                logger.warning(f"Rewrite task failed: {result}")
        
        return valid_results
    
    def _auto_select_strategy(self, query: str) -> RewriteStrategy:
        """Automatically select the best rewrite strategy for a query."""
        
        query_lower = query.lower()
        
        # Game-specific terms
        game_terms = ["玩家", "付费", "充值", "关卡", "道具", "流失", "留存", "LTV", "ARPU"]
        if any(term in query_lower for term in game_terms):
            return RewriteStrategy.GAME_SPECIFIC
        
        # Complex queries (multiple clauses, conjunctions)
        complex_indicators = ["和", "或", "以及", "同时", "另外", "此外", "而且"]
        if any(indicator in query_lower for indicator in complex_indicators) or len(query.split()) > 10:
            return RewriteStrategy.DECOMPOSITION
        
        # Ambiguous queries (pronouns, vague terms)
        ambiguous_terms = ["这个", "那个", "它", "他们", "怎么样", "如何"]
        if any(term in query_lower for term in ambiguous_terms):
            return RewriteStrategy.CLARIFICATION
        
        # Default to expansion
        return RewriteStrategy.EXPANSION
    
    def get_available_strategies(self) -> List[RewriteStrategy]:
        """Get list of available rewrite strategies."""
        return list(self.rewriters.keys())


# Utility functions
def create_query_rewrite_engine(
    model: ChatModel,
    entities: Optional[List[Entity]] = None,
    model_params: Optional[Dict[str, Any]] = None,
    **kwargs
) -> QueryRewriteEngine:
    """Create a query rewrite engine with default configuration."""
    return QueryRewriteEngine(
        model=model,
        entities=entities,
        model_params=model_params,
        **kwargs
    )


async def rewrite_for_graphrag(
    query: str,
    rewrite_engine: QueryRewriteEngine,
    max_rewrites: int = 3
) -> List[str]:
    """
    Rewrite a query specifically for GraphRAG search optimization.
    
    Returns a list of rewritten queries optimized for different search strategies.
    """
    
    # Apply game-specific rewrite first
    game_result = await rewrite_engine.rewrite_query(
        query, RewriteStrategy.GAME_SPECIFIC
    )
    
    # Apply expansion for broader coverage
    expansion_result = await rewrite_engine.rewrite_query(
        query, RewriteStrategy.EXPANSION
    )
    
    # Combine and deduplicate
    all_queries = [query]  # Keep original
    all_queries.extend(game_result.rewritten_queries)
    all_queries.extend(expansion_result.rewritten_queries)
    
    # Remove duplicates and limit count
    unique_queries = []
    seen = set()
    for q in all_queries:
        if q not in seen and len(unique_queries) < max_rewrites:
            unique_queries.append(q)
            seen.add(q)
    
    return unique_queries 