# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Scenario-based evaluation framework for GraphRAG."""

import time
import logging
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """Different application scenarios for GraphRAG."""
    ENTERPRISE_QA = "enterprise_qa"
    RESEARCH_ANALYSIS = "research_analysis"
    CUSTOMER_SUPPORT = "customer_support"
    GAME_ANALYSIS = "game_analysis"
    FINANCIAL_ANALYSIS = "financial_analysis"
    MEDICAL_RESEARCH = "medical_research"
    LEGAL_DISCOVERY = "legal_discovery"


@dataclass
class EvaluationMetric:
    """Single evaluation metric."""
    name: str
    value: float
    threshold: Optional[float] = None
    unit: str = ""
    description: str = ""
    weight: float = 1.0
    
    @property
    def is_passing(self) -> bool:
        """Check if metric passes threshold."""
        if self.threshold is None:
            return True
        return self.value >= self.threshold


@dataclass
class ScenarioEvaluationResult:
    """Result of scenario-based evaluation."""
    scenario_type: ScenarioType
    metrics: Dict[str, EvaluationMetric] = field(default_factory=dict)
    overall_score: float = 0.0
    passing_rate: float = 0.0
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_metric(self, metric: EvaluationMetric) -> None:
        """Add a metric to the results."""
        self.metrics[metric.name] = metric
    
    def calculate_overall_score(self) -> float:
        """Calculate weighted overall score."""
        if not self.metrics:
            return 0.0
        
        total_weight = sum(m.weight for m in self.metrics.values())
        weighted_sum = sum(m.value * m.weight for m in self.metrics.values())
        
        self.overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        return self.overall_score
    
    def calculate_passing_rate(self) -> float:
        """Calculate percentage of metrics passing their thresholds."""
        if not self.metrics:
            return 0.0
        
        passing_metrics = sum(1 for m in self.metrics.values() if m.is_passing)
        self.passing_rate = passing_metrics / len(self.metrics)
        return self.passing_rate


