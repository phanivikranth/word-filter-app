#!/usr/bin/env python3
"""
Quick smoke test for Oxford Dictionaries API credentials.

Usage (from backend/):
  venv\\Scripts\\python.exe scripts\\test_oxford_dictionaries_api.py
  venv\\Scripts\\python.exe scripts\\test_oxford_dictionaries_api.py apple xyzzy
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator  # noqa: E402


async def main() -> None:
    words = sys.argv[1:] or ["test", "xyzzy"]
    validator = OxfordDictionariesApiValidator()

    if not validator.is_configured():
        print("Oxford Dictionaries API is not configured.")
        print(f"Add credentials to: {BACKEND_DIR / '.env'}")
        print("  OXFORD_DICTIONARIES_APP_ID=...")
        print("  OXFORD_DICTIONARIES_APP_KEY=...")
        sys.exit(1)

    print(f"Base URL: {validator.base_url}")
    print(f"Language: {validator.language}")
    print(f"Quota: {validator.get_usage_stats()['remaining_today']}/"
          f"{validator.get_usage_stats()['daily_limit']} remaining today\n")

    for word in words:
        url = validator.build_url("entries", word)
        result = await validator.validate_word(word)
        print(f"Word: {word}")
        print(f"  URL: {url}")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Reason: {result['reason']}")
        if result.get("definitions"):
            print(f"  Definition: {result['definitions'][0][:120]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
