from typing import List, Optional, Any
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi cần tra cứu từ tài liệu")
    top_k: Optional[int] = Field(5, description="Số lượng chunks tối đa trích xuất")
    document_id: Optional[str] = Field(None, description="Lọc theo document_id cụ thể (tùy chọn)")


class SourceCitation(BaseModel):
    file_name: str
    chunk_id: str
    page: Optional[Any] = None
    similarity_score: Optional[float] = None
    snippet: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    total_chunks_retrieved: Optional[int] = 0
    execution_time_seconds: Optional[float] = 0.0
