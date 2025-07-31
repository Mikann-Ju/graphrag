# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""DeepSearch implementation with path control and visualization logic chain."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from graphrag.callbacks.query_callbacks import QueryCallbacks
from graphrag.language_model.protocol.base import ChatModel
from graphrag.prompts.query.deep_search_system_prompt import (
    DEEP_SEARCH_SYSTEM_PROMPT,
)
from graphrag.query.context_builder.conversation_history import ConversationHistory
from graphrag.query.structured_search.base import BaseSearch, SearchResult
from graphrag.query.structured_search.deep_search.deep_context import (
    DeepSearchContextBuilder,
)
from graphrag.query.structured_search.deep_search.intent_recognizer import (
    IntentRecognizer,
    create_intent_recognizer,
    QueryIntent,
    SearchStrategy,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.local_search.search import LocalSearch

logger = logging.getLogger(__name__)


@dataclass
class SearchPath:
    """表示搜索路径的数据结构."""
    
    step: int
    search_type: str
    query: str
    context_used: list[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class LogicChain:
    """表示逻辑推理链的数据结构."""
    
    paths: list[SearchPath] = field(default_factory=list)
    final_reasoning: str = ""
    total_confidence: float = 0.0
    
    def add_path(self, path: SearchPath) -> None:
        """添加搜索路径."""
        self.paths.append(path)
    
    def to_visualization_data(self) -> dict[str, Any]:
        """转换为可视化数据格式."""
        return {
            "paths": [
                {
                    "step": path.step,
                    "search_type": path.search_type,
                    "query": path.query,
                    "context_used": path.context_used,
                    "reasoning": path.reasoning,
                    "confidence": path.confidence,
                    "timestamp": path.timestamp,
                }
                for path in self.paths
            ],
            "final_reasoning": self.final_reasoning,
            "total_confidence": self.total_confidence,
        }


@dataclass(kw_only=True)
class DeepSearchResult(SearchResult):
    """DeepSearch结果类，包含逻辑链和意图信息."""
    
    logic_chain: LogicChain | None = None
    search_depth: int = 0
    path_count: int = 0
    intent_analysis: Any | None = None  # IntentAnalysis类型


class DeepSearch(BaseSearch[DeepSearchContextBuilder]):
    """DeepSearch搜索编排，具备路径控制和可视化逻辑链功能."""

    def __init__(
        self,
        model: ChatModel,
        context_builder: DeepSearchContextBuilder,
        local_search: LocalSearch | None = None,
        global_search: GlobalSearch | None = None,
        token_encoder: Any | None = None,
        system_prompt: str | None = None,
        max_depth: int = 3,
        confidence_threshold: float = 0.7,
        enable_intent_recognition: bool = True,
        game_mode: bool = False,
        callbacks: list[QueryCallbacks] | None = None,
        model_params: dict[str, Any] | None = None,
        context_builder_params: dict | None = None,
    ):
        """
        初始化DeepSearch.
        
        Args:
            model: 聊天模型
            context_builder: 上下文构建器
            local_search: 本地搜索实例
            global_search: 全局搜索实例
            system_prompt: 系统提示
            max_depth: 最大搜索深度
            confidence_threshold: 置信度阈值
            callbacks: 回调函数列表
            model_params: 模型参数
            context_builder_params: 上下文构建器参数
        """
        super().__init__(
            model=model,
            context_builder=context_builder,
            token_encoder=token_encoder,
            model_params=model_params,
            context_builder_params=context_builder_params or {},
        )
        
        self.system_prompt = system_prompt or DEEP_SEARCH_SYSTEM_PROMPT
        self.local_search = local_search
        self.global_search = global_search
        self.max_depth = max_depth
        self.confidence_threshold = confidence_threshold
        self.callbacks = callbacks or []
        
        # 初始化意图识别器
        self.enable_intent_recognition = enable_intent_recognition
        self.intent_recognizer: IntentRecognizer | None = None
        if enable_intent_recognition:
            self.intent_recognizer = create_intent_recognizer(
                model=model,
                game_mode=game_mode,
                model_params=model_params,
            )

    async def stream_search(
        self,
        query: str,
        conversation_history: ConversationHistory | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式搜索实现."""
        async for result in self._stream_deep_search(query, conversation_history):
            yield result

    async def search(
        self,
        query: str,
        conversation_history: ConversationHistory | None = None,
        **kwargs: Any,
    ) -> DeepSearchResult:
        """
        执行深度搜索.
        
        Deep search模式包括多个步骤：
        1. 初始查询分析和路径规划
        2. 多层次搜索执行（Local + Global + 推理）
        3. 结果整合和逻辑链构建
        4. 置信度评估和结果优化
        """
        start_time = time.time()
        logic_chain = LogicChain()
        
        # 第0步：意图识别（如果启用）
        intent_analysis = None
        if self.intent_recognizer:
            intent_analysis = await self.intent_recognizer.analyze_intent(query)
            
            # 根据意图调整搜索参数
            if intent_analysis.search_depth_suggestion:
                self.max_depth = min(self.max_depth, intent_analysis.search_depth_suggestion)
        
        # 第1步：查询分析和初始搜索策略规划
        search_plan = await self._analyze_query_and_plan(query, conversation_history, intent_analysis)
        
        # 第2步：执行多层次搜索
        search_results = []
        current_depth = 0
        
        while current_depth < self.max_depth:
            current_depth += 1
            
            # 执行本地搜索
            if self.local_search and search_plan.get("use_local", True):
                local_result = await self._execute_local_search(
                    query, conversation_history, current_depth, logic_chain
                )
                search_results.append(local_result)
            
            # 执行全局搜索
            if self.global_search and search_plan.get("use_global", True):
                global_result = await self._execute_global_search(
                    query, conversation_history, current_depth, logic_chain
                )
                search_results.append(global_result)
            
            # 基于当前结果评估是否需要继续深度搜索
            should_continue = await self._should_continue_search(
                search_results, logic_chain, current_depth
            )
            
            if not should_continue:
                break
        
        # 第3步：结果整合和最终推理
        final_response = await self._integrate_results(
            query, search_results, logic_chain, conversation_history
        )
        
        # 第4步：构建最终结果
        end_time = time.time()
        
        return DeepSearchResult(
            response=final_response,
            context_data=self._build_context_data(search_results),
            completion_time=end_time - start_time,
            llm_calls=sum(result.get("llm_calls", 0) for result in search_results),
            prompt_tokens=sum(result.get("prompt_tokens", 0) for result in search_results),
            output_tokens=sum(result.get("output_tokens", 0) for result in search_results),
            logic_chain=logic_chain,
            search_depth=current_depth,
            path_count=len(logic_chain.paths),
        )

    async def _analyze_query_and_plan(
        self,
        query: str,
        conversation_history: ConversationHistory | None = None,
    ) -> dict[str, Any]:
        """分析查询并制定搜索计划."""
        analysis_prompt = f"""
        分析以下查询并制定搜索策略：
        
        查询: {query}
        
        请提供：
        1. 查询复杂度评估 (1-5)
        2. 推荐搜索深度
        3. 是否需要本地搜索
        4. 是否需要全局搜索
        5. 关键实体和概念
        6. 搜索路径建议
        
        以JSON格式返回结果。
        """
        
        response = await self.model.achat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": analysis_prompt},
            ],
            **self.model_params,
        )
        
        try:
            plan = json.loads(response.output.content or "{}")
        except json.JSONDecodeError:
            # 如果解析失败，使用默认计划
            plan = {
                "complexity": 3,
                "recommended_depth": 2,
                "use_local": True,
                "use_global": True,
                "key_entities": [],
                "search_paths": ["local_first", "global_expand"],
            }
        
        return plan

    async def _execute_local_search(
        self,
        query: str,
        conversation_history: ConversationHistory | None,
        depth: int,
        logic_chain: LogicChain,
    ) -> dict[str, Any]:
        """执行本地搜索并记录路径."""
        if not self.local_search:
            return {}
        
        start_time = time.time()
        result = await self.local_search.search(query, conversation_history)
        
        # 记录搜索路径
        search_path = SearchPath(
            step=len(logic_chain.paths) + 1,
            search_type="local",
            query=query,
            context_used=["entities", "relationships", "text_units"],
            reasoning=f"深度{depth}的本地搜索，关注具体实体和关系",
            confidence=0.8,  # 可以通过分析结果质量来计算
        )
        logic_chain.add_path(search_path)
        
        return {
            "type": "local",
            "result": result,
            "depth": depth,
            "completion_time": time.time() - start_time,
            "llm_calls": result.llm_calls if hasattr(result, "llm_calls") else 0,
            "prompt_tokens": result.prompt_tokens if hasattr(result, "prompt_tokens") else 0,
            "output_tokens": result.output_tokens if hasattr(result, "output_tokens") else 0,
        }

    async def _execute_global_search(
        self,
        query: str,
        conversation_history: ConversationHistory | None,
        depth: int,
        logic_chain: LogicChain,
    ) -> dict[str, Any]:
        """执行全局搜索并记录路径."""
        if not self.global_search:
            return {}
        
        start_time = time.time()
        result = await self.global_search.search(query, conversation_history)
        
        # 记录搜索路径
        search_path = SearchPath(
            step=len(logic_chain.paths) + 1,
            search_type="global",
            query=query,
            context_used=["communities", "community_reports"],
            reasoning=f"深度{depth}的全局搜索，关注高层次模式和社区结构",
            confidence=0.75,  # 可以通过分析结果质量来计算
        )
        logic_chain.add_path(search_path)
        
        return {
            "type": "global", 
            "result": result,
            "depth": depth,
            "completion_time": time.time() - start_time,
            "llm_calls": result.llm_calls if hasattr(result, "llm_calls") else 0,
            "prompt_tokens": result.prompt_tokens if hasattr(result, "prompt_tokens") else 0,
            "output_tokens": result.output_tokens if hasattr(result, "output_tokens") else 0,
        }

    async def _should_continue_search(
        self,
        search_results: list[dict[str, Any]],
        logic_chain: LogicChain,
        current_depth: int,
    ) -> bool:
        """评估是否应该继续深度搜索."""
        if current_depth >= self.max_depth:
            return False
        
        if not search_results:
            return True
        
        # 计算平均置信度
        total_confidence = sum(
            path.confidence for path in logic_chain.paths
        )
        avg_confidence = total_confidence / len(logic_chain.paths) if logic_chain.paths else 0
        
        # 如果置信度足够高，可以停止搜索
        if avg_confidence >= self.confidence_threshold:
            return False
        
        return True

    async def _integrate_results(
        self,
        query: str,
        search_results: list[dict[str, Any]],
        logic_chain: LogicChain,
        conversation_history: ConversationHistory | None,
    ) -> str:
        """整合搜索结果并生成最终响应."""
        if not search_results:
            return "无法找到相关信息。"
        
        # 构建整合提示
        integration_prompt = f"""
        基于以下多层次搜索结果，为用户查询提供全面的答案：
        
        用户查询: {query}
        
        搜索结果：
        """
        
        for i, result in enumerate(search_results):
            if "result" in result and hasattr(result["result"], "response"):
                integration_prompt += f"\n{i+1}. {result['type'].upper()}搜索结果:\n{result['result'].response}\n"
        
        integration_prompt += f"""
        
        搜索路径记录：
        {json.dumps(logic_chain.to_visualization_data(), ensure_ascii=False, indent=2)}
        
        请提供：
        1. 综合分析和答案
        2. 关键发现总结
        3. 推理过程解释
        4. 置信度评估
        """
        
        response = await self.model.achat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": integration_prompt},
            ],
            **self.model_params,
        )
        
        # 更新逻辑链的最终推理
        logic_chain.final_reasoning = f"基于{len(search_results)}个搜索结果的综合分析"
        logic_chain.total_confidence = sum(path.confidence for path in logic_chain.paths) / len(logic_chain.paths) if logic_chain.paths else 0
        
        return response.output.content or "处理结果时出现错误。"

    async def _stream_deep_search(
        self,
        query: str,
        conversation_history: ConversationHistory | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式深度搜索实现."""
        yield f"开始深度搜索：{query}\n\n"
        
        # 执行搜索并流式返回进度
        logic_chain = LogicChain()
        search_results = []
        
        for depth in range(1, self.max_depth + 1):
            yield f"执行第{depth}层搜索...\n"
            
            if self.local_search:
                yield "  正在执行本地搜索...\n"
                local_result = await self._execute_local_search(
                    query, conversation_history, depth, logic_chain
                )
                search_results.append(local_result)
                if local_result and "result" in local_result:
                    yield f"  本地搜索完成，找到相关信息\n"
            
            if self.global_search:
                yield "  正在执行全局搜索...\n"
                global_result = await self._execute_global_search(
                    query, conversation_history, depth, logic_chain
                )
                search_results.append(global_result)
                if global_result and "result" in global_result:
                    yield f"  全局搜索完成，找到相关模式\n"
            
            should_continue = await self._should_continue_search(
                search_results, logic_chain, depth
            )
            
            if not should_continue:
                yield f"搜索在第{depth}层达到最优结果\n\n"
                break
        
        yield "正在整合搜索结果...\n"
        final_response = await self._integrate_results(
            query, search_results, logic_chain, conversation_history
        )
        
        yield f"\n=== 深度搜索结果 ===\n{final_response}\n\n"
        yield f"=== 搜索路径可视化 ===\n{json.dumps(logic_chain.to_visualization_data(), ensure_ascii=False, indent=2)}\n"

    def _build_context_data(self, search_results: list[dict[str, Any]]) -> dict[str, Any]:
        """构建上下文数据."""
        context_data = {
            "search_results": search_results,
            "result_count": len(search_results),
            "search_types": list(set(result.get("type", "unknown") for result in search_results)),
        }
        
        # 合并所有结果的上下文数据
        for result in search_results:
            if "result" in result and hasattr(result["result"], "context_data"):
                context_data.update(result["result"].context_data)
        
        return context_data 