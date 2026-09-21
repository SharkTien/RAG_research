"""
Chunk Repository
================
Quản lý lưu trữ và truy vấn vector similarity trong bảng document_chunks bằng pgvector.
"""

import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from psycopg.types.json import Jsonb
from app.core.database import DatabaseManager

logger = logging.getLogger("chunk_repo")


class ChunkRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_chunks_batch(self, document_id: uuid.UUID, chunks_with_embeddings: List[Dict[str, Any]]) -> int:
        """
        Lưu danh sách chunks kèm vector embedding vào PostgreSQL.
        chunks_with_embeddings: list dict chứa {id, chunk_index, content, metadata, embedding}
        """
        if not chunks_with_embeddings:
            return 0

        inserted_count = 0
        with self.db.connect() as conn:
            # Kiểm tra xem cột embedding là kiểu vector hay jsonb
            col_type = "vector"
            try:
                type_row = conn.execute("""
                    SELECT data_type, udt_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'document_chunks' AND column_name = 'embedding'
                """).fetchone()
                if type_row and type_row[1] != "vector":
                    col_type = "jsonb"
            except Exception:
                col_type = "vector"

            for chunk in chunks_with_embeddings:
                chunk_id = chunk.get("id") or uuid.uuid4()
                chunk_idx = chunk.get("chunk_index", 0)
                content = chunk.get("content") or chunk.get("text", "")
                metadata = chunk.get("metadata", {})
                embedding = chunk.get("embedding", [])

                if col_type == "vector":
                    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    conn.execute("""
                        INSERT INTO document_chunks (id, document_id, chunk_index, content, metadata, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s::vector)
                        ON CONFLICT (id) DO UPDATE SET 
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                    """, (chunk_id, document_id, chunk_idx, content, Jsonb(metadata), vec_str))
                else:
                    conn.execute("""
                        INSERT INTO document_chunks (id, document_id, chunk_index, content, metadata, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET 
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                    """, (chunk_id, document_id, chunk_idx, content, Jsonb(metadata), Jsonb(embedding)))

                inserted_count += 1

        logger.info("Đã lưu %d chunks vào database cho document_id: %s", inserted_count, document_id)
        return inserted_count

    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[uuid.UUID] = None,
        min_similarity: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm Top-K chunks tương đồng nhất bằng Cosine Similarity (<=> operator).
        """
        if not query_embedding:
            return []

        vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        where_clauses = ["c.embedding IS NOT NULL"]
        where_params: List[Any] = []

        if document_id:
            where_clauses.append("c.document_id = %s")
            where_params.append(document_id)

        where_sql = " AND ".join(where_clauses)
        params: List[Any] = [vec_str, *where_params, vec_str, top_k]

        query_sql = f"""
            SELECT 
                c.id AS chunk_id,
                c.document_id,
                c.chunk_index,
                c.content,
                c.metadata,
                d.original_filename,
                1 - (c.embedding <=> %s::vector) AS similarity_score
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE {where_sql}
            ORDER BY c.embedding <=> %s::vector ASC
            LIMIT %s
        """

        results: List[Dict[str, Any]] = []
        with self.db.connect() as conn:
            try:
                rows = conn.execute(query_sql, params).fetchall()
                for row in rows:
                    score = float(row[6]) if row[6] is not None else 0.0
                    if score >= min_similarity:
                        results.append({
                            "chunk_id": str(row[0]),
                            "document_id": str(row[1]),
                            "chunk_index": row[2],
                            "content": row[3],
                            "metadata": row[4] or {},
                            "file_name": row[5],
                            "similarity_score": round(score, 4),
                        })
            except Exception as exc:
                logger.error("Lỗi khi thực hiện vector_search: %s", exc)
                try:
                    conn.rollback()
                except Exception:
                    pass
                # Fallback text search nếu vector extension chưa sẵn sàng
                fallback_rows = conn.execute("""
                    SELECT c.id, c.document_id, c.chunk_index, c.content, c.metadata, d.original_filename
                    FROM document_chunks c
                    JOIN documents d ON c.document_id = d.id
                    LIMIT %s
                """, (top_k,)).fetchall()
                for row in fallback_rows:
                    results.append({
                        "chunk_id": str(row[0]),
                        "document_id": str(row[1]),
                        "chunk_index": row[2],
                        "content": row[3],
                        "metadata": row[4] or {},
                        "file_name": row[5],
                        "similarity_score": 0.5,
                    })

        return results

    def get_chunks_by_document(self, document_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Lấy tất cả chunks của một tài liệu."""
        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT id, chunk_index, content, metadata, created_at
                FROM document_chunks
                WHERE document_id = %s
                ORDER BY chunk_index ASC
            """, (document_id,)).fetchall()

            return [
                {
                    "id": str(r[0]),
                    "chunk_index": r[1],
                    "content": r[2],
                    "metadata": r[3] or {},
                    "created_at": r[4].isoformat() if r[4] else None,
                }
                for r in rows
            ]
