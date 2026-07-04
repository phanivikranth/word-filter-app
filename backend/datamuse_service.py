"""
DataMuse API client (https://api.datamuse.com).

Endpoints:
  GET /words  — word-finding queries (synonyms, spelling, sounds-like, patterns, etc.)
  GET /sug    — autocomplete suggestions
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.datamuse.com"


class DatamuseService:
    """Query words via the DataMuse API (free, no key required until 2027)."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (
            base_url or os.getenv("DATAMUSE_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self.enabled = os.getenv("DATAMUSE_ENABLED", "true").lower() == "true"
        self.api_key = (os.getenv("DATAMUSE_API_KEY") or "").strip()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.rate_limit_delay = float(os.getenv("DATAMUSE_DELAY", "0.15"))
        self._last_request_time = 0.0

    def is_configured(self) -> bool:
        return self.enabled

    async def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _request(
        self,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "ok": False,
                "status": 0,
                "data": None,
                "error": "DataMuse is disabled (DATAMUSE_ENABLED=false)",
            }

        await self._throttle()
        cleaned: Dict[str, str] = {}
        if params:
            for key, value in params.items():
                if value is None or value == "":
                    continue
                cleaned[str(key)] = str(value)

        query = f"?{urlencode(cleaned)}" if cleaned else ""
        url = f"{self.base_url}/{endpoint.lstrip('/')}{query}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=self._headers(), timeout=20
                ) as response:
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
            logger.error("DataMuse request failed for %s: %s", url, exc)
            return {"ok": False, "status": 0, "data": None, "error": str(exc)}

    async def query_words(self, **params: Any) -> Dict[str, Any]:
        """GET /words with arbitrary DataMuse query parameters."""
        return await self._request("words", params=params)

    async def suggest(self, prefix: str, *, max_results: int = 10) -> Dict[str, Any]:
        """GET /sug — autocomplete suggestions."""
        return await self._request(
            "sug",
            params={"s": prefix, "max": max_results},
        )

    @staticmethod
    def extract_words(data: Any) -> List[str]:
        if not isinstance(data, list):
            return []
        words: List[str] = []
        seen: Set[str] = set()
        for item in data:
            if not isinstance(item, dict):
                continue
            word = str(item.get("word", "")).strip().lower()
            if word and word.isalpha() and word not in seen:
                seen.add(word)
                words.append(word)
        return words

    @staticmethod
    def _parse_entry(word_key: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        tags = entry.get("tags") or []
        definitions: List[str] = []
        for tag in tags:
            text = str(tag).strip()
            if text.startswith("def:"):
                definitions.append(text[4:].strip())

        defs_field = entry.get("defs") or []
        if isinstance(defs_field, list):
            for item in defs_field:
                text = str(item).strip()
                if text and text not in definitions:
                    definitions.append(text)

        if not definitions and entry.get("word"):
            definitions.append(f"Word found in DataMuse ({entry.get('word')})")

        return {
            "word": word_key,
            "is_valid": True,
            "definitions": definitions[:5],
            "synonyms": [],
            "word_forms": [],
            "examples": [],
            "pronunciations": [],
            "etymology": "",
            "origin_language": "",
            "first_known_use": "",
            "reason": f"Found in DataMuse with {len(definitions)} definition(s)",
            "source": "datamuse",
            "source_url": f"{DEFAULT_BASE_URL}/words?sp={word_key}&md=d",
            "dictionary_url": f"{DEFAULT_BASE_URL}/words?sp={word_key}&md=d",
            "summary": definitions[0] if definitions else "",
            "datamuse": {
                "score": entry.get("score"),
                "tags": tags,
                "numSyllables": entry.get("numSyllables"),
            },
        }

    async def validate_word(self, word: str) -> Dict[str, Any]:
        word_key = word.strip().lower()
        if not word_key or not word_key.isalpha():
            return self._invalid_result(
                word_key, "Invalid word format (must contain only letters)"
            )
        if not self.is_configured():
            return self._invalid_result(
                word_key, "DataMuse is disabled (DATAMUSE_ENABLED=false)"
            )

        if word_key in self.cache:
            return self.cache[word_key]

        payload = await self.query_words(sp=word_key, md="dp", max=5)
        if not payload.get("ok") or not isinstance(payload.get("data"), list):
            result = self._invalid_result(
                word_key,
                payload.get("error") or "DataMuse lookup failed",
            )
            self.cache[word_key] = result
            return result

        for entry in payload["data"]:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("word", "")).strip().lower() == word_key:
                result = self._parse_entry(word_key, entry)
                self.cache[word_key] = result
                return result

        result = self._invalid_result(word_key, "Not found in DataMuse")
        self.cache[word_key] = result
        return result

    async def find_words_for_puzzle(self, **params: Any) -> List[str]:
        """Return word list from DataMuse for puzzle queries."""
        payload = await self.query_words(**params)
        if not payload.get("ok"):
            return []
        return self.extract_words(payload.get("data"))

    async def pick_random_word(
        self,
        *,
        min_length: int = 5,
        max_length: int = 8,
        topic: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Pick a random dictionary word via spelled-like wildcard query."""
        length = min_length
        if max_length > min_length:
            import random as py_random

            length = py_random.randint(min_length, max_length)

        pattern = "?" * length
        params: Dict[str, Any] = {"sp": pattern, "max": 100, "md": "d"}
        if topic:
            params["topics"] = topic

        payload = await self.query_words(**params)
        if not payload.get("ok"):
            return None

        words = self.extract_words(payload.get("data"))
        words = [w for w in words if min_length <= len(w) <= max_length]
        if not words:
            return None

        import random as py_random

        chosen = py_random.choice(words)
        entry = next(
            (
                item
                for item in (payload.get("data") or [])
                if isinstance(item, dict)
                and str(item.get("word", "")).strip().lower() == chosen
            ),
            {"word": chosen},
        )
        parsed = self._parse_entry(chosen, entry)
        return parsed

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
            "source": "datamuse",
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured(),
            "enabled": self.enabled,
            "base_url": self.base_url,
            "cached_words": len(self.cache),
        }
