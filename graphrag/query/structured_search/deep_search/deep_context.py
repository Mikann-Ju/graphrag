# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""DeepSearchContextBuilder implementation."""

from typing import Any

from graphrag.query.context_builder.builders import GlobalContextBuilder, ContextBuilderResult
from graphrag.query.context_builder.conversation_history import ConversationHistory


class DeepSearchContextBuilder(GlobalContextBuilder):
    """DeepSearch上下文构建器，用于构建深度搜索的上下文."""

    def __init__(self, **kwargs: Any):
        """初始化上下文构建器."""
        self.config = kwargs

    async def build_context(
        self,
        query: str,
        conversation_history: ConversationHistory | None = None,
        **kwargs: Any,
    ) -> ContextBuilderResult:
        """构建深度搜索的上下文."""
        # 构建深度搜索所需的上下文
        context_chunks = f"深度搜索查询: {query}"
        context_records = {}
        
        # 这是一个基础实现，可以根据需要扩展
        return ContextBuilderResult(
            context_chunks=context_chunks,
            context_records=context_records,
            llm_calls=0,
            prompt_tokens=0,
            output_tokens=0,
        ) 