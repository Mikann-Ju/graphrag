# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""GraphRAG智能缓存模块"""

from .vector_similarity_cache import VectorSimilarityCache, CachedResult

__all__ = [
    "VectorSimilarityCache",
    "CachedResult"
]
