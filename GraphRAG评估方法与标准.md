# GraphRAG 游戏智能分析平台 - 评估方法与标准

## 1. 概述

为了确保GraphRAG游戏智能分析平台的质量、可靠性和持续改进，我们建立了一套针对游戏业务场景的双轨制评估体系。该体系包含**日常自动化自评**和**上线前人工评定**两个核心部分，旨在从不同维度全面、客观地评估系统在玩家行为分析、流失预警、付费模式识别等核心任务上的表现。

**评估方法论基础**: 我们的评估体系参考并整合了**DeepEval**、**RAGAS**、**TruLens**等业界领先的RAG评估框架，采用**LLM-as-a-Judge**方法和**RAG Triad**核心指标，确保评估的科学性和权威性。

- **日常自动化自评 (Automated Self-Assessment)**: 在每次模型或算法迭代后自动运行，提供快速、量化的性能反馈，确保核心分析功能稳定、可靠。
- **上线评定 (Manual Pre-launch Assessment)**: 在新版本或新功能（如新的分析策略）上线前进行，由游戏分析师和运营专家进行深度、定性的评估，确保分析洞察的准确性、深度和可行动性。

---

## 2. 日常自动化自评

### 2.1 目标
- **快速反馈**: 在代码迭代后几分钟内获得核心业务指标的反馈。
- **性能监控**: 长期跟踪关键分析任务（如流失预测、LTV计算）的准确率变化。
- **成本控制**: 监控LLM调用和token消耗，优化分析任务的资源效率。
- **组件协同**: 评估各模块（查询改写、搜索、推理）的协同效果。

### 2.2 核心自动化指标体系

#### 2.2.1 RAG Triad 核心指标 (参考TruLens)

基于TruLens提出的RAG Triad，我们针对游戏分析场景进行了适配：

| 指标 (Metric) | 定义 | 游戏场景适配 | 实现方式 | 目标 (Target) |
| --- | --- | --- | --- | --- |
| **Context Relevance** | 检索上下文与查询的相关性 | 检索的玩家数据、游戏事件是否与分析需求相关 | LLM-as-a-Judge评估检索内容相关性 | ≥ 0.8 |
| **Faithfulness/Groundedness** | 回答是否忠实于检索的上下文 | 分析结论是否基于实际游戏数据，无幻觉 | LLM-as-a-Judge检查答案与数据的一致性 | ≥ 0.85 |
| **Answer Relevance** | 回答与原始查询的相关性 | 分析结果是否直接回应了业务问题 | LLM-as-a-Judge评估答案相关性 | ≥ 0.8 |

#### 2.2.2 RAGAS 扩展指标

参考RAGAS框架，增加精确度和召回率指标：

| 指标 (Metric) | 定义 | 游戏场景适配 | 实现方式 | 目标 (Target) |
| --- | --- | --- | --- | --- |
| **Context Precision** | 检索文档的精确度 | 检索的游戏数据中有多少是真正有用的 | 计算相关检索项占总检索项的比例 | ≥ 0.75 |
| **Context Recall** | 检索文档的召回率 | 相关游戏数据有多少被成功检索到 | 计算检索到的相关项占所有相关项的比例 | ≥ 0.7 |

#### 2.2.3 基础性能指标

| 指标 (Metric) | 定义 | 实现方式 | 目标 (Target) |
| --- | --- | --- | --- |
| **业务指标准确率 (Business Accuracy)** | 分析结果（如LTV预测、流失率）与数据库真实值的偏差。 | 对比RAG输出与BI系统数据。 | 偏差 < 10% |
| **洞察覆盖度 (Insight Coverage)** | 答案是否覆盖了问题所涉及的关键游戏元素（如玩家分群、关卡、道具）。 | `_check_insight_coverage` - 检查答案是否包含预设的关键词列表。 | ≥ 85% |
| **响应延迟 (Latency)** | 从收到分析请求到返回完整洞察的平均时间。 | `time.time()` 计时，区分在线（Dashboard）与离线（报告）场景。 | 在线≤5s, 离线≤5min |
| **鲁棒性 (Robustness)** | 系统成功处理各种复杂分析查询的比例。 | 捕获和统计查询过程中的异常。 | ≥ 99.5% |

#### 2.2.4 高级功能指标

