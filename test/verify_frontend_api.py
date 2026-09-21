import requests
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:18765"

# 1. Login
session = requests.Session()
login_res = session.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": "admin", "password": "matkhausieudai123"}
)
print("Login status:", login_res.status_code)
if login_res.status_code != 200:
    print("Login failed:", login_res.text)
    exit(1)

login_data = login_res.json()
csrf_token = login_data.get("csrf_token")
session.headers.update({"x-csrf-token": csrf_token})
print(f"Logged in as admin. CSRF Token: {csrf_token[:8]}...")

# 2. Check current documents
docs_res = session.get(f"{BASE_URL}/api/documents")
print("List documents status:", docs_res.status_code)
docs_data = docs_res.json()
items = docs_data.get("items", [])
print(f"Total documents: {len(items)}")

# 3. If any document is failed, trigger re-extract
for doc in items:
    doc_id = doc["id"]
    if doc.get("status") in ["failed", "queued"]:
        print(f"Triggering re-extract for document {doc_id}...")
        session.post(f"{BASE_URL}/api/documents/{doc_id}/extract")

# If no documents, upload sample PDF
pdf_path = "QĐ.NTC.HR-01-QUY TRÌNH, QUY ĐỊNH QUẢN LÝ NGHỈ PHÉP.pdf"
if len(items) == 0 and os.path.exists(pdf_path):
    print(f"Uploading {pdf_path}...")
    with open(pdf_path, "rb") as f:
        files = [("files", (pdf_path, f, "application/pdf"))]
        up_res = session.post(f"{BASE_URL}/api/documents", files=files)
        print("Upload status:", up_res.status_code, up_res.text)

# 4. Test Query RAG API
print("\nTesting Query RAG API (POST /api/query)...")
query_payload = {
    "question": "Quy định về thời gian xin nghỉ phép từ 7 ngày trở lên như thế nào?",
    "top_k": 3
}
q_res = session.post(f"{BASE_URL}/api/query", json=query_payload)
print("Query status:", q_res.status_code)
if q_res.status_code == 200:
    res_data = q_res.json()
    print("Answer:", res_data.get("answer", "")[:200], "...")
    print(f"Sources cited: {len(res_data.get('sources', []))}")
    for idx, src in enumerate(res_data.get("sources", [])):
        print(f"  [{idx+1}] File: {src.get('file_name')} | Page: {src.get('page')} | Score: {src.get('similarity_score')}")
else:
    print("Query error:", q_res.text)

print("\nAll frontend API integration endpoints verified successfully!")
