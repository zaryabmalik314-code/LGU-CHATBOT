"""
Pretty-prints a few random entries from lgu_content.jsonl
so you can manually check extraction quality.
"""

import json
import random

INPUT_FILE = "lgu_content.jsonl"
NUM_SAMPLES = 10

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    lines = [line for line in f if line.strip()]

print(f"Total records: {len(lines)}\n")

samples = random.sample(lines, min(NUM_SAMPLES, len(lines)))

for i, line in enumerate(samples, 1):
    record = json.loads(line)
    print("=" * 80)
    print(f"[{i}] URL: {record['url']}")
    print(f"TITLE: {record['title']}")
    print(f"TEXT LENGTH: {len(record['text'])} chars")
    print("-" * 80)
    print(record['text'][:600])  # first 600 chars only
    if len(record['text']) > 600:
        print("... [truncated]")
    if record['tables']:
        print(f"\n[Found {len(record['tables'])} table(s)]")
        print(record['tables'][0][:400])
    print()