| 指标 (Metric) | 定义 | 实现方式 | 目标 (Target) |
| --- | --- | --- | --- |
| **查询改写效果 (Query Rewrite Effectiveness)** | 改写后查询相比原始查询的检索精度提升。 | `_evaluate_rewrite_improvement` - 对比改写前后的搜索结果质量。 | 提升 ≥ 15% |
| **意图识别准确率 (Intent Recognition Accuracy)** | 系统识别查询意图的准确性。 | 与人工标注的查询意图进行对比。 | ≥ 90% |
| **DeepSearch路径有效性 (Path Validity)** | DeepSearch的逻辑链是否符合游戏分析逻辑（如付费分析应包含玩家、道具、付费节点）。 | `_validate_deepsearch_path` - 基于规则检查逻辑链的节点类型和顺序。 | ≥ 95% |
| **多策略融合效果 (Multi-Strategy Fusion)** | 多种搜索策略（Local、Global、DRIFT、DeepSearch）组合使用的效果。 | `_evaluate_strategy_fusion` - 评估组合搜索相比单一策略的效果提升。 | 提升 ≥ 20% |
| **混合检索精度 (Hybrid Retrieval Precision)** | BM25+Dense混合检索相比单一检索方式的精度提升。 | `_measure_hybrid_retrieval_gain` - 对比混合检索与单一方式的相关性得分。 | 提升 ≥ 12% |
| **置信度相关性 (Confidence Correlation)** | 系统输出的置信度分数与人工评估分数的正相关性。 | 计算置信度与人工评分的皮尔逊相关系数。 | r > 0.6 |

### 2.3 LLM-as-a-Judge 评估实现

#### 2.3.1 核心方法论

参考DeepEval和TruLens的实践，我们实现基于LLM的自动化评估：

```python
# graphrag/evaluation/llm_judge_evaluator.py

class LLMJudgeEvaluator:
    """基于LLM-as-a-Judge的评估器，参考DeepEval和TruLens方法论。"""
    
    def __init__(self, judge_model: ChatModel, evaluation_model: str = "gpt-4o"):
        self.judge_model = judge_model
        self.evaluation_model = evaluation_model
        
        # RAG Triad 评估提示模板
        self.triad_prompts = {
            "context_relevance": self._load_context_relevance_prompt(),
            "faithfulness": self._load_faithfulness_prompt(), 
            "answer_relevance": self._load_answer_relevance_prompt()
        }
    
    async def evaluate_rag_triad(self, 
                                query: str, 
                                retrieved_contexts: List[str], 
                                response: str) -> RAGTriadResult:
        """使用RAG Triad方法评估RAG系统的三个核心维度。"""
        
        # 1. Context Relevance - 上下文相关性
        context_relevance_score = await self._judge_context_relevance(
            query, retrieved_contexts
        )
        
        # 2. Faithfulness - 忠实度/基础性
        faithfulness_score = await self._judge_faithfulness(
            retrieved_contexts, response
        )
        
        # 3. Answer Relevance - 答案相关性
        answer_relevance_score = await self._judge_answer_relevance(
            query, response
        )
        
        return RAGTriadResult(
            context_relevance=context_relevance_score,
            faithfulness=faithfulness_score,
            answer_relevance=answer_relevance_score,
            overall_score=(context_relevance_score + faithfulness_score + answer_relevance_score) / 3
        )
    
    async def _judge_context_relevance(self, query: str, contexts: List[str]) -> float:
        """评估检索上下文的相关性。"""
        prompt = f"""
你是一个专业的游戏数据分析评估专家。请评估以下检索到的上下文对于用户查询的相关性。

用户查询: {query}

检索到的上下文:
{chr(10).join([f"{i+1}. {ctx}" for i, ctx in enumerate(contexts)])}

评估标准:
1. 上下文是否包含回答查询所需的关键信息？
2. 上下文是否与游戏分析场景相关？
3. 上下文的信息质量如何？

请给出0-1之间的相关性分数，其中:
- 0.0-0.3: 不相关或误导性信息
- 0.4-0.6: 部分相关但信息不足
- 0.7-0.8: 相关且信息充分
- 0.9-1.0: 高度相关且信息完整

只输出数字分数，不要其他内容。
"""
        
        response = await self.judge_model.achat(prompt)
        try:
            return float(response.output.content.strip())
        except ValueError:
            return 0.0
    
    async def _judge_faithfulness(self, contexts: List[str], response: str) -> float:
        """评估答案对检索上下文的忠实度。"""
        prompt = f"""
你是一个专业的事实核查专家。请评估生成的回答是否忠实于提供的上下文，是否存在幻觉或不准确的信息。

提供的上下文:
{chr(10).join([f"{i+1}. {ctx}" for i, ctx in enumerate(contexts)])}

生成的回答:
{response}

评估标准:
1. 回答中的每个事实声明都能在上下文中找到支持吗？
2. 回答是否包含上下文中没有的信息（幻觉）？
3. 回答是否曲解或误解了上下文中的信息？

请给出0-1之间的忠实度分数，其中:
- 0.0-0.3: 严重失实，包含大量幻觉
- 0.4-0.6: 部分失实，有一些不准确信息
- 0.7-0.8: 基本忠实，偶有小误差
- 0.9-1.0: 完全忠实，所有信息都有依据

只输出数字分数，不要其他内容。
"""
        
        response = await self.judge_model.achat(prompt)
        try:
            return float(response.output.content.strip())
        except ValueError:
            return 0.0
    
    async def _judge_answer_relevance(self, query: str, response: str) -> float:
        """评估答案对查询的相关性。"""
        prompt = f"""
你是一个专业的游戏业务分析专家。请评估生成的回答对于用户查询的相关性。

用户查询: {query}

生成的回答:
{response}

评估标准:
1. 回答是否直接回应了用户的问题？
2. 回答是否提供了查询所需的信息？
3. 回答是否包含无关或偏题的内容？
4. 回答是否符合游戏分析的业务需求？

请给出0-1之间的相关性分数，其中:
- 0.0-0.3: 完全不相关或答非所问
- 0.4-0.6: 部分相关但偏离主题
- 0.7-0.8: 相关且有价值
- 0.9-1.0: 高度相关且完全回应查询

只输出数字分数，不要其他内容。
"""
        
        response = await self.judge_model.achat(prompt)
        try:
            return float(response.output.content.strip())
        except ValueError:
            return 0.0

@dataclass
class RAGTriadResult:
    """RAG Triad评估结果。"""
    context_relevance: float
    faithfulness: float
    answer_relevance: float
    overall_score: float
    
    def is_passing(self, thresholds: Dict[str, float] = None) -> bool:
        """判断是否通过评估阈值。"""
        if thresholds is None:
            thresholds = {
                "context_relevance": 0.8,
                "faithfulness": 0.85,
                "answer_relevance": 0.8
            }
        
        return (
            self.context_relevance >= thresholds["context_relevance"] and
            self.faithfulness >= thresholds["faithfulness"] and
            self.answer_relevance >= thresholds["answer_relevance"]
        )
```

