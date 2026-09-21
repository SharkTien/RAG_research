import json
import os
import glob
import sys

# Reconfigure utf-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

base_dir = "datasets/synthdocqa"
manifest_files = glob.glob(os.path.join(base_dir, "manifest_files", "*.json"))
print(f"Total manifest files found: {len(manifest_files)}")

# Load queries to count questions per PDF
queries_file = os.path.join(base_dir, "ALL_queries.json")
query_counts = {}
sample_queries = {}
if os.path.exists(queries_file):
    with open(queries_file, encoding="utf-8") as f:
        queries = json.load(f)
    for q in queries:
        for ref in q.get("refs", []):
            fp = ref.get("filePath")
            if fp:
                query_counts[fp] = query_counts.get(fp, 0) + 1
                if fp not in sample_queries:
                    sample_queries[fp] = []
                if len(sample_queries[fp]) < 3:
                    sample_queries[fp].append(q.get("query"))

catalog = []
for mf in manifest_files:
    try:
        with open(mf, encoding="utf-8") as f:
            data = json.load(f)
            pdf_name = os.path.basename(data.get("files", {}).get("pdf", ""))
            pdf_path = os.path.join(base_dir, "grounding_pdfs_v2", pdf_name)
            is_downloaded = os.path.exists(pdf_path)
            size_mb = round(os.path.getsize(pdf_path) / (1024 * 1024), 2) if is_downloaded else 0.0

            catalog.append({
                "doc_id": data.get("doc_id"),
                "title": data.get("title"),
                "recipe": data.get("recipe_name"),
                "topic": data.get("topic_id"),
                "pdf_filename": pdf_name,
                "downloaded": is_downloaded,
                "size_mb": size_mb,
                "num_questions": query_counts.get(pdf_name, 0),
                "sample_questions": sample_queries.get(pdf_name, [])
            })
    except Exception as e:
        print(f"Error reading {mf}: {e}")

catalog.sort(key=lambda x: (not x["downloaded"], x["recipe"], x["title"]))

catalog_path = os.path.join(base_dir, "catalog.json")
with open(catalog_path, "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"Catalog saved to {catalog_path} with {len(catalog)} documents.")
print("\n--- Downloaded Documents ---")
for doc in catalog:
    if doc["downloaded"]:
        print(f"[*] {doc['pdf_filename']} ({doc['size_mb']} MB) - [{doc['recipe']}] {doc['title']}")
        for q in doc['sample_questions'][:2]:
            print(f"    Q: {q}")