class BaseScenarioEvaluator(ABC):
    """Base class for scenario-specific evaluators."""
    
    def __init__(self, scenario_type: ScenarioType):
        self.scenario_type = scenario_type
    
    @abstractmethod
    async def evaluate(
        self,
        queries: List[str],
        expected_answers: Optional[List[str]] = None,
        search_engine=None,
        **kwargs
    ) -> ScenarioEvaluationResult:
        """Evaluate GraphRAG performance for this scenario."""
        pass
    
    @abstractmethod
    def get_metric_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get definitions of metrics used in this scenario."""
        pass


class EnterpriseQAEvaluator(BaseScenarioEvaluator):
    """Evaluator for enterprise Q&A scenarios."""
    
    def __init__(self):
        super().__init__(ScenarioType.ENTERPRISE_QA)
    
    async def evaluate(
        self,
        queries: List[str],
        expected_answers: Optional[List[str]] = None,
        search_engine=None,
        **kwargs
    ) -> ScenarioEvaluationResult:
        """Evaluate enterprise Q&A performance."""
        start_time = time.time()
        result = ScenarioEvaluationResult(scenario_type=self.scenario_type)
        
        if not search_engine:
            logger.error("Search engine required for evaluation")
            return result
        
        # Metrics for enterprise Q&A
        response_times = []
        accuracy_scores = []
        completeness_scores = []
        cost_per_query = []
        
        for i, query in enumerate(queries):
            query_start = time.time()
            
            try:
                # Execute search
                search_result = await search_engine.search(query)
                query_time = time.time() - query_start
                response_times.append(query_time)
                
                # Calculate accuracy if expected answer provided
                if expected_answers and i < len(expected_answers):
                    accuracy = self._calculate_semantic_similarity(
                        search_result.response, expected_answers[i]
                    )
                    accuracy_scores.append(accuracy)
                
                # Calculate completeness based on context coverage
                completeness = self._calculate_completeness(search_result)
                completeness_scores.append(completeness)
                
                # Estimate cost (token usage)
                cost = self._estimate_cost(search_result)
                cost_per_query.append(cost)
                
            except Exception as e:
                logger.error(f"Error evaluating query '{query}': {e}")
                response_times.append(float('inf'))
                accuracy_scores.append(0.0)
                completeness_scores.append(0.0)
                cost_per_query.append(0.0)
        
        # Calculate aggregate metrics
        avg_response_time = float(np.mean(response_times)) if response_times else 0.0
        avg_accuracy = float(np.mean(accuracy_scores)) if accuracy_scores else 0.0
        avg_completeness = float(np.mean(completeness_scores)) if completeness_scores else 0.0
        avg_cost = float(np.mean(cost_per_query)) if cost_per_query else 0.0
        
        # Add metrics with enterprise-specific thresholds
        result.add_metric(EvaluationMetric(
            name="response_time",
            value=avg_response_time,
            threshold=5.0,  # 5 seconds max for enterprise
            unit="seconds",
            description="Average response time per query",
            weight=2.0
        ))
        
        result.add_metric(EvaluationMetric(
            name="accuracy",
            value=avg_accuracy,
            threshold=0.8,  # 80% accuracy minimum
            unit="ratio",
            description="Semantic similarity to expected answers",
            weight=3.0
        ))
        
        result.add_metric(EvaluationMetric(
            name="completeness",
            value=avg_completeness,
            threshold=0.7,  # 70% completeness minimum
            unit="ratio",
            description="Coverage of relevant information",
            weight=2.5
        ))
        
        result.add_metric(EvaluationMetric(
            name="cost_efficiency",
            value=1.0 / (avg_cost + 0.001),  # Inverse of cost for higher is better
            threshold=10.0,  # Cost efficiency threshold
            unit="1/cost",
            description="Cost efficiency per query",
            weight=1.5
        ))
        
        result.execution_time = time.time() - start_time
        result.calculate_overall_score()
        result.calculate_passing_rate()
        
        result.metadata = {
            "query_count": len(queries),
            "response_times": response_times,
            "accuracy_scores": accuracy_scores,
            "completeness_scores": completeness_scores,
            "cost_per_query": cost_per_query,
        }
        
        return result
    
    def _calculate_semantic_similarity(self, response: str, expected: str) -> float:
        """Calculate semantic similarity between response and expected answer."""
        # Simplified semantic similarity - in practice, use embeddings
        response_words = set(response.lower().split())
        expected_words = set(expected.lower().split())
        
        if not expected_words:
            return 0.0
        
        overlap = len(response_words & expected_words)
        return overlap / len(expected_words)
    
    def _calculate_completeness(self, search_result) -> float:
        """Calculate completeness based on context coverage."""
        # Simplified completeness calculation
        if hasattr(search_result, 'context_data') and search_result.context_data:
            context_items = len(search_result.context_data.get('context_chunks', []))
            return min(context_items / 10.0, 1.0)  # Normalize to 0-1
        return 0.5  # Default moderate completeness
    
    def _estimate_cost(self, search_result) -> float:
        """Estimate cost based on token usage."""
        prompt_tokens = getattr(search_result, 'prompt_tokens', 0)
        output_tokens = getattr(search_result, 'output_tokens', 0)
        
        # Simplified cost calculation (adjust rates as needed)
        input_rate = 0.0015 / 1000  # $0.0015 per 1K tokens
        output_rate = 0.002 / 1000   # $0.002 per 1K tokens
        
        return prompt_tokens * input_rate + output_tokens * output_rate
    
    def get_metric_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get metric definitions for enterprise Q&A."""
        return {
            "response_time": {
                "description": "Average time to respond to queries",
                "unit": "seconds",
                "threshold": 5.0,
                "target": "lower_is_better"
            },
            "accuracy": {
                "description": "Semantic accuracy of responses",
                "unit": "ratio (0-1)",
                "threshold": 0.8,
                "target": "higher_is_better"
            },
            "completeness": {
                "description": "Coverage of relevant information",
                "unit": "ratio (0-1)",
                "threshold": 0.7,
                "target": "higher_is_better"
            },
            "cost_efficiency": {
                "description": "Cost efficiency per query",
                "unit": "1/cost",
                "threshold": 10.0,
                "target": "higher_is_better"
            }
        }


