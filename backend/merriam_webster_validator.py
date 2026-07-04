"""
Merriam-Webster Dictionary API validator (Thesaurus endpoint).

API docs: https://dictionaryapi.com/products/api-collegiate-thesaurus
Free tier: 1,000 requests/day per key.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_USAGE_FILE = Path(__file__).resolve().parent / "mw_api_usage.json"
DEFAULT_DAILY_LIMIT = 1000
THESAURUS_URL = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json"


class MerriamWebsterValidator:
    """Validate words using the Merriam-Webster Collegiate Thesaurus API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        daily_limit: int = DEFAULT_DAILY_LIMIT,
        usage_file: Optional[Path] = None,
    ):
        self.api_key = api_key or os.getenv("MERRIAM_WEBSTER_API_KEY")
        self.daily_limit = int(os.getenv("MERRIAM_WEBSTER_DAILY_LIMIT", daily_limit))
        self.usage_file = Path(usage_file or os.getenv("MERRIAM_WEBSTER_USAGE_FILE", DEFAULT_USAGE_FILE))
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limit_delay = 0.1
        self._last_request_time = 0.0

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _load_usage(self) -> Dict[str, Any]:
        if not self.usage_file.exists():
            return {"date": date.today().isoformat(), "count": 0}
        try:
            with open(self.usage_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            if data.get("date") != date.today().isoformat():
                return {"date": date.today().isoformat(), "count": 0}
            return {"date": data["date"], "count": int(data.get("count", 0))}
        except (OSError, json.JSONDecodeError, ValueError):
            return {"date": date.today().isoformat(), "count": 0}

    def _save_usage(self, usage: Dict[str, Any]) -> None:
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_file, "w", encoding="utf-8") as file:
            json.dump(usage, file)

    def get_usage_stats(self) -> Dict[str, Any]:
        usage = self._load_usage()
        remaining = max(0, self.daily_limit - usage["count"])
        return {
            "configured": self.is_configured(),
            "daily_limit": self.daily_limit,
            "used_today": usage["count"],
            "remaining_today": remaining,
            "quota_exhausted": remaining == 0,
            "usage_date": usage["date"],
            "cached_words": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
        }

    def has_quota(self) -> bool:
        if not self.is_configured():
            return False
        return self._load_usage()["count"] < self.daily_limit

    def _consume_quota(self) -> bool:
        usage = self._load_usage()
        if usage["count"] >= self.daily_limit:
            return False
        usage["count"] += 1
        self._save_usage(usage)
        return True

    @staticmethod
    def _invalid_result(word: str, reason: str) -> Dict[str, Any]:
        return {
            "word": word,
            "is_valid": False,
            "definitions": [],
            "synonyms": [],
            "word_forms": [],
            "suggestions": [],
            "reason": reason,
            "source": "merriam_webster",
        }

    @staticmethod
    def _parse_response(word: str, data: Any) -> Dict[str, Any]:
        if not isinstance(data, list) or not data:
            return MerriamWebsterValidator._invalid_result(
                word, "Not found in Merriam-Webster Thesaurus"
            )

        if isinstance(data[0], str):
            suggestions = [item for item in data if isinstance(item, str)]
            return {
                "word": word,
                "is_valid": False,
                "definitions": [],
                "synonyms": [],
                "word_forms": [],
                "suggestions": suggestions[:10],
                "reason": "Not found in Merriam-Webster Thesaurus",
                "source": "merriam_webster",
            }

        definitions: List[str] = []
        synonyms: List[str] = []
        word_forms: List[str] = []

        for entry in data:
            if not isinstance(entry, dict):
                continue

            meta = entry.get("meta", {})
            if meta.get("id"):
                word_forms.append(str(meta["id"]))

            for def_block in entry.get("def", []):
                for sense in def_block.get("sseq", []):
                    for sense_item in sense:
                        if not isinstance(sense_item, list) or len(sense_item) < 2:
                            continue
                        if sense_item[0] != "sense":
                            continue
                        sense_data = sense_item[1]
                        for dt in sense_data.get("dt", []):
                            if isinstance(dt, list) and dt and dt[0] == "text":
                                text = str(dt[1]).strip()
                                if text and text not in definitions:
                                    definitions.append(text)
                        for syn_group in sense_data.get("syn_list", []):
                            for syn_entry in syn_group:
                                if not isinstance(syn_entry, dict):
                                    continue
                                synonym = syn_entry.get("wd") or syn_entry.get("w", "")
                                if isinstance(synonym, str):
                                    synonym = synonym.strip()
                                if synonym and synonym not in synonyms:
                                    synonyms.append(synonym)

        if not definitions and not synonyms:
            return MerriamWebsterValidator._invalid_result(
                word, "No definitions found in Merriam-Webster Thesaurus response"
            )

        reason = "Found in Merriam-Webster Thesaurus"
        if definitions:
            reason += f" with {len(definitions)} definition(s)"
        if synonyms:
            reason += f" and {len(synonyms)} synonym(s)"

        return {
            "word": word,
            "is_valid": True,
            "definitions": definitions[:5],
            "synonyms": synonyms[:10],
            "word_forms": word_forms[:5],
            "suggestions": [],
            "reason": reason,
            "source": "merriam_webster",
            "source_url": f"https://www.merriam-webster.com/thesaurus/{word}",
        }

    async def validate_word(self, word: str, *, use_quota: bool = True) -> Dict[str, Any]:
        word = word.strip().lower()

        if not word or not word.isalpha():
            return self._invalid_result(word, "Invalid word format (must contain only letters)")

        if not self.is_configured():
            return self._invalid_result(word, "Merriam-Webster API key not configured")

        if word in self.cache:
            self.cache_hits += 1
            return self.cache[word]

        if use_quota and not self.has_quota():
            return self._invalid_result(
                word,
                f"Merriam-Webster daily quota exhausted ({self.daily_limit}/day)",
            )

        self.cache_misses += 1

        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

        url = f"{THESAURUS_URL}/{word}"
        params = {"key": self.api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    self._last_request_time = time.time()

                    if response.status == 200:
                        data = await response.json()
                        result = self._parse_response(word, data)
                        if use_quota:
                            self._consume_quota()
                        self.cache[word] = result
                        return result

                    if response.status == 404:
                        result = self._invalid_result(
                            word, "Not found in Merriam-Webster Thesaurus"
                        )
                        if use_quota:
                            self._consume_quota()
                        self.cache[word] = result
                        return result

                    body = await response.text()
                    logger.warning(
                        "Merriam-Webster API status %s for '%s': %s",
                        response.status,
                        word,
                        body[:200],
                    )
                    return self._invalid_result(
                        word, f"Merriam-Webster API error: HTTP {response.status}"
                    )
        except Exception as exc:
            logger.error("Merriam-Webster request failed for '%s': %s", word, exc)
            return self._invalid_result(word, f"Merriam-Webster network error: {exc}")

    async def validate_words_batch(
        self, words: List[str], max_concurrent: int = 5
    ) -> Dict[str, Any]:
        if not words:
            return {
                "total_words": 0,
                "valid_words": 0,
                "invalid_words": 0,
                "results": [],
            }

        semaphore = asyncio.Semaphore(max(1, max_concurrent))

        async def _validate_one(item: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.validate_word(item)

        results = await asyncio.gather(*[_validate_one(word) for word in words])
        valid_count = sum(1 for result in results if result["is_valid"])

        return {
            "total_words": len(results),
            "valid_words": valid_count,
            "invalid_words": len(results) - valid_count,
            "results": results,
        }
