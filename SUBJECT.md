# TECHNICAL TASK — MINI RAG SERVICE & BASIC MLOPS

## 1. Bối cảnh

Team đang phát triển các giải pháp AI có sử dụng dữ liệu, Retrieval-Augmented Generation (RAG), vector search và các AI service.

Trong task này, mục tiêu là xây dựng một **Mini RAG Service** ở mức cơ bản, tập trung vào ba nhóm năng lực chính:

- Data processing.
- AI/RAG integration.
- MLOps cơ bản.

Task không yêu cầu train model từ đầu, không yêu cầu Kubernetes, monitoring stack hoặc các kỹ thuật deployment nâng cao.

---

## 2. Mục tiêu

Xây dựng một service có khả năng xử lý tài liệu và trả lời câu hỏi dựa trên nội dung đã được ingest.

Luồng xử lý chính:

```text
Document
   ↓
Extract / Clean Data
   ↓
Chunking
   ↓
Embedding
   ↓
Vector Database
   ↓
Retrieval
   ↓
LLM
   ↓
Answer + Source
```

Sau khi hoàn thành phần RAG, service cần được:

```text
Build
 ↓
Test
 ↓
Containerize
 ↓
Run
```

và có CI cơ bản để kiểm tra code khi có thay đổi.

---

# 3. Functional Requirements

## 3.1 Document Ingestion

Hệ thống cần hỗ trợ tối thiểu các định dạng:

- PDF
- TXT
- DOCX

Luồng xử lý:

```text
Upload Document
      ↓
Extract Text
      ↓
Clean / Normalize
      ↓
Chunk
      ↓
Create Embedding
      ↓
Store Vector + Metadata
```

Metadata tối thiểu cần lưu:

```text
document_id
file_name
chunk_id
content
embedding_model
created_at
```

Có thể bổ sung metadata khác nếu cần.

---

## 3.2 Health Check API

```http
GET /health
```

Ví dụ response:

```json
{
  "status": "ok"
}
```

---

## 3.3 Document Upload API

```http
POST /documents
```

API cần:

1. Nhận file.
2. Kiểm tra định dạng.
3. Trích xuất nội dung.
4. Chunk dữ liệu.
5. Tạo embedding.
6. Lưu vector và metadata vào database.
7. Trả về trạng thái xử lý.

Ví dụ response:

```json
{
  "document_id": "doc_001",
  "file_name": "policy.pdf",
  "status": "success",
  "total_chunks": 20
}
```

---

## 3.4 Query API

```http
POST /query
```

Ví dụ request:

```json
{
  "question": "Chính sách bảo hành sản phẩm là gì?"
}
```

Ví dụ response:

```json
{
  "answer": "...",
  "sources": [
    {
      "file_name": "policy.pdf",
      "chunk_id": "chunk_10"
    }
  ]
}
```

Response bắt buộc có:

- Câu trả lời.
- Source đã được sử dụng.

Hệ thống không được chỉ trả câu trả lời mà không xác định được nguồn dữ liệu liên quan.

---

# 4. Data & Retrieval Requirements

Khuyến nghị sử dụng:

```text
PostgreSQL + pgvector
```

Luồng retrieval tối thiểu:

```text
Question
   ↓
Embedding
   ↓
Vector Search
   ↓
Top-K Chunks
   ↓
LLM
   ↓
Answer
```

Các thông số sau không được hard-code trực tiếp trong business logic:

```text
DATABASE_URL
EMBEDDING_MODEL
LLM_MODEL
CHUNK_SIZE
CHUNK_OVERLAP
TOP_K
```

Các giá trị này cần được quản lý bằng:

- Environment variables; hoặc
- Configuration file.

---

# 5. Containerization

Toàn bộ hệ thống cần có thể chạy bằng Docker.

Yêu cầu tối thiểu:

```text
rag-api
postgres + pgvector
```

Hệ thống phải có thể khởi chạy bằng command tương đương:

```bash
docker compose up -d
```

Repository cần có:

```text
Dockerfile
docker-compose.yml
.env.example
```

Không commit:

- API key thật.
- Password thật.
- Secret.
- Token.
- Credential nội bộ.

---

# 6. CI Requirements

Thiết lập CI bằng một trong các công cụ:

- GitHub Actions.
- GitLab CI.

Pipeline tối thiểu:

```text
Push / Pull Request
        ↓
      Lint
        ↓
   Unit Test
        ↓
Docker Build
```

Pipeline cần fail nếu:

- Unit test fail.
- Docker build fail.

Không yêu cầu tự động deploy lên production.

---

# 7. Testing Requirements

## 7.1 Unit Test

Cần có unit test cho một số component chính như:

- Text cleaning.
- Chunking.
- Config loading.
- Metadata processing.

Không yêu cầu test toàn bộ mọi function trong project.

---

## 7.2 API Test

Cần kiểm tra tối thiểu các API:

```text
GET  /health
POST /documents
POST /query
```

Bao gồm một số trường hợp:

- Request hợp lệ.
- File không được hỗ trợ.
- Question rỗng hoặc không hợp lệ.
- Query không tìm thấy dữ liệu phù hợp.

---

## 7.3 Basic Retrieval Verification

Chuẩn bị một tập nhỏ khoảng **5–10 câu hỏi** dựa trên bộ tài liệu đã ingest.

Mục tiêu:

- Kiểm tra hệ thống có retrieve đúng tài liệu/chunk liên quan hay không.
- Kiểm tra source trả về có phù hợp với câu hỏi hay không.

Không yêu cầu xây dựng hệ thống AI evaluation phức tạp.

Có thể lưu kết quả đơn giản như:

| Question | Expected Source | Retrieved Source | Result |
|---|---|---|---|
| ... | policy.pdf | policy.pdf | Pass |
| ... | product.docx | product.docx | Pass |

---

# 8. Repository Structure

Cấu trúc repository có thể tham khảo:

```text
repository/
│
├── app/
│   ├── api/
│   ├── ingestion/
│   ├── retrieval/
│   ├── services/
│   └── config/
│
├── tests/
│
├── evaluation/
│   └── retrieval_test_results.csv
│
├── docs/
│   └── architecture.md
│
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt / pyproject.toml
└── README.md
```

Không bắt buộc phải sử dụng chính xác cấu trúc trên nếu có cách tổ chức hợp lý hơn.

---

# 9. Deliverables

Khi hoàn thành task cần bàn giao:

## Source Code

Repository Git có:

- Source code.
- Commit history.
- Cấu trúc project rõ ràng.