#### 2.3.2 测试集构造方法

参考主流框架的最佳实践，我们建立系统化的测试集构造方法：

```python
# graphrag/evaluation/test_dataset_builder.py

class GameAnalysisTestDatasetBuilder:
    """游戏分析测试集构造器，参考RAGAS和DeepEval的方法。"""
    
    def __init__(self, llm_model: ChatModel):
        self.llm_model = llm_model
        
    async def build_comprehensive_testset(self, 
                                        knowledge_base: List[str],
                                        target_size: int = 100) -> GameAnalysisTestDataset:
        """构造全面的游戏分析测试集。"""
        
        testset = GameAnalysisTestDataset()
        
        # 1. 基于知识库生成多样化查询
        queries = await self._generate_diverse_queries(knowledge_base, target_size)
        
        # 2. 为每个查询生成标准答案和干扰项
        for query in queries:
            test_case = await self._create_test_case(query, knowledge_base)
            testset.add_case(test_case)
        
        # 3. 添加边界情况和负面案例
        edge_cases = await self._generate_edge_cases(knowledge_base)
        testset.extend(edge_cases)
        
        return testset
    
    async def _generate_diverse_queries(self, 
                                      knowledge_base: List[str], 
                                      target_size: int) -> List[str]:
        """生成多样化的游戏分析查询。"""
        
        query_templates = {
            "descriptive": [
                "分析{}的趋势变化",
                "描述{}的分布情况", 
                "总结{}的主要特征"
            ],
            "analytical": [
                "为什么{}会发生变化？",
                "{}的主要影响因素是什么？",
                "如何解释{}的异常表现？"
            ],
            "predictive": [
                "预测{}的未来走势",
                "估算{}的潜在影响",
                "评估{}的风险程度"
            ],
            "actionable": [
                "如何优化{}？",
                "针对{}制定什么策略？",
                "{}的最佳实践是什么？"
            ]
        }
        
        game_entities = [
            "玩家留存率", "付费转化率", "LTV", "ARPU", "新手玩家流失", 
            "高价值玩家行为", "关卡通过率", "道具使用情况", "活动参与度",
            "玩家分群特征", "付费路径", "游戏平衡性"
        ]
        
        queries = []
        for category, templates in query_templates.items():
            for template in templates:
                for entity in game_entities:
                    if len(queries) < target_size:
                        query = template.format(entity)
                        queries.append(query)
        
        return queries[:target_size]
    
    async def _create_test_case(self, 
                              query: str, 
                              knowledge_base: List[str]) -> GameAnalysisTestCase:
        """为单个查询创建完整的测试用例。"""
        
        # 1. 生成golden answer
        golden_answer = await self._generate_golden_answer(query, knowledge_base)
        
        # 2. 模拟检索上下文
        relevant_contexts = await self._retrieve_relevant_contexts(query, knowledge_base)
        
        # 3. 生成负面样本（用于测试robustness）
        negative_contexts = await self._generate_negative_contexts(query, knowledge_base)
        
        return GameAnalysisTestCase(
            query=query,
            golden_answer=golden_answer,
            relevant_contexts=relevant_contexts,
            negative_contexts=negative_contexts,
            metadata={
                "category": self._classify_query_type(query),
                "difficulty": self._assess_query_difficulty(query),
                "business_impact": self._assess_business_impact(query)
            }
        )

@dataclass 
class GameAnalysisTestCase:
    """游戏分析测试用例。"""
    query: str
    golden_answer: str
    relevant_contexts: List[str]
    negative_contexts: List[str]  # 用于测试抗干扰能力
    metadata: Dict[str, Any]

class GameAnalysisTestDataset:
    """游戏分析测试数据集。"""
    
    def __init__(self):
        self.test_cases: List[GameAnalysisTestCase] = []
    
    def add_case(self, test_case: GameAnalysisTestCase):
        self.test_cases.append(test_case)
    
    def extend(self, test_cases: List[GameAnalysisTestCase]):
        self.test_cases.extend(test_cases)
    
    def get_by_category(self, category: str) -> List[GameAnalysisTestCase]:
        return [case for case in self.test_cases if case.metadata.get("category") == category]
    
    def get_by_difficulty(self, difficulty: str) -> List[GameAnalysisTestCase]:
        return [case for case in self.test_cases if case.metadata.get("difficulty") == difficulty]
```

