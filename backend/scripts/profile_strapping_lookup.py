"""Profile lookup timing for a single word (default: strapping)."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


async def main() -> None:
    from nhost_service import NhostWordService
    from word_entry_utils import missing_fields, missing_optional_fields, missing_required_fields
    from word_lookup_orchestrator import WordLookupOrchestrator
    from word_enrichment_service import WordEnrichmentService
    from main import (
        unified_lookup,
        nhost_service,
        synonym_service,
        _enrich_synonyms,
    )

    word = "strapping"

    print("=== Nhost direct lookup ===")
    t0 = time.perf_counter()
    cached = await nhost_service.lookup_word(word)
    t1 = time.perf_counter()
    print(f"Nhost lookup: {(t1 - t0):.2f}s")
    if cached:
        print(f"  definitions: {len(cached.get('definitions') or [])}")
        print(f"  synonyms: {len(cached.get('synonyms') or [])}")
        print(f"  pronunciations: {len(cached.get('pronunciations') or [])}")
        print(f"  validation_source: {cached.get('validation_source')}")
        gaps = missing_fields(cached)
        print(f"  missing_fields: {gaps}")
    else:
        print("  NOT FOUND in Nhost")

    enrichment = WordEnrichmentService(
        unified_lookup,
        synonym_enricher=_enrich_synonyms,
    )
    orchestrator = WordLookupOrchestrator(
        enrichment,
        nhost_service,
        synonym_enricher=_enrich_synonyms,
    )

    print("\n=== Per-source enrichment (portal order) ===")
    order = enrichment._portal_source_order()
    print(f"Source order: {order}")
    merged = dict(cached) if cached else {"word": word}
    for source in order:
        gaps_before = missing_fields(merged)
        if not gaps_before:
            print("All fields filled — stopping")
            break
        t_src = time.perf_counter()
        fetched = await enrichment._fetch_source(word, source, flags=enrichment.portal_flags)
        elapsed = time.perf_counter() - t_src
        status = "hit" if fetched else "miss/skip"
        print(f"  {source}: {elapsed:.2f}s ({status})")
        if fetched:
            from word_entry_utils import merge_word_entries

            merged = merge_word_entries(merged, fetched, word=word)
            print(f"    gaps after: {missing_fields(merged)}")

    print("\n=== Full orchestrator lookup_for_ui (should be fast — no blocking API fan-out) ===")
    t2 = time.perf_counter()
    result = await orchestrator.lookup_for_ui(word)
    t3 = time.perf_counter()
    print(f"Total lookup_for_ui: {(t3 - t2):.2f}s")
    print(f"  sources_used: {result.get('sources_used', [])}")
    print(f"  validation_source: {result.get('validation_source')}")

    print("\n=== Cache completeness check ===")
    from word_lookup_orchestrator import WordLookupOrchestrator as WLO
    orch = WLO(enrichment, nhost_service)
    if cached:
        complete = orch._is_cache_complete(cached)
        print(f"_is_cache_complete (required fields only): {complete}")
        print(f"  missing_required: {missing_required_fields(cached)}")
        print(f"  missing_optional: {missing_optional_fields(cached)}")


if __name__ == "__main__":
    asyncio.run(main())