class GameAnalysisEvaluator(BaseScenarioEvaluator):
    """Evaluator for game analysis scenarios."""
    
    def __init__(self):
        super().__init__(ScenarioType.GAME_ANALYSIS)
    
    async def evaluate(
        self,
        queries: List[str],
        expected_answers: Optional[List[str]] = None,
        search_engine=None,
        **kwargs
    ) -> ScenarioEvaluationResult:
        """Evaluate game analysis performance."""
        start_time = time.time()
        result = ScenarioEvaluationResult(scenario_type=self.scenario_type)
        
        if not search_engine:
            logger.error("Search engine required for evaluation")
            return result
        
        # Game-specific metrics
        strategy_depth_scores = []
        player_insight_scores = []
        real_time_performance = []
        context_relevance_scores = []
        
        for query in queries:
            query_start = time.time()
            
            try:
                search_result = await search_engine.search(query)
                query_time = time.time() - query_start
                real_time_performance.append(query_time)
                
                # Game-specific scoring
                strategy_depth = self._evaluate_strategy_depth(search_result.response)
                strategy_depth_scores.append(strategy_depth)
                
                player_insight = self._evaluate_player_insights(search_result.response)
                player_insight_scores.append(player_insight)
                
                context_relevance = self._evaluate_gaming_context(search_result)
                context_relevance_scores.append(context_relevance)
                
            except Exception as e:
                logger.error(f"Error evaluating query '{query}': {e}")
                strategy_depth_scores.append(0.0)
                player_insight_scores.append(0.0)
                real_time_performance.append(float('inf'))
                context_relevance_scores.append(0.0)
        
        # Game-specific thresholds
        result.add_metric(EvaluationMetric(
            name="real_time_performance",
            value=float(np.mean(real_time_performance)),
            threshold=2.0,  # 2 seconds for gaming
            unit="seconds",
            description="Real-time response for gaming scenarios",
            weight=3.0
        ))
        
        result.add_metric(EvaluationMetric(
            name="strategy_depth",
            value=float(np.mean(strategy_depth_scores)),
            threshold=0.75,
            unit="ratio",
            description="Depth of strategic analysis",
            weight=2.5
        ))
        
        result.add_metric(EvaluationMetric(
            name="player_insights",
            value=float(np.mean(player_insight_scores)),
            threshold=0.7,
            unit="ratio",
            description="Quality of player behavior insights",
            weight=2.0
        ))
        
        result.add_metric(EvaluationMetric(
            name="context_relevance",
            value=float(np.mean(context_relevance_scores)),
            threshold=0.8,
            unit="ratio",
            description="Relevance to gaming context",
            weight=2.0
        ))
        
        result.execution_time = time.time() - start_time
        result.calculate_overall_score()
        result.calculate_passing_rate()
        
        return result
    
    def _evaluate_strategy_depth(self, response: str) -> float:
        """Evaluate strategic depth of gaming analysis."""
        strategy_keywords = ['strategy', 'tactic', 'approach', 'plan', 'method', 'technique']
        depth_indicators = ['because', 'therefore', 'results in', 'leads to', 'causes']
        
        response_lower = response.lower()
        strategy_score = sum(1 for kw in strategy_keywords if kw in response_lower)
        depth_score = sum(1 for kw in depth_indicators if kw in response_lower)
        
        return min((strategy_score + depth_score) / 10.0, 1.0)
    
    def _evaluate_player_insights(self, response: str) -> float:
        """Evaluate quality of player behavior insights."""
        player_keywords = ['player', 'user', 'behavior', 'preference', 'pattern', 'trend']
        insight_keywords = ['tendency', 'likely', 'prefer', 'usually', 'often', 'frequently']
        
        response_lower = response.lower()
        player_score = sum(1 for kw in player_keywords if kw in response_lower)
        insight_score = sum(1 for kw in insight_keywords if kw in response_lower)
        
        return min((player_score + insight_score) / 8.0, 1.0)
    
    def _evaluate_gaming_context(self, search_result) -> float:
        """Evaluate relevance to gaming context."""
        gaming_terms = ['game', 'gaming', 'player', 'strategy', 'level', 'score', 'achievement']
        
        if hasattr(search_result, 'context_data') and search_result.context_data:
            context_text = str(search_result.context_data).lower()
            gaming_score = sum(1 for term in gaming_terms if term in context_text)
            return min(gaming_score / 5.0, 1.0)
        
        return 0.5
    
    def get_metric_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get metric definitions for game analysis."""
        return {
            "real_time_performance": {
                "description": "Response time for real-time gaming analysis",
                "unit": "seconds",
                "threshold": 2.0,
                "target": "lower_is_better"
            },
            "strategy_depth": {
                "description": "Depth of strategic analysis provided",
                "unit": "ratio (0-1)",
                "threshold": 0.75,
                "target": "higher_is_better"
            },
            "player_insights": {
                "description": "Quality of player behavior insights",
                "unit": "ratio (0-1)",
                "threshold": 0.7,
                "target": "higher_is_better"
            },
            "context_relevance": {
                "description": "Relevance to gaming context",
                "unit": "ratio (0-1)",
                "threshold": 0.8,
                "target": "higher_is_better"
            }
        }


class ScenarioEvaluationSuite:
    """Suite for running multiple scenario evaluations."""
    
    def __init__(self):
        self.evaluators = {
            ScenarioType.ENTERPRISE_QA: EnterpriseQAEvaluator(),
            ScenarioType.GAME_ANALYSIS: GameAnalysisEvaluator(),
        }
    
    def add_evaluator(self, evaluator: BaseScenarioEvaluator) -> None:
        """Add a custom evaluator."""
        self.evaluators[evaluator.scenario_type] = evaluator
    
    async def run_evaluation(
        self,
        scenario_type: ScenarioType,
        queries: List[str],
        search_engine,
        **kwargs
    ) -> ScenarioEvaluationResult:
        """Run evaluation for a specific scenario."""
        if scenario_type not in self.evaluators:
            raise ValueError(f"No evaluator found for scenario: {scenario_type}")
        
        evaluator = self.evaluators[scenario_type]
        return await evaluator.evaluate(queries, search_engine=search_engine, **kwargs)
    
    async def run_all_scenarios(
        self,
        queries_by_scenario: Dict[ScenarioType, List[str]],
        search_engine,
        **kwargs
    ) -> Dict[ScenarioType, ScenarioEvaluationResult]:
        """Run evaluations for all configured scenarios."""
        results = {}
        
        for scenario_type, queries in queries_by_scenario.items():
            if scenario_type in self.evaluators:
                try:
                    result = await self.run_evaluation(
                        scenario_type, queries, search_engine, **kwargs
                    )
                    results[scenario_type] = result
                except Exception as e:
                    logger.error(f"Error evaluating scenario {scenario_type}: {e}")
        
        return results
    
    def generate_comparison_report(
        self,
        results: Dict[ScenarioType, ScenarioEvaluationResult]
    ) -> Dict[str, Any]:
        """Generate comparative analysis report."""
        report = {
            "summary": {},
            "metrics_comparison": {},
            "scenario_rankings": {},
            "recommendations": []
        }
        
        # Summary statistics
        overall_scores = {scenario.value: result.overall_score 
                         for scenario, result in results.items()}
        passing_rates = {scenario.value: result.passing_rate 
                        for scenario, result in results.items()}
        
        report["summary"] = {
            "overall_scores": overall_scores,
            "passing_rates": passing_rates,
            "best_scenario": max(overall_scores.keys(), key=lambda k: overall_scores[k]),
            "worst_scenario": min(overall_scores.keys(), key=lambda k: overall_scores[k]),
        }
        
        # Metrics comparison
        all_metrics = set()
        for result in results.values():
            all_metrics.update(result.metrics.keys())
        
        for metric_name in all_metrics:
            metric_values = {}
            for scenario, result in results.items():
                if metric_name in result.metrics:
                    metric_values[scenario.value] = result.metrics[metric_name].value
            report["metrics_comparison"][metric_name] = metric_values
        
        return report


# Convenience function
def create_evaluation_suite() -> ScenarioEvaluationSuite:
    """Create a pre-configured evaluation suite."""
    return ScenarioEvaluationSuite() 