### 2.4 端到端评估流程

#### 2.4.1 完整链路评估

```python
# graphrag/evaluation/end_to_end_evaluator.py

class EndToEndEvaluator:
    """端到端评估器，评估完整的查询处理链路。"""
    
    def __init__(self, graphrag_engine, rewrite_engine, intent_recognizer):
        self.graphrag_engine = graphrag_engine
        self.rewrite_engine = rewrite_engine
        self.intent_recognizer = intent_recognizer
        self.llm_judge = LLMJudgeEvaluator(graphrag_engine.chat_model)
    
    async def evaluate_complete_pipeline(self, test_dataset: GameAnalysisTestDataset) -> Dict[str, float]:
        """评估完整的查询处理管道。"""
        
        results = {
            "original_baseline": [],
            "with_rewrite": [],
            "with_intent": [],
            "full_pipeline": []
        }
        
        for test_case in test_dataset.test_cases:
            query = test_case.query
            
            # 1. 基线：直接搜索
            baseline_result = await self.graphrag_engine.search(query)
            baseline_triad = await self.llm_judge.evaluate_rag_triad(
                query, baseline_result.context_data.get("contexts", []), baseline_result.response
            )
            results["original_baseline"].append(baseline_triad.overall_score)
            
            # 2. 仅查询改写
            rewritten_result = await self.rewrite_engine.rewrite_query(query)
            rewrite_search_result = await self.graphrag_engine.search(rewritten_result.rewritten_queries[0])
            rewrite_triad = await self.llm_judge.evaluate_rag_triad(
                query, rewrite_search_result.context_data.get("contexts", []), rewrite_search_result.response
            )
            results["with_rewrite"].append(rewrite_triad.overall_score)
            
            # 3. 仅意图识别
            intent_analysis = await self.intent_recognizer.analyze_intent(query)
            intent_result = await self.graphrag_engine.search(
                query, strategy_hint=intent_analysis.recommended_strategy
            )
            intent_triad = await self.llm_judge.evaluate_rag_triad(
                query, intent_result.context_data.get("contexts", []), intent_result.response
            )
            results["with_intent"].append(intent_triad.overall_score)
            
            # 4. 完整管道
            full_result = await self._run_full_pipeline(query)
            full_triad = await self.llm_judge.evaluate_rag_triad(
                query, full_result.context_data.get("contexts", []), full_result.response
            )
            results["full_pipeline"].append(full_triad.overall_score)
        
        # 计算平均提升
        improvements = {}
        baseline_avg = np.mean(results["original_baseline"])
        
        for pipeline, scores in results.items():
            if pipeline != "original_baseline":
                avg_score = np.mean(scores)
                improvement = (avg_score - baseline_avg) / baseline_avg * 100
                improvements[f"{pipeline}_improvement"] = improvement
        
        return improvements
```

