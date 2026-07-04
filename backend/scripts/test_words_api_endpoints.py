#!/usr/bin/env python3
"""Test all Words API (RapidAPI) endpoints for a single word."""

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

from words_api_rapidapi_service import WordsApiRapidapiService

WORD = "absolute"


async def main() -> int:
    service = WordsApiRapidapiService()
    if not service.is_configured():
        print("SKIP: WORDS_API_RAPIDAPI_KEY not set")
        return 1

    tests = [
        ("GET /words/{word}", lambda: service.get_word(WORD)),
        ("GET /words/{word}/synonyms", lambda: service.get_word_detail(WORD, "synonyms")),
        ("GET /words/{word}/effect", lambda: service.get_word_detail(WORD, "effect")),
        ("GET /words/{word}/rhymes", lambda: service.get_word_detail(WORD, "rhymes")),
        ("GET /words/{word}/frequency", lambda: service.get_word_detail(WORD, "frequency")),
        (
            "GET /words?letterPattern=^a.{4}$",
            lambda: service.search_words(letter_pattern="^a.{4}$"),
        ),
        ("GET /words?random=true", lambda: service.get_random_word()),
    ]

    failures = 0
    for label, call in tests:
        try:
            result = await call()
            ok = result.get("ok", False)
            status = result.get("status", "?")
            preview = json.dumps(result.get("data"), default=str)[:200]
            print(f"{'OK' if ok else 'FAIL'} [{status}] {label}")
            print(f"  {preview}...")
            if not ok:
                failures += 1
        except Exception as exc:
            print(f"FAIL {label}: {exc}")
            failures += 1
        await asyncio.sleep(0.5)

    merged = await service.validate_word(WORD)
    print(f"\nvalidate_word('{WORD}'): valid={merged.get('is_valid')} "
          f"defs={len(merged.get('definitions', []))} "
          f"syns={len(merged.get('synonyms', []))} "
          f"rhymes={len(merged.get('rhymes', []))} "
          f"freq={merged.get('frequency')}")
    if not merged.get("is_valid"):
        failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
