#!/usr/bin/env python3
"""Smoke test for Word Game DB API integration."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")

from oxford_validator import OxfordValidator
from unified_word_lookup import UnifiedWordLookup
from word_game_db_service import WordGameDbService

TEST_WORD = "gecko"


async def main() -> int:
    service = WordGameDbService()
    print("=== WordGameDbService ===")
    print(f"configured={service.is_configured()}")
    failures = 0

    categories = await service.get_categories()
    print(f"categories ok={categories.get('ok')} count={len(categories.get('data') or [])}")

    random_word = await service.get_random_word()
    print(f"random ok={random_word.get('ok')} word={(random_word.get('data') or {}).get('word')}")

    listed = await service.list_words(min_letters=5, max_letters=5, limit=2, offset=0)
    words = (listed.get("data") or {}).get("words") or []
    print(f"list ok={listed.get('ok')} returned={len(words)}")

    validated = await service.validate_word(TEST_WORD)
    if not validated.get("is_valid"):
        print(f"validate '{TEST_WORD}' FAIL: {validated.get('reason')}")
        failures += 1
    else:
        print(
            f"validate '{TEST_WORD}' OK hint={validated.get('definitions', [''])[0][:60]}"
        )

    lookup = UnifiedWordLookup(OxfordValidator(), word_game_db_service=service)
    unified = await lookup.lookup_word(TEST_WORD, source_order=("word_game_db",))
    if not unified.get("is_valid"):
        print(f"unified FAIL: {unified.get('reason')}")
        failures += 1
    else:
        print(f"unified OK source={unified.get('validation_source')}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