#### 2.4.2 游戏场景专项评估

```python
class GameAnalysisEvaluator(BaseScenarioEvaluator):
    """扩展的游戏分析场景评估器，整合LLM-as-a-Judge方法。"""
    
    def __init__(self):
        super().__init__()
        self.llm_judge = LLMJudgeEvaluator(ChatModel())
    
    async def evaluate(self, queries, expected_kpis, search_engine):
        # ... (评估逻辑)
        
        for i, query in enumerate(queries):
            search_result = await search_engine.search(query)
            
            # 1. RAG Triad 评估
            triad_result = await self.llm_judge.evaluate_rag_triad(
                query, 
                search_result.context_data.get("contexts", []), 
                search_result.response
            )
            
            # 2. 业务指标准确率
            predicted_ltv = self._extract_kpi_from_response(search_result.response, "LTV")
            accuracy = 1 - abs(predicted_ltv - expected_kpis[i]["LTV"]) / expected_kpis[i]["LTV"]
            business_accuracy_scores.append(accuracy)
            
            # 3. 洞察覆盖度
            required_elements = ["付费路径", "关键决策点", "促销活动", "玩家分群", "留存分析"]
            coverage = self._check_insight_coverage(search_result.response, required_elements)
            insight_coverage_scores.append(coverage)
            
            # 4. DeepSearch路径有效性
            if "deep_search" in search_result.metadata:
                path_validity = self._validate_deepsearch_path(search_result.metadata["logic_chain"])
                path_validity_scores.append(path_validity)
            
            # 5. 查询改写效果评估
            if "query_rewrite" in search_result.metadata:
                rewrite_effectiveness = self._evaluate_rewrite_effectiveness(
                    search_result.metadata["original_query"],
                    search_result.metadata["rewritten_queries"],
                    search_result
                )
                rewrite_effectiveness_scores.append(rewrite_effectiveness)
            
            # 6. 游戏专业术语使用准确性
            terminology_accuracy = self._check_game_terminology_usage(search_result.response)
            terminology_scores.append(terminology_accuracy)
            
            # 7. 添加RAG Triad评分
            rag_triad_scores.append(triad_result.overall_score)
            context_relevance_scores.append(triad_result.context_relevance)
            faithfulness_scores.append(triad_result.faithfulness)
            answer_relevance_scores.append(triad_result.answer_relevance)
        
        # 聚合所有指标
        result = ScenarioEvaluationResult(scenario_type=ScenarioType.GAME_ANALYSIS)
        
        # 添加RAG Triad指标
        result.add_metric(EvaluationMetric(
            name="rag_triad_overall", value=float(np.mean(rag_triad_scores)),
            threshold=0.8, description="RAG Triad综合评分", weight=3.0
        ))
        
        result.add_metric(EvaluationMetric(
            name="context_relevance", value=float(np.mean(context_relevance_scores)),
            threshold=0.8, description="上下文相关性", weight=2.0
        ))
        
        result.add_metric(EvaluationMetric(
            name="faithfulness", value=float(np.mean(faithfulness_scores)),
            threshold=0.85, description="回答忠实度", weight=3.0
        ))
        
        result.add_metric(EvaluationMetric(
            name="answer_relevance", value=float(np.mean(answer_relevance_scores)),
            threshold=0.8, description="回答相关性", weight=2.0
        ))
        
        # 其他现有指标...
        
        return result

# 运行增强的游戏评估
async def run_enhanced_game_assessment_with_llm_judge():
    # 1. 构建测试集
    dataset_builder = GameAnalysisTestDatasetBuilder(llm_model)
    test_dataset = await dataset_builder.build_comprehensive_testset(
        knowledge_base=load_game_knowledge_base(),
        target_size=200
    )
    
    # 2. 端到端评估
    end_to_end_evaluator = EndToEndEvaluator(graphrag_engine, rewrite_engine, intent_recognizer)
    pipeline_improvements = await end_to_end_evaluator.evaluate_complete_pipeline(test_dataset)
    
    # 3. LLM-as-a-Judge详细评估
    game_evaluator = GameAnalysisEvaluator()
    detailed_results = await game_evaluator.evaluate(
        queries=[case.query for case in test_dataset.test_cases],
        expected_kpis=[{"LTV": 100}] * len(test_dataset.test_cases),  # 示例
        search_engine=graphrag_engine
    )
    
    # 4. 生成评估报告
    report = generate_comprehensive_evaluation_report(pipeline_improvements, detailed_results)
    
    return report
```

