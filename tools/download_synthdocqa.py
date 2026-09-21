import os
import sys
import json
import argparse
import concurrent.futures
from huggingface_hub import hf_hub_download

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ID = "goodboyanush/synthdocqa"
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets", "synthdocqa")
PDF_DIR = os.path.join(BASE_DIR, "grounding_pdfs_v2")

os.makedirs(PDF_DIR, exist_ok=True)

def download_one_pdf(filename):
    out_path = os.path.join(PDF_DIR, filename)
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        sz = round(os.path.getsize(out_path) / (1024 * 1024), 2)
        print(f"  [OK] Exists: {filename} ({sz} MB)")
        return filename, True, sz

    try:
        remote_path = f"grounding_pdfs_v2/{filename}"
        print(f"  [>] Downloading: {filename}...")
        hf_hub_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            filename=remote_path,
            local_dir=BASE_DIR
        )
        sz = round(os.path.getsize(out_path) / (1024 * 1024), 2)
        print(f"  [+] Finished: {filename} ({sz} MB)")
        return filename, True, sz
    except Exception as e:
        print(f"  [X] Failed {filename}: {e}")
        return filename, False, 0.0

def main():
    parser = argparse.ArgumentParser(description="Download PDFs from goodboyanush/synthdocqa")
    parser.add_argument("--count", type=int, default=5, help="Number of diverse PDFs to download (default 5, use -1 for all 100)")
    parser.add_argument("--file", type=str, default="", help="Specific PDF file to download")
    parser.add_argument("--workers", type=int, default=4, help="Parallel download workers")
    args = parser.parse_args()

    catalog_path = os.path.join(BASE_DIR, "catalog.json")
    if not os.path.exists(catalog_path):
        print("Catalog not found. Running catalog generator...")
        import subprocess
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "build_dataset_catalog.py")])

    with open(catalog_path, encoding="utf-8") as f:
        catalog = json.load(f)

    if args.file:
        files_to_download = [args.file]
    elif args.count == -1:
        files_to_download = [item["pdf_filename"] for item in catalog]
    else:
        # Pick diverse documents across recipes
        seen_recipes = set()
        chosen = []
        for item in catalog:
            r = item.get("recipe")
            if r not in seen_recipes:
                seen_recipes.add(r)
                chosen.append(item["pdf_filename"])
            if len(chosen) >= args.count:
                break
        # If not enough, fill with remaining
        if len(chosen) < args.count:
            for item in catalog:
                if item["pdf_filename"] not in chosen:
                    chosen.append(item["pdf_filename"])
                if len(chosen) >= args.count:
                    break
        files_to_download = chosen

    print("================================================================")
    print(f"  SynthDocQA Downloader — Downloading {len(files_to_download)} files (workers={args.workers})")
    print(f"  Destination: {PDF_DIR}")
    print("================================================================")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(download_one_pdf, files_to_download))

    success = sum(1 for _, ok, _ in results if ok)
    total_size = sum(sz for _, ok, sz in results if ok)
    print("================================================================")
    print(f"  Downloaded: {success}/{len(files_to_download)} files ({total_size:.2f} MB total)")
    print("================================================================")

    # Re-build catalog to update downloaded status
    import subprocess
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "build_dataset_catalog.py")])

if __name__ == "__main__":
    main()
