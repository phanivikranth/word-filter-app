#!/usr/bin/env python3
"""Test a single word against all dictionary APIs."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from combined_word_validator import CombinedWordValidator
from merriam_webster_validator import MerriamWebsterValidator
from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator
from oxford_validator import OxfordValidator

WORD = sys.argv[1] if len(sys.argv) > 1 else "scherenschnitte"


async def main() -> None:
    mw = MerriamWebsterValidator()
    oda = OxfordDictionariesApiValidator()
    oxweb = OxfordValidator()
    combined = CombinedWordValidator(oxweb, mw, oda)

    print("=== Configuration ===")
    mw_stats = mw.get_usage_stats()
    oda_stats = oda.get_usage_stats()
    print(f"Merriam-Webster configured: {mw.is_configured()}, quota: {mw_stats['remaining_today']}/{mw_stats['daily_limit']}")
    print(f"Oxford API configured: {oda.is_configured()}, base: {oda.base_url}, lang: {oda.language}")
    print(f"Oxford API quota: {oda_stats['remaining_today']}/{oda_stats['daily_limit']}")
    print()

    apis = [
        ("Merriam-Webster Thesaurus API", mw.validate_word(WORD)),
        ("Oxford Dictionaries API v2 (entries)", oda.validate_word(WORD)),
        ("Oxford Learner's web (scraper)", oxweb.validate_word(WORD)),
    ]

    individual_results = []
    for label, coro in apis:
        print(f"--- {label} ---")
        if "Oxford Dictionaries" in label:
            print(f"  URL: {oda.build_url('entries', WORD)}")
        result = await coro
        individual_results.append((label, result))
        print(f"  Valid: {result['is_valid']}")
        print(f"  Reason: {result['reason']}")
        if result.get("definitions"):
            print(f"  Definition: {result['definitions'][0][:150]}")
        if result.get("synonyms"):
            print(f"  Synonyms: {result['synonyms'][:5]}")
        if result.get("suggestions"):
            print(f"  Suggestions: {result['suggestions'][:5]}")
        print()

    print("--- Combined validator (app flow) ---")
    combined_result = await combined.validate_word(WORD)
    print(f"  Valid: {combined_result['is_valid']}")
    print(f"  Primary source: {combined_result['validation_source']}")
    print(f"  Sources consulted: {combined_result['sources_used']}")
    print(f"  Reason: {combined_result['reason']}")
    print()

    # Extra Oxford API endpoint/language sweep
    print("--- Oxford API: other endpoints / languages ---")
    for lang in ("en-gb", "en-us", "en"):
        for endpoint in ("entries", "thesaurus", "words"):
            validator = OxfordDictionariesApiValidator(language=lang)
            result = await validator.fetch_endpoint(WORD, endpoint=endpoint)
            status = "FOUND" if result["is_valid"] else "NOT FOUND"
            print(f"  {endpoint}/{lang}: {status} — {result['reason'][:70]}")
    print()

    print("=== SUMMARY for", repr(WORD), "===")
    for label, result in individual_results:
        status = "FOUND" if result["is_valid"] else "NOT FOUND"
        print(f"  {label}: {status}")

    found = [label for label, r in individual_results if r["is_valid"]]
    not_found = [label for label, r in individual_results if not r["is_valid"]]
    print()
    if found:
        print("APIs that returned a valid result:", ", ".join(found))
    else:
        print("APIs that returned a valid result: none")
    if not_found:
        print("APIs that did not find the word:", ", ".join(not_found))


if __name__ == "__main__":
    asyncio.run(main())
