import json

files = [
    "lgu_content.jsonl",
    "lgu_pdf_content.jsonl",
    "lgu_docx_content.jsonl"
]

merged = []

for file in files:
    try:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        merged.append(json.loads(line))
                    except:
                        pass
        print(f"✓ Loaded: {file}")
    except FileNotFoundError:
        print(f"✗ Not found: {file}")

with open("lgu_merged.jsonl", "w", encoding="utf-8") as f:
    for item in merged:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"\nTotal items merged: {len(merged)}")
print("Saved to: lgu_merged.jsonl")
