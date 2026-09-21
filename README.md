# NTC Document RAG — ingestion MVP

## Chạy

```bash
# Cấu hình các secret và port trong .env
docker compose up -d --build
```

- UI: http://localhost:41873
- MinIO Console: http://localhost:41901
- Health: http://localhost:41873/health

Tên container được Docker Compose đặt theo project để có thể chạy song song với các stack khác. UI dùng Vite + React + Tailwind và mặc định chạy tại port host `41873`; MinIO Console chạy tại `41901`. Có thể đổi bằng `APP_PORT` và `MINIO_CONSOLE_PORT` trong `.env`. Tài liệu upload tối đa 200 MB/file, được lưu tại bucket `ntc-documents` dưới prefix `raw/<document-id>/`; PostgreSQL chỉ lưu metadata, checksum SHA-256 và trạng thái ingestion.

Worker `ntc_document_rag_worker` xử lý tài liệu từ hàng đợi PostgreSQL. Nếu worker bị restart, tài liệu ở trạng thái `queued` vẫn được xử lý tiếp. Với môi trường production, đặt `APP_ENV=production`, `COOKIE_SECURE=true` và chạy sau reverse proxy HTTPS.

Thư mục `documents/NTC_doc` là nguồn tài liệu ban đầu; MVP này chưa tự động nạp hàng loạt để tránh upload ngoài ý muốn. Bước tiếp theo có thể thêm job bulk-ingestion có dry-run, dedup theo SHA-256 và trạng thái xử lý chunk/embedding.

## OCR tiếng Việt và định tuyến model

Pipeline mặc định dùng `DOCUMENT_PARSER_ENGINE=auto`:

1. PDF có lớp text: Docling đọc text trực tiếp, không OCR và không gọi LLM.
2. PDF scan/JPG/PNG: render ở 180 DPI, chạy Tesseract `vie+eng` song song theo trang.
3. Nếu Tesseract lỗi: fallback sang PP-OCRv6 GPU local tại `http://host.docker.internal:8012`.
4. Nếu confidence Tesseract dưới `0.93`: sửa lỗi OCR bằng Qwen local tại cổng `8027`.
5. Nếu Qwen local lỗi và có `NGC_API_KEY`: fallback NVIDIA NIM hosted API; nếu cả hai lỗi thì giữ nguyên kết quả rule-based.

Kết quả lưu cả `raw_ocr_text` và `ocr_text` sau hậu xử lý. Metadata có parser, confidence, thời gian extraction và provider normalization để theo dõi chất lượng/latency.

Các chế độ vận hành:

- `DOCUMENT_PARSER_ENGINE=auto`: khuyến nghị cho luồng tiếng Việt hỗn hợp.
- `DOCUMENT_PARSER_ENGINE=tesseract`: ép OCR Tesseract trực tiếp.
- `DOCUMENT_PARSER_ENGINE=ppocr`: ép PP-OCRv6 local, phù hợp khi cần orientation/unwarping.
- `DOCUMENT_PARSER_ENGINE=ragflow`: DeepDoc cho tài liệu có layout/bảng phức tạp.
- `DOCUMENT_PARSER_ENGINE=docling`: pipeline Docling đầy đủ.
- `SEMANTIC_NORMALIZER=auto|local|nvidia|none`: chọn chiến lược sửa OCR/semantic.

Các biến tuning chính:

```dotenv
DOCLING_OCR_LANG=vie,eng
DOCLING_TESSERACT_PSM=3
LOCAL_OCR_DPI=180
TESSERACT_PAGE_CONCURRENCY=4
SEMANTIC_NORMALIZER=auto
SEMANTIC_NORMALIZE_OCR_ONLY=true
SEMANTIC_OCR_CONFIDENCE_GATE=0.93
```

Kiểm tra sau khi chạy:

```bash
docker compose ps --all
docker compose logs --tail=200 ntc_document_rag_worker
curl -fsS http://localhost:41873/health
```

Chi tiết quyết định kỹ thuật và kế hoạch benchmark nằm tại `Tinh_hoa_van_hoa/OCR_DEPLOYMENT.md`.
