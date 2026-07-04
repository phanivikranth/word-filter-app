"""
Unified word lookup across all dictionary sources.

Order (first source with usable definitions wins):
  Web UI (default): Merriam-Webster -> Oxford Dictionaries API -> Oxford web -> TheFreeDictionary
  Bulk validate_words.py: Oxford web -> TheFreeDictionary -> Merriam-Webster -> Oxford Dictionaries API

Returns a stable UI-friendly shape (compatible with OxfordValidation in the frontend).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from freedictionary_service import FreeDictionaryService
from merriam_webster_validator import MerriamWebsterValidator
from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator
from oxford_validator import OxfordValidator

logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    "merriam_webster": "Merriam-Webster Thesaurus",
    "oxford_dictionaries_api": "Oxford Dictionaries API",
    "oxford_web": "Oxford Learner's Dictionary",
    "freedictionary": "TheFreeDictionary",
    "freedictionary_encyclopedia": "TheFreeDictionary Encyclopedia",
    "none": "No source",
}

# Web UI: quota APIs first, then scrapers (fast official lookups for common words).
WEB_UI_SOURCE_ORDER = (
    "merriam_webster",
    "oxford_dictionaries_api",
    "oxford_web",
    "freedictionary",
)

# Bulk validate_words.py: free/unlimited sources first, quota APIs last.
BULK_VALIDATE_SOURCE_ORDER = (
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
        freedictionary_service: Optional[FreeDictionaryService] = None,
    ):
        self.oxford_validator = oxford_validator
        self.merriam_validator = merriam_validator or MerriamWebsterValidator()
        self.oxford_api_validator = oxford_api_validator or OxfordDictionariesApiValidator()
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

        return UnifiedWordLookup._empty_lists({
            "word": word,
            "is_valid": bool(data.get("is_valid") or data.get("found")),
            "definitions": definitions,
            "word_forms": list(data.get("word_forms") or []),
            "examples": list(data.get("examples") or []),
            "synonyms": list(data.get("synonyms") or []),
            "pronunciations": list(data.get("pronunciations") or []),
            "reason": data.get("reason") or f"Found via {SOURCE_LABELS.get(source, source)}",
            "validation_source": source,
            "summary": data.get("summary") or (definitions[0] if definitions else ""),
        })

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
            "synonyms": [],
            "pronunciations": list(data.get("pronunciations") or []),
            "reason": data.get("reason") or f"Found via {label}",
            "validation_source": source,
            "summary": summary,
            "dictionary_url": data.get("dictionary_url"),
            "encyclopedia_url": data.get("encyclopedia_url"),
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
    ) -> Dict[str, Any]:
        if primary.get("pronunciations"):
            return primary

        for source in ("oxford_web", "oxford_dictionaries_api", "freedictionary"):
            data = details.get(source)
            if data and data.get("pronunciations"):
                primary["pronunciations"] = list(data["pronunciations"])
                return primary

        if "oxford_web" not in details:
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

    async def lookup_word(
        self,
        word: str,
        *,
        enrich_synonyms: Optional[Any] = None,
        source_order: Optional[tuple[str, ...]] = None,
    ) -> Dict[str, Any]:
        """
        Look up a word using dictionary sources in priority order.

        enrich_synonyms: optional async callable(word, oxford_data) -> {synonyms: [...]}
        source_order: tuple of source keys; defaults to WEB_UI_SOURCE_ORDER
        """
        word = word.strip().lower()
        sources_tried: List[str] = []
        details: Dict[str, Any] = {}
        order = source_order or WEB_UI_SOURCE_ORDER

        if not word or not word.isalpha():
            return self._not_found(word, sources_tried, details)

        for source in order:
            if source == "merriam_webster":
                if not (
                    self.merriam_validator.is_configured()
                    and self.merriam_validator.has_quota()
                ):
                    continue
                sources_tried.append(source)
                mw = await self.merriam_validator.validate_word(word)
                details[source] = mw
                if self._has_content(mw):
                    primary = self._from_api_result(word, source, mw)
                    return await self._finalize(
                        primary, sources_tried, details, word, enrich_synonyms
                    )

            elif source == "oxford_dictionaries_api":
                if not (
                    self.oxford_api_validator.is_configured()
                    and self.oxford_api_validator.has_quota()
                ):
                    continue
                sources_tried.append(source)
                oda = await self.oxford_api_validator.validate_word(word)
                details[source] = oda
                if self._has_content(oda):
                    primary = self._from_api_result(word, source, oda)
                    return await self._finalize(
                        primary, sources_tried, details, word, enrich_synonyms
                    )

            elif source == "oxford_web":
                sources_tried.append(source)
                oxweb = await self.oxford_validator.validate_word(word)
                details[source] = oxweb
                if self._has_content(oxweb):
                    primary = self._from_api_result(word, source, oxweb)
                    return await self._finalize(
                        primary, sources_tried, details, word, enrich_synonyms
                    )

            elif source == "freedictionary":
                sources_tried.append(source)
                fd = await self.freedictionary_service.lookup_word(word)
                details[source] = fd
                if fd.get("found"):
                    primary = self._from_freedictionary(word, fd)
                    return await self._finalize(
                        primary, sources_tried, details, word, enrich_synonyms
                    )

        return self._not_found(word, sources_tried, details)

    async def _finalize(
        self,
        primary: Dict[str, Any],
        sources_tried: List[str],
        details: Dict[str, Any],
        word: str,
        enrich_synonyms: Optional[Any],
    ) -> Dict[str, Any]:
        primary["sources_used"] = sources_tried
        primary["source_details"] = details

        primary = await self._enrich_pronunciations(word, primary, details)

        if enrich_synonyms and primary["validation_source"] in {
            "merriam_webster",
            "oxford_dictionaries_api",
            "oxford_web",
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
                return await self.lookup_word(word, source_order=source_order)

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
            "reason": result.get("reason") or "",
            "validation_source": result.get("validation_source", "none"),
            "summary": result.get("summary", ""),
            "sources_used": result.get("sources_used", []),
        })
