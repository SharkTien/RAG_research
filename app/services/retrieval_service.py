"""
Retrieval Service
=================
Tìm kiếm các chunks tài liệu liên quan nhất với câu hỏi bằng Vector Search (pgvector).
"""

import uuid
import logging
from typing import List, Dict, Any, Optional

from app.core.config import TOP_K, SIMILARITY_THRESHOLD
from app.services.embedding_service import EmbeddingService
from app.repositories.chunk_repo import ChunkRepository

logger = logging.getLogger("retrieval_service")


class RetrievalService:
    def __init__(self, chunk_repo: ChunkRepository, embedder: Optional[EmbeddingService] = None):
        self.chunk_repo = chunk_repo
        self.embedder = embedder or EmbeddingService()

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        document_id: Optional[str] = None,
        min_score: float = SIMILARITY_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """
        1. Embed câu hỏi
        2. Truy vấn Cosine Similarity trong bảng document_chunks
        3. Trả về Top-K chunks liên quan nhất kèm metadata
        """
        if not query or not query.strip():
            return []

        doc_uuid = uuid.UUID(document_id) if document_id else None
        
        # 1. Tạo vector cho câu hỏi (input_type='query')
        query_vector = self.embedder.embed_query(query.strip())

        # 2. Vector search trong PostgreSQL
        matched_chunks = self.chunk_repo.vector_search(
            query_embedding=query_vector,
            top_k=top_k,
            document_id=doc_uuid,
            min_similarity=min_score,
        )

        logger.info("Truy vấn: '%s' -> Tìm thấy %d chunks phù hợp", query[:50], len(matched_chunks))
        return matched_chunks
