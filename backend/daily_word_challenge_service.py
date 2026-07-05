"""
Daily Word Challenge cards — 4 education-topic words from DataMuse with definitions.
Cached per calendar day.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE = (
    Path(__file__).resolve().parent / "data" / "daily_word_challenge_cache.json"
)
DEFAULT_COUNT = 4
DEFAULT_PATTERN = "????????"
DEFAULT_MD = "f"
DEFAULT_TOPICS = "education"


class DailyWordChallengeService:
    """Fetch and cache daily word-challenge cards for the UI."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = Path(
            cache_path
            or os.getenv("DAILY_WORD_CHALLENGE_CACHE_FILE", str(DEFAULT_CACHE))
        )
        self.word_count = int(
            os.getenv("DAILY_WORD_CHALLENGE_COUNT", str(DEFAULT_COUNT))
        )

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
            logger.warning("Could not read daily word challenge cache: %s", exc)
            return {}

    def _save_cache(self, payload: Dict[str, Any]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    async def _datamuse_definition(self, word: str) -> str:
        from datamuse_service import DatamuseService

        datamuse = DatamuseService()
        payload = await datamuse.query_words(sp=word, md="d", max=1)
        if payload.get("ok") and isinstance(payload.get("data"), list):
            for entry in payload["data"]:
                if not isinstance(entry, dict):
                    continue
                for tag in entry.get("tags") or []:
                    text = str(tag).strip()
                    if text.startswith("def:"):
                        return text[4:].strip()
        return ""

    async def _dictionary_definition(self, word: str) -> str:
        from dictionary_api_dev_service import DictionaryApiDevService

        dad = DictionaryApiDevService()
        result = await dad.validate_word(word)
        definitions = result.get("definitions") or []
        if definitions:
            return str(definitions[0]).strip()
        return (result.get("summary") or "").strip()

    async def _definition_for_word(self, word: str) -> str:
        dict_def, datamuse_def = await asyncio.gather(
            self._dictionary_definition(word),
            self._datamuse_definition(word),
            return_exceptions=True,
        )
        if isinstance(dict_def, str) and dict_def:
            return dict_def
        if isinstance(datamuse_def, str) and datamuse_def:
            return datamuse_def
        return f"Explore the meaning of “{word}” in the dictionary."

    async def _build_items(self, words: List[str]) -> List[Dict[str, str]]:
        tasks = [self._definition_for_word(word) for word in words]
        definitions = await asyncio.gather(*tasks, return_exceptions=True)
        items: List[Dict[str, str]] = []
        for word, definition in zip(words, definitions):
            if isinstance(definition, Exception):
                logger.warning(
                    "Definition lookup failed for '%s': %s", word, definition
                )
                definition = f"Explore the meaning of “{word}” in the dictionary."
            items.append(
                {
                    "word": word,
                    "definition": str(definition).strip(),
                }
            )
        return items

    async def get_daily_challenge(self) -> Dict[str, Any]:
        today = self._today_key()
        cached = self._load_cache()
        if cached.get("date") == today and cached.get("items"):
            return {
                "success": True,
                "date": today,
                "items": list(cached["items"]),
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
            max=self.word_count,
            topics=DEFAULT_TOPICS,
        )
        if not payload.get("ok"):
            return {
                "success": False,
                "date": today,
                "error": payload.get("error") or "DataMuse query failed",
            }

        words = datamuse.extract_words(payload.get("data"))
        words = [w for w in words if len(w) == 8][: self.word_count]

        if len(words) < self.word_count:
            extra = await datamuse.query_words(
                sp=DEFAULT_PATTERN,
                md=DEFAULT_MD,
                max=20,
                topics=DEFAULT_TOPICS,
            )
            if extra.get("ok"):
                pool = datamuse.extract_words(extra.get("data"))
                pool = [w for w in pool if len(w) == 8]
                seen = set(words)
                for candidate in pool:
                    if candidate not in seen:
                        words.append(candidate)
                        seen.add(candidate)
                    if len(words) >= self.word_count:
                        break

        if not words:
            return {
                "success": False,
                "date": today,
                "error": "No suitable words returned from DataMuse",
            }

        items = await self._build_items(words[: self.word_count])
        cache_payload = {
            "date": today,
            "items": items,
            "source": "datamuse",
            "query": {
                "sp": DEFAULT_PATTERN,
                "md": DEFAULT_MD,
                "max": self.word_count,
                "topics": DEFAULT_TOPICS,
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_cache(cache_payload)

        return {
            "success": True,
            "date": today,
            "items": items,
            "source": "datamuse",
            "cached": False,
        }
