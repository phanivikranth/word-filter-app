"""
Daily Safe Words to Explore — 8-letter words from DataMuse (frequency metadata).
Cached per calendar day; stable word set for the day, changes the next day.
"""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE = (
    Path(__file__).resolve().parent / "data" / "daily_safe_explore_cache.json"
)
DEFAULT_COUNT = 10
DEFAULT_PATTERN = "????????"
DEFAULT_MD = "f"
DEFAULT_POOL_MAX = 50


class DailySafeExploreService:
    """Fetch and cache daily explore-word chips for the UI."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = Path(
            cache_path
            or os.getenv("DAILY_SAFE_EXPLORE_CACHE_FILE", str(DEFAULT_CACHE))
        )
        self.word_count = int(os.getenv("DAILY_SAFE_EXPLORE_COUNT", str(DEFAULT_COUNT)))

    @staticmethod
    def _today_key() -> str:
        return date.today().isoformat()

    def _load_cache(self) -> Dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read daily safe explore cache: %s", exc)
            return {}

    def _save_cache(self, payload: Dict[str, Any]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    @staticmethod
    def _pick_daily_words(pool: List[str], today: str, count: int) -> List[str]:
        cleaned = [w.strip().lower() for w in pool if w and str(w).isalpha()]
        seen: set[str] = set()
        unique: List[str] = []
        for word in cleaned:
            if word not in seen:
                seen.add(word)
                unique.append(word)
        if not unique:
            return []
        rng = random.Random(today)
        if len(unique) <= count:
            rng.shuffle(unique)
            return unique[:count]
        return rng.sample(unique, count)

    async def get_daily_words(self) -> Dict[str, Any]:
        today = self._today_key()
        cached = self._load_cache()
        if cached.get("date") == today and cached.get("words"):
            return {
                "success": True,
                "date": today,
                "words": list(cached["words"]),
                "source": "datamuse",
                "cached": True,
            }

        from datamuse_service import DatamuseService

        datamuse = DatamuseService()
        if not datamuse.is_configured():
            return {
                "success": False,
                "date": today,
                "error": "DataMuse is disabled (DATAMUSE_ENABLED=false)",
            }

        payload = await datamuse.query_words(
            sp=DEFAULT_PATTERN,
            md=DEFAULT_MD,
            max=DEFAULT_POOL_MAX,
        )
        if not payload.get("ok"):
            return {
                "success": False,
                "date": today,
                "error": payload.get("error") or "DataMuse query failed",
            }

        pool = datamuse.extract_words(payload.get("data"))
        pool = [w for w in pool if len(w) == 8]

        if len(pool) < self.word_count:
            fallback = await datamuse.query_words(
                sp=DEFAULT_PATTERN,
                md=DEFAULT_MD,
                max=10,
            )
            if fallback.get("ok"):
                pool = datamuse.extract_words(fallback.get("data"))
                pool = [w for w in pool if len(w) == 8]

        words = self._pick_daily_words(pool, today, self.word_count)
        if not words:
            return {
                "success": False,
                "date": today,
                "error": "No suitable words returned from DataMuse",
            }

        cache_payload = {
            "date": today,
            "words": words,
            "source": "datamuse",
            "query": {
                "sp": DEFAULT_PATTERN,
                "md": DEFAULT_MD,
                "max": DEFAULT_POOL_MAX,
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_cache(cache_payload)

        return {
            "success": True,
            "date": today,
            "words": words,
            "source": "datamuse",
            "cached": False,
        }
