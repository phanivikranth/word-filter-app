"""
Advanced word list filtering via Words API (primary) and Word Game DB (fallback).
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import string
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_WORDS_API_LIMIT = 100


def build_letter_pattern(
    *,
    contains: Optional[str] = None,
    starts_with: Optional[str] = None,
    ends_with: Optional[str] = None,
    exact_length: Optional[int] = None,
) -> Optional[str]:
    """Build a Words API letterPattern regex from UI filter fields."""
    contains_key = (contains or "").strip().lower()
    starts = (starts_with or "").strip().lower()
    ends = (ends_with or "").strip().lower()

    if not contains_key and not starts and not ends:
        return None

    if exact_length and starts and not contains_key and not ends:
        gap = exact_length - len(starts)
        if gap >= 0:
            return f"^{re.escape(starts)}.{{{gap}}}$"

    if exact_length and ends and not contains_key and not starts:
        gap = exact_length - len(ends)
        if gap >= 0:
            return f"^.{{{gap}}}{re.escape(ends)}$"

    if exact_length and starts and ends and not contains_key:
        gap = exact_length - len(starts) - len(ends)
        if gap >= 0:
            return f"^{re.escape(starts)}.{{{gap}}}{re.escape(ends)}$"

    pattern = "^"
    if starts:
        pattern += re.escape(starts)
    if contains_key:
        if starts or ends:
            pattern += f".*{re.escape(contains_key)}"
        else:
            pattern += f".*{re.escape(contains_key)}.*"
    elif not starts and not ends:
        pattern += ".*"
    else:
        pattern += ".*"
    if ends:
        pattern += re.escape(ends)
    pattern += "$"
    return pattern


def extract_words_api_list(data: Any) -> List[str]:
    """Parse Words API search/list response into word strings."""
    if not isinstance(data, dict):
        return []

    results = data.get("results")
    if isinstance(results, dict):
        items = results.get("data") or []
        if isinstance(items, list):
            return [
                str(word).strip().lower()
                for word in items
                if word and str(word).strip().isalpha()
            ]

    word = data.get("word")
    if word and str(word).strip().isalpha():
        return [str(word).strip().lower()]

    return []


def extract_word_game_db_list(data: Any) -> List[str]:
    if not isinstance(data, dict):
        return []
    words = data.get("words") or []
    if not isinstance(words, list):
        return []
    result: List[str] = []
    for entry in words:
        if isinstance(entry, dict):
            text = str(entry.get("word") or "").strip().lower()
        else:
            text = str(entry).strip().lower()
        if text and text.isalpha():
            result.append(text)
    return result


def apply_local_filters(
    words: List[str],
    *,
    contains: Optional[str] = None,
    starts_with: Optional[str] = None,
    ends_with: Optional[str] = None,
    exact_length: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> List[str]:
    contains_key = (contains or "").strip().lower()
    starts = (starts_with or "").strip().lower()
    ends = (ends_with or "").strip().lower()

    filtered: List[str] = []
    seen: set[str] = set()
    for word in words:
        key = word.lower()
        if key in seen:
            continue
        if contains_key and contains_key not in key:
            continue
        if starts and not key.startswith(starts):
            continue
        if ends and not key.endswith(ends):
            continue
        if exact_length is not None and len(key) != exact_length:
            continue
        if min_length is not None and len(key) < min_length:
            continue
        if max_length is not None and len(key) > max_length:
            continue
        seen.add(key)
        filtered.append(key)
    return filtered


class AdvancedWordFilterService:
    """Filter word lists using Words API with Word Game DB fallback."""

    def __init__(self, words_api_service=None, word_game_db_service=None):
        self.words_api_service = words_api_service
        self.word_game_db_service = word_game_db_service

    def _get_words_api(self):
        if self.words_api_service is None:
            from words_api_rapidapi_service import WordsApiRapidapiService

            self.words_api_service = WordsApiRapidapiService()
        return self.words_api_service

    def _get_word_game_db(self):
        if self.word_game_db_service is None:
            from word_game_db_service import WordGameDbService

            self.word_game_db_service = WordGameDbService()
        return self.word_game_db_service

    def _has_active_filters(
        self,
        *,
        contains: Optional[str],
        starts_with: Optional[str],
        ends_with: Optional[str],
        exact_length: Optional[int],
        min_length: Optional[int],
        max_length: Optional[int],
        letter_pattern: Optional[str],
    ) -> bool:
        return bool(
            (contains or "").strip()
            or (starts_with or "").strip()
            or (ends_with or "").strip()
            or exact_length is not None
            or min_length is not None
            or max_length is not None
            or (letter_pattern or "").strip()
        )

    async def _fetch_words_api(
        self,
        *,
        letter_pattern: Optional[str],
        exact_length: Optional[int],
        min_length: Optional[int],
        max_length: Optional[int],
        limit: int,
        diversify: bool = False,
    ) -> Dict[str, Any]:
        service = self._get_words_api()
        if not service.is_configured():
            return {"ok": False, "words": [], "error": "Words API not configured"}

        params: Dict[str, str] = {"limit": str(min(limit, MAX_WORDS_API_LIMIT))}
        if letter_pattern:
            params["letterPattern"] = letter_pattern
        if exact_length is not None and not letter_pattern:
            params["letters"] = str(exact_length)
        if min_length is not None:
            params["lettersMin"] = str(min_length)
        if max_length is not None:
            params["lettersMax"] = str(max_length)

        # Words API page 1 is always alphabetical (a…); rotate pages for length-only queries.
        if diversify or (
            not letter_pattern and (exact_length or min_length or max_length)
        ):
            params["page"] = str(random.randint(1, 40))

        payload = await service.search_words(**params)
        if not payload.get("ok"):
            return {
                "ok": False,
                "words": [],
                "error": payload.get("error") or "Words API filter failed",
            }

        words = extract_words_api_list(payload.get("data"))
        return {"ok": True, "words": words[:limit], "source": "words_api_rapidapi"}

    async def _fetch_words_api_by_letters(
        self, *, length: int, limit: int
    ) -> Dict[str, Any]:
        """Fetch diverse words by sampling several random starting letters."""
        service = self._get_words_api()
        if not service.is_configured():
            return {"ok": False, "words": [], "error": "Words API not configured"}

        if length < 2:
            return await self._fetch_words_api(
                exact_length=length, letter_pattern=None, min_length=None,
                max_length=None, limit=limit, diversify=True,
            )

        sample_count = min(12, max(4, limit // 8))
        letters = random.sample(string.ascii_lowercase, sample_count)
        per_letter = max(8, min(20, (limit // sample_count) + 2))
        gap = length - 1

        async def fetch_for_letter(letter: str) -> List[str]:
            pattern = f"^{letter}.{{{gap}}}$"
            payload = await service.search_words(
                letter_pattern=pattern,
                limit=str(per_letter),
                page=str(random.randint(1, 5)),
            )
            if payload.get("ok"):
                return extract_words_api_list(payload.get("data"))
            return []

        batches = await asyncio.gather(
            *(fetch_for_letter(letter) for letter in letters),
            return_exceptions=True,
        )

        merged: List[str] = []
        seen: set[str] = set()
        for batch in batches:
            if isinstance(batch, Exception):
                continue
            for word in batch:
                key = word.lower()
                if key not in seen:
                    seen.add(key)
                    merged.append(key)

        random.shuffle(merged)
        if merged:
            return {
                "ok": True,
                "words": merged[:limit],
                "source": "words_api_rapidapi",
            }
        return {"ok": False, "words": [], "error": "Words API browse returned no words"}

    async def _fetch_word_game_db(
        self,
        *,
        contains: Optional[str],
        starts_with: Optional[str],
        ends_with: Optional[str],
        exact_length: Optional[int],
        min_length: Optional[int],
        max_length: Optional[int],
        limit: int,
    ) -> Dict[str, Any]:
        service = self._get_word_game_db()
        if not service.is_configured():
            return {"ok": False, "words": [], "error": "Word Game DB disabled"}

        min_letters = min_length
        max_letters = max_length
        if exact_length is not None:
            min_letters = exact_length
            max_letters = exact_length

        search_query = (contains or "").strip().lower()
        if search_query and len(search_query) >= 3:
            payload = await service.search_word(search_query, limit=min(limit * 3, 100))
            if payload.get("ok"):
                words = extract_word_game_db_list(payload.get("data"))
                words = apply_local_filters(
                    words,
                    contains=contains,
                    starts_with=starts_with,
                    ends_with=ends_with,
                    exact_length=exact_length,
                    min_length=min_length,
                    max_length=max_length,
                )
                if words:
                    return {
                        "ok": True,
                        "words": words[:limit],
                        "source": "word_game_db",
                    }

        fetch_limit = min(max(limit * 5, 50), 100)
        payload = await service.list_words(
            min_letters=min_letters,
            max_letters=max_letters,
            limit=fetch_limit,
            offset=random.randint(0, 2000),
        )
        if not payload.get("ok"):
            return {
                "ok": False,
                "words": [],
                "error": payload.get("error") or "Word Game DB filter failed",
            }

        words = extract_word_game_db_list(payload.get("data"))
        words = apply_local_filters(
            words,
            contains=contains,
            starts_with=starts_with,
            ends_with=ends_with,
            exact_length=exact_length,
            min_length=min_length,
            max_length=max_length,
        )
        random.shuffle(words)
        return {"ok": True, "words": words[:limit], "source": "word_game_db"}

    async def _fetch_default_words(self, limit: int) -> Dict[str, Any]:
        """Populate browse list with diverse words (not just alphabetical page 1)."""
        limit = min(max(limit, 1), MAX_WORDS_API_LIMIT)
        browse_length = random.choice([5, 6, 7, 8])

        words_api = self._get_words_api()
        if words_api.is_configured():
            result = await self._fetch_words_api_by_letters(
                length=browse_length, limit=limit
            )
            if result.get("ok") and result.get("words"):
                return {
                    "ok": True,
                    "words": result["words"][:limit],
                    "source": "words_api_rapidapi",
                    "mode": "browse",
                }

        word_game_db = self._get_word_game_db()
        if word_game_db.is_configured():
            payload = await word_game_db.list_words(
                min_letters=4,
                max_letters=10,
                limit=limit,
                offset=random.randint(0, 3000),
            )
            if payload.get("ok"):
                words = extract_word_game_db_list(payload.get("data"))
                random.shuffle(words)
                if words:
                    return {
                        "ok": True,
                        "words": words[:limit],
                        "source": "word_game_db",
                        "mode": "browse",
                    }

            random_payload = await word_game_db.get_random_word()
            if random_payload.get("ok") and isinstance(random_payload.get("data"), dict):
                entry = random_payload["data"]
                word = str(entry.get("word") or "").strip().lower()
                if word:
                    return {
                        "ok": True,
                        "words": [word],
                        "source": "word_game_db",
                        "mode": "browse",
                    }

        return {
            "ok": False,
            "words": [],
            "error": "No word browse API available",
        }

    async def filter_words(
        self,
        *,
        contains: Optional[str] = None,
        starts_with: Optional[str] = None,
        ends_with: Optional[str] = None,
        exact_length: Optional[int] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        letter_pattern: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        limit = min(max(int(limit or 100), 1), MAX_WORDS_API_LIMIT)

        if not self._has_active_filters(
            contains=contains,
            starts_with=starts_with,
            ends_with=ends_with,
            exact_length=exact_length,
            min_length=min_length,
            max_length=max_length,
            letter_pattern=letter_pattern,
        ):
            result = await self._fetch_default_words(limit)
            return {
                "success": result.get("ok", False),
                "words": result.get("words") or [],
                "count": len(result.get("words") or []),
                "source": result.get("source", ""),
                "mode": result.get("mode", "browse"),
                "error": result.get("error"),
            }

        pattern = (letter_pattern or "").strip() or build_letter_pattern(
            contains=contains,
            starts_with=starts_with,
            ends_with=ends_with,
            exact_length=exact_length,
        )

        user_letter_anchor = bool((starts_with or "").strip())
        length_only = (
            not pattern
            and not user_letter_anchor
            and not (contains or "").strip()
            and not (ends_with or "").strip()
            and (exact_length is not None or min_length is not None or max_length is not None)
        )

        if length_only and exact_length is not None:
            words_api_result = await self._fetch_words_api_by_letters(
                length=exact_length, limit=limit
            )
        else:
            words_api_result = await self._fetch_words_api(
                letter_pattern=pattern,
                exact_length=exact_length if not pattern else None,
                min_length=min_length,
                max_length=max_length,
                limit=limit,
                diversify=length_only,
            )
        if words_api_result.get("ok") and words_api_result.get("words"):
            words = apply_local_filters(
                words_api_result["words"],
                contains=contains if pattern else None,
                starts_with=starts_with if pattern else None,
                ends_with=ends_with if pattern else None,
            )
            return {
                "success": True,
                "words": words[:limit],
                "count": len(words[:limit]),
                "source": "words_api_rapidapi",
                "mode": "filter",
                "letterPattern": pattern,
            }

        logger.info(
            "Words API filter unavailable (%s); trying Word Game DB fallback",
            words_api_result.get("error"),
        )

        fallback = await self._fetch_word_game_db(
            contains=contains,
            starts_with=starts_with,
            ends_with=ends_with,
            exact_length=exact_length,
            min_length=min_length,
            max_length=max_length,
            limit=limit,
        )
        if fallback.get("ok") and fallback.get("words"):
            return {
                "success": True,
                "words": fallback["words"][:limit],
                "count": len(fallback["words"][:limit]),
                "source": "word_game_db",
                "mode": "filter",
                "letterPattern": pattern,
                "fallback": True,
            }

        # Last resort: return empty success with hint rather than hard 503 when APIs rate-limit
        if words_api_result.get("ok") and not words_api_result.get("words"):
            return {
                "success": True,
                "words": [],
                "count": 0,
                "source": "words_api_rapidapi",
                "mode": "filter",
                "letterPattern": pattern,
            }

        error = (
            words_api_result.get("error")
            or fallback.get("error")
            or "Advanced word filter failed"
        )
        return {
            "success": False,
            "words": [],
            "count": 0,
            "source": "",
            "mode": "filter",
            "error": error,
        }
