"""
Oxford Dictionaries API v2 client and word validator.

API docs: https://developer.oxforddictionaries.com/documentation
URL pattern: {base}/{endpoint}/{language_code}/{word_id}

Headers: app_id, app_key
Free/sandbox tier: typically 500 requests/day (configurable).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://od-api.oxforddictionaries.com/api/v2"
SANDBOX_BASE_URL = "https://od-api-sandbox.oxforddictionaries.com/api/v2"
DEFAULT_USAGE_FILE = Path(__file__).resolve().parent / "oxford_dictionaries_api_usage.json"
DEFAULT_DAILY_LIMIT = 500

VALID_ENDPOINTS = ("entries", "thesaurus", "sentences", "words", "pronunciations")
VALID_LANGUAGES = ("en-us", "en-gb", "en")


class OxfordDictionariesApiValidator:
    """Validate and look up words using the official Oxford Dictionaries API v2."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        language: str = "en-gb",
        base_url: Optional[str] = None,
        daily_limit: int = DEFAULT_DAILY_LIMIT,
        usage_file: Optional[Path] = None,
    ):
        self.app_id = app_id or os.getenv("OXFORD_DICTIONARIES_APP_ID")
        self.app_key = app_key or os.getenv("OXFORD_DICTIONARIES_APP_KEY")
        self.language = os.getenv("OXFORD_DICTIONARIES_LANGUAGE", language)
        if self.language not in VALID_LANGUAGES:
            raise ValueError(f"language must be one of {VALID_LANGUAGES}")

        env_base = os.getenv("OXFORD_DICTIONARIES_API_BASE")
        self.base_url = (base_url or env_base or DEFAULT_BASE_URL).rstrip("/")
        self.daily_limit = int(os.getenv("OXFORD_DICTIONARIES_DAILY_LIMIT", daily_limit))
        self.usage_file = Path(
            usage_file or os.getenv("OXFORD_DICTIONARIES_USAGE_FILE", DEFAULT_USAGE_FILE)
        )
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limit_delay = 0.1
        self._last_request_time = 0.0

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "app_id": self.app_id or "",
            "app_key": self.app_key or "",
            "Accept": "application/json",
        }

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
            "base_url": self.base_url,
            "language": self.language,
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

    def build_url(
        self,
        endpoint: str,
        word_id: str,
        language: Optional[str] = None,
    ) -> str:
        if endpoint not in VALID_ENDPOINTS:
            raise ValueError(f"endpoint must be one of {VALID_ENDPOINTS}")
        lang = language or self.language
        if lang not in VALID_LANGUAGES:
            raise ValueError(f"language must be one of {VALID_LANGUAGES}")
        encoded_word = quote(word_id.strip().lower(), safe="")
        return f"{self.base_url}/{endpoint}/{lang}/{encoded_word}"

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
            "reason": reason,
            "source": "oxford_dictionaries_api",
        }

    @staticmethod
    def _parse_entries_response(word: str, data: Dict[str, Any]) -> Dict[str, Any]:
        results = data.get("results", [])
        if not results:
            return OxfordDictionariesApiValidator._invalid_result(
                word, "Not found in Oxford Dictionaries API"
            )

        definitions: List[str] = []
        examples: List[str] = []
        word_forms: List[str] = []
        synonyms: List[str] = []
        pronunciations: List[Dict[str, str]] = []
        etymology = ""
        origin_language = ""
        first_known_use = ""
        seen_pron: set[tuple[str, str]] = set()

        for result in results:
            for lexical_entry in result.get("lexicalEntries", []):
                category = lexical_entry.get("lexicalCategory", {})
                category_text = category.get("text") or category.get("id")
                if category_text and category_text not in word_forms:
                    word_forms.append(str(category_text))

                for pron in lexical_entry.get("pronunciations", []):
                    ipa = (
                        pron.get("phoneticSpelling")
                        or pron.get("text")
                        or ""
                    ).strip().strip("/")
                    if not ipa:
                        continue
                    dialects = pron.get("dialects") or []
                    prefix = str(dialects[0]).upper() if dialects else "IPA"
                    audio_url = pron.get("audioFile") or ""
                    key = (prefix, ipa)
                    if key in seen_pron:
                        continue
                    seen_pron.add(key)
                    pronunciations.append(
                        {"prefix": prefix, "ipa": ipa, "url": audio_url}
                    )

                for entry in lexical_entry.get("entries", []):
                    for ety in entry.get("etymologies", []):
                        text = ety.get("text") if isinstance(ety, dict) else str(ety)
                        text = (text or "").strip()
                        if text and not etymology:
                            etymology = text
                            from_match = re.search(
                                r"(?:from|via)\s+([A-Za-z][\w\s-]{1,40})",
                                text,
                                flags=re.IGNORECASE,
                            )
                            if from_match:
                                origin_language = from_match.group(1).strip().rstrip(".,;")
                    for sense in entry.get("senses", []):
                        for definition in sense.get("definitions", []):
                            if isinstance(definition, str) and definition not in definitions:
                                definitions.append(definition)
                        for example in sense.get("examples", []):
                            text = example.get("text") if isinstance(example, dict) else str(example)
                            if text and text not in examples:
                                examples.append(text)
                        for synonym_group in sense.get("synonyms", []):
                            for synonym in synonym_group:
                                if isinstance(synonym, str) and synonym not in synonyms:
                                    synonyms.append(synonym)

        if not definitions and not word_forms:
            return OxfordDictionariesApiValidator._invalid_result(
                word, "No definitions found in Oxford Dictionaries API response"
            )

        reason = f"Found in Oxford Dictionaries API ({word})"
        if definitions:
            reason += f" with {len(definitions)} definition(s)"
        if examples:
            reason += f" and {len(examples)} example(s)"

        return {
            "word": word,
            "is_valid": True,
            "definitions": definitions[:5],
            "synonyms": synonyms[:10],
            "word_forms": word_forms[:5],
            "examples": examples[:5],
            "pronunciations": pronunciations[:4],
            "etymology": etymology,
            "origin_language": origin_language,
            "first_known_use": first_known_use,
            "reason": reason,
            "source": "oxford_dictionaries_api",
            "raw_id": data.get("id"),
            "source_url": f"https://www.oxfordlearnersdictionaries.com/definition/english/{word}",
            "oxford_url": f"https://www.oxfordlearnersdictionaries.com/definition/english/{word}",
        }

    async def fetch_endpoint(
        self,
        word: str,
        endpoint: str = "entries",
        language: Optional[str] = None,
        *,
        use_quota: bool = True,
    ) -> Dict[str, Any]:
        """Call any supported Oxford Dictionaries API endpoint."""
        word = word.strip().lower()
        cache_key = f"{endpoint}:{language or self.language}:{word}"

        if not word or not word.isalpha():
            return self._invalid_result(word, "Invalid word format (must contain only letters)")

        if not self.is_configured():
            return self._invalid_result(word, "Oxford Dictionaries API credentials not configured")

        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]

        if use_quota and not self.has_quota():
            return self._invalid_result(
                word,
                f"Oxford Dictionaries API daily quota exhausted ({self.daily_limit}/day)",
            )

        self.cache_misses += 1
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

        url = self.build_url(endpoint, word, language=language)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers(), timeout=15) as response:
                    self._last_request_time = time.time()
                    body = await response.text()

                    if response.status == 200:
                        data = json.loads(body)
                        if endpoint == "entries":
                            result = self._parse_entries_response(word, data)
                        else:
                            result = {
                                "word": word,
                                "is_valid": True,
                                "definitions": [],
                                "synonyms": [],
                                "word_forms": [],
                                "examples": [],
                                "reason": f"Oxford Dictionaries API {endpoint} lookup succeeded",
                                "source": "oxford_dictionaries_api",
                                "endpoint": endpoint,
                                "raw": data,
                            }
                        if use_quota:
                            self._consume_quota()
                        self.cache[cache_key] = result
                        return result

                    if response.status == 404:
                        result = self._invalid_result(
                            word, "Not found in Oxford Dictionaries API"
                        )
                        if use_quota:
                            self._consume_quota()
                        self.cache[cache_key] = result
                        return result

                    logger.warning(
                        "Oxford Dictionaries API %s for '%s': HTTP %s %s",
                        endpoint,
                        word,
                        response.status,
                        body[:200],
                    )
                    return self._invalid_result(
                        word,
                        f"Oxford Dictionaries API error: HTTP {response.status}",
                    )
        except Exception as exc:
            logger.error("Oxford Dictionaries API request failed for '%s': %s", word, exc)
            return self._invalid_result(word, f"Oxford Dictionaries API network error: {exc}")

    async def validate_word(self, word: str, *, use_quota: bool = True) -> Dict[str, Any]:
        """Validate a word using the entries endpoint."""
        return await self.fetch_endpoint(word, endpoint="entries", use_quota=use_quota)

    async def validate_words_batch(
        self, words: List[str], max_concurrent: int = 3
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
