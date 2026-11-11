"""
Cache Manager
Handles persisting novel metadata and translated chapter content to disk.
"""

import os
import json
from typing import Optional, Dict

CACHE_DIR = "cache"

class CacheManager:
    def __init__(self, work_id: str):
        self.work_id = str(work_id)
        self.work_cache_dir = os.path.join(CACHE_DIR, self.work_id)
        os.makedirs(self.work_cache_dir, exist_ok=True)

    def get_novel_info_path(self) -> str:
        return os.path.join(self.work_cache_dir, "novel_info.json")

    def save_novel_info(self, info: Dict) -> None:
        path = self.get_novel_info_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

    def load_novel_info(self) -> Optional[Dict]:
        path = self.get_novel_info_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def get_episode_cache_path(self, episode_id: str, engine_name: str) -> str:
        # Cache key includes engine name (e.g. sugoi, llm-id, llm-en)
        safe_engine = "".join(c if c.isalnum() or c in "-_" else "_" for c in engine_name)
        return os.path.join(self.work_cache_dir, f"ep_{episode_id}_{safe_engine}.json")

    def save_episode(self, episode_id: str, engine_name: str, data: Dict) -> None:
        path = self.get_episode_cache_path(episode_id, engine_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_episode(self, episode_id: str, engine_name: str) -> Optional[Dict]:
        path = self.get_episode_cache_path(episode_id, engine_name)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

