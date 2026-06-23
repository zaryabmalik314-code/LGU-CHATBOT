import json

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
    return chunks

seen_urls = set()
all_chunks = []
global_id = 0

with open("lgu_merged.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        url = item.get("url", "")
        title = item.get("title", "")
        scraped_at = item.get("scraped_at", "")

        if url in seen_urls:
            continue  # skip duplicate doc
        seen_urls.add(url)

        tables = item.get("tables", [])
        text = item.get("text", "")

        # 1. Each table becomes its OWN chunk, kept whole (never split mid-table)
        for table in tables:
            if not table.strip():
                continue
            all_chunks.append({
                "url": url,
                "title": title,
                "chunk_id": f"chunk_{global_id}",
                "text": f"{title}\n\n{table}",
                "scraped_at": scraped_at
            })
            global_id += 1

        # 2. Main text gets chunked normally by word count (as before)
        if text.strip():
            pieces = chunk_text(text)
            for piece in pieces:
                all_chunks.append({
                    "url": url,
                    "title": title,
                    "chunk_id": f"chunk_{global_id}",
                    "text": piece,
                    "scraped_at": scraped_at
                })
                global_id += 1

with open("lgu_chunks.jsonl", "w", encoding="utf-8") as f:
    for c in all_chunks:
        f.write(json.dumps(c) + "\n")

print(f"Total chunks created: {len(all_chunks)}")