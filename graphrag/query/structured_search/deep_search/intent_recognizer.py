# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Query Intent Recognition for DeepSearch."""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from graphrag.language_model.protocol.base import ChatModel

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """查询意图类型."""
    
    FACTUAL = "factual"                    # 事实查询 - 寻找具体信息
    ANALYTICAL = "analytical"              # 分析查询 - 寻找模式和趋势
    COMPARATIVE = "comparative"            # 比较查询 - 比较不同实体或概念
    CAUSAL = "causal"                     # 因果查询 - 寻找原因和结果
    PREDICTIVE = "predictive"             # 预测查询 - 预测未来趋势
    EXPLORATORY = "exploratory"           # 探索查询 - 开放式探索
    OPERATIONAL = "operational"           # 操作查询 - 寻找行动建议
    SUMMARY = "summary"                   # 总结查询 - 总结和概括


class SearchStrategy(Enum):
    """推荐的搜索策略."""
    
    LOCAL_FOCUSED = "local_focused"       # 本地搜索为主
    GLOBAL_FOCUSED = "global_focused"     # 全局搜索为主
    BALANCED = "balanced"                 # 平衡搜索
    ITERATIVE = "iterative"              # 迭代搜索
    COMPREHENSIVE = "comprehensive"       # 全面搜索


@dataclass
class IntentAnalysis:
    """意图分析结果."""
    
    primary_intent: QueryIntent
    secondary_intents: list[QueryIntent]
    confidence: float
    recommended_strategy: SearchStrategy
    search_depth_suggestion: int
    key_entities: list[str]
    context_requirements: list[str]
    reasoning: str