---

## 3. 上线前人工评定

### 3.1 目标
- **洞察质量把关**: 确保上线版本的分析结果准确、深刻、具有业务价值。
- **深度分析**: 发现自动化测试无法覆盖的、与游戏运营直觉相悖的或有问题的分析逻辑。
- **Bad Case收集**: 为模型、Prompt和DeepSearch策略的迭代提供高质量的训练数据。
- **新功能验收**: 对查询改写、意图识别等新功能进行人工验收。
- **LLM-as-a-Judge校准**: 验证和校准自动化评估的准确性。

### 3.2 人工评定维度 (游戏场景)
评估人员（游戏分析师/运营专家）需要从以下七个维度对每个分析结果进行打分（1-5分）：

1.  **准确性 (Accuracy)**: 分析结论中的每一个声明是否都可以在源数据中找到依据？是否存在与游戏事实不符的错误？
2.  **分析深度 (Analytical Depth)**: 答案是停留在表面数据描述，还是提供了深度的、多维度的归因分析？是否揭示了数据背后的潜在规律？
3.  **可行动性 (Actionability)**: 分析结果是否能直接转化为具体的运营策略？是否对游戏优化、市场活动或玩家管理有明确的指导意义？
4.  **逻辑链条理性 (Logic Coherence)**: (DeepSearch专项) 搜索路径是否符合分析逻辑？每一步的推理是否清晰、合理？可视化是否易于理解？
5.  **查询理解准确性 (Query Understanding)**: 系统是否正确理解了用户的真实意图？改写后的查询是否保持了原意？
6.  **专业术语适配性 (Domain Adaptation)**: 分析结果是否使用了准确的游戏行业术语？是否体现了游戏业务的专业性？
7.  **安全性与公平性 (Safety & Fairness)**: 玩家分群或个性化建议是否存在歧视性或不公平的风险？是否可能导致负面的玩家体验？

### 3.3 LLM-as-a-Judge 校准流程

为确保自动化评估的可靠性，我们建立人工评估与LLM-as-a-Judge的校准机制：

```python
# graphrag/evaluation/judge_calibration.py

class LLMJudgeCalibration:
    """LLM-as-a-Judge校准器，确保自动化评估与人工评估的一致性。"""
    
    async def calibrate_judge_with_human_annotations(self, 
                                                   test_cases: List[GameAnalysisTestCase],
                                                   human_annotations: List[HumanEvaluation]) -> CalibrationResult:
        """使用人工标注校准LLM评估器。"""
        
        judge_scores = []
        human_scores = []
        
        for test_case, human_eval in zip(test_cases, human_annotations):
            # LLM-as-a-Judge评分
            llm_result = await self.llm_judge.evaluate_rag_triad(
                test_case.query, test_case.relevant_contexts, test_case.golden_answer
            )
            
            # 人工评分（转换为0-1范围）
            human_score = self._convert_human_score_to_normalized(human_eval)
            
            judge_scores.append(llm_result.overall_score)
            human_scores.append(human_score)
        
        # 计算相关性和一致性指标
        correlation = pearsonr(judge_scores, human_scores)[0]
        mse = mean_squared_error(human_scores, judge_scores)
        
        return CalibrationResult(
            correlation=correlation,
            mse=mse,
            judge_scores=judge_scores,
            human_scores=human_scores,
            is_well_calibrated=correlation > 0.7 and mse < 0.1
        )

@dataclass
class HumanEvaluation:
    """人工评估结果。"""
    accuracy: int  # 1-5
    analytical_depth: int  # 1-5
    actionability: int  # 1-5
    logic_coherence: int  # 1-5
    query_understanding: int  # 1-5
    domain_adaptation: int  # 1-5
    safety_fairness: int  # 1-5
    
    @property
    def overall_score(self) -> float:
        """计算综合评分（0-1范围）。"""
        scores = [
            self.accuracy, self.analytical_depth, self.actionability,
            self.logic_coherence, self.query_understanding, 
            self.domain_adaptation, self.safety_fairness
        ]
        return (sum(scores) - 7) / (35 - 7)  # 归一化到0-1
```

### 3.4 评估结果定义

#### 正确与错误 (Correct vs. Incorrect)
- **正确 (Correct)**: 分析结论的核心论点都有数据支持，没有明显的事实错误，查询理解准确。
- **错误 (Incorrect)**: 分析结论中至少有一个核心论点无法从数据中得到支持，或与数据明确冲突，或严重误解了查询意图。

