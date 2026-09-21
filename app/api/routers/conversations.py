import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_conversation_repo, get_rag_service
from app.repositories.conversation_repo import ConversationRepository
from app.services.rag_service import RagService

logger = logging.getLogger("conversations_router")

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default="Hội thoại mới", description="Tiêu đề cuộc trò chuyện")
    id: Optional[str] = Field(default=None, description="Tùy chọn UUID do client khởi tạo")

class UpdateConversationRequest(BaseModel):
    title: str = Field(..., description="Tiêu đề mới của cuộc trò chuyện")

class SendMessageRequest(BaseModel):
    question: str = Field(..., description="Nội dung câu hỏi của người dùng")
    top_k: Optional[int] = Field(default=10, ge=1, le=20, description="Số lượng chunks trích xuất")
    document_id: Optional[str] = Field(default=None, description="ID tài liệu cần giới hạn phạm vi tra cứu")

@router.get("", summary="Lấy danh sách các cuộc hội thoại")
def list_conversations(
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    try:
        return repo.list_conversations()
    except Exception as e:
        logger.error("Lỗi khi lấy danh sách hội thoại: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn cơ sở dữ liệu: {e}")

@router.post("", summary="Tạo cuộc hội thoại mới")
def create_conversation(
    payload: CreateConversationRequest,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    try:
        conv = repo.create_conversation(title=payload.title or "Hội thoại mới", conv_id=payload.id)
        return conv
    except Exception as e:
        logger.error("Lỗi khi tạo cuộc hội thoại: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi tạo cuộc hội thoại: {e}")

@router.get("/{conversation_id}", summary="Lấy chi tiết và lịch sử tin nhắn của cuộc hội thoại")
def get_conversation_details(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hội thoại")
    messages = repo.get_messages(conversation_id)
    conv["messages"] = messages
    return conv

@router.patch("/{conversation_id}", summary="Đổi tên cuộc hội thoại")
def update_conversation(
    conversation_id: str,
    payload: UpdateConversationRequest,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    success = repo.update_title(conversation_id, payload.title)
    if not success:
        raise HTTPException(status_code=404, detail="Không thể cập nhật cuộc hội thoại")
    return {"message": "Đã cập nhật tiêu đề thành công"}

@router.delete("/{conversation_id}", summary="Xóa cuộc hội thoại")
def delete_conversation(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    success = repo.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không thể xóa cuộc hội thoại")
    return {"message": "Đã xóa cuộc hội thoại thành công"}

@router.post("/{conversation_id}/messages", summary="Gửi câu hỏi và sinh câu trả lời RAG lưu vào DB")
def send_message_in_conversation(
    conversation_id: str,
    payload: SendMessageRequest,
    repo: ConversationRepository = Depends(get_conversation_repo),
    rag_service: RagService = Depends(get_rag_service),
):
    conv = repo.get_conversation(conversation_id)
    if not conv:
        # Tự động tạo conversation nếu ID hợp lệ nhưng chưa có trong DB
        try:
            conv = repo.create_conversation(
                title=payload.question[:50].strip() or "Hội thoại mới",
                conv_id=conversation_id
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Cuộc hội thoại không tồn tại")

    query_text = payload.question.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống")

    # 1. Lưu tin nhắn User vào CSDL
    user_msg = repo.add_message(
        conv_id=conversation_id,
        role="user",
        content=query_text
    )

    # Nếu tên hội thoại đang là mặc định, tự động cập nhật tiêu đề theo câu hỏi đầu tiên
    if conv.get("title") in ("Hội thoại mới", "New Chat", "", None):
        clean_title = query_text[:50].strip()
        repo.update_title(conversation_id, clean_title)

    # 2. Xử lý RAG với Hybrid Search + LLM Synthesis
    try:
        rag_res = rag_service.answer_question(
            question=query_text,
            top_k=payload.top_k or 10,
            document_id=payload.document_id
        )
        answer_text = rag_res.get("answer", "")
        sources = rag_res.get("sources", [])
        retrieved_chunks = rag_res.get("retrieved_chunks", [])
    except Exception as exc:
        logger.error("Lỗi khi xử lý RAG: %s", exc, exc_info=True)
        answer_text = f"Xin lỗi, đã xảy ra lỗi khi tìm kiếm thông tin: {str(exc)}"
        sources = []
        retrieved_chunks = []

    # 3. Lưu tin nhắn Assistant vào CSDL
    assistant_msg = repo.add_message(
        conv_id=conversation_id,
        role="assistant",
        content=answer_text,
        sources=sources,
        retrieved_chunks=retrieved_chunks
    )

    return {
        "user_message": user_msg,
        "assistant_message": assistant_msg,
        "answer": answer_text,
        "sources": sources,
        "retrieved_chunks": retrieved_chunks
    }
