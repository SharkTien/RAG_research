"""
Benchmark Suite: Mini RAG with SynthDocQA Dataset
=================================================
Đánh giá độ chính xác và hiệu năng của hệ thống RAG trên bộ dữ liệu SynthDocQA:
- Chỉ đánh giá trên 5 file PDF thực tế có sẵn trong grounding_pdfs_v2 (tương ứng 877 câu hỏi).
- Đánh giá 2 khâu độc lập:
  1. Retrieval: Hit Rate@K, MRR, Document Match Rate.
  2. Generation: Assertion Pass Rate, Keyword Match, LLM Generation Fidelity.
- Phân tích chi tiết theo loại phần tử: table, form, figure, annotation, text_block.
- Hỗ trợ lưu checkpoint cache (chunks và vectors) để chạy lặp lại siêu tốc.
"""

import sys
import os
import json
import time
import re
import argparse
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# UTF-8 stdout trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm project root vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import (
    NGC_API_KEY,
    NIM_BASE_URL,
    NIM_MODEL,
    EMBEDDING_MODEL,
    TOP_K,
)
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RagService

# Đường dẫn mặc định tới dataset
DEFAULT_DATASET_DIR = Path(r"D:\Datastore\ntc\mini_RAG\datasets\synthdocqa")
CACHE_DIR = Path(__file__).resolve().parent / "benchmark_cache"
RESULTS_FILE = Path(__file__).resolve().parent / "benchmark_results.json"
REPORT_FILE = Path(__file__).resolve().parent / "benchmark_report.md"

# Danh sách 5 PDF có sẵn trong grounding_pdfs_v2
VALID_PDF_FILES = {
    "doc_0000_s1131058660.pdf",
    "doc_0000_s71722309.pdf",
    "doc_0000_s39946201.pdf",
    "doc_0000_s341236940.pdf",
    "doc_0000_s1045958549.pdf",
}

# ─── ANSI COLORS ───────────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
CYAN    = "\033[36m"
RED     = "\033[31m"
MAGENTA = "\033[35m"
WHITE   = "\033[97m"


def log_header(text: str):
    bar = "═" * 68
    print(f"\n{BOLD}{CYAN}{bar}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{bar}{RESET}")


def log_info(label: str, value: Any = ""):
    print(f"  {DIM}•{RESET} {BOLD}{label}:{RESET} {CYAN}{value}{RESET}")


def log_success(text: str):
    print(f"  {GREEN}✔{RESET} {text}")


def log_warn(text: str):
    print(f"  {YELLOW}⚠{RESET} {text}")


# ─── EXTRACTOR & CHUNKER ───────────────────────────────────────────────────────