#### 好、中、差分档 (Good / Medium / Bad)
- **优秀 (Good)**: 所有维度得分均较高（≥4分）。分析准确、深刻、可行动性强，能带来显著业务价值。
- **中等 (Medium)**: 分析基本正确，但在深度、可行动性或专业性上有所欠缺。可以作为参考，但需进一步挖掘。
- **差 (Bad)**: 分析存在明显的事实错误，或逻辑混乱，或完全没有业务价值。该case需要被优先分析和修复。

### 3.5 Bad Case分类体系 (游戏场景增强版)

| 分类 (Category) | 描述 | 游戏场景示例 |
| --- | --- | --- |
| **事实计算错误 (Factual/Calculation Error)** | 答案中的指标或事实与数据源冲突。 | 报告中玩家A的付费总额是$50，但数据库记录是$100。 |
| **因果倒置 (Causal Misinterpretation)** | 错误地将相关性判断为因果性，或颠倒了因果关系。 | 结论："因为玩家购买了皮肤，所以他们付费意愿高。"（实际可能是因为付费意愿高才买皮肤） |
| **查询意图误解 (Query Misunderstanding)** | 系统未能正确理解用户的真实查询意图。 | 用户问"新手玩家留存问题"，系统回答了"所有玩家的留存情况"。 |
| **改写过度失真 (Over-rewriting Distortion)** | 查询改写过程中偏离了原始意图。 | 原询"这个月收入如何？"被改写为"用户生命周期价值分析"，偏离了月度收入查询。 |
| **分析不完整 (Incomplete Analysis)** | 分析遗漏了影响结论的关键维度或玩家群体。 | 分析流失原因时，只分析了关卡难度，忽略了社交因素和运营活动的影响。 |
| **洞察表面化 (Superficial Insight)** | 答案只是对数据的简单复述，缺乏深层洞察。 | "付费玩家比免费玩家付了更多的钱。" |
| **逻辑链断裂 (Broken Logic Chain)** | (DeepSearch) 搜索路径不合逻辑，或推理步骤之间缺乏关联。 | 分析付费路径时，从"玩家注册"直接跳到"大额付费"，缺少了中间的"小额尝试"、"活动参与"等关键步骤。 |
| **置信度误判 (Confidence Misjudgment)**| 系统给出了高置信度，但结果却是错误的；或结果正确但置信度很低。 | 系统以95%的置信度声称某次更新提升了留存率，但实际数据是下降的。 |
| **术语使用不当 (Improper Terminology)** | 使用了错误或不专业的游戏行业术语。 | 使用"客户"而非"玩家"，使用"销售额"而非"付费金额"或"流水"。 |
| **建议不可行 (Impractical Suggestion)** | 提出的运营建议不符合游戏实际或无法执行。 | 建议"为所有玩家提供稀有道具"，忽略了游戏经济系统的平衡。 |
| **玩家分群偏见 (Segment Bias)** | 对特定玩家群体的分析或建议存在刻板印象或不公平。 | 将所有低付费玩家标记为"无价值用户"，并建议忽略他们的体验。 |
| **多策略冲突 (Multi-Strategy Conflict)** | 不同搜索策略得出的结论相互矛盾，且未妥善处理冲突。 | Local搜索显示玩家满意度高，Global搜索显示满意度低，最终结果未解释矛盾。 |
| **RAG Triad失衡 (RAG Triad Imbalance)** | 三个核心维度（上下文相关性、忠实度、答案相关性）严重失衡。 | 上下文高度相关，但答案完全不相关；或答案相关但不忠实于数据。 |

---

## 4. 评估流程与工具

### 4.1 增强评估流程

1.  **测试集构建**: 联合游戏策划和数据分析师，构建覆盖核心业务问题（如LTV预测、流失分析、活动效果评估）的标准化测试集，包含简单、复杂、模糊、专业四个类别的查询。
2.  **LLM-as-a-Judge自动化评估**: 使用RAG Triad和RAGAS指标进行大规模自动化评估，集成到CI/CD流程中。
3.  **A/B测试框架**: 对新功能（如查询改写策略）进行A/B测试，量化评估效果提升。
4.  **人工评估平台**: 使用内部BI工具或标注平台，将需要评测的复杂问题分发给游戏分析师，收集多维度评分和Bad Case分类。
5.  **LLM-as-a-Judge校准**: 定期使用人工评估结果校准自动化评估器，确保评估质量。
6.  **双周评估会议**: 定期汇总自动化和人工评测结果，由产品、运营和开发共同参与，分析关键Bad Case，确定下一轮迭代的优化方向。

