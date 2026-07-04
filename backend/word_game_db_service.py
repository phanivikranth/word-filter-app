"""
Word Game DB API client (https://www.wordgamedb.com/api/v2).

Endpoints:
  GET /categories
  GET /words/random
  GET /words?minLetters=&maxLetters=&minSyllables=&maxSyllables=&limit=&offset=
  GET /words/search?q=   (used for exact word lookup during validation)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.wordgamedb.com/api/v2"


class WordGameDbService:
    """Look up words via Word Game DB REST API (no API key required)."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (
            base_url or os.getenv("WORD_GAME_DB_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self.enabled = os.getenv("WORD_GAME_DB_ENABLED", "true").lower() == "true"
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limit_delay = float(os.getenv("WORD_GAME_DB_DELAY", "0.2"))
        self._last_request_time = 0.0

    def is_configured(self) -> bool:
        return self.enabled

    async def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

    async def _request(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "ok": False,
                "status": 0,
                "data": None,
                "error": "Word Game DB is disabled (WORD_GAME_DB_ENABLED=false)",
            }

        await self._throttle()
        query = ""
        if params:
            cleaned = {
                str(key): str(value)
                for key, value in params.items()
                if value is not None and str(value) != ""
            }
            if cleaned:
                query = f"?{urlencode(cleaned)}"
        url = f"{self.base_url}/{path.lstrip('/')}{query}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=20) as response:
                    self._last_request_time = time.time()
                    try:
                        body = await response.json()
                    except Exception:
                        body = await response.text()
                    ok = response.status == 200
                    return {
                        "ok": ok,
                        "status": response.status,
                        "data": body if ok else None,
                        "error": None if ok else str(body)[:300],
                    }
        except Exception as exc:
            logger.error("Word Game DB request failed for %s: %s", url, exc)
            return {"ok": False, "status": 0, "data": None, "error": str(exc)}

    async def get_categories(self) -> Dict[str, Any]:
        return await self._request("categories")

    async def get_random_word(self) -> Dict[str, Any]:
        return await self._request("words/random")

    async def list_words(
        self,
        *,
        min_letters: Optional[int] = None,
        max_letters: Optional[int] = None,
        min_syllables: Optional[int] = None,
        max_syllables: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if min_letters is not None:
            params["minLetters"] = min_letters
        if max_letters is not None:
            params["maxLetters"] = max_letters
        if min_syllables is not None:
            params["minSyllables"] = min_syllables
        if max_syllables is not None:
            params["maxSyllables"] = max_syllables
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if category:
            params["category"] = category
        return await self._request("words", params=params or None)

    async def search_word(self, word: str, *, limit: int = 5) -> Dict[str, Any]:
        return await self._request(
            "words/search",
            params={"q": word.strip().lower(), "limit": limit},
        )

    @staticmethod
    def _invalid_result(word: str, reason: str) -> Dict[str, Any]:
        return {
            "word": word,
            "is_valid": False,
            "definitions": [],
            "synonyms": [],
            "word_forms": [],
            "examples": [],
            "pronunciations": [],
            "etymology": "",
            "origin_language": "",
            "first_known_use": "",
            "reason": reason,
            "source": "word_game_db",
        }

    @classmethod
    def _entry_to_result(cls, word_key: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        hint = (entry.get("hint") or "").strip()
        category = (entry.get("category") or "").strip()
        num_letters = entry.get("numLetters")
        num_syllables = entry.get("numSyllables")

        definitions: List[str] = []
        if hint:
            definitions.append(hint)
        elif category:
            definitions.append(f"A {category} word from Word Game DB")

        word_forms: List[str] = []
        if category:
            word_forms.append(category)
        if num_letters is not None:
            word_forms.append(f"{num_letters} letters")
        if num_syllables is not None:
            word_forms.append(f"{num_syllables} syllables")

        source_url = f"{DEFAULT_BASE_URL}/words/search?q={quote(word_key)}"
        reason = "Found in Word Game DB"
        if hint:
            reason += f": {hint}"

        return {
            "word": word_key,
            "is_valid": True,
            "definitions": definitions[:3],
            "synonyms": [],
            "word_forms": word_forms[:5],
            "examples": [],
            "pronunciations": [],
            "etymology": "",
            "origin_language": category,
            "first_known_use": "",
            "reason": reason,
            "source": "word_game_db",
            "source_url": source_url,
            "dictionary_url": source_url,
            "summary": definitions[0] if definitions else "",
            "word_game_db": {
                "category": category,
                "hint": hint,
                "numLetters": num_letters,
                "numSyllables": num_syllables,
                "_id": entry.get("_id"),
            },
        }

    @classmethod
    def _pick_exact_match(
        cls, word_key: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        words = data.get("words") or []
        if not isinstance(words, list):
            return None
        for entry in words:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("word", "")).strip().lower() == word_key:
                return entry
        return words[0] if len(words) == 1 and isinstance(words[0], dict) else None

    async def validate_word(self, word: str) -> Dict[str, Any]:
        word_key = word.strip().lower()
        if not word_key or not word_key.isalpha():
            return self._invalid_result(
                word_key, "Invalid word format (must contain only letters)"
            )
        if not self.is_configured():
            return self._invalid_result(
                word_key, "Word Game DB is disabled (WORD_GAME_DB_ENABLED=false)"
            )

        if word_key in self.cache:
            self.cache_hits += 1
            return self.cache[word_key]

        self.cache_misses += 1
        payload = await self.search_word(word_key, limit=5)
        if not payload.get("ok") or not isinstance(payload.get("data"), dict):
            result = self._invalid_result(
                word_key,
                payload.get("error") or "Word Game DB search failed",
            )
            self.cache[word_key] = result
            return result

        entry = self._pick_exact_match(word_key, payload["data"])
        if not entry:
            result = self._invalid_result(word_key, "Not found in Word Game DB")
            self.cache[word_key] = result
            return result

        result = self._entry_to_result(word_key, entry)
        self.cache[word_key] = result
        return result

    def get_cache_stats(self) -> Dict[str, Any]:
        total = self.cache_hits + self.cache_misses
        rate = f"{(self.cache_hits / total * 100):.1f}%" if total > 0 else "0.0%"
        return {
            "configured": self.is_configured(),
            "enabled": self.enabled,
            "base_url": self.base_url,
            "cached_words": len(self.cache),
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "cache_hit_rate": rate,
        }
