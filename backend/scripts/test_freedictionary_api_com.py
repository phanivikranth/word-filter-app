"""Smoke tests for freedictionaryapi.com integration."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freedictionary_api_com_service import FreeDictionaryApiComService
from oxford_validator import OxfordValidator
from unified_word_lookup import UnifiedWordLookup

TEST_WORDS = ("pococurante", "prospicience", "succedaneum", "hello")


async def main() -> None:
    service = FreeDictionaryApiComService()
    print("=== FreeDictionaryApiComService ===")
    for word in TEST_WORDS:
        result = await service.validate_word(word)
        print(
            word,
            "OK" if result["is_valid"] else "MISS",
            f"defs={len(result.get('definitions', []))}",
            f"syns={len(result.get('synonyms', []))}",
            f"ex={len(result.get('examples', []))}",
            f"pron={len(result.get('pronunciations', []))}",
        )
        if result.get("definitions"):
            print("  def[0]:", result["definitions"][0][:100], "...")

    print("\n=== UnifiedWordLookup (freedictionary_api_com only) ===")
    lookup = UnifiedWordLookup(
        OxfordValidator(),
        freedictionary_api_com_service=service,
    )
    for word in TEST_WORDS:
        result = await lookup.lookup_word(
            word, source_order=("freedictionary_api_com",)
        )
        print(
            word,
            result.get("validation_source"),
            f"defs={len(result.get('definitions', []))}",
            f"syns={len(result.get('synonyms', []))}",
        )


if __name__ == "__main__":
    asyncio.run(main())
