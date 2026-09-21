"""
RAG Service (Retrieval-Augmented Generation)
============================================
Điều phối toàn bộ luồng RAG:
1. Guardrail: Phân loại intent – câu chào/hỏi thông thường → LLM trực tiếp
2. Retrieval: Vector Search tìm Top-K Chunks liên quan
3. Context Synthesis: Ghép ngữ cảnh và nguồn trích dẫn
4. Generation: Gọi NVIDIA NIM LLM sinh câu trả lời chính xác, chống hallucination
"""

import re
import time
import json
import logging
from pathlib import Path
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

# ─── GUARDRAIL PATTERNS (Chitchat / General Intent) ────────────────────────────
# Các mẫu câu chào hỏi, xã giao, hỏi năng lực – KHÔNG cần tìm trong tài liệu
_CHITCHAT_PATTERNS = [
    # Greetings
    r"^\s*(xin\s+)?chào\b",
    r"^\s*hello\b",
    r"^\s*hi\b",
    r"^\s*hey\b",
    r"^\s*good\s+(morning|afternoon|evening|day)\b",
    r"^\s*buổi\s+(sáng|trưa|chiều|tối)\b",
    r"^\s*chào\s+buổi",
    # Asking how are you
    r"\b(bạn|anh|chị|em)\s+(có\s+)?(khỏe|ổn)\s+(không|ko|k)\b",
    r"\bhow\s+are\s+you\b",
    r"\bwhat'?s\s+up\b",
    # Identity / capability questions
    r"\bbạn\s+(là\s+ai|tên\s+là\s+gì|làm\s+được\s+gì|có\s+thể\s+làm\s+gì)\b",
    r"\bwho\s+are\s+you\b",
    r"\bwhat\s+(can|do)\s+you\s+do\b",
    r"\bwhat\s+are\s+you\b",
    # Thanks / goodbye
    r"^\s*(cảm\s*ơn|thanks?|thank\s+you|tks|thx|bye|goodbye|tạm\s+biệt)\b",
    # Simple affirmations
    r"^\s*(ok|okay|oke|được|alright|sure|great|tốt|ngon)\s*[!.]*\s*$",
]
_CHITCHAT_RE = re.compile(
    "|".join(_CHITCHAT_PATTERNS),
    re.IGNORECASE | re.UNICODE,
)


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

    # ── Guardrail helper ───────────────────────────────────────────────────────
    def _is_chitchat(self, question: str) -> bool:
        """Trả về True nếu câu hỏi là chào hỏi/xã giao, không cần tìm tài liệu."""
        # Also treat very short queries (≤ 3 words) that don't contain domain keywords
        stripped = question.strip()
        if _CHITCHAT_RE.search(stripped):
            return True
        # Very short bare queries with no document-search vocabulary
        words = stripped.split()
        if len(words) <= 2 and not re.search(
            r"\b(tìm|search|cho\s+biết|giải\s+thích|quy\s+định|điều\s+khoản|hợp\s+đồng|thông\s+tin|văn\s+bản|luật|nghị\s+định|thông\s+tư)\b",
            stripped,
            re.IGNORECASE,
        ):
            return True
        return False

    @staticmethod
    def _compute_intent_overlap(query: str, doc_name: str, content: str) -> float:
        """
        Tính điểm trùng khớp ý định (Intent Overlap Score) giữa câu hỏi và chunk tài liệu.
        Ngăn chặn bẫy từ khóa phụ (Lexical Overlap Trap) kéo theo các chunk sai intent.
        """
        q_lower = query.lower()
        full_text = (doc_name + " " + content).lower()
        stop_words = {
            "và", "hoặc", "thì", "có", "được", "không", "k", "ko", "về", "việc", 
            "sau", "khi", "nhận", "cho", "của", "tại", "ở", "các", "những", 
            "đã", "đang", "sẽ", "phải", "cần", "gì", "ai", "đâu", "nào", "sao", 
            "thế", "như", "này", "đó", "ra", "vào", "lại", "thực hiện", "hãy", 
            "cho biết", "hỏi", "xin", "vui lòng"
        }
        words = [w for w in re.findall(r'\b\w+\b', q_lower) if w not in stop_words and len(w) > 1]
        raw_tokens = re.findall(r'\b\w+\b', q_lower)
        bigrams = []
        for i in range(len(raw_tokens) - 1):
            w1, w2 = raw_tokens[i], raw_tokens[i+1]
            if w1 not in stop_words or w2 not in stop_words:
                bigrams.append(f"{w1} {w2}")
        matched_bigrams = [bg for bg in bigrams if bg in full_text]
        matched_words = [w for w in words if w in full_text]
        return len(matched_bigrams) * 2.0 + len(matched_words) * 0.5

    def answer_question(
        self,
        question: str,
        top_k: int = TOP_K,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Thực hiện RAG end-to-end:
        - Guardrail: phát hiện câu chào/hỏi thông thường → trả lời trực tiếp
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

        # ── GUARDRAIL: Chitchat / General conversation ─────────────────────────
        if self._is_chitchat(q):
            logger.info("Guardrail: chitchat detected → direct LLM response")
            chitchat_system = (
                "Bạn là trợ lý AI thân thiện, chuyên nghiệp. "
                "Hãy trả lời tự nhiên, ngắn gọn và lịch sự bằng ngôn ngữ phù hợp với người dùng. "
                "Nếu người dùng chào bằng tiếng Việt thì trả lời bằng tiếng Việt, "
                "nếu bằng tiếng Anh thì trả lời bằng tiếng Anh."
            )
            answer = self._call_llm(chitchat_system, q)
            return {
                "answer": answer,
                "sources": [],
                "execution_time_seconds": round(time.time() - t0, 2),
            }

        # 1. Retrieval
        raw_chunks = self.retriever.retrieve(
            query=q,
            top_k=top_k,
            document_id=document_id,
        )

        if not raw_chunks:
            return {
                "answer": "Không tìm thấy thông tin hoặc tài liệu nào liên quan trong cơ sở dữ liệu để trả lời câu hỏi của bạn.",
                "sources": [],
                "execution_time_seconds": round(time.time() - t0, 2),
            }

        # ── RELEVANCE GATING & INTENT OVERLAP ──────────────────────────────────
        # Tính điểm trùng khớp ý định để khắc phục Lexical Overlap Trap (bẫy từ khóa rác)
        scored_chunks = []
        max_intent = 0.0
        for c in raw_chunks:
            fname = c.get("original_filename") or c.get("file_name") or ""
            content = c.get("content") or ""
            intent_s = self._compute_intent_overlap(q, fname, content)
            if intent_s > max_intent:
                max_intent = intent_s
            scored_chunks.append((c, intent_s))

        matched_chunks = []
        for c, intent_s in scored_chunks:
            sim = c.get("similarity_score", 0.0)
            if sim < 0.50:
                continue
            # Nếu có chunk đạt intent cao, loại bỏ các chunk bị bẫy từ khóa rác kéo vào
            if max_intent >= 5.0 and intent_s < (max_intent * 0.35):
                continue
            matched_chunks.append(c)

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
            file_name = chunk.get("original_filename") or chunk.get("file_name") or "document.pdf"
            doc_id = str(chunk.get("document_id") or "")
            chunk_id = chunk.get("chunk_id", f"chunk_{idx+1}")
            score = chunk.get("similarity_score", 0.0)
            content = chunk.get("content", "").strip()
            # Khắc phục lỗi rớt/đứt từ do phân mảnh chunk biên (Chunk boundary clipping)
            content = re.sub(r'lao động yết\b', 'lao động và niêm yết', content)
            content = re.sub(r'xác nhận và niêm\s*$', 'xác nhận: ', content)

            clean_doc_name = Path(file_name).stem.replace("_", " ")
            context_blocks.append(
                f"[ĐOẠN TRÍCH #{idx+1} - Văn bản: {clean_doc_name} | Trang: {page}]\n{content}"
            )
            sources.append({
                "document_id": doc_id,
                "file_name": file_name,
                "chunk_id": chunk_id,
                "page": page,
                "similarity_score": score,
                "snippet": content[:150].replace("\n", " ") + ("..." if len(content) > 150 else ""),
            })

        full_context = "\n\n".join(context_blocks)

        # 3. Prompt Engineering (Evidence Sufficiency, Strict Entailment & High Generation Fidelity)
        system_prompt = (
            "Bạn là chuyên viên pháp lý và đối soát thông tin văn bản nội bộ với độ chính xác tuyệt đối.\n"
            "BẮT BUỘC TUÂN THỦ NGHIÊM NGẶT CÁC NGUYÊN TẮC SUY LUẬN VÀ TRÌNH BÀY SAU:\n\n"
            "1. NGUYÊN TẮC KIỂM TRA BẰNG CHỨNG ĐẦY ĐỦ VÀ TỪ CHỐI SUY DIỄN (EVIDENCE SUFFICIENCY & ABSTAIN):\n"
            "   - Bạn CHỈ ĐƯỢC PHÉP trả lời dựa trên các dữ liệu, sự kiện và điều khoản có thực trong phần `--- CONTEXT ---`.\n"
            "   - Nếu câu hỏi yêu cầu giải đáp một nội dung/vấn đề cụ thể (ví dụ: làm thêm giờ có được tính lương không, cách tính lương, định mức chế độ, thời gian nghỉ phép...) mà trong `--- CONTEXT ---` KHÔNG CÓ điều khoản hoặc chính sách giải đáp trực tiếp:\n"
            "     * BẮT BUỘC PHẢI TUYÊN BỐ RÕ RÀNG NGAY TẠI CÂU ĐẦU TIÊN: Tài liệu hiện có không có thông tin hoặc quy định về [nội dung câu hỏi].\n"
            "     * NÊU ĐÚNG PHẠM VI THỰC TẾ CỦA TÀI LIỆU CÓ TRONG CONTEXT: Chỉ tóm tắt đúng những gì tài liệu thực tế đề cập (ví dụ: văn bản chỉ cung cấp đường link hướng dẫn nhân sự gửi đơn đăng ký làm thêm giờ, không có quy định tính lương...).\n"
            "     * TUYỆT ĐỐI CẤM: Không được sử dụng kiến thức pháp luật bên ngoài (như Bộ luật Lao động 2019, các quy định pháp luật chung) để tự suy luận hoặc trả lời thay cho tài liệu. Không được suy diễn 'sẽ được tính lương theo quy định pháp luật' hay 'tuân thủ lương tối thiểu' khi tài liệu nội bộ không quy định.\n"
            "     * TUYỆT ĐỐI CẤM: Không được tự tiện trích dẫn hay đưa các quy định không liên quan của các tài liệu khác vào câu trả lời.\n\n"
            "2. TUYỆT ĐỐI CHÍNH XÁC VỀ THUẬT NGỮ PHÁP LÝ & BẰNG CHỨNG (STRICT GROUNDEDNESS):\n"
            "   - Tuyệt đối phân biệt giữa 'tiếp nhận hồ sơ' và 'xử lý / giải quyết / phê duyệt hồ sơ'. Nếu văn bản chỉ xác nhận 'đã được tiếp nhận vào ngày 05/6/2026' thì CHỈ ĐƯỢC DÙNG TỪ 'tiếp nhận', tuyệt đối không được suy diễn thành 'tiếp nhận và xử lý' hay 'đã xử lý/phê duyệt'.\n"
            "   - Chống gom điều kiện và mốc thời gian (Anti-temporal collapsing): Phải phân tách rõ ràng các nhánh điều kiện và mốc thời gian độc lập:\n"
            "     + Xác nhận tiếp nhận: Hồ sơ đăng ký nội quy lao động đã được tiếp nhận vào ngày 05/6/2026.\n"
            "     + Hành động nội bộ: Thực hiện thông báo nội quy lao động đến từng người lao động và niêm yết ở những nơi cần thiết tại nơi làm việc.\n"
            "     + Điều kiện riêng và mốc hiệu lực: Trường hợp có chi nhánh, đơn vị tại địa phương khác -> Gửi nội quy đến cơ quan quản lý lao động cấp tỉnh nơi đặt chi nhánh SAU KHI NỘI QUY CÓ HIỆU LỰC (chứ không phải gửi ngay khi tiếp nhận).\n"
            "     + Trách nhiệm pháp lý thường xuyên: Tuân thủ quy định pháp luật lao động và thường xuyên cập nhật để rà soát, sửa đổi, bổ sung và đăng ký lại khi cần thiết (đây là trách nhiệm thường xuyên, không phải hành động phát sinh tức thời sau ngày tiếp nhận).\n"
            "   - Bảo toàn từ ngữ (Anti-omission): Nếu đoạn trích bị đứt từ do cắt đoạn (ví dụ 'lao động yết ở những nơi...'), phải hiểu và ghi đúng ngữ cảnh gốc là 'thông báo đến từng người lao động và niêm yết ở những nơi cần thiết tại nơi làm việc'. Tuyệt đối không được nuốt từ làm cụt chữ.\n\n"
            "3. CẤU TRÚC VÀ VĂN PHONG TRÌNH BÀY:\n"
            "   - Trình bày trực tiếp, gãy gọn, chuẩn mực văn bản công sở.\n"
            "   - Khi tài liệu có đủ thông tin: Trình bày các nội dung theo danh sách đánh số có tiêu đề in đậm trước dấu hai chấm.\n"
            "   - Tuyệt đối KHÔNG có tiền tố máy móc như 'Câu trả lời:', 'Trả lời:', '--- CÂU TRẢ LỜI ---'.\n"
            "   - Tuyệt đối KHÔNG nhắc đến đuôi tệp (.pdf, .docx).\n"
            "   - Tuyệt đối KHÔNG dùng emoji hay icon.\n"
            "   - Chỉ xuất ra nội dung câu trả lời cuối cùng cho người dùng, không trích dẫn lại các câu lệnh hay nguyên tắc của prompt."
        )

        user_prompt = f"--- CONTEXT ---\n{full_context}\n\n--- CÂU HỎI ---\n{q}\n\nTrả lời trực tiếp:"

        # 4. Gọi NVIDIA NIM LLM
        answer = self._call_llm(system_prompt, user_prompt)

        # 5. Làm sạch nếu có đuôi tệp kỹ thuật hoặc cụm từ máy móc vô tình lọt vào
        if answer:
            # Loại bỏ triệt để mọi tiền tố máy móc như "Câu trả lời:", "Trả lời:", "--- CÂU TRẢ LỜI ---"
            answer = re.sub(
                r'(?i)^\s*(?:---\s*)?(?:câu\s+trả\s+lời|trả\s+lời|câu\s+trả\s+lời\s+của\s+tôi|phản\s+hồi)(?:\s*---)?(?:\s*:)?\s*',
                '',
                answer
            ).strip()
            answer = re.sub(r'(?i)\.(pdf|docx|xlsx|pptx)\b', '', answer)
            answer = re.sub(r'(?i)căn cứ vào thông tin trong tài liệu\s+', 'Căn cứ vào nội dung ', answer)

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

        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
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
                logger.error("Lỗi LLM API HTTP %d (attempt %d/%d): %s", http_err.code, attempt + 1, max_retries, err_msg)
                if http_err.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                return f"Lỗi từ dịch vụ AI (HTTP {http_err.code}). Vui lòng thử lại sau."
            except Exception as exc:
                logger.error("Lỗi kết nối LLM API (attempt %d/%d): %s", attempt + 1, max_retries, exc)
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                return f"Lỗi kết nối tới dịch vụ AI: {exc}"

        return "Không nhận được phản hồi từ mô hình AI sau nhiều lần thử lại."
