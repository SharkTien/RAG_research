# NTC Document RAG — ingestion MVP

## Chạy

```bash
cp .env.example .env
# Sửa toàn bộ các giá trị secret trong .env trước khi chạy
docker compose up -d --build
```

- UI: http://localhost:18765
- MinIO Console: http://localhost:9001
- Health: http://localhost:18765/health

Container ứng dụng có tên cố định `ntc_document_rag`. UI dùng Vite + React + Tailwind và chạy tại port host `18765`. Tài liệu upload tối đa 200 MB/file, được lưu tại bucket `ntc-documents` dưới prefix `raw/<document-id>/`; PostgreSQL chỉ lưu metadata, checksum SHA-256 và trạng thái ingestion.

Worker `ntc_document_rag_worker` xử lý tài liệu từ hàng đợi PostgreSQL. Nếu worker bị restart, tài liệu ở trạng thái `queued` vẫn được xử lý tiếp. Với môi trường production, đặt `APP_ENV=production`, `COOKIE_SECURE=true` và chạy sau reverse proxy HTTPS.

Thư mục `documents/NTC_doc` là nguồn tài liệu ban đầu; MVP này chưa tự động nạp hàng loạt để tránh upload ngoài ý muốn. Bước tiếp theo có thể thêm job bulk-ingestion có dry-run, dedup theo SHA-256 và trạng thái xử lý chunk/embedding.
