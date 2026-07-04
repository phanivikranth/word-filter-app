"""
Daily word scramble: random word from external APIs, shuffled with random.shuffle.
Cached per calendar day (UTC).
"""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE = Path(__file__).resolve().parent / "data" / "daily_scramble_cache.json"


class DailyScrambleService:
    """Build and cache the daily scrambled-word puzzle."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = Path(
            cache_path
            or os.getenv("DAILY_SCRAMBLE_CACHE_FILE", str(DEFAULT_CACHE))
        )

    @staticmethod
    def _today_key() -> str:
        return date.today().isoformat()

    @staticmethod
    def scramble_word(word: str) -> str:
        letters = list(word.lower())
        if len(letters) < 2:
            return word.lower()
        scrambled = letters[:]
        attempts = 0
        while scrambled == letters and attempts < 10:
            random.shuffle(scrambled)
            attempts += 1
        return "".join(scrambled)

    def _load_cache(self) -> Dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read daily scramble cache: %s", exc)
            return {}

    def _save_cache(self, payload: Dict[str, Any]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    @staticmethod
    def _is_suitable_word(word: str) -> bool:
        return bool(word) and word.isalpha() and 4 <= len(word) <= 10

    async def _fetch_random_word(
        self, local_words: Optional[list[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Try APIs in order until a suitable word is found."""
        from datamuse_service import DatamuseService
        from word_game_db_service import WordGameDbService
        from words_api_rapidapi_service import WordsApiRapidapiService

        datamuse = DatamuseService()
        word_game_db = WordGameDbService()
        words_api = WordsApiRapidapiService()

        if word_game_db.is_configured():
            payload = await word_game_db.get_random_word()
            if payload.get("ok"):
                data = payload.get("data") or {}
                word = str(data.get("word") or "").strip().lower()
                if self._is_suitable_word(word):
                    return {
                        "word": word,
                        "hint": str(data.get("hint") or "").strip(),
                        "source": "word_game_db",
                    }

        if words_api.is_configured():
            payload = await words_api.get_random_daily_word()
            if payload.get("ok") and payload.get("word"):
                word = str(payload["word"]).strip().lower()
                if self._is_suitable_word(word):
                    return {
                        "word": word,
                        "hint": payload.get("definition") or "",
                        "source": "words_api_rapidapi",
                    }

        if datamuse.is_configured():
            picked = await datamuse.pick_random_word(min_length=5, max_length=7)
            if picked and picked.get("word"):
                word = str(picked["word"]).strip().lower()
                if self._is_suitable_word(word):
                    return {
                        "word": word,
                        "hint": picked.get("summary") or (
                            picked.get("definitions") or [""]
                        )[0],
                        "source": "datamuse",
                    }

        if local_words:
            candidates = [
                w.lower()
                for w in local_words
                if self._is_suitable_word(str(w).strip().lower())
            ]
            if candidates:
                chosen = random.choice(candidates)
                return {
                    "word": chosen,
                    "hint": "Unscramble this word from our local dictionary.",
                    "source": "local",
                }

        return None

    async def get_daily_scramble(
        self, local_words: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        today = self._today_key()
        cached = self._load_cache()
        if cached.get("date") == today and cached.get("word"):
            return {
                "success": True,
                "date": today,
                "word": cached["word"],
                "scrambled": cached["scrambled"],
                "hint": cached.get("hint", ""),
                "source": cached.get("source", "cache"),
                "cached": True,
            }

        fetched = await self._fetch_random_word(local_words)
        if not fetched:
            return {
                "success": False,
                "date": today,
                "error": "Could not fetch a random word from configured APIs",
            }

        word = fetched["word"]
        scrambled = self.scramble_word(word)
        payload = {
            "date": today,
            "word": word,
            "scrambled": scrambled,
            "hint": fetched.get("hint", ""),
            "source": fetched.get("source", "api"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_cache(payload)

        return {
            "success": True,
            "date": today,
            "word": word,
            "scrambled": scrambled,
            "hint": payload["hint"],
            "source": payload["source"],
            "cached": False,
        }
