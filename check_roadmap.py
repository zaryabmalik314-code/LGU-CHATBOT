import json

target_url = "https://lgu.edu.pk/bs-cs-road-map"

with open("lgu_merged.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        if item.get("url") == target_url:
            print("FOUND! Full text length:", len(item.get("text", "")))
            print("=" * 70)
            print(item.get("text", ""))
            print("=" * 70)
            break
    else:
        print("URL not found in lgu_merged.jsonl")
