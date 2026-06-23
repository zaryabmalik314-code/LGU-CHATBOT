import json

target_url = "https://lgu.edu.pk/structure-of-bs-cs-programme/"

with open("lgu_merged.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        if item.get("url", "").rstrip("/") == target_url.rstrip("/"):
            print("FOUND! Text length:", len(item.get("text", "")))
            print(item.get("text", "")[:500])
            break
    else:
        print("NOT FOUND in lgu_merged.jsonl — needs to be added manually")
