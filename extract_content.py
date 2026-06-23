"""
Extracts clean text content from each URL in lgu_urls_clean.txt
Saves results as one JSON object per line (JSONL) in lgu_content.jsonl
"""

import urllib.request
import urllib.error
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

INPUT_FILE = "lgu_urls_clean.txt"
OUTPUT_FILE = "lgu_content.jsonl"
FAILED_FILE = "lgu_extraction_failed.txt"

HEADERS = {'User-Agent': 'Mozilla/5.0'}
DELAY = 0.3  # seconds between requests

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

print(f"Found {len(urls)} URLs to process.\n")

success_count = 0
failed_urls = []

with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Fetching: {url}")
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            response = urllib.request.urlopen(req, timeout=10)
            html = response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed_urls.append(url)
            time.sleep(DELAY)
            continue

        soup = BeautifulSoup(html, 'html.parser')

        # Remove noise elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'form']):
            tag.decompose()

        # Title
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Extract tables separately (so they don't get flattened/lost)
        tables_text = []
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                tables_text.append("\n".join(rows))
            table.decompose()  # remove so it's not duplicated in main text

        # Main text (after removing tables/noise)
        text = soup.get_text(separator='\n', strip=True)
        # Collapse multiple blank lines
        lines = [line for line in text.split('\n') if line.strip()]
        clean_text = "\n".join(lines)

        record = {
            "url": url,
            "title": title,
            "text": clean_text,
            "tables": tables_text,
            "scraped_at": datetime.now().isoformat()
        }

        out.write(json.dumps(record, ensure_ascii=False) + "\n")
        success_count += 1
        time.sleep(DELAY)

with open(FAILED_FILE, "w", encoding="utf-8") as f:
    for url in failed_urls:
        f.write(url + "\n")

print(f"\nDone!")
print(f"Successfully extracted: {success_count}")
print(f"Failed: {len(failed_urls)} -> {FAILED_FILE}")
print(f"Saved to: {OUTPUT_FILE}")
