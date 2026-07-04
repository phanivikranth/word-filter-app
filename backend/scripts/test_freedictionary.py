#!/usr/bin/env python3
"""Test TheFreeDictionary scraper for sample words."""

import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from freedictionary_service import FreeDictionaryService

WORDS = sys.argv[1:] or [
    "Feldenkrais",
    "scherenschnitte",
    "knaidel",
    "cymotrichous",
    "apple",
]


async def main() -> None:
    service = FreeDictionaryService()
    for word in WORDS:
        result = await service.lookup_word(word)
        print("=" * 60)
        print(f"Word: {word}")
        print(f"Found: {result['found']} | Source: {result['source']}")
        print(f"Reason: {result.get('reason', '')}")
        if result.get("definitions"):
            print("Definitions:")
            for d in result["definitions"][:3]:
                print(f"  - {d[:200]}")
        if result.get("summary"):
            print(f"Summary:\n  {result['summary']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
