import os
import json

cache_dir = "cache"
novels = []
for d in os.listdir(cache_dir):
    info_p = os.path.join(cache_dir, d, "novel_info.json")
    if os.path.exists(info_p):
        with open(info_p, "r", encoding="utf-8") as f:
            data = json.load(f)
            novels.append({
                "work_id": d,
                "url": data.get("url", ""),
                "title_ja": data.get("title", ""),
                "title_tl": data.get("title_id") or data.get("title_en") or data.get("title", ""),
                "total_episodes": data.get("total_episodes", len(data.get("episodes", [])))
            })

print(f"Total saved novels found: {len(novels)}\n")
for idx, n in enumerate(novels, 1):
    print(f"{idx}. [{n['work_id']}] {n['title_tl'][:45]}")
    print(f"   URL: {n['url']}")
    print(f"   Total Bab: {n['total_episodes']}")

