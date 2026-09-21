"""
RAG Service (Retrieval-Augmented Generation)
============================================
Điều phối toàn bộ luồng RAG:
1. Retrieval: Vector Search tìm Top-K Chunks liên quan
2. Context Synthesis: Ghép ngữ cảnh và nguồn trích dẫn
3. Generation: Gọi NVIDIA NIM LLM sinh câu trả lời chính xác, chống hallucination
"""

import time
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from app.core.config import (
    NGC_API_KEY,
    NIM_BASE_URL,
    LLM_RAG_MODEL,
    TOP_K,
)
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger("rag_service")


class RagService:
    def __init__(
        self,
        retriever: RetrievalService,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.retriever = retriever
        self.api_key = (api_key or NGC_API_KEY or "").strip()
        self.base_url = (base_url or NIM_BASE_URL or "https://integrate.api.nvidia.com/v1").rstrip("/")
        self.model = model or LLM_RAG_MODEL or "meta/llama-3.3-70b-instruct"

    def answer_question(
        self,
        question: str,
        top_k: int = TOP_K,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Thực hiện RAG end-to-end:
        - Retrieval chunks
        - Gọi LLM sinh câu trả lời
        - Trả về câu trả lời kèm danh sách nguồn trích dẫn bắt buộc
        """
        t0 = time.time()
        q = question.strip()
        if not q:
            return {
                "answer": "Vui lòng nhập câu hỏi cần tra cứu.",
                "sources": [],
                "execution_time_seconds": 0.0,
            }

        # 1. Retrieval
        matched_chunks = self.retriever.retrieve(
            query=q,
            top_k=top_k,
            document_id=document_id,
        )

        if not matched_chunks:
            return {
                "answer": "Không tìm thấy thông tin hoặc tài liệu nào liên quan trong cơ sở dữ liệu để trả lời câu hỏi của bạn.",
                "sources": [],
                "execution_time_seconds": round(time.time() - t0, 2),
            }

        # 2. Xây dựng Context và danh sách Sources
        context_blocks = []
        sources = []

        for idx, chunk in enumerate(matched_chunks):
            meta = chunk.get("metadata") or {}
            page = meta.get("page") or meta.get("page_no") or "?"
            file_name = chunk.get("file_name", "document.pdf")
            chunk_id = chunk.get("chunk_id", f"chunk_{idx+1}")
            score = chunk.get("similarity_score", 0.0)
            content = chunk.get("content", "").strip()

            context_blocks.append(
                f"[TÀI LIỆU #{idx+1} - Nguồn: {file_name} | Trang: {page}]\n{content}"
            )
            sources.append({
                "file_name": file_name,
                "chunk_id": chunk_id,
                "page": page,
                "similarity_score": score,
                "snippet": content[:150].replace("\n", " ") + ("..." if len(content) > 150 else ""),
            })

        full_context = "\n\n".join(context_blocks)

        # 3. Prompt Engineering (Tuân thủ RULES.md: Anti-hallucination & Untrusted Input)
        system_prompt = (
            "Bạn là trợ lý AI chuyên nghiệp về tư vấn và giải đáp thông tin từ tài liệu nội bộ.\n"
            "NGUYÊN TẮC BẮT BUỘC:\n"
            "1. CHỈ sử dụng thông tin có trong phần CONTEXT được cung cấp dưới đây để trả lời.\n"
            "2. Tuyệt đối KHÔNG tự bịa đặt, suy đoán hoặc thêm thắt thông tin ngoài CONTEXT.\n"
            "3. Nếu CONTEXT không chứa câu trả lời, hãy nêu rõ: 'Dựa trên tài liệu được cung cấp, không có thông tin về vấn đề này.'\n"
            "4. Trả lời bằng tiếng Việt lịch sự, gãy gọn, nêu rõ các điều khoản, số ngày, quy trình cụ thể (nếu có).\n"
            "5. Đính kèm chú thích các phần trích dẫn từ tài liệu."
        )

        user_prompt = f"--- CONTEXT ---\n{full_context}\n\n--- CÂU HỎI ---\n{q}\n\n--- CÂU TRẢ LỜI ---"

        # 4. Gọi NVIDIA NIM LLM
        answer = self._call_llm(system_prompt, user_prompt)
        elapsed = round(time.time() - t0, 2)

        return {
            "answer": answer,
            "sources": sources,
            "total_chunks_retrieved": len(matched_chunks),
            "execution_time_seconds": elapsed,
        }

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Gửi request tới OpenAI-compatible chat completions endpoint của NVIDIA NIM."""
        if not self.api_key:
            return (
                "Lưu ý: NGC_API_KEY chưa được cấu hình, không thể kết nối tới mô hình AI để sinh câu trả lời.\n"
                "Dữ liệu liên quan đã được tìm thấy trong danh sách sources bên dưới."
            )

        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 1500,
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "MiniRAG-RagService/1.0",
        }

        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                choices = resp_json.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
                return "Không nhận được phản hồi từ mô hình AI."
        except urllib.error.HTTPError as http_err:
            err_msg = http_err.read().decode("utf-8", errors="ignore")
            logger.error("Lỗi LLM API HTTP %d: %s", http_err.code, err_msg)
            return f"Lỗi từ dịch vụ AI (HTTP {http_err.code}). Vui lòng thử lại sau."
        except Exception as exc:
            logger.error("Lỗi kết nối LLM API: %s", exc)
            return f"Lỗi kết nối tới dịch vụ AI: {exc}"
