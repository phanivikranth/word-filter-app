"""
Centralized true/false toggles for dictionary API sources and Nhost persistence.

All flags are read from environment variables (see backend/.env.example).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Tuple


def env_bool(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() == "true"


@dataclass(frozen=True)
class SourceFlags:
    merriam_webster: bool = True
    oxford_dictionaries_api: bool = True
    dictionary_api_dev: bool = True
    freedictionary_api_com: bool = True
    words_api_rapidapi: bool = True
    word_game_db: bool = True
    datamuse: bool = True
    oxford_web: bool = True
    freedictionary: bool = True

    def as_dict(self) -> Dict[str, bool]:
        return {
            "merriam_webster": self.merriam_webster,
            "oxford_dictionaries_api": self.oxford_dictionaries_api,
            "dictionary_api_dev": self.dictionary_api_dev,
            "freedictionary_api_com": self.freedictionary_api_com,
            "words_api_rapidapi": self.words_api_rapidapi,
            "word_game_db": self.word_game_db,
            "datamuse": self.datamuse,
            "oxford_web": self.oxford_web,
            "freedictionary": self.freedictionary,
        }

    def filter_order(self, order: Tuple[str, ...]) -> Tuple[str, ...]:
        flags = self.as_dict()
        return tuple(source for source in order if flags.get(source, True))


@dataclass(frozen=True)
class NhostFlags:
    enabled: bool
    use_cache: bool
    save_on_lookup: bool


def get_portal_source_flags() -> SourceFlags:
    """Flags for portal /words/validate and UI enrichment."""
    scraper_fallback = env_bool("UI_USE_SCRAPER_FALLBACK", "true")
    return SourceFlags(
        merriam_webster=env_bool("UI_ALLOW_MERRIAM_WEBSTER", "true"),
        oxford_dictionaries_api=env_bool("UI_ALLOW_OXFORD_DICTIONARIES_API", "true"),
        dictionary_api_dev=env_bool("UI_ALLOW_DICTIONARY_API_DEV", "true"),
        freedictionary_api_com=env_bool("UI_ALLOW_FREE_DICTIONARY_API_COM", "true"),
        words_api_rapidapi=env_bool("UI_ALLOW_WORDS_API_RAPIDAPI", "true"),
        word_game_db=env_bool("UI_ALLOW_WORD_GAME_DB", "true"),
        datamuse=env_bool("UI_ALLOW_DATAMUSE", "true"),
        oxford_web=scraper_fallback
        and env_bool("UI_ALLOW_OXFORD_WEB_SCRAPER", "true"),
        freedictionary=scraper_fallback
        and env_bool("UI_ALLOW_FREEDICTIONARY", "true"),
    )


def get_enrich_source_flags() -> SourceFlags:
    """Flags for scripts/enrich_words_in_nhost.py bulk enrichment."""
    return SourceFlags(
        merriam_webster=env_bool("ENRICH_ALLOW_MERRIAM_WEBSTER", "true"),
        oxford_dictionaries_api=env_bool(
            "ENRICH_ALLOW_OXFORD_DICTIONARIES_API", "true"
        ),
        dictionary_api_dev=env_bool("ENRICH_ALLOW_DICTIONARY_API_DEV", "true"),
        freedictionary_api_com=env_bool(
            "ENRICH_ALLOW_FREE_DICTIONARY_API_COM", "true"
        ),
        words_api_rapidapi=env_bool("ENRICH_ALLOW_WORDS_API_RAPIDAPI", "true"),
        word_game_db=env_bool("ENRICH_ALLOW_WORD_GAME_DB", "true"),
        datamuse=env_bool("ENRICH_ALLOW_DATAMUSE", "true"),
        oxford_web=env_bool("ENRICH_ALLOW_OXFORD_WEB", "true"),
        freedictionary=env_bool("ENRICH_ALLOW_FREEDICTIONARY", "true"),
    )


def get_validate_source_flags() -> SourceFlags:
    """Flags for validate_words.py — try every configured API in order."""
    return SourceFlags(
        merriam_webster=env_bool("VALIDATE_ALLOW_MERRIAM_WEBSTER", "true"),
        oxford_dictionaries_api=env_bool(
            "VALIDATE_ALLOW_OXFORD_DICTIONARIES_API", "true"
        ),
        dictionary_api_dev=env_bool("VALIDATE_ALLOW_DICTIONARY_API_DEV", "true"),
        freedictionary_api_com=env_bool(
            "VALIDATE_ALLOW_FREE_DICTIONARY_API_COM", "true"
        ),
        words_api_rapidapi=env_bool("VALIDATE_ALLOW_WORDS_API_RAPIDAPI", "true"),
        word_game_db=env_bool("VALIDATE_ALLOW_WORD_GAME_DB", "true"),
        datamuse=env_bool("VALIDATE_ALLOW_DATAMUSE", "true"),
        oxford_web=env_bool("VALIDATE_ALLOW_OXFORD_WEB", "true"),
        freedictionary=env_bool("VALIDATE_ALLOW_FREEDICTIONARY", "true"),
    )


def get_nhost_flags() -> NhostFlags:
    return NhostFlags(
        enabled=env_bool("USE_NHOST", "false"),
        use_cache=env_bool("USE_NHOST_CACHE", "true"),
        save_on_lookup=env_bool("USE_NHOST_SAVE", "true"),
    )
