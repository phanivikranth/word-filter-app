"""
Judicious word lookup: Nhost cache first, quota APIs second, scrapers last.

Portal lookups return immediately when Nhost has definitions; missing fields are
filled asynchronously in the background and persisted to Nhost.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set

from nhost_service import NhostWordService
from word_enrichment_service import WordEnrichmentService
from word_entry_utils import (
    is_ui_ready,
    merge_word_entries,
    missing_fields,
    missing_optional_fields,
    missing_required_fields,
)

logger = logging.getLogger(__name__)

AioEnricher = Optional[Callable[..., Any]]


class WordLookupOrchestrator:
    """Coordinate Nhost cache + external dictionary sources with rate-limit awareness."""

    def __init__(
        self,
        enrichment_service: WordEnrichmentService,
        nhost_service: NhostWordService,
        synonym_enricher: AioEnricher = None,
    ):
        self.enrichment = enrichment_service
        self.nhost = nhost_service
        self.synonym_enricher = synonym_enricher
        self.enrich_synonyms_enabled = (
            os.getenv("UI_ENRICH_SYNONYMS", "true").lower() == "true"
        )
        self.use_mw_for_synonyms = (
            os.getenv("UI_USE_MERRIAM_FOR_SYNONYMS", "false").lower() == "true"
        )
        self.background_enrich_enabled = (
            os.getenv("UI_BACKGROUND_ENRICH", "true").lower() == "true"
        )
        self._background_inflight: Set[str] = set()

    def _is_cache_complete(self, cached: Dict[str, Any]) -> bool:
        if not cached.get("definitions"):
            return False
        return not missing_required_fields(cached)

    def _schedule_background_enrich(
        self, word_key: str, existing: Dict[str, Any]
    ) -> None:
        if not self.background_enrich_enabled:
            return
        gaps = missing_fields(existing)
        if not gaps:
            return
        if word_key in self._background_inflight:
            return
        asyncio.create_task(self._background_enrich(word_key, dict(existing), gaps))

    async def _enrich_synonyms_if_needed(
        self, word: str, oxford_data: dict, *, existing_synonyms: List[str]
    ) -> dict:
        if existing_synonyms or not self.enrich_synonyms_enabled:
            return {
                "synonyms": existing_synonyms,
                "count": len(existing_synonyms),
                "sources": {},
            }
        if not self.synonym_enricher:
            return {"synonyms": [], "count": 0, "sources": {}}

        use_mw = (
            self.use_mw_for_synonyms
            and self.enrichment.unified_lookup.merriam_validator.is_configured()
            and self.enrichment.unified_lookup.merriam_validator.has_quota()
        )
        return await self.synonym_enricher(word, oxford_data, use_merriam=use_mw)

    async def _background_enrich(
        self, word_key: str, existing: Dict[str, Any], gaps: List[str]
    ) -> None:
        if word_key in self._background_inflight:
            return
        self._background_inflight.add(word_key)
        try:
            logger.info(
                "Background enrich started for '%s' (gaps: %s)",
                word_key,
                gaps,
            )
            result = await self.enrichment.enrich_word(
                word_key,
                existing=existing,
                required_fields=gaps,
                stop_when_only_optional_remain=False,
            )

            if (
                self.enrich_synonyms_enabled
                and not result.get("synonyms")
                and self.synonym_enricher
            ):
                syn_data = await self._enrich_synonyms_if_needed(
                    word_key, {}, existing_synonyms=[]
                )
                if syn_data.get("synonyms"):
                    result = merge_word_entries(
                        result,
                        {"synonyms": syn_data["synonyms"], "word": word_key},
                        word=word_key,
                    )

            if missing_fields(result) != gaps:
                await self._persist(result)
                logger.info(
                    "Background enrich finished for '%s' (remaining: %s)",
                    word_key,
                    missing_fields(result),
                )
            else:
                logger.info(
                    "Background enrich made no progress for '%s'",
                    word_key,
                )
        except Exception as exc:
            logger.warning(
                "Background enrich failed for '%s': %s", word_key, exc
            )
        finally:
            self._background_inflight.discard(word_key)

    async def lookup_for_ui(self, word: str) -> Dict[str, Any]:
        word_key = word.strip().lower()
        cached: Optional[Dict[str, Any]] = None

        if self.nhost.is_configured() and self.nhost.use_cache_on_lookup:
            cached = await self.nhost.lookup_word(word_key)

        if cached and self._is_cache_complete(cached):
            optional_gaps = missing_optional_fields(cached)
            if optional_gaps:
                self._schedule_background_enrich(word_key, cached)
            logger.info("Nhost cache hit (complete) for '%s'", word_key)
            return cached

        if cached and is_ui_ready(cached):
            required_gaps = missing_required_fields(cached)
            logger.info(
                "Fast Nhost return for '%s' (required gaps: %s, optional: %s)",
                word_key,
                required_gaps,
                missing_optional_fields(cached),
            )
            self._schedule_background_enrich(word_key, cached)
            return cached

        if cached and cached.get("definitions"):
            logger.info(
                "Nhost partial hit for '%s' — blocking enrich for: %s",
                word_key,
                missing_required_fields(cached),
            )
            result = await self.enrichment.enrich_word(
                word_key,
                existing=cached,
                required_fields=missing_required_fields(cached),
                stop_when_only_optional_remain=True,
            )
        else:
            logger.info("Nhost miss for '%s' — fetching from external sources", word_key)
            result = await self.enrichment.enrich_word(
                word_key,
                existing=cached,
                stop_when_only_optional_remain=True,
            )

        if (
            self.enrich_synonyms_enabled
            and not result.get("synonyms")
            and self.synonym_enricher
        ):
            syn_data = await self._enrich_synonyms_if_needed(
                word_key, {}, existing_synonyms=[]
            )
            if syn_data.get("synonyms"):
                result = merge_word_entries(
                    result,
                    {"synonyms": syn_data["synonyms"], "word": word_key},
                    word=word_key,
                )
                result["synonym_sources"] = syn_data.get("sources", {})

        await self._persist(result)

        remaining = missing_fields(result)
        if remaining:
            self._schedule_background_enrich(word_key, result)

        return result

    async def _persist(self, result: Dict[str, Any]) -> None:
        if not self.nhost.is_configured():
            return
        if not self.nhost.save_on_lookup:
            logger.info(
                "Skipping Nhost persist for '%s' (USE_NHOST_SAVE=false)",
                result.get("word"),
            )
            return
        if not result.get("definitions") and not result.get("is_valid"):
            return
        try:
            await self.nhost.save_word_entry(result)
            logger.info("Persisted '%s' to Nhost", result.get("word"))
        except Exception as exc:
            logger.warning(
                "Failed to persist '%s' to Nhost: %s", result.get("word"), exc
            )
