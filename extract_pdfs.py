"""
Downloads and extracts text from PDF URLs in lgu_urls_pdfs.txt
Saves results as JSONL in lgu_pdf_content.jsonl
Resumes from where it left off - skips already processed URLs
"""

import urllib.request
import json
import time
import io
from datetime import datetime
import pdfplumber

INPUT_FILE = "lgu_urls_pdfs.txt"
OUTPUT_FILE = "lgu_pdf_content.jsonl"
FAILED_FILE = "lgu_pdf_failed.txt"

HEADERS = {'User-Agent': 'Mozilla/5.0'}
DELAY = 0.3

# Load already processed URLs
already_done = set()
try:
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                already_done.add(record["url"])
            except:
                pass
    print(f"Resuming — skipping {len(already_done)} already processed PDFs.\n")
except FileNotFoundError:
    print("Starting fresh.\n")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

print(f"Found {len(urls)} PDFs total. {len(urls) - len(already_done)} remaining.\n")

success_count = 0
failed_urls = []

with open(OUTPUT_FILE, "a", encoding="utf-8") as out:  # append mode
    for i, url in enumerate(urls, 1):
        if url in already_done:
            print(f"[{i}/{len(urls)}] Skipping (done): {url.split('/')[-1]}")
            continue

        print(f"[{i}/{len(urls)}] Fetching: {url}")
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            response = urllib.request.urlopen(req, timeout=15)
            pdf_bytes = response.read()
        except Exception as e:
            print(f"  [FAIL download] {e}")
            failed_urls.append(url)
            time.sleep(DELAY)
            continue

        try:
            text_parts = []
            tables_text = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    for table in page.extract_tables():
                        rows = [" | ".join([cell or "" for cell in row]) for row in table]
                        tables_text.append("\n".join(rows))
        except Exception as e:
            print(f"  [FAIL parse] {e}")
            failed_urls.append(url)
            time.sleep(DELAY)
            continue

        full_text = "\n".join(text_parts)

        record = {
            "url": url,
            "title": url.split("/")[-1],
            "text": full_text,
            "tables": tables_text,
            "scraped_at": datetime.now().isoformat()
        }

        out.write(json.dumps(record, ensure_ascii=False) + "\n")
        out.flush()  # save immediately
        success_count += 1
        time.sleep(DELAY)

with open(FAILED_FILE, "w", encoding="utf-8") as f:
    for url in failed_urls:
        f.write(url + "\n")

print(f"\nDone!")
print(f"Successfully extracted: {success_count}")
print(f"Failed: {len(failed_urls)} -> {FAILED_FILE}")
print(f"Saved to: {OUTPUT_FILE}")