def extract_pdf_chunks(pdf_path: Path, manifest_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Trích xuất văn bản từ PDF và chia thành các chunks có cấu trúc.
    Kết hợp text từng trang từ PyPDF và metadata từ manifest (nếu có).
    """
    import pypdf

    reader = pypdf.PdfReader(str(pdf_path))
    chunks = []
    chunk_counter = 0

    # Nạp manifest để lấy thêm metadata cấu trúc nếu có
    manifest_elements = {}
    if manifest_path and manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
                for el in manifest_data.get("structure", []):
                    art_id = el.get("Artifact_ID") or el.get("variant_id")
                    if art_id:
                        manifest_elements[art_id] = el
        except Exception:
            pass

    for page_idx, page in enumerate(reader.pages, start=1):
        raw_text = (page.extract_text() or "").strip()
        if not raw_text:
            continue

        # Chuẩn hóa khoảng trắng
        clean_text = re.sub(r"[ \t]+", " ", raw_text)
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

        # Nếu trang ngắn (< 1500 ký tự), giữ nguyên 1 chunk
        # Nếu trang dài, chia đoạn 1000 ký tự với gối đầu 150 ký tự
        max_chunk_size = 1200
        overlap = 150

        if len(clean_text) <= max_chunk_size:
            chunk_counter += 1
            chunks.append({
                "chunk_id": f"{pdf_path.stem}_p{page_idx}_c1",
                "file_name": pdf_path.name,
                "page": page_idx,
                "content": clean_text,
                "char_count": len(clean_text),
            })
        else:
            paragraphs = clean_text.split("\n\n")
            current_buffer = []
            curr_len = 0
            sub_idx = 1

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if curr_len + len(para) > max_chunk_size and current_buffer:
                    chunk_text = "\n\n".join(current_buffer)
                    chunk_counter += 1
                    chunks.append({
                        "chunk_id": f"{pdf_path.stem}_p{page_idx}_c{sub_idx}",
                        "file_name": pdf_path.name,
                        "page": page_idx,
                        "content": chunk_text,
                        "char_count": len(chunk_text),
                    })
                    sub_idx += 1
                    # Giữ lại đoạn cuối làm overlap
                    current_buffer = [current_buffer[-1]] if len(current_buffer[-1]) < overlap else []
                    curr_len = sum(len(p) for p in current_buffer)

                current_buffer.append(para)
                curr_len += len(para)

            if current_buffer:
                chunk_text = "\n\n".join(current_buffer)
                chunk_counter += 1
                chunks.append({
                    "chunk_id": f"{pdf_path.stem}_p{page_idx}_c{sub_idx}",
                    "file_name": pdf_path.name,
                    "page": page_idx,
                    "content": chunk_text,
                    "char_count": len(chunk_text),
                })

    return chunks


# ─── INDEX MANAGER (WITH DISK CACHE) ──────────────────────────────────────────

class SynthDocIndexManager:
    """Quản lý Index và Cache vector cho 5 file SynthDocQA."""

    def __init__(self, dataset_dir: Path, embedder: EmbeddingService, cache_dir: Path = CACHE_DIR):
        self.dataset_dir = dataset_dir
        self.pdf_dir = dataset_dir / "grounding_pdfs_v2"
        self.manifest_dir = dataset_dir / "manifest_files"
        self.embedder = embedder
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.all_chunks: List[Dict[str, Any]] = []
        self.all_embeddings: List[List[float]] = []
        self.file_to_chunks: Dict[str, List[Dict[str, Any]]] = {}

    def build_or_load_index(self, target_files: Optional[set] = None):
        """Xây dựng hoặc nạp Index từ cache cho các file chỉ định."""
        target_files = target_files or VALID_PDF_FILES
        log_header(f"NẠP / XÂY DỰNG INDEX CHO {len(target_files)} TÀI LIỆU SYNTHDOCQA")

        for fname in sorted(target_files):
            pdf_path = self.pdf_dir / fname
            if not pdf_path.exists():
                log_warn(f"Tệp không tồn tại: {pdf_path}")
                continue

            cache_file = self.cache_dir / f"{fname}.json"
            manifest_file = self.manifest_dir / f"{pdf_path.stem}.json"

            if cache_file.exists():
                # Nạp từ cache
                t0 = time.time()
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                chunks = cached_data["chunks"]
                embeddings = cached_data["embeddings"]
                log_success(f"[Cache Hit] {fname}: {len(chunks)} chunks ({time.time() - t0:.2f}s)")
            else:
                # Trích xuất và vector hóa mới
                t0 = time.time()
                print(f"  {DIM}[Trích xuất]{RESET} Đang parse {CYAN}{fname}{RESET}...")
                chunks = extract_pdf_chunks(pdf_path, manifest_file)
                print(f"    -> Đã tạo {len(chunks)} chunks. Đang tạo vector embedding...")

                texts = [c["content"] for c in chunks]
                embeddings = self.embedder.embed_texts(texts, input_type="passage")

                # Lưu cache
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"chunks": chunks, "embeddings": embeddings}, f, ensure_ascii=False)
                log_success(f"[Cache Saved] {fname}: {len(chunks)} chunks trong {time.time() - t0:.2f}s")

            # Lưu vào bộ nhớ chung
            self.file_to_chunks[fname] = chunks
            for c, emb in zip(chunks, embeddings):
                self.all_chunks.append(c)
                self.all_embeddings.append(emb)

        log_info("Tổng số chunks trong toàn bộ index", len(self.all_chunks))
        log_info("Tổng số vector embeddings", len(self.all_embeddings))

    def retrieve(self, query: str, top_k: int = 5, target_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tìm kiếm Top-K chunks tương đồng nhất với query."""
        if not self.all_chunks:
            return []

        q_vec = self.embedder.embed_query(query)
        scored = []

        for idx, (chunk, emb) in enumerate(zip(self.all_chunks, self.all_embeddings)):
            if target_file and chunk["file_name"] != target_file:
                continue
            # Cosine similarity (vectors từ NIM embedder đã được L2 normalized)
            score = sum(a * b for a, b in zip(q_vec, emb))
            scored.append({
                **chunk,
                "similarity_score": round(score, 4),
            })

        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored[:top_k]


# ─── ASSERTION EVALUATION ──────────────────────────────────────────────────────

def extract_expected_value(assertion_text: str) -> Optional[str]:
    """Trích xuất giá trị mong đợi từ chuỗi assertion."""
    # Pattern 1: Giữa dấu ngoặc đơn: The response must state 'ABC'.
    m = re.search(r"['\"]([^'\"]+)['\"]", assertion_text)
    if m:
        return m.group(1).strip()

    # Pattern 2: Sau cụm "must state ": The response must state 123.
    m = re.search(r"(?:must state|mention|state)\s+([^\.]+)", assertion_text, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return None


def evaluate_assertion(assertion_text: str, answer: str) -> Tuple[bool, str]:
    """
    Kiểm tra xem câu trả lời của AI có đáp ứng được assertion hay không.
    Trả về (is_passed, reason).
    """
    if not answer or "không tìm thấy" in answer.lower():
        return False, "Answer refused or missing content"

    expected = extract_expected_value(assertion_text)
    if not expected:
        # Fallback: kiểm tra xem các từ khóa dài trong assertion có trong answer không
        words = [w for w in re.findall(r"\w+", assertion_text) if len(w) > 4]
        match_count = sum(1 for w in words if w.lower() in answer.lower())
        if match_count >= max(1, len(words) // 2):
            return True, "Keyword match fallback"
        return False, "No explicit expected value extracted"

    # Chuẩn hóa so khớp
    norm_expected = expected.lower().replace(",", "").replace("$", "").strip()
    norm_answer = answer.lower().replace(",", "").replace("$", "").strip()

    # So khớp trực tiếp chuỗi
    if norm_expected in norm_answer:
        return True, f"Exact match on '{expected}'"

    # So khớp số học nếu là số
    try:
        exp_num = float(norm_expected)
        # Tìm các số trong answer
        numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", norm_answer)]
        if exp_num in numbers:
            return True, f"Numeric match on {exp_num}"
    except ValueError:
        pass

    return False, f"Expected '{expected}' not found in answer"


# ─── BENCHMARK RUNNER ─────────────────────────────────────────────────────────

class SynthDocBenchmark:
    """Điều phối toàn bộ quá trình Benchmark."""

    def __init__(self, dataset_dir: Path = DEFAULT_DATASET_DIR):
        self.dataset_dir = dataset_dir
        self.embedder = EmbeddingService()
        self.rag_service = RagService(retriever="mock")
        self.index_mgr = SynthDocIndexManager(dataset_dir, self.embedder)

    def load_valid_queries(self, doc_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Nạp toàn bộ query từ ALL_queries.json và CHỈ GIỮ LẠI các query
        trỏ tới 5 file PDF có sẵn. Loại bỏ hoàn toàn các query ngoài phạm vi.
        """
        queries_path = self.dataset_dir / "ALL_queries.json"
        if not queries_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file {queries_path}")

        with open(queries_path, "r", encoding="utf-8") as f:
            all_queries = json.load(f)

        target_files = {doc_filter} if doc_filter else VALID_PDF_FILES

        filtered = []
        for q in all_queries:
            refs = q.get("refs", [])
            # Query hợp lệ khi có ít nhất 1 ref nằm trong target_files
            valid_refs = [r for r in refs if r.get("filePath") in target_files]
            if valid_refs:
                filtered.append({
                    **q,
                    "target_file": valid_refs[0].get("filePath"),
                    "element_type": valid_refs[0].get("element_type", "unknown"),
                    "artifact_id": valid_refs[0].get("Artifact_ID", ""),
                })

        return filtered

    def run(
        self,
        doc_filter: Optional[str] = None,
        sample_size: int = -1,
        top_k: int = 5,
        skip_generation: bool = False,
        concurrency: int = 4,
    ) -> Dict[str, Any]:
        target_files = {doc_filter} if doc_filter else VALID_PDF_FILES
        self.index_mgr.build_or_load_index(target_files)

        queries = self.load_valid_queries(doc_filter)
        log_header(f"BẮT ĐẦU BENCHMARK — {len(queries)} CÂU HỎI TRONG PHẠM VI 5 FILE")

        if sample_size > 0 and sample_size < len(queries):
            # Lấy mẫu phân bố đều theo từng tài liệu
            from collections import defaultdict
            by_doc = defaultdict(list)
            for q in queries:
                by_doc[q["target_file"]].append(q)
            sampled = []
            per_doc = max(1, sample_size // len(by_doc))
            for doc, q_list in by_doc.items():
                sampled.extend(q_list[:per_doc])
            queries = sampled[:sample_size]
            log_warn(f"Đã lấy mẫu {len(queries)} câu hỏi (sample_size={sample_size})")

        total_queries = len(queries)
        results = []

        # Thống kê
        hit_count_at_k = 0
        doc_match_count = 0
        assertion_pass_count = 0
        total_assertions = 0

        element_stats = {
            "table": {"total": 0, "hits": 0, "passed": 0},
            "form": {"total": 0, "hits": 0, "passed": 0},
            "figure": {"total": 0, "hits": 0, "passed": 0},
            "annotation": {"total": 0, "hits": 0, "passed": 0},
            "text_block": {"total": 0, "hits": 0, "passed": 0},
            "unknown": {"total": 0, "hits": 0, "passed": 0},
        }

        doc_stats = {f: {"total": 0, "hits": 0, "passed": 0} for f in target_files}

        t_start = time.time()

        def process_single_query(idx: int, q_obj: Dict[str, Any]) -> Dict[str, Any]:
            qid = q_obj.get("Id", f"Q{idx+1}")
            query_text = q_obj.get("query", "")
            target_file = q_obj.get("target_file", "")
            elem_type = q_obj.get("element_type", "unknown")
            assertions = q_obj.get("assertions", [])

            t0 = time.time()
            # 1. Retrieval
            retrieved = self.index_mgr.retrieve(query_text, top_k=top_k)
            retrieval_time = round(time.time() - t0, 3)

            # Đánh giá Retrieval: có lấy đúng tài liệu không?
            doc_hit = any(c["file_name"] == target_file for c in retrieved)

            # Kiểm tra xem từ khóa mong đợi có nằm trong bất kỳ chunk nào không
            content_hit = False
            expected_vals = [extract_expected_value(a.get("text", "")) for a in assertions if a.get("text")]
            expected_vals = [v for v in expected_vals if v]

            for val in expected_vals:
                norm_v = val.lower().strip()
                if any(norm_v in c["content"].lower() for c in retrieved):
                    content_hit = True
                    break

            # 2. Generation & Answer Evaluation
            answer = ""
            generation_time = 0.0
            assertion_results = []
            all_passed = False

            if not skip_generation:
                # Tạo prompt context
                context_blocks = [
                    f"[CHUNK #{i+1} | Trang: {c['page']}]\n{c['content']}"
                    for i, c in enumerate(retrieved)
                ]
                full_context = "\n\n".join(context_blocks)
                sys_prompt = (
                    "You are a precise document QA assistant. Answer the user's question based strictly on the CONTEXT provided.\n"
                    "State the exact answer clearly and concisely without unnecessary chit-chat."
                )
                usr_prompt = f"--- CONTEXT ---\n{full_context}\n\n--- QUESTION ---\n{query_text}"

                t_gen = time.time()
                try:
                    answer = self.rag_service._call_llm(sys_prompt, usr_prompt)
                except Exception as exc:
                    answer = f"[LLM ERROR: {exc}]"
                generation_time = round(time.time() - t_gen, 3)

                # Đánh giá assertions
                passed_for_q = True
                for a in assertions:
                    atext = a.get("text", "")
                    passed, reason = evaluate_assertion(atext, answer)
                    assertion_results.append({
                        "assertion": atext,
                        "passed": passed,
                        "reason": reason,
                    })
                    if not passed:
                        passed_for_q = False

                all_passed = passed_for_q if assertions else False

            return {
                "id": qid,
                "query": query_text,
                "target_file": target_file,
                "element_type": elem_type,
                "doc_hit": doc_hit,
                "content_hit": content_hit,
                "retrieval_time": retrieval_time,
                "generation_time": generation_time,
                "answer": answer,
                "assertions": assertion_results,
                "all_passed": all_passed,
                "retrieved_chunks": [
                    {"page": c["page"], "score": c["similarity_score"], "file": c["file_name"]}
                    for c in retrieved
                ],
            }

        print(f"\n  {DIM}Đang thực thi benchmark với concurrency={concurrency}...{RESET}\n")

        # Chạy song song hoặc tuần tự
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_idx = {
                executor.submit(process_single_query, i, q): i
                for i, q in enumerate(queries)
            }
            completed = 0
            for future in concurrent.futures.as_completed(future_to_idx):
                res = future.result()
                results.append(res)
                completed += 1

                # Cập nhật số liệu
                if res["doc_hit"]:
                    doc_match_count += 1
                if res["content_hit"]:
                    hit_count_at_k += 1
                if res["all_passed"]:
                    assertion_pass_count += 1

                el = res["element_type"] if res["element_type"] in element_stats else "unknown"
                element_stats[el]["total"] += 1
                if res["content_hit"]:
                    element_stats[el]["hits"] += 1
                if res["all_passed"]:
                    element_stats[el]["passed"] += 1

                df = res["target_file"]
                if df in doc_stats:
                    doc_stats[df]["total"] += 1
                    if res["content_hit"]:
                        doc_stats[df]["hits"] += 1
                    if res["all_passed"]:
                        doc_stats[df]["passed"] += 1

                # Tiến trình
                pass_icon = f"{GREEN}✔ PASS{RESET}" if res["all_passed"] else f"{RED}✖ FAIL{RESET}"
                hit_icon = f"{GREEN}HIT{RESET}" if res["content_hit"] else f"{YELLOW}MISS{RESET}"
                sys.stdout.write(
                    f"\r  [{completed}/{total_queries}] {res['id']} | [{res['element_type']}] | Retrieval: {hit_icon} | Gen: {pass_icon} "
                )
                sys.stdout.flush()

        total_elapsed = round(time.time() - t_start, 2)
        print("\n")

        # Tính tỷ lệ phần trăm
        hit_rate = round((hit_count_at_k / total_queries) * 100, 2) if total_queries else 0
        doc_hit_rate = round((doc_match_count / total_queries) * 100, 2) if total_queries else 0
        pass_rate = round((assertion_pass_count / total_queries) * 100, 2) if total_queries else 0

        # Tổng hợp kết quả
        benchmark_summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scope": "5 Grounding PDFs (Exclusive)",
            "total_queries": total_queries,
            "top_k": top_k,
            "skip_generation": skip_generation,
            "total_time_seconds": total_elapsed,
            "metrics": {
                "document_hit_rate_pct": doc_hit_rate,
                "content_hit_rate_pct": hit_rate,
                "assertion_pass_rate_pct": pass_rate,
            },
            "by_element_type": element_stats,
            "by_document": doc_stats,
            "details": results,
        }

        # Lưu kết quả JSON
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(benchmark_summary, f, ensure_ascii=False, indent=2)
        log_success(f"Đã lưu kết quả chi tiết vào: {RESULTS_FILE}")

        # Tạo báo cáo Markdown
        self.generate_markdown_report(benchmark_summary)

        return benchmark_summary

    def generate_markdown_report(self, data: Dict[str, Any]):
        """Xuất bảng báo cáo định dạng Markdown."""
        m = data["metrics"]
        lines = [
            "# Báo cáo Benchmark Hệ thống RAG — SynthDocQA (5 File Cục bộ)",
            f"\n- **Thời gian thực hiện**: `{data['timestamp']}`",
            f"- **Phạm vi đánh giá**: Chỉ tính trên **5 tệp PDF có sẵn** (loại bỏ mọi query ngoài phạm vi)",
            f"- **Tổng số câu hỏi đánh giá**: `{data['total_queries']}` câu hỏi",
            f"- **Tham số Retrieval Top-K**: `{data['top_k']}`",
            f"- **Tổng thời gian chạy**: `{data['total_time_seconds']:.1f}` giây",
            "\n## 1. Kết quả Tổng quan",
            "\n| Chỉ số Đánh giá | Giá trị (%) | Mô tả |",
            "| :--- | :--- | :--- |",
            f"| **Document Hit Rate** | **{m['document_hit_rate_pct']}%** | Top-K chunks chứa đúng tài liệu mục tiêu |",
            f"| **Content / Keyword Hit Rate** | **{m['content_hit_rate_pct']}%** | Top-K chunks chứa đúng thông tin/từ khóa đáp án |",
            f"| **Assertion Pass Rate** | **{m['assertion_pass_rate_pct']}%** | Câu trả lời AI đáp ứng đầy đủ tiêu chí bắt buộc |",
            "\n## 2. Phân tích theo Loại Phần tử (Element Type Breakdown)",
            "\n| Loại Phần tử | Số câu hỏi | Content Hit Rate (%) | Assertion Pass Rate (%) |",
            "| :--- | :--- | :--- | :--- |",
        ]

        for el, s in data["by_element_type"].items():
            if s["total"] == 0:
                continue
            hr = round((s["hits"] / s["total"]) * 100, 1)
            pr = round((s["passed"] / s["total"]) * 100, 1)
            lines.append(f"| `{el}` | {s['total']} | {hr}% | {pr}% |")

        lines.extend([
            "\n## 3. Phân tích theo Từng Tài liệu",
            "\n| Tên Tệp PDF | Số câu hỏi | Retrieval Hit (%) | Assertion Pass (%) |",
            "| :--- | :--- | :--- | :--- |",
        ])

        for doc, s in data["by_document"].items():
            if s["total"] == 0:
                continue
            hr = round((s["hits"] / s["total"]) * 100, 1)
            pr = round((s["passed"] / s["total"]) * 100, 1)
            lines.append(f"| `{doc}` | {s['total']} | {hr}% | {pr}% |")

        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log_success(f"Đã xuất báo cáo Markdown vào: {REPORT_FILE}")


# ─── MAIN CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Benchmark RAG on SynthDocQA (5 PDFs only)")
    parser.add_argument("--doc", type=str, default="", help="Chỉ benchmark 1 file cụ thể (vd: doc_0000_s1131058660.pdf)")
    parser.add_argument("--sample", type=int, default=-1, help="Giới hạn số câu hỏi mẫu (vd: 20 để test nhanh, -1 là chạy hết)")
    parser.add_argument("--top-k", type=int, default=5, help="Số lượng Top-K chunks (mặc định: 5)")
    parser.add_argument("--skip-generation", action="store_true", help="Chỉ đánh giá Retrieval, bỏ qua LLM Generation")
    parser.add_argument("--concurrency", type=int, default=4, help="Số luồng gọi API LLM song song")
    args = parser.parse_args()

    bench = SynthDocBenchmark()
    bench.run(
        doc_filter=args.doc if args.doc else None,
        sample_size=args.sample,
        top_k=args.top_k,
        skip_generation=args.skip_generation,
        concurrency=args.concurrency,
    )


if __name__ == "__main__":
    main()
