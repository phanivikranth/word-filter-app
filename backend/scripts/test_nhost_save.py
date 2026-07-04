#!/usr/bin/env python3
"""Smoke test: Nhost save (insert) and update via save_word_entry."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")

from nhost_service import NhostWordService

TEST_WORD = "zzznhostsaveprobe"


async def main() -> int:
    nhost = NhostWordService()
    print("=== Nhost save/update test ===")
    print(f"USE_NHOST={nhost.enabled}")
    print(f"USE_NHOST_CACHE={nhost.use_cache_on_lookup}")
    print(f"USE_NHOST_SAVE={nhost.save_on_lookup}")

    if not nhost.is_configured():
        print("SKIP: Nhost not configured")
        return 1
    if not nhost.save_on_lookup:
        print("SKIP: USE_NHOST_SAVE=false — set to true to test persistence")
        return 0

    initial = {
        "word": TEST_WORD,
        "is_valid": True,
        "definitions": ["Initial probe definition for Nhost save test."],
        "synonyms": ["probe-alpha"],
        "pronunciations": [{"prefix": "Test", "ipa": "/probe/"}],
        "examples": ["This is a probe example."],
        "validation_source": "test_script",
        "summary": "Initial probe definition for Nhost save test.",
    }
    await nhost.save_word_entry(initial)
    after_save = await nhost.lookup_word(TEST_WORD)
    if not after_save or not after_save.get("definitions"):
        print("FAIL: insert — word not found after save")
        return 1
    if after_save["definitions"][0] != initial["definitions"][0]:
        print("FAIL: insert — definition mismatch")
        return 1
    print(f"INSERT OK defs={len(after_save.get('definitions', []))} syns={len(after_save.get('synonyms', []))}")

    updated = {
        "word": TEST_WORD,
        "is_valid": True,
        "definitions": ["Updated probe definition after Nhost upsert."],
        "synonyms": ["probe-alpha", "probe-beta"],
        "pronunciations": [{"prefix": "Test", "ipa": "/probe-updated/"}],
        "examples": ["Updated probe example sentence."],
        "validation_source": "test_script",
        "summary": "Updated probe definition after Nhost upsert.",
    }
    await nhost.save_word_entry(updated)
    after_update = await nhost.lookup_word(TEST_WORD)
    if not after_update:
        print("FAIL: update — word not found")
        return 1
    if after_update["definitions"][0] != updated["definitions"][0]:
        print("FAIL: update — definition not refreshed")
        print(f"  got: {after_update['definitions']}")
        return 1
    if len(after_update.get("synonyms", [])) < 2:
        print("FAIL: update — synonyms not merged")
        return 1
    print(
        f"UPDATE OK defs={len(after_update.get('definitions', []))} "
        f"syns={len(after_update.get('synonyms', []))} "
        f"pron={len(after_update.get('pronunciations', []))}"
    )
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
