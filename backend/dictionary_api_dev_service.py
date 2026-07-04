"""
Free Dictionary API client (dictionaryapi.dev / Wiktionary-backed).

API: https://api.dictionaryapi.dev/api/v2/entries/en/{word}
No API key required. Respect rate limits (use modest concurrency).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"


class DictionaryApiDevService:
    """Look up words via the free dictionaryapi.dev REST API."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (
            base_url or os.getenv("DICTIONARY_API_DEV_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limit_delay = float(os.getenv("DICTIONARY_API_DEV_DELAY", "0.15"))
        self._last_request_time = 0.0

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
            "source": "dictionary_api_dev",
        }

    @staticmethod
    def _parse_response(word: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not data or not isinstance(data, list):
            return DictionaryApiDevService._invalid_result(
                word, "Not found in Dictionary API (dictionaryapi.dev)"
            )

        entry = data[0]
        definitions: List[str] = []
        examples: List[str] = []
        synonyms: List[str] = []
        word_forms: List[str] = []
        pronunciations: List[Dict[str, str]] = []
        seen_syn: set[str] = set()
        seen_pron: set[tuple[str, str]] = set()

        for meaning in entry.get("meanings") or []:
            pos = (meaning.get("partOfSpeech") or "").strip()
            if pos and pos not in word_forms:
                word_forms.append(pos)

            for syn in meaning.get("synonyms") or []:
                key = str(syn).strip().lower()
                if key and key not in seen_syn and key != word.lower():
                    seen_syn.add(key)
                    synonyms.append(str(syn).strip())

            for def_block in meaning.get("definitions") or []:
                definition = (def_block.get("definition") or "").strip()
                if definition and definition not in definitions:
                    definitions.append(definition)
                example = (def_block.get("example") or "").strip()
                if example and example not in examples:
                    examples.append(example)
                for syn in def_block.get("synonyms") or []:
                    key = str(syn).strip().lower()
                    if key and key not in seen_syn and key != word.lower():
                        seen_syn.add(key)
                        synonyms.append(str(syn).strip())

        phonetic = (entry.get("phonetic") or "").strip().strip("/")
        if phonetic:
            pronunciations.append({"prefix": "IPA", "ipa": phonetic, "url": ""})

        for index, item in enumerate(entry.get("phonetics") or []):
            ipa = (item.get("text") or "").strip().strip("/")
            if not ipa:
                continue
            audio = (item.get("audio") or "").strip()
            prefix = "US" if audio.endswith("-us.mp3") else ("UK" if "uk" in audio else "IPA")
            key = (prefix, ipa)
            if key in seen_pron:
                continue
            seen_pron.add(key)
            pronunciations.append({"prefix": prefix, "ipa": ipa, "url": audio})

        source_urls = [
            str(url).strip()
            for url in (entry.get("sourceUrls") or [])
            if str(url).strip()
        ]
        wiktionary_url = next(
            (url for url in source_urls if "wiktionary.org" in url),
            source_urls[0] if source_urls else "",
        )

        if not definitions:
            return DictionaryApiDevService._invalid_result(
                word, "No definitions in Dictionary API response"
            )

        reason = f"Found in Dictionary API (dictionaryapi.dev) with {len(definitions)} definition(s)"
        if synonyms:
            reason += f" and {len(synonyms)} synonym(s)"

        return {
            "word": word,
            "is_valid": True,
            "definitions": definitions[:5],
            "synonyms": synonyms[:15],
            "word_forms": word_forms[:5],
            "examples": examples[:5],
            "pronunciations": pronunciations[:4],
            "etymology": "",
            "origin_language": "",
            "first_known_use": "",
            "reason": reason,
            "source": "dictionary_api_dev",
            "source_url": wiktionary_url,
            "dictionary_url": wiktionary_url,
            "source_urls": source_urls,
        }

    async def validate_word(self, word: str) -> Dict[str, Any]:
        word = word.strip().lower()
        if not word or not word.isalpha():
            return self._invalid_result(
                word, "Invalid word format (must contain only letters)"
            )

        if word in self.cache:
            self.cache_hits += 1
            return self.cache[word]

        self.cache_misses += 1
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

        url = f"{self.base_url}/{quote(word)}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    self._last_request_time = time.time()
                    if response.status == 200:
                        data = await response.json()
                        result = self._parse_response(word, data)
                        self.cache[word] = result
                        return result
                    if response.status == 404:
                        result = self._invalid_result(
                            word, "Not found in Dictionary API (dictionaryapi.dev)"
                        )
                        self.cache[word] = result
                        return result
                    body = await response.text()
                    logger.warning(
                        "Dictionary API dev HTTP %s for '%s': %s",
                        response.status,
                        word,
                        body[:200],
                    )
                    return self._invalid_result(
                        word, f"Dictionary API error: HTTP {response.status}"
                    )
        except Exception as exc:
            logger.error("Dictionary API dev request failed for '%s': %s", word, exc)
            return self._invalid_result(word, f"Dictionary API network error: {exc}")

    async def validate_words_batch(
        self, words: List[str], max_concurrent: int = 10
    ) -> Dict[str, Any]:
        if not words:
            return {
                "total_words": 0,
                "valid_words": 0,
                "invalid_words": 0,
                "results": [],
            }

        semaphore = asyncio.Semaphore(max(1, max_concurrent))

        async def _one(item: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.validate_word(item)

        results = await asyncio.gather(*[_one(word) for word in words])
        valid_count = sum(1 for result in results if result["is_valid"])
        return {
            "total_words": len(results),
            "valid_words": valid_count,
            "invalid_words": len(results) - valid_count,
            "results": results,
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        total = self.cache_hits + self.cache_misses
        rate = f"{(self.cache_hits / total * 100):.1f}%" if total > 0 else "0.0%"
        return {
            "base_url": self.base_url,
            "cached_words": len(self.cache),
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "cache_hit_rate": rate,
        }
