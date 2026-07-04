"""
Combined word validation using Merriam-Webster, Oxford Dictionaries API, and Oxford web fallback.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from merriam_webster_validator import MerriamWebsterValidator
from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator
from oxford_validator import OxfordValidator

logger = logging.getLogger(__name__)


class CombinedWordValidator:
    """
    Validate words using multiple dictionary sources.

    Strategy (combined mode):
    1. Merriam-Webster when configured and daily quota remains (1,000/day).
    2. Oxford Dictionaries API when configured and daily quota remains (500/day).
    3. Oxford Learner's web scraper as unlimited fallback.
    4. A word is valid if any source confirms it.
    """

    def __init__(
        self,
        oxford_validator: OxfordValidator,
        merriam_validator: Optional[MerriamWebsterValidator] = None,
        oxford_api_validator: Optional[OxfordDictionariesApiValidator] = None,
    ):
        self.oxford_validator = oxford_validator
        self.merriam_validator = merriam_validator or MerriamWebsterValidator()
        self.oxford_api_validator = oxford_api_validator or OxfordDictionariesApiValidator()

    async def validate_word(self, word: str) -> Dict[str, Any]:
        word = word.strip().lower()
        merriam_result: Optional[Dict[str, Any]] = None
        oxford_api_result: Optional[Dict[str, Any]] = None
        oxford_web_result: Optional[Dict[str, Any]] = None
        sources_used: List[str] = []

        if self.merriam_validator.is_configured() and self.merriam_validator.has_quota():
            merriam_result = await self.merriam_validator.validate_word(word)
            sources_used.append("merriam_webster")
            if merriam_result["is_valid"]:
                return self._build_combined_result(
                    word=word,
                    is_valid=True,
                    merriam_result=merriam_result,
                    oxford_api_result=None,
                    oxford_web_result=None,
                    primary_source="merriam_webster",
                    sources_used=sources_used,
                )

        if self.oxford_api_validator.is_configured() and self.oxford_api_validator.has_quota():
            oxford_api_result = await self.oxford_api_validator.validate_word(word)
            sources_used.append("oxford_dictionaries_api")
            if oxford_api_result["is_valid"]:
                return self._build_combined_result(
                    word=word,
                    is_valid=True,
                    merriam_result=merriam_result,
                    oxford_api_result=oxford_api_result,
                    oxford_web_result=None,
                    primary_source="oxford_dictionaries_api",
                    sources_used=sources_used,
                )

        oxford_web_result = await self.oxford_validator.validate_word(word)
        sources_used.append("oxford_web")

        is_valid = bool(
            (merriam_result and merriam_result.get("is_valid"))
            or (oxford_api_result and oxford_api_result.get("is_valid"))
            or oxford_web_result.get("is_valid")
        )

        if merriam_result and merriam_result.get("is_valid"):
            primary_source = "merriam_webster"
        elif oxford_api_result and oxford_api_result.get("is_valid"):
            primary_source = "oxford_dictionaries_api"
        elif oxford_web_result.get("is_valid"):
            primary_source = "oxford_web"
        else:
            primary_source = "none"

        return self._build_combined_result(
            word=word,
            is_valid=is_valid,
            merriam_result=merriam_result,
            oxford_api_result=oxford_api_result,
            oxford_web_result=oxford_web_result,
            primary_source=primary_source,
            sources_used=sources_used,
        )

    def _build_combined_result(
        self,
        *,
        word: str,
        is_valid: bool,
        merriam_result: Optional[Dict[str, Any]],
        oxford_api_result: Optional[Dict[str, Any]],
        oxford_web_result: Optional[Dict[str, Any]],
        primary_source: str,
        sources_used: List[str],
    ) -> Dict[str, Any]:
        source_map = {
            "merriam_webster": merriam_result,
            "oxford_dictionaries_api": oxford_api_result,
            "oxford_web": oxford_web_result,
            "oxford": oxford_web_result,
        }
        primary = source_map.get(primary_source)
        if primary is None:
            primary = merriam_result or oxford_api_result or oxford_web_result or {
                "definitions": [],
                "word_forms": [],
                "synonyms": [],
                "examples": [],
                "reason": "Word not found in any dictionary source",
            }

        reasons = [
            result.get("reason", "")
            for result in (merriam_result, oxford_api_result, oxford_web_result)
            if result and result.get("reason")
        ]
        combined_reason = primary.get("reason", " | ".join(reasons))

        return {
            "word": word,
            "is_valid": is_valid,
            "definitions": primary.get("definitions", []),
            "word_forms": primary.get("word_forms", []),
            "examples": primary.get("examples", []),
            "synonyms": primary.get("synonyms", []),
            "reason": combined_reason,
            "validation_source": primary_source,
            "sources_used": sources_used,
            "merriam_webster": merriam_result,
            "oxford_dictionaries_api": oxford_api_result,
            "oxford": oxford_web_result,
        }

    async def validate_words_batch(self, words: List[str], batch_size: int = 20) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for word in words:
            results.append(await self.validate_word(word))

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
        }
