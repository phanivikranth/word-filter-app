"""
Free Dictionary API client (freedictionaryapi.com / Wiktionary-backed).

API: https://freedictionaryapi.com/api/v1/entries/en/{word}
No API key required. CC BY-SA 4.0 — see response source.license.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://freedictionaryapi.com/api/v1/entries/en"


class FreeDictionaryApiComService:
    """Look up words via freedictionaryapi.com REST API."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (
            base_url
            or os.getenv("FREE_DICTIONARY_API_COM_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limit_delay = float(
            os.getenv("FREE_DICTIONARY_API_COM_DELAY", "0.2")
        )
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
            "source": "freedictionary_api_com",
        }

    @staticmethod
    def _pronunciation_prefix(tags: List[str]) -> str:
        cleaned = [str(tag).strip() for tag in (tags or []) if str(tag).strip()]
        return cleaned[0] if cleaned else "IPA"

    @classmethod
    def _parse_response(cls, word: str, data: Dict[str, Any]) -> Dict[str, Any]:
        entries = data.get("entries") or []
        if not entries:
            return cls._invalid_result(
                word, "Not found in Free Dictionary API (freedictionaryapi.com)"
            )

        definitions: List[str] = []
        examples: List[str] = []
        synonyms: List[str] = []
        word_forms: List[str] = []
        pronunciations: List[Dict[str, str]] = []
        seen_def: Set[str] = set()
        seen_syn: Set[str] = set()
        seen_ex: Set[str] = set()
        seen_form: Set[str] = set()
        seen_pron: Set[tuple[str, str]] = set()

        for entry in entries:
            pos = (entry.get("partOfSpeech") or "").strip()
            if pos and pos.lower() not in seen_form:
                seen_form.add(pos.lower())
                word_forms.append(pos)

            for form in entry.get("forms") or []:
                form_word = (form.get("word") or "").strip()
                tags = ", ".join(str(t) for t in (form.get("tags") or []) if t)
                label = f"{tags}: {form_word}" if tags and form_word else form_word
                if label and label.lower() not in seen_form:
                    seen_form.add(label.lower())
                    word_forms.append(label)

            for pron in entry.get("pronunciations") or []:
                ipa = (pron.get("text") or "").strip().strip("/")
                if not ipa:
                    continue
                prefix = cls._pronunciation_prefix(pron.get("tags") or [])
                key = (prefix, ipa)
                if key in seen_pron:
                    continue
                seen_pron.add(key)
                pronunciations.append({"prefix": prefix, "ipa": ipa, "url": ""})

            for syn in entry.get("synonyms") or []:
                text = str(syn).strip()
                key = text.lower()
                if text and key not in seen_syn and key != word.lower():
                    seen_syn.add(key)
                    synonyms.append(text)

            for sense in entry.get("senses") or []:
                definition = (sense.get("definition") or "").strip()
                if definition and definition not in seen_def:
                    seen_def.add(definition)
                    definitions.append(definition)

                for example in sense.get("examples") or []:
                    text = str(example).strip()
                    if text and text not in seen_ex:
                        seen_ex.add(text)
                        examples.append(text)

                for quote in sense.get("quotes") or []:
                    text = (quote.get("text") or "").strip()
                    if text and len(text) > 20 and text not in seen_ex:
                        seen_ex.add(text)
                        examples.append(text)

                for syn in sense.get("synonyms") or []:
                    text = str(syn).strip()
                    key = text.lower()
                    if text and key not in seen_syn and key != word.lower():
                        seen_syn.add(key)
                        synonyms.append(text)

        if not definitions:
            return cls._invalid_result(
                word, "No definitions in Free Dictionary API response"
            )

        source_meta = data.get("source") or {}
        source_url = (source_meta.get("url") or "").strip()
        wiktionary_url = source_url or (
            f"https://en.wiktionary.org/wiki/{quote(word)}"
        )

        reason = (
            f"Found in Free Dictionary API (freedictionaryapi.com) "
            f"with {len(definitions)} definition(s)"
        )
        if synonyms:
            reason += f" and {len(synonyms)} synonym(s)"
        if examples:
            reason += f" and {len(examples)} example(s)"

        return {
            "word": word,
            "is_valid": True,
            "definitions": definitions[:8],
            "synonyms": synonyms[:15],
            "word_forms": word_forms[:8],
            "examples": examples[:5],
            "pronunciations": pronunciations[:6],
            "etymology": "",
            "origin_language": "",
            "first_known_use": "",
            "reason": reason,
            "source": "freedictionary_api_com",
            "source_url": wiktionary_url,
            "dictionary_url": wiktionary_url,
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
        headers = {"Accept": "application/json", "User-Agent": "word-filter-app/1.0"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=20) as response:
                    self._last_request_time = time.time()
                    if response.status == 200:
                        data = await response.json()
                        result = self._parse_response(word, data)
                        self.cache[word] = result
                        return result
                    if response.status == 404:
                        result = self._invalid_result(
                            word,
                            "Not found in Free Dictionary API (freedictionaryapi.com)",
                        )
                        self.cache[word] = result
                        return result
                    body = await response.text()
                    logger.warning(
                        "Free Dictionary API HTTP %s for '%s': %s",
                        response.status,
                        word,
                        body[:200],
                    )
                    return self._invalid_result(
                        word, f"Free Dictionary API error: HTTP {response.status}"
                    )
        except Exception as exc:
            logger.error("Free Dictionary API request failed for '%s': %s", word, exc)
            return self._invalid_result(
                word, f"Free Dictionary API network error: {exc}"
            )

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

        async def _one(item: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.validate_word(item)

        results = await asyncio.gather(*[_one(w) for w in words])
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
