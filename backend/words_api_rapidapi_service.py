"""
Words API client via RapidAPI (wordsapiv1.p.rapidapi.com).

Endpoints:
  GET /words/{word}
  GET /words/{word}/{detail}  — synonyms, rhymes, frequency, examples, etc.
  GET /words?letterPattern=...
  GET /words?random=true

Docs: https://rapidapi.com/dpventures/api/wordsapi
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote, urlencode

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://wordsapiv1.p.rapidapi.com"
DEFAULT_HOST = "wordsapiv1.p.rapidapi.com"


class WordsApiRapidapiService:
    """Look up words via Words API on RapidAPI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        rapidapi_host: Optional[str] = None,
    ):
        self.api_key = (api_key or os.getenv("WORDS_API_RAPIDAPI_KEY") or "").strip()
        if self.api_key == "your-rapidapi-key-here":
            self.api_key = ""
        self.base_url = (
            base_url or os.getenv("WORDS_API_RAPIDAPI_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self.rapidapi_host = (
            rapidapi_host or os.getenv("WORDS_API_RAPIDAPI_HOST", DEFAULT_HOST)
        ).strip()
        self.enrich_details = (
            os.getenv("WORDS_API_RAPIDAPI_ENRICH_DETAILS", "true").lower() == "true"
        )
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limit_delay = float(os.getenv("WORDS_API_RAPIDAPI_DELAY", "0.35"))
        self._last_request_time = 0.0

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.rapidapi_host,
            "Accept": "application/json",
        }

    async def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

    async def _request(
        self,
        path: str,
        *,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "ok": False,
                "status": 0,
                "data": None,
                "error": "Words API (RapidAPI) is not configured (WORDS_API_RAPIDAPI_KEY)",
            }

        await self._throttle()
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}/{path.lstrip('/')}{query}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=self._headers(), timeout=25
                ) as response:
                    self._last_request_time = time.time()
                    body: Any
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
            logger.error("Words API request failed for %s: %s", url, exc)
            return {"ok": False, "status": 0, "data": None, "error": str(exc)}

    async def get_word(self, word: str) -> Dict[str, Any]:
        return await self._request(f"words/{quote(word.strip().lower())}")

    async def get_word_detail(self, word: str, detail: str) -> Dict[str, Any]:
        word_key = word.strip().lower()
        detail_key = detail.strip().lower()
        return await self._request(f"words/{quote(word_key)}/{quote(detail_key)}")

    async def get_word_synonyms(self, word: str) -> Dict[str, Any]:
        return await self.get_word_detail(word, "synonyms")

    async def get_word_rhymes(self, word: str) -> Dict[str, Any]:
        return await self.get_word_detail(word, "rhymes")

    async def get_word_frequency(self, word: str) -> Dict[str, Any]:
        return await self.get_word_detail(word, "frequency")

    async def search_words(
        self,
        *,
        letter_pattern: Optional[str] = None,
        **params: str,
    ) -> Dict[str, Any]:
        query: Dict[str, str] = dict(params)
        if letter_pattern:
            query["letterPattern"] = letter_pattern
        return await self._request("words", params=query or None)

    async def get_random_word(self, **params: str) -> Dict[str, Any]:
        query = {"random": "true", **params}
        return await self._request("words", params=query)

    @staticmethod
    def extract_definition(data: Optional[Dict[str, Any]]) -> str:
        if not isinstance(data, dict):
            return ""
        results = data.get("results") or []
        if not isinstance(results, list):
            return ""
        for item in results:
            if not isinstance(item, dict):
                continue
            definition = (item.get("definition") or "").strip()
            if definition:
                return definition
        return ""

    async def get_random_daily_word(self, *, max_attempts: int = 6) -> Dict[str, Any]:
        """Random word from Words API with first definition for Daily Safe Word UI."""
        last_error = "Words API random word failed"
        patterns = (
            "^[a-z]{5,10}$",
            "^[a-z]{4,12}$",
            None,
        )

        for pattern in patterns:
            for _ in range(3):
                params: Dict[str, str] = {"random": "true"}
                if pattern:
                    params["letterPattern"] = pattern
                payload = await self._request("words", params=params)
                if not payload.get("ok") or not isinstance(payload.get("data"), dict):
                    last_error = payload.get("error") or last_error
                    continue

                data = payload["data"]
                word = str(data.get("word") or "").strip().lower()
                if not word or " " in word or not word.replace("-", "").isalpha():
                    last_error = "Skipped non-single-word random result"
                    continue

                definition = self.extract_definition(data)
                if not definition:
                    full = await self.get_word(word)
                    if full.get("ok") and isinstance(full.get("data"), dict):
                        definition = self.extract_definition(full["data"])

                if definition:
                    return {
                        "ok": True,
                        "status": 200,
                        "word": word,
                        "definition": definition,
                        "data": data,
                        "error": None,
                    }

                last_error = "No definition in Words API random response"

        return {
            "ok": False,
            "status": 0,
            "word": "",
            "definition": "",
            "error": last_error,
        }

    @staticmethod
    def _invalid_result(word: str, reason: str) -> Dict[str, Any]:
        return {
            "word": word,
            "is_valid": False,
            "definitions": [],
            "synonyms": [],
            "antonyms": [],
            "rhymes": [],
            "word_forms": [],
            "examples": [],
            "pronunciations": [],
            "frequency": None,
            "frequency_details": {},
            "etymology": "",
            "origin_language": "",
            "first_known_use": "",
            "reason": reason,
            "source": "words_api_rapidapi",
        }

    @staticmethod
    def _collect_strings(value: Any, *, limit: int = 20) -> List[str]:
        items: List[str] = []
        seen: Set[str] = set()
        if isinstance(value, list):
            for entry in value:
                text = str(entry).strip()
                key = text.lower()
                if text and key not in seen:
                    seen.add(key)
                    items.append(text)
        elif isinstance(value, str) and value.strip():
            items.append(value.strip())
        return items[:limit]

    @classmethod
    def _parse_rhymes(cls, data: Any) -> List[str]:
        rhymes: List[str] = []
        seen: Set[str] = set()
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "word":
                    continue
                for item in cls._collect_strings(value, limit=50):
                    lowered = item.lower()
                    if lowered not in seen:
                        seen.add(lowered)
                        rhymes.append(item)
        return rhymes[:20]

    @classmethod
    def _parse_frequency(cls, data: Any) -> tuple[Optional[float], Dict[str, Any]]:
        if isinstance(data, dict):
            details = {k: v for k, v in data.items() if k != "word"}
            score = data.get("frequency")
            if score is None and "zipf" in data:
                score = data.get("zipf")
            try:
                return (float(score) if score is not None else None, details)
            except (TypeError, ValueError):
                return (None, details)
        if isinstance(data, (int, float)):
            return (float(data), {})
        return (None, {})

    @classmethod
    def _parse_word_payload(cls, word: str, data: Dict[str, Any]) -> Dict[str, Any]:
        results = data.get("results") or []
        if not isinstance(results, list) or not results:
            return cls._invalid_result(word, "Not found in Words API (RapidAPI)")

        definitions: List[str] = []
        examples: List[str] = []
        synonyms: List[str] = []
        antonyms: List[str] = []
        word_forms: List[str] = []
        pronunciations: List[Dict[str, str]] = []
        seen_def: Set[str] = set()
        seen_syn: Set[str] = set()
        seen_ant: Set[str] = set()
        seen_form: Set[str] = set()

        for item in results:
            if not isinstance(item, dict):
                continue
            definition = (item.get("definition") or "").strip()
            if definition:
                pos = (item.get("partOfSpeech") or "").strip()
                label = f"({pos}) {definition}" if pos else definition
                if label not in seen_def:
                    seen_def.add(label)
                    definitions.append(label)

            pos = (item.get("partOfSpeech") or "").strip()
            if pos and pos not in seen_form:
                seen_form.add(pos)
                word_forms.append(pos)

            for syn in item.get("synonyms") or []:
                key = str(syn).strip().lower()
                if key and key not in seen_syn and key != word.lower():
                    seen_syn.add(key)
                    synonyms.append(str(syn).strip())

            for ant in item.get("antonyms") or []:
                key = str(ant).strip().lower()
                if key and key not in seen_ant and key != word.lower():
                    seen_ant.add(key)
                    antonyms.append(str(ant).strip())

            example = (item.get("example") or "").strip()
            if example and example not in examples:
                examples.append(example)

        pronunciation = data.get("pronunciation") or {}
        if isinstance(pronunciation, dict):
            for key, value in pronunciation.items():
                ipa = str(value).strip()
                if ipa:
                    prefix = str(key).replace("_", " ").title()
                    pronunciations.append(
                        {
                            "prefix": prefix if prefix != "All" else "IPA",
                            "ipa": ipa,
                            "url": "",
                        }
                    )
        elif isinstance(pronunciation, str) and pronunciation.strip():
            pronunciations.append(
                {"prefix": "IPA", "ipa": pronunciation.strip(), "url": ""}
            )

        syllables = data.get("syllables") or {}
        if isinstance(syllables, dict):
            syllable_list = syllables.get("list") or []
            if syllable_list:
                word_forms.append(
                    f"syllables: {'-'.join(str(s) for s in syllable_list)}"
                )

        frequency, frequency_details = cls._parse_frequency(data.get("frequency"))

        if not definitions:
            return cls._invalid_result(
                word, "No definitions in Words API (RapidAPI) response"
            )

        reason = (
            f"Found in Words API (RapidAPI) with {len(definitions)} definition(s)"
        )
        if synonyms:
            reason += f" and {len(synonyms)} synonym(s)"

        source_url = f"{DEFAULT_BASE_URL}/words/{quote(word)}"

        return {
            "word": word,
            "is_valid": True,
            "definitions": definitions[:8],
            "synonyms": synonyms[:15],
            "antonyms": antonyms[:15],
            "rhymes": [],
            "word_forms": word_forms[:8],
            "examples": examples[:5],
            "pronunciations": pronunciations[:4],
            "frequency": frequency,
            "frequency_details": frequency_details,
            "etymology": "",
            "origin_language": "",
            "first_known_use": "",
            "reason": reason,
            "source": "words_api_rapidapi",
            "source_url": source_url,
            "dictionary_url": source_url,
            "summary": definitions[0],
        }

    def _merge_detail_into_result(
        self, result: Dict[str, Any], detail: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not payload.get("ok") or not isinstance(payload.get("data"), dict):
            return result

        data = payload["data"]
        detail_key = detail.lower()

        if detail_key == "synonyms":
            extra = self._collect_strings(data.get("synonyms"), limit=15)
            merged = list(result.get("synonyms") or [])
            seen = {s.lower() for s in merged}
            for syn in extra:
                if syn.lower() not in seen and syn.lower() != result.get("word", ""):
                    merged.append(syn)
                    seen.add(syn.lower())
            result["synonyms"] = merged[:15]
        elif detail_key == "rhymes":
            result["rhymes"] = self._parse_rhymes(data)
        elif detail_key == "frequency":
            score, details = self._parse_frequency(data)
            if score is not None:
                result["frequency"] = score
            if details:
                result["frequency_details"] = details
        elif detail_key == "effect":
            # Not a documented detail type; store raw payload when API returns data.
            result.setdefault("words_api_details", {})["effect"] = data
        else:
            result.setdefault("words_api_details", {})[detail_key] = data

        return result

    async def validate_word(self, word: str) -> Dict[str, Any]:
        word = word.strip().lower()
        if not word or not word.isalpha():
            return self._invalid_result(
                word, "Invalid word format (must contain only letters)"
            )
        if not self.is_configured():
            return self._invalid_result(
                word, "Words API (RapidAPI) is not configured (WORDS_API_RAPIDAPI_KEY)"
            )

        if word in self.cache:
            self.cache_hits += 1
            return self.cache[word]

        self.cache_misses += 1
        base = await self.get_word(word)
        if not base.get("ok") or not isinstance(base.get("data"), dict):
            status = base.get("status", 0)
            if status in (404, 400):
                result = self._invalid_result(
                    word, "Not found in Words API (RapidAPI)"
                )
            else:
                result = self._invalid_result(
                    word,
                    base.get("error")
                    or f"Words API (RapidAPI) error: HTTP {status}",
                )
            self.cache[word] = result
            return result

        result = self._parse_word_payload(word, base["data"])

        if self.enrich_details and result.get("is_valid"):
            detail_calls = [
                ("synonyms", self.get_word_synonyms(word)),
                ("effect", self.get_word_detail(word, "effect")),
                ("rhymes", self.get_word_rhymes(word)),
                ("frequency", self.get_word_frequency(word)),
            ]
            detail_results = await asyncio.gather(
                *(call for _, call in detail_calls), return_exceptions=True
            )
            for (detail_name, _), detail_payload in zip(detail_calls, detail_results):
                if isinstance(detail_payload, Exception):
                    logger.warning(
                        "Words API detail '%s' failed for '%s': %s",
                        detail_name,
                        word,
                        detail_payload,
                    )
                    continue
                result = self._merge_detail_into_result(
                    result, detail_name, detail_payload
                )

            if result.get("rhymes"):
                result["reason"] += f", {len(result['rhymes'])} rhyme(s)"
            if result.get("frequency") is not None:
                result["reason"] += f", frequency {result['frequency']}"

        self.cache[word] = result
        return result

    def get_cache_stats(self) -> Dict[str, Any]:
        total = self.cache_hits + self.cache_misses
        rate = f"{(self.cache_hits / total * 100):.1f}%" if total > 0 else "0.0%"
        return {
            "configured": self.is_configured(),
            "base_url": self.base_url,
            "rapidapi_host": self.rapidapi_host,
            "enrich_details": self.enrich_details,
            "cached_words": len(self.cache),
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "cache_hit_rate": rate,
        }
