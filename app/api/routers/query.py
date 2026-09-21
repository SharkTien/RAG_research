"""
Query Router
============
Triển khai endpoint POST /query theo đúng đặc tả kỹ thuật trong SUBJECT.md:
- Nhận question
- Thực hiện RAG (Retrieval-Augmented Generation)
- Trả về answer + danh sách sources trích dẫn bắt buộc
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.query import QueryRequest, QueryResponse
from app.services.rag_service import RagService
from app.api.dependencies import get_rag_service

router = APIRouter(tags=["query"])
logger = logging.getLogger("query_router")


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Truy vấn hỏi đáp thông minh dựa trên tài liệu đã nạp (RAG)",
)
def query_documents(
    payload: QueryRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> QueryResponse:
    """
    API tiếp nhận câu hỏi từ người dùng:
    1. Vector hóa câu hỏi bằng NVIDIA NIM Embedding
    2. Vector Search lấy Top-K chunks liên quan nhất từ PostgreSQL pgvector
    3. Ghép context và gọi NVIDIA NIM LLM sinh câu trả lời
    4. Trả về answer cùng danh sách sources trích dẫn cụ thể
    """
    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Câu hỏi (question) không được để trống",
        )

    try:
        result = rag_service.answer_question(
            question=payload.question,
            top_k=payload.top_k or 5,
            document_id=payload.document_id,
        )
        return QueryResponse(**result)
    except Exception as exc:
        logger.error("Lỗi khi xử lý POST /query: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi trong quá trình xử lý câu hỏi: {str(exc)}",
        )
