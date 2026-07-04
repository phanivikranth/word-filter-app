"""
Fetch and merge full word entries (definitions, synonyms, pronunciations, etymology, links).
Quota APIs first; scrapers fill remaining gaps.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from dictionary_source_config import (
    SourceFlags,
    get_enrich_source_flags,
    get_portal_source_flags,
)
from unified_word_lookup import (
    BULK_VALIDATE_SOURCE_ORDER,
    UnifiedWordLookup,
    WEB_UI_SOURCE_ORDER,
)
from word_entry_utils import (
    merge_word_entries,
    missing_fields,
    only_optional_gaps_remain,
)

logger = logging.getLogger(__name__)

AioEnricher = Optional[Callable[..., Any]]


class WordEnrichmentService:
    """Accumulate word data from multiple dictionary sources."""

    def __init__(
        self,
        unified_lookup: UnifiedWordLookup,
        *,
        synonym_enricher: AioEnricher = None,
        use_merriam_for_synonyms: bool = False,
        portal_flags: Optional[SourceFlags] = None,
        bulk_flags: Optional[SourceFlags] = None,
    ):
        self.unified_lookup = unified_lookup
        self.synonym_enricher = synonym_enricher
        self.use_merriam_for_synonyms = use_merriam_for_synonyms
        self.portal_flags = portal_flags or get_portal_source_flags()
        self.bulk_flags = bulk_flags or get_enrich_source_flags()
        self.enrich_synonyms = (
            os.getenv("ENRICH_SYNONYMS", "true").lower() == "true"
        )

    def _build_source_order(
        self, flags: SourceFlags, *, for_bulk: bool
    ) -> Tuple[str, ...]:
        order: List[str] = []
        mw = self.unified_lookup.merriam_validator
        oda = self.unified_lookup.oxford_api_validator

        if for_bulk:
            if flags.dictionary_api_dev:
                order.append("dictionary_api_dev")
            if flags.freedictionary_api_com:
                order.append("freedictionary_api_com")
            if flags.word_game_db:
                order.append("word_game_db")
            if flags.datamuse:
                order.append("datamuse")
            if flags.words_api_rapidapi:
                order.append("words_api_rapidapi")
            if flags.oxford_web:
                order.append("oxford_web")
            if flags.freedictionary:
                order.append("freedictionary")
            if flags.merriam_webster and mw.is_configured() and mw.has_quota():
                order.append("merriam_webster")
            if flags.oxford_dictionaries_api and oda.is_configured() and oda.has_quota():
                order.append("oxford_dictionaries_api")
            base = tuple(order) if order else BULK_VALIDATE_SOURCE_ORDER
        else:
            if flags.merriam_webster and mw.is_configured() and mw.has_quota():
                order.append("merriam_webster")
            if flags.oxford_dictionaries_api and oda.is_configured() and oda.has_quota():
                order.append("oxford_dictionaries_api")
            if flags.words_api_rapidapi:
                order.append("words_api_rapidapi")
            if flags.dictionary_api_dev:
                order.append("dictionary_api_dev")
            if flags.freedictionary_api_com:
                order.append("freedictionary_api_com")
            if flags.word_game_db:
                order.append("word_game_db")
            if flags.datamuse:
                order.append("datamuse")
            if flags.oxford_web:
                order.append("oxford_web")
            if flags.freedictionary:
                order.append("freedictionary")
            base = tuple(order) if order else WEB_UI_SOURCE_ORDER

        return flags.filter_order(base)

    def _portal_source_order(self) -> Tuple[str, ...]:
        return self._build_source_order(self.portal_flags, for_bulk=False)

    def _bulk_source_order(self) -> Tuple[str, ...]:
        return self._build_source_order(self.bulk_flags, for_bulk=True)

    async def _fetch_source(
        self, word: str, source: str, *, flags: SourceFlags
    ) -> Optional[Dict[str, Any]]:
        lookup = self.unified_lookup
        if not flags.as_dict().get(source, True):
            return None
        try:
            if source == "merriam_webster":
                if not (
                    lookup.merriam_validator.is_configured()
                    and lookup.merriam_validator.has_quota()
                ):
                    return None
                data = await lookup.merriam_validator.validate_word(word)
            elif source == "oxford_dictionaries_api":
                if not (
                    lookup.oxford_api_validator.is_configured()
                    and lookup.oxford_api_validator.has_quota()
                ):
                    return None
                data = await lookup.oxford_api_validator.validate_word(word)
            elif source == "dictionary_api_dev":
                data = await lookup.dictionary_api_dev_service.validate_word(word)
            elif source == "freedictionary_api_com":
                data = await lookup.freedictionary_api_com_service.validate_word(word)
            elif source == "words_api_rapidapi":
                if not lookup.words_api_rapidapi_service.is_configured():
                    return None
                data = await lookup.words_api_rapidapi_service.validate_word(word)
            elif source == "word_game_db":
                if not lookup.word_game_db_service.is_configured():
                    return None
                data = await lookup.word_game_db_service.validate_word(word)
            elif source == "datamuse":
                if not lookup.datamuse_service.is_configured():
                    return None
                data = await lookup.datamuse_service.validate_word(word)
            elif source == "oxford_web":
                data = await lookup.oxford_validator.validate_word(word)
            elif source == "freedictionary":
                fd = await lookup.freedictionary_service.lookup_word(word)
                data = lookup._from_freedictionary(word, fd)
            else:
                return None

            if not data:
                return None
            normalized = lookup._from_api_result(word, source, data)
            has_content = bool(
                normalized.get("definitions")
                or normalized.get("synonyms")
                or normalized.get("pronunciations")
                or normalized.get("etymology")
                or normalized.get("examples")
            )
            return normalized if has_content else None
        except Exception as exc:
            logger.warning("Source '%s' failed for '%s': %s", source, word, exc)
            return None

    async def enrich_word(
        self,
        word: str,
        *,
        existing: Optional[Dict[str, Any]] = None,
        source_order: Optional[Tuple[str, ...]] = None,
        required_fields: Optional[List[str]] = None,
        source_flags: Optional[SourceFlags] = None,
        stop_when_only_optional_remain: bool = True,
    ) -> Dict[str, Any]:
        word_key = word.strip().lower()
        merged = merge_word_entries(existing, word=word_key)
        flags = source_flags or self.portal_flags
        order = source_order or self._build_source_order(flags, for_bulk=False)
        sources_tried: List[str] = []

        def _still_needed(entry: Dict[str, Any]) -> List[str]:
            gaps = missing_fields(entry)
            if required_fields:
                return [field for field in gaps if field in required_fields]
            return gaps

        def _should_stop_early() -> bool:
            if not stop_when_only_optional_remain:
                return False
            gaps = _still_needed(merged)
            if not gaps:
                return True
            if not merged.get("definitions"):
                return False
            return only_optional_gaps_remain(merged)

        for source in order:
            if not _still_needed(merged):
                break
            if _should_stop_early():
                logger.debug(
                    "Stopping enrich early for '%s' — only optional gaps remain: %s",
                    word_key,
                    _still_needed(merged),
                )
                break
            sources_tried.append(source)
            fetched = await self._fetch_source(word_key, source, flags=flags)
            if not fetched:
                continue
            merged = merge_word_entries(merged, fetched, word=word_key)

        if (
            self.enrich_synonyms
            and not merged.get("synonyms")
            and self.synonym_enricher
            and not _should_stop_early()
        ):
            use_mw = (
                self.use_merriam_for_synonyms
                and self.unified_lookup.merriam_validator.is_configured()
                and self.unified_lookup.merriam_validator.has_quota()
            )
            try:
                syn_data = await self.synonym_enricher(
                    word_key, {}, use_merriam=use_mw
                )
                if syn_data.get("synonyms"):
                    merged = merge_word_entries(
                        merged,
                        {"synonyms": syn_data["synonyms"], "word": word_key},
                        word=word_key,
                    )
            except Exception as exc:
                logger.warning("Synonym enrich failed for '%s': %s", word_key, exc)

        merged["sources_used"] = sources_tried
        if merged.get("definitions"):
            merged["is_valid"] = True
        return merged

    async def enrich_word_bulk(
        self, word: str, existing: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return await self.enrich_word(
            word,
            existing=existing,
            source_order=self._bulk_source_order(),
            source_flags=self.bulk_flags,
        )
