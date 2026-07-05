"""
Unified word lookup across all dictionary sources.

Order (first source with usable definitions wins):
  Web UI (default): Merriam-Webster -> Oxford Dictionaries API -> Dictionary API (dictionaryapi.dev) -> Oxford web -> TheFreeDictionary
  Bulk validate_words.py: Dictionary API -> Oxford web -> TheFreeDictionary -> Merriam-Webster -> Oxford Dictionaries API

Returns a stable UI-friendly shape (compatible with OxfordValidation in the frontend).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from dictionary_api_dev_service import DictionaryApiDevService
from dictionary_source_config import (
    SourceFlags,
    get_enrich_source_flags,
    get_portal_source_flags,
)
from api_source_cooldown import get_source_cooldown
from freedictionary_api_com_service import FreeDictionaryApiComService
from freedictionary_service import FreeDictionaryService
from merriam_webster_validator import MerriamWebsterValidator
from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator
from oxford_validator import OxfordValidator
from word_entry_utils import build_links
from datamuse_service import DatamuseService
from word_game_db_service import WordGameDbService
from words_api_rapidapi_service import WordsApiRapidapiService

logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    "merriam_webster": "Merriam-Webster Thesaurus",
    "oxford_dictionaries_api": "Oxford Dictionaries API",
    "dictionary_api_dev": "Dictionary API (Wiktionary)",
    "freedictionary_api_com": "Free Dictionary API",
    "words_api_rapidapi": "Words API (RapidAPI)",
    "word_game_db": "Word Game DB",
    "datamuse": "DataMuse",
    "oxford_web": "Oxford Learner's Dictionary",
    "freedictionary": "TheFreeDictionary",
    "freedictionary_encyclopedia": "TheFreeDictionary Encyclopedia",
    "none": "No source",
}

# Web UI: quota APIs first, then free REST API, then scrapers.
WEB_UI_SOURCE_ORDER = (
    "merriam_webster",
    "oxford_dictionaries_api",
    "words_api_rapidapi",
    "dictionary_api_dev",
    "freedictionary_api_com",
    "word_game_db",
    "datamuse",
    "oxford_web",
    "freedictionary",
)

# Bulk validate_words.py: free API + scrapers first, quota APIs last.
BULK_VALIDATE_SOURCE_ORDER = (
    "dictionary_api_dev",
    "freedictionary_api_com",
    "word_game_db",
    "datamuse",
    "words_api_rapidapi",
    "oxford_web",
    "freedictionary",
    "merriam_webster",
    "oxford_dictionaries_api",
)


class UnifiedWordLookup:
    """Orchestrate all dictionary APIs and return one normalized result."""

    def __init__(
        self,
        oxford_validator: OxfordValidator,
        merriam_validator: Optional[MerriamWebsterValidator] = None,
        oxford_api_validator: Optional[OxfordDictionariesApiValidator] = None,
        dictionary_api_dev_service: Optional[DictionaryApiDevService] = None,
        freedictionary_api_com_service: Optional[FreeDictionaryApiComService] = None,
        words_api_rapidapi_service: Optional[WordsApiRapidapiService] = None,
        word_game_db_service: Optional[WordGameDbService] = None,
        datamuse_service: Optional[DatamuseService] = None,
        freedictionary_service: Optional[FreeDictionaryService] = None,
    ):
        self.oxford_validator = oxford_validator
        self.merriam_validator = merriam_validator or MerriamWebsterValidator()
        self.oxford_api_validator = oxford_api_validator or OxfordDictionariesApiValidator()
        self.dictionary_api_dev_service = (
            dictionary_api_dev_service or DictionaryApiDevService()
        )
        self.freedictionary_api_com_service = (
            freedictionary_api_com_service or FreeDictionaryApiComService()
        )
        self.words_api_rapidapi_service = (
            words_api_rapidapi_service or WordsApiRapidapiService()
        )
        self.word_game_db_service = word_game_db_service or WordGameDbService()
        self.datamuse_service = datamuse_service or DatamuseService()
        self.freedictionary_service = freedictionary_service or FreeDictionaryService()

    @staticmethod
    def _empty_lists(result: Dict[str, Any]) -> Dict[str, Any]:
        result.setdefault("definitions", [])
        result.setdefault("word_forms", [])
        result.setdefault("examples", [])
        result.setdefault("synonyms", [])
        result.setdefault("pronunciations", [])
        return result

    @staticmethod
    def _has_content(result: Optional[Dict[str, Any]]) -> bool:
        if not result:
            return False
        if not result.get("is_valid") and not result.get("found"):
            return False
        return bool(
            result.get("definitions")
            or result.get("synonyms")
            or result.get("summary")
        )

    @staticmethod
    def _from_api_result(word: str, source: str, data: Dict[str, Any]) -> Dict[str, Any]:
        definitions = list(data.get("definitions") or [])
        if not definitions and data.get("summary"):
            definitions = [data["summary"]]

        payload = {
            "word": word,
            "is_valid": bool(data.get("is_valid") or data.get("found")),
            "definitions": definitions,
            "word_forms": list(data.get("word_forms") or []),
            "examples": list(data.get("examples") or []),
            "synonyms": list(data.get("synonyms") or []),
            "pronunciations": list(data.get("pronunciations") or []),
            "etymology": (data.get("etymology") or "").strip(),
            "origin_language": (data.get("origin_language") or "").strip(),
            "first_known_use": (data.get("first_known_use") or "").strip(),
            "reason": data.get("reason") or f"Found via {SOURCE_LABELS.get(source, source)}",
            "validation_source": source,
            "summary": data.get("summary") or (definitions[0] if definitions else ""),
            **{k: data[k] for k in ("dictionary_url", "encyclopedia_url", "source_url", "oxford_url") if data.get(k)},
        }
        payload["links"] = build_links(payload)
        return UnifiedWordLookup._empty_lists(payload)

    @staticmethod
    def _from_freedictionary(word: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data.get("found"):
            return UnifiedWordLookup._empty_lists({
                "word": word,
                "is_valid": False,
                "definitions": [],
                "word_forms": [],
                "examples": [],
                "synonyms": [],
                "reason": data.get("reason") or "Not found on TheFreeDictionary",
                "validation_source": "none",
                "summary": "",
            })

        source = (
            "freedictionary_encyclopedia"
            if data.get("source") == "encyclopedia"
            else "freedictionary"
        )
        definitions = list(data.get("definitions") or [])
        summary = data.get("summary") or data.get("encyclopedia_summary") or ""
        if not definitions and summary:
            definitions = [summary]

        label = SOURCE_LABELS[source]
        return UnifiedWordLookup._empty_lists({
            "word": word,
            "is_valid": True,
            "definitions": definitions,
            "word_forms": [],
            "examples": [],
            "synonyms": list(data.get("synonyms") or []),
            "pronunciations": list(data.get("pronunciations") or []),
            "etymology": (data.get("etymology") or "").strip(),
            "origin_language": (data.get("origin_language") or "").strip(),
            "first_known_use": "",
            "reason": data.get("reason") or f"Found via {label}",
            "validation_source": source,
            "summary": summary,
            "dictionary_url": data.get("dictionary_url"),
            "encyclopedia_url": data.get("encyclopedia_url"),
            "links": {
                k: v
                for k, v in {
                    "dictionary": data.get("dictionary_url"),
                    "encyclopedia": data.get("encyclopedia_url"),
                }.items()
                if v
            },
        })

    @staticmethod
    def _not_found(word: str, sources_tried: List[str], details: Dict[str, Any]) -> Dict[str, Any]:
        return UnifiedWordLookup._empty_lists({
            "word": word,
            "is_valid": False,
            "definitions": [],
            "word_forms": [],
            "examples": [],
            "synonyms": [],
            "reason": "Word not found in any dictionary source",
            "validation_source": "none",
            "sources_used": sources_tried,
            "summary": "",
            "source_details": details,
        })

    def _merge_synonyms(
        self, primary: Dict[str, Any], extra_synonyms: List[str]
    ) -> Dict[str, Any]:
        if not extra_synonyms:
            return primary
        seen = {s.lower() for s in primary.get("synonyms", [])}
        merged = list(primary.get("synonyms", []))
        for syn in extra_synonyms:
            key = syn.lower()
            if key not in seen and key != primary["word"]:
                merged.append(syn)
                seen.add(key)
        primary["synonyms"] = merged[:15]
        return primary

    @staticmethod
    def _merge_pronunciations(
        primary: Dict[str, Any], extra: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not extra:
            return primary
        merged = list(primary.get("pronunciations") or [])
        seen = {(p.get("prefix", ""), p.get("ipa", "")) for p in merged}
        for item in extra:
            key = (item.get("prefix", ""), item.get("ipa", ""))
            if item.get("ipa") and key not in seen:
                merged.append(item)
                seen.add(key)
        primary["pronunciations"] = merged[:4]
        return primary

    async def _enrich_pronunciations(
        self,
        word: str,
        primary: Dict[str, Any],
        details: Dict[str, Any],
        *,
        allow_oxford_web: bool = True,
        skip: bool = False,
    ) -> Dict[str, Any]:
        if skip or primary.get("pronunciations"):
            return primary

        for source in (
            "oxford_web",
            "oxford_dictionaries_api",
            "dictionary_api_dev",
            "freedictionary_api_com",
            "words_api_rapidapi",
            "freedictionary",
        ):
            data = details.get(source)
            if data and data.get("pronunciations"):
                primary["pronunciations"] = list(data["pronunciations"])
                return primary

        if allow_oxford_web and "oxford_web" not in details:
            try:
                oxweb = await self.oxford_validator.validate_word(word)
                details["oxford_web"] = oxweb
                if oxweb.get("pronunciations"):
                    primary["pronunciations"] = list(oxweb["pronunciations"])
                    return primary
            except Exception as exc:
                logger.warning("Pronunciation enrichment (Oxford web) failed for '%s': %s", word, exc)

        if (
            "oxford_dictionaries_api" not in details
            and self.oxford_api_validator.is_configured()
            and self.oxford_api_validator.has_quota()
        ):
            try:
                oda = await self.oxford_api_validator.validate_word(word)
                details["oxford_dictionaries_api"] = oda
                if oda.get("pronunciations"):
                    primary["pronunciations"] = list(oda["pronunciations"])
            except Exception as exc:
                logger.warning(
                    "Pronunciation enrichment (Oxford API) failed for '%s': %s", word, exc
                )

        return primary

    def _filter_source_order(
        self,
        order: tuple[str, ...],
        *,
        flags: Optional[SourceFlags] = None,
        allow_oxford_web: Optional[bool] = None,
        allow_freedictionary: Optional[bool] = None,
    ) -> tuple[str, ...]:
        source_flags = flags or get_portal_source_flags()
        if allow_oxford_web is not None or allow_freedictionary is not None:
            source_flags = SourceFlags(
                merriam_webster=source_flags.merriam_webster,
                oxford_dictionaries_api=source_flags.oxford_dictionaries_api,
                dictionary_api_dev=source_flags.dictionary_api_dev,
                freedictionary_api_com=source_flags.freedictionary_api_com,
                words_api_rapidapi=source_flags.words_api_rapidapi,
                word_game_db=source_flags.word_game_db,
                datamuse=source_flags.datamuse,
                oxford_web=(
                    allow_oxford_web
                    if allow_oxford_web is not None
                    else source_flags.oxford_web
                ),
                freedictionary=(
                    allow_freedictionary
                    if allow_freedictionary is not None
                    else source_flags.freedictionary
                ),
            )
        return source_flags.filter_order(order)

    async def lookup_word(
        self,
        word: str,
        *,
        enrich_synonyms: Optional[Any] = None,
        source_order: Optional[tuple[str, ...]] = None,
        source_flags: Optional[SourceFlags] = None,
        allow_oxford_web: Optional[bool] = None,
        allow_freedictionary: Optional[bool] = None,
        skip_pronunciation_enrichment: bool = False,
    ) -> Dict[str, Any]:
        """
        Look up a word using dictionary sources in priority order.

        enrich_synonyms: optional async callable(word, oxford_data) -> {synonyms: [...]}
        source_order: tuple of source keys; defaults to WEB_UI_SOURCE_ORDER
        source_flags: per-source enable flags from .env (defaults to portal flags)
        allow_oxford_web / allow_freedictionary: override scraper flags when set
        skip_pronunciation_enrichment: when True, avoids extra API/scraper calls for IPA
        """
        word = word.strip().lower()
        sources_tried: List[str] = []
        details: Dict[str, Any] = {}
        base_order = source_order or WEB_UI_SOURCE_ORDER
        flags = source_flags or get_portal_source_flags()
        order = self._filter_source_order(
            base_order,
            flags=flags,
            allow_oxford_web=allow_oxford_web,
            allow_freedictionary=allow_freedictionary,
        )
        cooldown = get_source_cooldown()
        order = cooldown.filter_available(order)
        effective_allow_oxford_web = (
            allow_oxford_web if allow_oxford_web is not None else flags.oxford_web
        )

        if not word or not word.isalpha():
            return self._not_found(word, sources_tried, details)

        for source in order:
            if not cooldown.is_available(source):
                continue
            if source == "merriam_webster":
                if not flags.merriam_webster:
                    continue
                if not self.merriam_validator.is_configured():
                    continue
                if not self.merriam_validator.has_quota():
                    cooldown.mark_unavailable(
                        "merriam_webster",
                        "Merriam-Webster daily quota exhausted",
                    )
                    continue
                sources_tried.append(source)
                mw = await self.merriam_validator.validate_word(word)
                details[source] = mw
                if self._has_content(mw):
                    cooldown.record_success(source)
                    primary = self._from_api_result(word, source, mw)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )
                cooldown.record_failure(source, result=mw)

            elif source == "oxford_dictionaries_api":
                if not flags.oxford_dictionaries_api:
                    continue
                if not self.oxford_api_validator.is_configured():
                    continue
                if not self.oxford_api_validator.has_quota():
                    cooldown.mark_unavailable(
                        "oxford_dictionaries_api",
                        "Oxford Dictionaries API daily quota exhausted",
                    )
                    continue
                sources_tried.append(source)
                oda = await self.oxford_api_validator.validate_word(word)
                details[source] = oda
                if self._has_content(oda):
                    cooldown.record_success(source)
                    primary = self._from_api_result(word, source, oda)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )
                cooldown.record_failure(source, result=oda)

            elif source == "words_api_rapidapi":
                if not flags.words_api_rapidapi:
                    continue
                if not self.words_api_rapidapi_service.is_configured():
                    continue
                sources_tried.append(source)
                war = await self.words_api_rapidapi_service.validate_word(word)
                details[source] = war
                if self._has_content(war):
                    primary = self._from_api_result(word, source, war)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )

            elif source == "dictionary_api_dev":
                if not flags.dictionary_api_dev:
                    continue
                sources_tried.append(source)
                dad = await self.dictionary_api_dev_service.validate_word(word)
                details[source] = dad
                if self._has_content(dad):
                    primary = self._from_api_result(word, source, dad)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )

            elif source == "freedictionary_api_com":
                if not flags.freedictionary_api_com:
                    continue
                sources_tried.append(source)
                fda = await self.freedictionary_api_com_service.validate_word(word)
                details[source] = fda
                if self._has_content(fda):
                    primary = self._from_api_result(word, source, fda)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )

            elif source == "word_game_db":
                if not flags.word_game_db:
                    continue
                if not self.word_game_db_service.is_configured():
                    continue
                sources_tried.append(source)
                wgd = await self.word_game_db_service.validate_word(word)
                details[source] = wgd
                if self._has_content(wgd):
                    primary = self._from_api_result(word, source, wgd)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )

            elif source == "datamuse":
                if not flags.datamuse:
                    continue
                if not self.datamuse_service.is_configured():
                    continue
                sources_tried.append(source)
                dm = await self.datamuse_service.validate_word(word)
                details[source] = dm
                if self._has_content(dm):
                    primary = self._from_api_result(word, source, dm)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )

            elif source == "oxford_web":
                if not flags.oxford_web:
                    continue
                sources_tried.append(source)
                oxweb = await self.oxford_validator.validate_word(word)
                details[source] = oxweb
                if self._has_content(oxweb):
                    primary = self._from_api_result(word, source, oxweb)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )

            elif source == "freedictionary":
                if not flags.freedictionary:
                    continue
                sources_tried.append(source)
                try:
                    fd = await self.freedictionary_service.lookup_word(word)
                except Exception as exc:
                    cooldown.record_failure(source, exc=exc)
                    continue
                details[source] = fd
                if fd.get("blocked"):
                    cooldown.record_failure(
                        source,
                        result={"blocked": True, "reason": fd.get("reason", "blocked")},
                    )
                    continue
                if fd.get("found"):
                    primary = self._from_freedictionary(word, fd)
                    return await self._finalize(
                        primary,
                        sources_tried,
                        details,
                        word,
                        enrich_synonyms,
                        allow_oxford_web=effective_allow_oxford_web,
                        skip_pronunciation_enrichment=skip_pronunciation_enrichment,
                    )

        return self._not_found(word, sources_tried, details)

    async def _finalize(
        self,
        primary: Dict[str, Any],
        sources_tried: List[str],
        details: Dict[str, Any],
        word: str,
        enrich_synonyms: Optional[Any],
        *,
        allow_oxford_web: bool = True,
        skip_pronunciation_enrichment: bool = False,
    ) -> Dict[str, Any]:
        primary["sources_used"] = sources_tried
        primary["source_details"] = details

        primary = await self._enrich_pronunciations(
            word,
            primary,
            details,
            allow_oxford_web=allow_oxford_web,
            skip=skip_pronunciation_enrichment,
        )

        if enrich_synonyms and primary["validation_source"] in {
            "merriam_webster",
            "oxford_dictionaries_api",
            "dictionary_api_dev",
            "freedictionary_api_com",
            "words_api_rapidapi",
            "word_game_db",
            "oxford_web",
            "freedictionary",
        }:
            try:
                oxford_data = details.get("oxford_web") or primary
                syn_data = await enrich_synonyms(word, oxford_data)
                primary = self._merge_synonyms(primary, syn_data.get("synonyms", []))
                primary["synonym_sources"] = syn_data.get("sources", {})
                if syn_data.get("count", 0) > 0 and "synonym" not in primary.get("reason", "").lower():
                    primary["reason"] += f" with {syn_data['count']} synonym(s)"
            except Exception as exc:
                logger.warning("Synonym enrichment failed for '%s': %s", word, exc)

        return self._empty_lists(primary)

    async def validate_words_batch(
        self,
        words: List[str],
        *,
        source_order: Optional[tuple[str, ...]] = None,
        max_concurrent: int = 20,
    ) -> Dict[str, Any]:
        if not words:
            return {
                "total_words": 0,
                "valid_words": 0,
                "invalid_words": 0,
                "results": [],
            }

        semaphore = asyncio.Semaphore(max(1, max_concurrent))

        async def _lookup_one(word: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.lookup_word(
                    word,
                    source_order=source_order,
                    source_flags=get_enrich_source_flags(),
                )

        raw_results = await asyncio.gather(
            *[_lookup_one(word) for word in words],
            return_exceptions=True,
        )

        results: List[Dict[str, Any]] = []
        for index, item in enumerate(raw_results):
            if isinstance(item, Exception):
                word = words[index]
                logger.error("Exception validating word '%s': %s", word, item)
                results.append(self._not_found(word, [], {}))
                results[-1]["reason"] = f"Exception: {item}"
            else:
                results.append(item)

        valid_count = sum(1 for result in results if result["is_valid"])
        return {
            "total_words": len(results),
            "valid_words": valid_count,
            "invalid_words": len(results) - valid_count,
            "results": results,
        }

    def get_dictionary_stats(self) -> Dict[str, Any]:
        return {
            "merriam_webster": self.merriam_validator.get_usage_stats(),
            "oxford_dictionaries_api": self.oxford_api_validator.get_usage_stats(),
            "dictionary_api_dev": self.dictionary_api_dev_service.get_cache_stats(),
            "freedictionary_api_com": self.freedictionary_api_com_service.get_cache_stats(),
            "words_api_rapidapi": self.words_api_rapidapi_service.get_cache_stats(),
            "word_game_db": self.word_game_db_service.get_cache_stats(),
            "datamuse": self.datamuse_service.get_cache_stats(),
            "oxford_web": self.oxford_validator.get_cache_stats(),
            "freedictionary": self.freedictionary_service.get_cache_stats(),
        }

    def to_ui_validation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Shape returned as oxford_validation for frontend compatibility."""
        return self._empty_lists({
            "word": result.get("word", ""),
            "is_valid": bool(result.get("is_valid")),
            "definitions": list(result.get("definitions") or []),
            "word_forms": list(result.get("word_forms") or []),
            "examples": list(result.get("examples") or []),
            "synonyms": list(result.get("synonyms") or []),
            "pronunciations": list(result.get("pronunciations") or []),
            "etymology": result.get("etymology", ""),
            "origin_language": result.get("origin_language", ""),
            "first_known_use": result.get("first_known_use", ""),
            "summary": result.get("summary", ""),
            "reason": result.get("reason") or "",
            "validation_source": result.get("validation_source", "none"),
            "sources_used": result.get("sources_used", []),
            "links": result.get("links") or {},
            "dictionary_url": result.get("dictionary_url"),
            "encyclopedia_url": result.get("encyclopedia_url"),
            "rhymes": list(result.get("rhymes") or []),
            "antonyms": list(result.get("antonyms") or []),
            "frequency": result.get("frequency"),
            "frequency_details": result.get("frequency_details") or {},
            "words_api_details": result.get("words_api_details") or {},
            "word_game_db": result.get("word_game_db") or {},
        })
