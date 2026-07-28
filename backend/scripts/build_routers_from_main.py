"""Build router modules from legacy main.py (run once from backend/)."""
from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
MAIN = BACKEND / "main.py"
OUT_DIR = BACKEND / "api" / "routers"

HEADER = '''"""Route handlers (split from legacy main.py)."""
from typing import List, Optional
import asyncio
import random
import time

from fastapi import APIRouter, HTTPException, Query

from api import dependencies as deps
from api.schemas.word import (
    AddWordReq,
    AddWordResponse,
    AddWordsReq,
    BasicSearchResult,
    CleanupReq,
    FreeDictionaryLookupRequest,
    RemoveWordReq,
    RemoveWordsReq,
    ValidateWordRequest,
)
from dictionary_source_config import get_enrich_source_flags, get_portal_source_flags
from puzzle_solver import match_anagram, match_regex
from puzzle_solver import match_pattern as advanced_match_pattern

router = APIRouter()

'''

REPLACEMENTS = [
    (r"\bglobal words_list, words_set, word_stats\b", ""),
    (r"\btotal_api_requests\b", "deps.total_api_requests"),
    (r"\bword_manager\b", "deps.word_manager"),
    (r"\bnhost_service\b", "deps.nhost_service"),
    (r"\badvanced_word_filter_service\b", "deps.advanced_word_filter_service"),
    (r"\bword_lookup_orchestrator\b", "deps.word_lookup_orchestrator"),
    (r"\bunified_lookup\b", "deps.unified_lookup"),
    (r"\bfreedictionary_service\b", "deps.freedictionary_service"),
    (r"\bwords_api_rapidapi_service\b", "deps.words_api_rapidapi_service"),
    (r"\bword_game_db_service\b", "deps.word_game_db_service"),
    (r"\bdatamuse_service\b", "deps.datamuse_service"),
    (r"\bdaily_scramble_service\b", "deps.daily_scramble_service"),
    (r"\bdaily_safe_explore_service\b", "deps.daily_safe_explore_service"),
    (r"\bdaily_word_challenge_service\b", "deps.daily_word_challenge_service"),
    (r"\bwords_list\b", "deps.words_list"),
    (r"\bwords_set\b", "deps.words_set"),
    (r"\bword_stats\b", "deps.word_stats"),
    (r"\bthread_pool\b", "deps.thread_pool"),
    (r"\bprocess_pool\b", "deps.process_pool"),
    (r"\blogger\b", "deps.logger"),
    (r"\bfilter_words_concurrent\b", "deps.filter_words_concurrent"),
    (r"\bfilter_words_simple\b", "deps.filter_words_simple"),
    (r"\bload_words_concurrent\b", "deps.load_words_concurrent"),
]

SPLITS = [
    ("words.py", "# WORD QUERY ENDPOINTS", "# OXFORD DICTIONARY & SYNONYM ENDPOINTS"),
    (
        "words_mutations.py",
        "# OXFORD DICTIONARY & SYNONYM ENDPOINTS",
        "# STORAGE & CLOUD CONFIGURATION ENDPOINTS",
    ),
    (
        "storage.py",
        "# STORAGE & CLOUD CONFIGURATION ENDPOINTS",
        '@app.get("/word-game-db/categories")',
    ),
    (
        "integrations.py",
        '@app.get("/word-game-db/categories")',
        '@app.get("/datamuse/words")',
    ),
    ("datamuse.py", '@app.get("/datamuse/words")', "if __name__"),
]


def extract(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


def transform(body: str) -> str:
    body = re.sub(r"^@app\.(get|post|put|delete|patch)", r"@router.\1", body, flags=re.MULTILINE)
    for pattern, repl in REPLACEMENTS:
        body = re.sub(pattern, repl, body)
    # sync globals after mutations
    body = body.replace(
        "deps.words_list = deps.word_manager.words_list\n        deps.words_set = deps.word_manager.words_set",
        "deps.sync_word_globals_from_manager()",
    )
    return body


def main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, start, end in SPLITS:
        block = transform(extract(text, start, end))
        (OUT_DIR / filename).write_text(HEADER + block + "\n", encoding="utf-8")
        print("wrote", filename)


if __name__ == "__main__":
    main()