### 4.2 与主流框架的对比

我们的评估体系与业界领先框架的对比：

| 维度 | 我们的方案 | DeepEval | RAGAS | TruLens |
| --- | --- | --- | --- | --- |
| **核心方法** | LLM-as-a-Judge + RAG Triad | LLM-as-a-Judge + G-Eval | LLM + 统计方法 | LLM-as-a-Judge |
| **游戏场景适配** | ✅ 深度适配 | ❌ 通用框架 | ❌ 通用框架 | ❌ 通用框架 |
| **测试集构造** | ✅ 自动化生成 | ✅ 合成数据 | ✅ 合成数据 | ❌ 需手动构建 |
| **评估指标** | RAG Triad + 业务指标 | 全面指标库 | RAG专用指标 | RAG Triad |
| **实时评估** | ✅ 支持 | ✅ 支持 | ✅ 支持 | ✅ 支持 |
| **可解释性** | ✅ 详细推理 | ✅ 支持 | ⚠️ 部分支持 | ✅ 支持 |

### 4.3 实际应用示例

#### 4.3.1 真实游戏查询评估

```python
# 实际游戏运营查询的评估示例
game_analysis_queries = [
    {
        "query": "最近新上线的皮肤销售情况如何？",
        "expected_elements": ["皮肤名称", "销售数量", "收入", "购买玩家画像", "时间趋势"],
        "query_type": "simple",
        "business_impact": "high"
    },
    {
        "query": "分析高价值玩家在新版本更新后的行为变化，并提出个性化运营策略",
        "expected_elements": ["高价值玩家定义", "行为变化指标", "变化原因分析", "个性化策略", "实施建议"],
        "query_type": "complex", 
        "business_impact": "critical"
    },
    {
        "query": "这个活动效果怎么样？",
        "expected_elements": ["活动识别", "参与率", "转化效果", "ROI分析"],
        "query_type": "ambiguous",
        "business_impact": "medium"
    }
]

async def evaluate_real_game_queries_with_llm_judge():
    """使用LLM-as-a-Judge评估真实游戏查询的处理效果。"""
    evaluator = GameAnalysisEvaluator()
    llm_judge = LLMJudgeEvaluator(chat_model)
    
    for query_info in game_analysis_queries:
        # 完整管道处理
        result = await run_complete_pipeline(query_info["query"])
        
        # LLM-as-a-Judge评估
        triad_result = await llm_judge.evaluate_rag_triad(
            query_info["query"],
            result.context_data.get("contexts", []),
            result.response
        )
        
        # 多维度评估
        evaluation_score = await evaluator.evaluate_single_query(
            query=query_info["query"],
            result=result,
            expected_elements=query_info["expected_elements"],
            business_impact=query_info["business_impact"]
        )
        
        # 记录评估结果
        log_evaluation_result(query_info, evaluation_score, triad_result)
```

#### 4.3.2 渐进式评估策略

```python
class ProgressiveEvaluationStrategy:
    """渐进式评估策略，适用于不同成熟度的功能。"""
    
    def __init__(self):
        self.evaluation_stages = {
            "alpha": {"automation_ratio": 0.3, "human_oversight": 0.7},
            "beta": {"automation_ratio": 0.6, "human_oversight": 0.4}, 
            "production": {"automation_ratio": 0.9, "human_oversight": 0.1}
        }
        self.llm_judge = LLMJudgeEvaluator(ChatModel())
    
    async def evaluate_by_stage(self, functionality: str, stage: str, test_cases: List):
        """根据功能成熟度调整评估策略。"""
        stage_config = self.evaluation_stages[stage]
        
        # 自动化评估部分（使用LLM-as-a-Judge）
        auto_sample_size = int(len(test_cases) * stage_config["automation_ratio"])
        auto_results = await self.run_llm_judge_evaluation(test_cases[:auto_sample_size])
        
        # 人工评估部分
        human_sample_size = int(len(test_cases) * stage_config["human_oversight"])
        human_results = await self.run_human_evaluation(test_cases[-human_sample_size:])
        
        # 综合评估结果
        return self.combine_evaluation_results(auto_results, human_results, stage_config)
```

通过这套为游戏分析场景量身定制的增强评估体系，我们可以系统性地提升GraphRAG平台的洞察能力，确保查询改写、意图识别、多策略融合等新功能真正服务于数据驱动的精细化游戏运营。该体系充分借鉴了DeepEval、RAGAS、TruLens等业界领先框架的最佳实践，并针对游戏分析场景进行了深度优化。 