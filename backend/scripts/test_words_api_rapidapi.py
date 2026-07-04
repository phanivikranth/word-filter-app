#!/usr/bin/env python3
"""Smoke test for Words API (RapidAPI) integration."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")

from oxford_validator import OxfordValidator
from unified_word_lookup import UnifiedWordLookup
from words_api_rapidapi_service import WordsApiRapidapiService

TEST_WORDS = ("succedaneum", "pococurante", "prospicience", "soliloquy")


async def main() -> int:
    service = WordsApiRapidapiService()
    print("=== WordsApiRapidapiService ===")
    print(f"configured={service.is_configured()}")
    if not service.is_configured():
        print("SKIP: set WORDS_API_RAPIDAPI_KEY in backend/.env")
        return 0

    failures = 0
    for word in TEST_WORDS:
        result = await service.validate_word(word)
        if not result.get("is_valid"):
            print(f"{word} FAIL: {result.get('reason')}")
            failures += 1
            continue
        print(
            f"{word} OK defs={len(result.get('definitions', []))} "
            f"syns={len(result.get('synonyms', []))} "
            f"pron={len(result.get('pronunciations', []))}"
        )
        if result.get("definitions"):
            print(f"  def[0]: {result['definitions'][0][:80]}...")

    print("\n=== UnifiedWordLookup (words_api_rapidapi only) ===")
    lookup = UnifiedWordLookup(
        OxfordValidator(),
        words_api_rapidapi_service=service,
    )
    for word in TEST_WORDS:
        result = await lookup.lookup_word(
            word, source_order=("words_api_rapidapi",)
        )
        if not result.get("is_valid"):
            print(f"{word} unified FAIL: {result.get('reason')}")
            failures += 1
            continue
        print(
            f"{word} {result.get('validation_source')} "
            f"defs={len(result.get('definitions', []))} "
            f"syns={len(result.get('synonyms', []))}"
        )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