## Deployment Files

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`

## Testing

- Unit tests.
- API tests.
- Basic retrieval verification.

## Documentation

### README

README cần có tối thiểu:

1. Project overview.
2. Architecture.
3. Technology stack.
4. Setup.
5. Run.
6. Upload document.
7. Query API.
8. Run test.
9. Known limitations.

### Architecture Document

Tạo file:

```text
docs/architecture.md
```

Nội dung cần mô tả ngắn gọn:

- Kiến trúc hệ thống.
- Data flow.
- Document ingestion flow.
- Retrieval flow.
- Các thành phần chính.
- Lý do lựa chọn công nghệ.
- Các giới hạn hiện tại của hệ thống.
- Hướng cải thiện nếu có thêm thời gian.

---

# 10. Milestones

## Milestone 1 — Data Pipeline

Hoàn thành:

- Document upload.
- Extract text.
- Clean data.
- Chunking.
- Embedding.
- Lưu vector và metadata.

Expected result:

```text
Document → Vector Database
```

---

## Milestone 2 — RAG API

Hoàn thành:

- Query API.
- Vector retrieval.
- LLM integration.
- Source trả về cùng answer.

Expected result:

```text
Question → Retrieval → LLM → Answer + Source
```

---

## Milestone 3 — Docker & CI

Hoàn thành:

- Dockerfile.
- Docker Compose.
- Environment configuration.
- CI pipeline.
- Unit test.
- API test.

---

## Milestone 4 — Documentation & Demo

Hoàn thành:

- README.
- Architecture document.
- Basic retrieval verification.
- Chuẩn bị demo.

---

# 11. Acceptance Criteria

Task được xem là hoàn thành khi đáp ứng tối thiểu:

- [ ] Service chạy được bằng Docker Compose.
- [ ] Upload được PDF, TXT và DOCX.
- [ ] Document được extract và chunk.
- [ ] Chunk được tạo embedding.
- [ ] Vector và metadata được lưu vào database.
- [ ] Query API hoạt động.
- [ ] Câu trả lời có source.
- [ ] Configuration được tách khỏi business logic.
- [ ] Có `.env.example`.
- [ ] Không commit secret thật.
- [ ] Có unit test.
- [ ] Có API test.
- [ ] CI pipeline chạy thành công.
- [ ] Có basic retrieval verification.
- [ ] Có README.
- [ ] Có architecture document.

---

# 12. Evaluation Criteria

| Hạng mục | Trọng số |
|---|---:|
| Data ingestion & processing | 20% |
| Vector Database & Retrieval | 20% |
| AI / RAG Integration | 15% |
| Docker & Environment | 15% |
| CI | 10% |
| Testing | 10% |
| Documentation & Demo | 10% |
| **Tổng** | **100%** |

Ngoài điểm kỹ thuật, reviewer có thể quan sát thêm:

- Khả năng tự research.
- Cách debug.
- Khả năng đọc documentation.
- Cách chia nhỏ vấn đề.
- Chất lượng Git commit.
- Code organization.
- Khả năng giải thích quyết định kỹ thuật.
- Cách trao đổi khi gặp blocker.
- Khả năng tiếp nhận feedback và sửa lỗi.

---

# 13. Bonus

Các phần sau là **không bắt buộc**:

- Hybrid Search.
- Full-Text Search kết hợp Vector Search.
- Reranking.
- Hỗ trợ thêm CSV/XLSX.
- Background worker cho ingestion.
- Retry khi ingestion lỗi.
- Thêm API xóa tài liệu.
- Thêm API xem danh sách tài liệu đã ingest.
- Tối ưu retrieval.

Bonus chỉ được tính khi các yêu cầu cơ bản đã hoàn thành ổn định.

---

# 14. Out of Scope

Task này không yêu cầu:

- Train LLM từ đầu.
- Train embedding model từ đầu.
- Xây Frontend.
- Kubernetes.
- Prometheus / Grafana.
- Centralized logging.
- Blue/Green deployment.
- Model migration.
- Production rollback strategy.
- AI evaluation nâng cao.
- Production-grade infrastructure.

Ưu tiên:

> Xây dựng một hệ thống nhỏ nhưng có data flow rõ ràng, chạy được, test được, containerize được và giải thích được.

---

# 15. Final Demo

Thời gian demo đề xuất:

**20–30 phút.**

Nội dung demo:

1. Giới thiệu architecture.
2. Start system bằng Docker Compose.
3. Upload một tài liệu.
4. Kiểm tra dữ liệu đã được ingest.
5. Query hệ thống.
6. Hiển thị answer và source.
7. Chạy unit/API test.
8. Giới thiệu CI pipeline.
9. Trình bày basic retrieval verification.
10. Trình bày các vấn đề đã gặp và cách xử lý.
11. Q&A.

---

# 16. Expected Outcome

Sau khi hoàn thành task, nhân sự cần thể hiện được khả năng xây dựng một flow cơ bản:

```text
Data
 ↓
Processing
 ↓
Vector Storage
 ↓
Retrieval
 ↓
AI Service
 ↓
Test
 ↓
Docker
 ↓
CI
```

Mục tiêu không chỉ là làm được một chatbot, mà là có thể xây dựng một AI service nhỏ có cấu trúc rõ ràng, có khả năng kiểm thử và triển khai ở mức cơ bản.
