# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""DeepSearch configuration model."""

from dataclasses import dataclass

from .language_model_config import LanguageModelConfig


@dataclass
class DeepSearchConfig:
    """Deep search configuration."""

    max_depth: int = 3
    confidence_threshold: float = 0.7
    use_local_search: bool = True
    use_global_search: bool = True
    enable_path_visualization: bool = True
    enable_logic_chain: bool = True
    max_tokens: int = 8000
    temperature: float = 0.0
    top_p: float = 1.0
    n: int = 1
    
    # 本地搜索相关参数
    local_search_text_unit_prop: float = 0.9
    local_search_community_prop: float = 0.1
    local_search_top_k_mapped_entities: int = 10
    local_search_top_k_relationships: int = 10
    local_search_max_data_tokens: int = 12000
    
    # 全局搜索相关参数
    global_search_max_data_tokens: int = 8000
    global_search_map_max_length: int = 1000
    global_search_reduce_max_length: int = 2000
    
    # LLM配置
    llm: LanguageModelConfig | None = None
    llm_max_gen_tokens: int | None = None
    llm_max_gen_completion_tokens: int | None = None
    
    # 模型ID配置
    chat_model_id: str = "chat"
    embedding_model_id: str = "embedding" 