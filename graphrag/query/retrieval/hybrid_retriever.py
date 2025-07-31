# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Hybrid retrieval combining BM25 and dense vector search."""

import asyncio
import logging
from typing import Any, List, Dict, Optional
from dataclasses import dataclass
import numpy as np
import pandas as pd

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

from graphrag.vector_stores.base import BaseVectorStore, VectorStoreSearchResult
from graphrag.language_model.protocol.base import EmbeddingModel
from graphrag.data_model.entity import Entity
from graphrag.data_model.text_unit import TextUnit

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Result from hybrid search combining BM25 and dense retrieval."""
    
    item_id: str
    content: str
    bm25_score: float
    dense_score: float
    hybrid_score: float
    source: str  # 'bm25', 'dense', or 'both'
    metadata: Optional[Dict[str, Any]] = None


class BM25Retriever:
    """BM25-based keyword retrieval."""
    
    def __init__(self, corpus: List[str], ids: List[str]):
        """
        Initialize BM25 retriever.
        
        Args:
            corpus: List of text documents
            ids: Corresponding document IDs
        """
        if not BM25_AVAILABLE:
            raise ImportError(
                "BM25 retrieval requires rank_bm25. "
                "Install with: pip install rank_bm25"
            )
        
        self.ids = ids
        self.corpus = corpus
        
        # Tokenize corpus for BM25
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        logger.info(f"Initialized BM25 retriever with {len(corpus)} documents")
    
    def search(self, query: str, k: int = 10) -> List[HybridSearchResult]:
        """Search using BM25."""
        if not query.strip():
            return []
        
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k results
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                result = HybridSearchResult(
                    item_id=self.ids[idx],
                    content=self.corpus[idx],
                    bm25_score=float(scores[idx]),
                    dense_score=0.0,
                    hybrid_score=float(scores[idx]),
                    source='bm25'
                )
                results.append(result)
        
        return results


class HybridRetriever:
    """Hybrid retriever combining BM25 and dense vector search."""
    
    def __init__(
        self,
        vector_store: BaseVectorStore,
        text_embedder: EmbeddingModel,
        corpus_texts: List[str],
        corpus_ids: List[str],
        bm25_weight: float = 0.3,
        dense_weight: float = 0.7,
        enable_bm25: bool = True,
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_store: Dense vector store for semantic search
            text_embedder: Embedding model for query encoding
            corpus_texts: Text corpus for BM25
            corpus_ids: Corresponding IDs
            bm25_weight: Weight for BM25 scores (0-1)
            dense_weight: Weight for dense scores (0-1)
            enable_bm25: Whether to enable BM25 retrieval
        """
        self.vector_store = vector_store
        self.text_embedder = text_embedder
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self.enable_bm25 = enable_bm25 and BM25_AVAILABLE
        
        # Initialize BM25 if enabled and available
        self.bm25_retriever = None
        if self.enable_bm25:
            try:
                self.bm25_retriever = BM25Retriever(corpus_texts, corpus_ids)
            except ImportError:
                logger.warning("BM25 not available, falling back to dense-only retrieval")
                self.enable_bm25 = False
        
        logger.info(
            f"Initialized hybrid retriever: BM25={self.enable_bm25}, "
            f"weights=(BM25:{bm25_weight}, Dense:{dense_weight})"
        )
    
    def normalize_scores(self, scores: List[float]) -> List[float]:
        """Normalize scores to 0-1 range using min-max normalization."""
        if not scores:
            return scores
        
        scores_array = np.array(scores)
        min_score = scores_array.min()
        max_score = scores_array.max()
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        normalized = (scores_array - min_score) / (max_score - min_score)
        return normalized.tolist()
    
    async def search(
        self,
        query: str,
        k: int = 10,
        alpha: Optional[float] = None,
    ) -> List[HybridSearchResult]:
        """
        Perform hybrid search combining BM25 and dense retrieval.
        
        Args:
            query: Search query
            k: Number of results to return
            alpha: Dynamic weight for BM25 (overrides instance weight if provided)
        
        Returns:
            List of hybrid search results sorted by hybrid score
        """
        if not query.strip():
            return []
        
        # Use dynamic alpha if provided
        bm25_w = alpha if alpha is not None else self.bm25_weight
        dense_w = 1.0 - bm25_w
        
        # Collect results from both retrievers
        all_results = {}
        
        # BM25 retrieval
        if self.enable_bm25 and self.bm25_retriever:
            bm25_results = self.bm25_retriever.search(query, k * 2)  # Get more to ensure overlap
            for result in bm25_results:
                all_results[result.item_id] = result
        
        # Dense retrieval
        try:
            query_embedding = self.text_embedder.embed(query)
            dense_search_results = self.vector_store.similarity_search_by_vector(
                query_embedding=query_embedding,
                k=k * 2  # Get more to ensure overlap
            )
            
            for result in dense_search_results:
                item_id = str(result.document.id)
                content = result.document.text or ""
                if item_id in all_results:
                    # Update existing result with dense score
                    all_results[item_id].dense_score = result.score
                    all_results[item_id].source = 'both'
                else:
                    # Create new result from dense search
                    hybrid_result = HybridSearchResult(
                        item_id=item_id,
                        content=content,
                        bm25_score=0.0,
                        dense_score=result.score,
                        hybrid_score=result.score,
                        source='dense',
                        metadata=result.document.attributes
                    )
                    all_results[item_id] = hybrid_result
                    
        except Exception as e:
            logger.warning(f"Dense retrieval failed: {e}")
        
        # Normalize and combine scores
        results_list = list(all_results.values())
        if not results_list:
            return []
        
        # Extract and normalize scores
        bm25_scores = [r.bm25_score for r in results_list]
        dense_scores = [r.dense_score for r in results_list]
        
        normalized_bm25 = self.normalize_scores(bm25_scores)
        normalized_dense = self.normalize_scores(dense_scores)
        
        # Calculate hybrid scores
        for i, result in enumerate(results_list):
            hybrid_score = (
                bm25_w * normalized_bm25[i] + 
                dense_w * normalized_dense[i]
            )
            result.hybrid_score = hybrid_score
        
        # Sort by hybrid score and return top-k
        results_list.sort(key=lambda x: x.hybrid_score, reverse=True)
        return results_list[:k]
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "bm25_enabled": self.enable_bm25,
            "bm25_weight": self.bm25_weight,
            "dense_weight": self.dense_weight,
            "corpus_size": len(self.bm25_retriever.corpus) if self.bm25_retriever else 0,
        }


def create_hybrid_retriever_for_entities(
    entities: List[Entity],
    vector_store: BaseVectorStore,
    text_embedder: EmbeddingModel,
    **kwargs
) -> HybridRetriever:
    """Create hybrid retriever for entity search."""
    corpus_texts = [entity.description or entity.title for entity in entities]
    corpus_ids = [entity.id for entity in entities]
    
    return HybridRetriever(
        vector_store=vector_store,
        text_embedder=text_embedder,
        corpus_texts=corpus_texts,
        corpus_ids=corpus_ids,
        **kwargs
    )


def create_hybrid_retriever_for_text_units(
    text_units: List[TextUnit],
    vector_store: BaseVectorStore,
    text_embedder: EmbeddingModel,
    **kwargs
) -> HybridRetriever:
    """Create hybrid retriever for text unit search."""
    corpus_texts = [unit.text for unit in text_units]
    corpus_ids = [unit.id for unit in text_units]
    
    return HybridRetriever(
        vector_store=vector_store,
        text_embedder=text_embedder,
        corpus_texts=corpus_texts,
        corpus_ids=corpus_ids,
        **kwargs
    ) 