class IntentRecognizer:
    """查询意图识别器."""
    
    def __init__(
        self,
        model: ChatModel,
        system_prompt: str | None = None,
        model_params: dict[str, Any] | None = None,
    ):
        """初始化意图识别器."""
        self.model = model
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.model_params = model_params or {}
    
    async def analyze_intent(self, query: str) -> IntentAnalysis:
        """分析查询意图."""
        try:
            analysis_prompt = self._build_analysis_prompt(query)
            
            response = await self.model.achat(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt},
                ],
                **self.model_params,
            )
            
            # 解析响应
            analysis_data = json.loads(response.output.content or "{}")
            
            return IntentAnalysis(
                primary_intent=QueryIntent(analysis_data.get("primary_intent", "exploratory")),
                secondary_intents=[
                    QueryIntent(intent) for intent in analysis_data.get("secondary_intents", [])
                ],
                confidence=analysis_data.get("confidence", 0.5),
                recommended_strategy=SearchStrategy(
                    analysis_data.get("recommended_strategy", "balanced")
                ),
                search_depth_suggestion=analysis_data.get("search_depth_suggestion", 3),
                key_entities=analysis_data.get("key_entities", []),
                context_requirements=analysis_data.get("context_requirements", []),
                reasoning=analysis_data.get("reasoning", ""),
            )
            
        except Exception as e:
            logger.warning(f"意图识别失败，使用默认分析: {e}")
            return self._get_default_analysis(query)
    
    def _build_analysis_prompt(self, query: str) -> str:
        """构建意图分析提示."""
        return f"""
        请分析以下查询的意图并提供搜索策略建议：
        
        查询: "{query}"
        
        请按照以下JSON格式返回分析结果：
        {{
            "primary_intent": "主要意图类型",
            "secondary_intents": ["次要意图类型列表"],
            "confidence": 0.85,
            "recommended_strategy": "推荐搜索策略",
            "search_depth_suggestion": 3,
            "key_entities": ["关键实体列表"],
            "context_requirements": ["所需上下文类型"],
            "reasoning": "分析推理过程"
        }}
        
        意图类型选项：
        - factual: 事实查询，寻找具体信息
        - analytical: 分析查询，寻找模式和趋势
        - comparative: 比较查询，比较不同实体或概念
        - causal: 因果查询，寻找原因和结果
        - predictive: 预测查询，预测未来趋势
        - exploratory: 探索查询，开放式探索
        - operational: 操作查询，寻找行动建议
        - summary: 总结查询，总结和概括
        
        搜索策略选项：
        - local_focused: 本地搜索为主，适合具体事实查询
        - global_focused: 全局搜索为主，适合模式和趋势分析
        - balanced: 平衡搜索，适合综合性查询
        - iterative: 迭代搜索，适合复杂探索性查询
        - comprehensive: 全面搜索，适合重要决策查询
        
        搜索深度建议（1-5）：
        - 1-2: 简单直接的查询
        - 3: 标准复杂度查询
        - 4-5: 高复杂度分析查询
        """
    
    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示."""
        return """
        你是一个专业的查询意图分析师，专门分析用户查询的目的和类型，
        并为知识图谱搜索提供最佳策略建议。
        
        你的任务：
        1. 识别查询的主要和次要意图
        2. 评估意图识别的置信度
        3. 推荐最适合的搜索策略
        4. 建议搜索深度
        5. 识别关键实体和所需上下文
        6. 提供清晰的分析推理
        
        请始终以JSON格式返回结构化的分析结果。
        """
    
    def _get_default_analysis(self, query: str) -> IntentAnalysis:
        """获取默认意图分析结果."""
        return IntentAnalysis(
            primary_intent=QueryIntent.EXPLORATORY,
            secondary_intents=[],
            confidence=0.5,
            recommended_strategy=SearchStrategy.BALANCED,
            search_depth_suggestion=3,
            key_entities=[],
            context_requirements=["entities", "relationships"],
            reasoning=f"无法解析查询'{query}'，使用默认探索性意图分析",
        )


class GameIntentRecognizer(IntentRecognizer):
    """游戏数据专用的意图识别器."""
    
    def __init__(
        self,
        model: ChatModel,
        system_prompt: str | None = None,
        model_params: dict[str, Any] | None = None,
    ):
        """初始化游戏意图识别器."""
        game_system_prompt = system_prompt or self._get_game_system_prompt()
        super().__init__(model, game_system_prompt, model_params)
    
    def _get_game_system_prompt(self) -> str:
        """获取游戏专用系统提示."""
        return """
        你是一个专业的游戏数据分析意图识别专家，专门分析游戏相关查询的目的和类型。
        
        游戏数据分析的常见意图类型：
        - factual: 查询具体的游戏数据和统计信息
        - analytical: 分析玩家行为模式、游戏趋势
        - comparative: 比较不同玩家群体、关卡、时期等
        - causal: 分析玩家流失原因、付费转化因素等
        - predictive: 预测玩家行为、收入趋势等
        - exploratory: 探索游戏数据中的未知模式
        - operational: 寻找游戏运营改进建议
        - summary: 总结游戏表现、玩家行为等
        
        游戏数据上下文类型：
        - player_profiles: 玩家画像和行为数据
        - game_sessions: 游戏会话和进度数据
        - payment_data: 付费和交易数据
        - level_progression: 关卡进度和难度数据
        - social_interactions: 社交互动数据
        - item_usage: 道具使用数据
        - retention_metrics: 留存和流失数据
        - performance_metrics: 游戏表现指标
        
        请根据游戏业务场景提供专业的意图分析。
        """
    
    async def analyze_game_intent(self, query: str) -> IntentAnalysis:
        """分析游戏相关查询意图."""
        analysis = await self.analyze_intent(query)
        
        # 为游戏意图添加特定的上下文要求
        if analysis.primary_intent == QueryIntent.CAUSAL:
            analysis.context_requirements.extend([
                "player_profiles", "game_sessions", "retention_metrics"
            ])
        elif analysis.primary_intent == QueryIntent.ANALYTICAL:
            analysis.context_requirements.extend([
                "player_profiles", "payment_data", "performance_metrics"
            ])
        elif analysis.primary_intent == QueryIntent.OPERATIONAL:
            analysis.context_requirements.extend([
                "performance_metrics", "retention_metrics", "payment_data"
            ])
        
        return analysis


def create_intent_recognizer(
    model: ChatModel,
    game_mode: bool = False,
    **kwargs
) -> IntentRecognizer:
    """创建意图识别器工厂函数."""
    if game_mode:
        return GameIntentRecognizer(model, **kwargs)
    else:
        return IntentRecognizer(model, **kwargs) 