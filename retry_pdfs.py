"""
Retries failed PDF URLs from lgu_pdf_failed.txt
Appends successful results to lgu_pdf_content.jsonl
"""

import urllib.request
import json
import time
import io
from datetime import datetime
import pdfplumber

FAILED_FILE = "lgu_pdf_failed.txt"
OUTPUT_FILE = "lgu_pdf_content.jsonl"
STILL_FAILED_FILE = "lgu_pdf_failed.txt"  # overwrite with new failures

HEADERS = {'User-Agent': 'Mozilla/5.0'}
DELAY = 3

with open(FAILED_FILE, "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

print(f"Retrying {len(urls)} failed PDFs.\n")

success_count = 0
still_failed = []

with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Retrying: {url}")
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            response = urllib.request.urlopen(req, timeout=10)
            pdf_bytes = response.read()
        except Exception as e:
            print(f"  [FAIL download] {e}")
            still_failed.append(url)
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
            still_failed.append(url)
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
        success_count += 1
        time.sleep(DELAY)

with open(STILL_FAILED_FILE, "w", encoding="utf-8") as f:
    for url in still_failed:
        f.write(url + "\n")

print(f"\nDone!")
print(f"Newly extracted: {success_count}")
print(f"Still failed: {len(still_failed)} -> {STILL_FAILED_FILE}")
