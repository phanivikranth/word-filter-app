"""
TheFreeDictionary.com scraper (dictionary + encyclopedia fallback).

Dictionary: https://www.thefreedictionary.com/{word}
Encyclopedia (Wikipedia mirror): https://encyclopedia.thefreedictionary.com/{word}
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DICTIONARY_BASE = "https://www.thefreedictionary.com"
ENCYCLOPEDIA_BASE = "https://encyclopedia.thefreedictionary.com"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.thefreedictionary.com/",
}

NOT_IN_DICTIONARY_MARKERS = (
    "is not available in the general english dictionary",
    "word not found in the dictionary and encyclopedia",
)


class FreeDictionaryBlockedError(RuntimeError):
    """Raised when TheFreeDictionary returns repeated 403/429 blocks."""


class FreeDictionaryService:
    """Scrape word lookups from TheFreeDictionary with encyclopedia fallback."""

    def __init__(self, request_delay: float = 2.0):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.request_delay = max(0.0, request_delay)
        self._rate_lock = threading.Lock()
        self._last_request_time = 0.0
        self._blocked_backoff = float(
            os.getenv("FREEDICTIONARY_BLOCKED_BACKOFF", "15")
        )
        self._max_blocked_retries = int(
            os.getenv("FREEDICTIONARY_BLOCKED_RETRIES", "2")
        )
        self._last_fetch_blocked = False
        self.consecutive_blocked_fetches = 0
        self.blocked_pause_after = int(
            os.getenv("FREEDICTIONARY_BLOCKED_PAUSE_AFTER", "3")
        )

    def set_blocked_backoff(self, seconds: float) -> None:
        self._blocked_backoff = max(1.0, seconds)

    def set_blocked_pause_after(self, count: int) -> None:
        self.blocked_pause_after = max(1, count)

    def reset_blocked_counter(self) -> None:
        self.consecutive_blocked_fetches = 0
        self._last_fetch_blocked = False

    def set_request_delay(self, seconds: float) -> None:
        self.request_delay = max(0.0, seconds)

    def set_concurrency(self, max_concurrent: int) -> None:
        workers = max(1, min(max_concurrent, 50))
        if getattr(self.executor, "_max_workers", 0) != workers:
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.executor = ThreadPoolExecutor(max_workers=workers)

    def _wait_for_rate_limit(self) -> None:
        if self.request_delay <= 0:
            return
        with self._rate_lock:
            elapsed = time.time() - self._last_request_time
            wait = self.request_delay - elapsed
            if wait > 0:
                # Small jitter so requests do not land on a fixed cadence.
                wait += random.uniform(0.0, min(0.5, self.request_delay * 0.1))
                time.sleep(wait)
            self._last_request_time = time.time()

    def _fetch_html(self, url: str, *, max_retries: int | None = None) -> Optional[str]:
        retries = max_retries if max_retries is not None else self._max_blocked_retries
        self._last_fetch_blocked = False
        for attempt in range(retries):
            self._wait_for_rate_limit()
            try:
                response = self.session.get(url, timeout=20)
                if response.status_code == 200:
                    self.consecutive_blocked_fetches = 0
                    return response.text
                if response.status_code in (403, 429, 503):
                    self._last_fetch_blocked = True
                    self.consecutive_blocked_fetches += 1
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        pause = float(retry_after)
                    else:
                        pause = min(
                            self._blocked_backoff * (attempt + 1),
                            120.0,
                        )
                    logger.warning(
                        "FreeDictionary blocked/rate-limited (HTTP %s). Waiting %.0fs before retry %s/%s",
                        response.status_code,
                        pause,
                        attempt + 1,
                        retries,
                    )
                    if self.consecutive_blocked_fetches >= self.blocked_pause_after:
                        raise FreeDictionaryBlockedError(
                            f"TheFreeDictionary blocked this IP (HTTP {response.status_code}) "
                            f"after {self.consecutive_blocked_fetches} blocked responses. "
                            "Wait and retry later, or use --api dictionary-api-dev."
                        )
                    time.sleep(pause)
                    continue
                logger.warning("FreeDictionary HTTP %s for %s", response.status_code, url)
                return None
            except FreeDictionaryBlockedError:
                raise
            except requests.RequestException as exc:
                logger.error("FreeDictionary request failed for %s: %s", url, exc)
                if attempt + 1 < retries:
                    time.sleep(min(2.0 * (attempt + 1), 10.0))
                    continue
                return None
        self._last_fetch_blocked = True
        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"\[\d+\]", "", text)
        text = re.split(r"Collins English Dictionary", text, maxsplit=1)[0]
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _summarize(text: str, max_sentences: int = 3, max_chars: int = 420) -> str:
        text = FreeDictionaryService._clean_text(text)
        if not text:
            return ""

        # Skip Wikipedia "For X, see Y" / redirect lead-ins.
        for _ in range(2):
            lowered = text.lower()
            if lowered.startswith("for the ") and " see " in lowered[:120]:
                split_at = text.find(". ")
                if split_at > 0:
                    text = text[split_at + 2 :].strip()
                    continue
            if '" redirects here' in lowered[:80] or lowered.startswith('"'):
                split_at = text.find(". ")
                if split_at > 0:
                    text = text[split_at + 2 :].strip()
                    continue
            break

        sentences = re.split(r"(?<=[.!?])\s+", text)
        summary_parts: List[str] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            summary_parts.append(sentence)
            if len(summary_parts) >= max_sentences:
                break

        summary = " ".join(summary_parts)
        if len(summary) > max_chars:
            summary = summary[: max_chars - 3].rsplit(" ", 1)[0] + "..."
        return summary

    # Common part-of-speech tags used by Collins / TheFreeDictionary entries.
    _POS_TAGS = (
        r"adj|adv|n|v|vi|vt|aux|prep|conj|interj|pron|det|num|symbol|int|abbr|"
        r"combining form|modal verb|pl|sing|past|past participle|present participle"
    )

    @staticmethod
    def _extract_trailing_etymology(text: str) -> tuple[str, str]:
        """Return (etymology_phrase, origin_language) from trailing [from X] bracket."""
        match = re.search(r"\[([^\]]+)\]\s*$", text or "")
        if not match:
            return "", ""
        bracket = match.group(1).strip()
        if bracket.lower().startswith("from "):
            return bracket, bracket[5:].strip()
        if bracket.lower().startswith("via "):
            return bracket, bracket[4:].strip()
        return bracket, ""

    @staticmethod
    def _extract_synonyms_from_html(soup: BeautifulSoup, word: str) -> List[str]:
        synonyms: List[str] = []
        for anchor in soup.select("a[href*='thesaurus'], a[href*='synonym']"):
            text = anchor.get_text(strip=True)
            if (
                text
                and text.isalpha()
                and text.lower() != word.lower()
                and text not in synonyms
            ):
                synonyms.append(text)
            if len(synonyms) >= 10:
                break
        return synonyms

    @staticmethod
    def _polish_definition(entry: str) -> str:
        """
        Strip headword, pronunciation, and part-of-speech prefix from a dictionary line.
        Example: "cymotrichous ( saɪˈmɒtrɪkəs ) adj having wavy hair" -> "having wavy hair"
        """
        text = FreeDictionaryService._clean_text(entry)
        if not text:
            return ""

        # Numbered senses: "1. a. having wavy hair" -> "having wavy hair"
        numbered = re.match(r"^\d+\.\s*(?:[a-z]\.\s*)?(.+)$", text, flags=re.IGNORECASE)
        if numbered:
            text = numbered.group(1).strip()

        # Headword + IPA/pronunciation in parentheses
        headword = re.match(
            r"^[a-zA-ZÀ-ÿ][\w'-]*\s*\([^)]+\)\s*(.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if headword:
            text = headword.group(1).strip()

        # Part of speech at the start (adj, n, v, ...)
        text = re.sub(
            rf"^(?:{FreeDictionaryService._POS_TAGS})\b\.?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Drop leading domain/context parentheticals, keep the definition phrase.
        while True:
            stripped = re.sub(r"^\([^)]+\)\s*", "", text).strip()
            if stripped == text:
                break
            text = stripped

        # Trailing etymology bracket e.g. [from Yiddish] — kept in etymology field separately
        text = re.sub(r"\s*\[[^\]]+\]\s*$", "", text).strip()

        return text

    @staticmethod
    def _extract_definitions(text: str, limit: int = 5) -> List[str]:
        text = FreeDictionaryService._clean_text(text)
        if not text:
            return []

        definitions: List[str] = []
        # Numbered dictionary senses like "1. a. ..."
        for match in re.finditer(r"\b\d+\.\s+(?:[a-z]\.\s*)?.{10,200}", text):
            snippet = FreeDictionaryService._polish_definition(match.group(0).strip())
            if snippet and snippet not in definitions:
                definitions.append(snippet)
            if len(definitions) >= limit:
                break

        if definitions:
            return definitions

        # Collins-style single line: word (pronunciation) pos definition
        polished = FreeDictionaryService._polish_definition(text)
        if polished:
            return [polished]

        # Fallback: short summary for encyclopedia-style prose
        summary = FreeDictionaryService._summarize(text, max_sentences=2, max_chars=300)
        return [summary] if summary else []

    @staticmethod
    def _extract_pronunciations(word: str, text: str) -> List[Dict[str, str]]:
        """Pull IPA from Collins-style lines: word ( IPA ) pos definition."""
        if not text:
            return []
        patterns = [
            rf"{re.escape(word)}\s*\(([^)]+)\)",
            r"\[([^\]]+)\]",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            ipa = match.group(1).strip().strip("/[]")
            if len(ipa) < 2 or len(ipa) > 80:
                continue
            if re.search(r"[ˈˌɪɛæʌɒəɑɔʊuː]", ipa) or "pronunciation" not in ipa.lower():
                return [{"prefix": "IPA", "ipa": ipa, "url": ""}]
        return []

    def _parse_page(self, html: str, word: str = "") -> Dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta_description = (meta_tag.get("content") or "").strip() if meta_tag else ""

        definition_el = soup.select_one("#Definition")
        main_el = soup.select_one("#MainTxt")

        definition_text = definition_el.get_text(" ", strip=True) if definition_el else ""
        main_text = main_el.get_text(" ", strip=True) if main_el else ""
        body = definition_text or main_text or meta_description
        etymology, origin_language = self._extract_trailing_etymology(body)

        return {
            "title": title,
            "meta_description": meta_description,
            "definition_text": definition_text,
            "main_text": main_text,
            "pronunciations": self._extract_pronunciations(
                word, f"{definition_text} {main_text}"
            ),
            "etymology": etymology,
            "origin_language": origin_language,
            "synonyms": self._extract_synonyms_from_html(soup, word),
        }

    @staticmethod
    def _is_dictionary_miss(main_text: str, definition_text: str) -> bool:
        combined = f"{main_text} {definition_text}".lower()
        if any(marker in combined for marker in NOT_IN_DICTIONARY_MARKERS):
            return True
        if not definition_text and not main_text:
            return True
        if not definition_text and "check: wikipedia" in combined:
            return True
        return False

    def _lookup_sync(self, word: str) -> Dict[str, Any]:
        word_clean = word.strip()
        word_key = word_clean.lower()
        encoded = quote(word_clean)

        dictionary_url = f"{DICTIONARY_BASE}/{encoded}"
        encyclopedia_url = f"{ENCYCLOPEDIA_BASE}/{encoded}"

        dict_html = self._fetch_html(dictionary_url)
        if not dict_html:
            blocked = self._last_fetch_blocked
            return {
                "word": word_key,
                "found": False,
                "blocked": blocked,
                "source": "none",
                "definitions": [],
                "summary": "",
                "encyclopedia_summary": None,
                "dictionary_url": dictionary_url,
                "encyclopedia_url": encyclopedia_url,
                "reason": (
                    "TheFreeDictionary blocked this request (HTTP 403/429)"
                    if blocked
                    else "Failed to reach TheFreeDictionary"
                ),
            }

        dict_parsed = self._parse_page(dict_html, word_key)
        main_text = dict_parsed["main_text"]
        definition_text = dict_parsed["definition_text"]

        if not self._is_dictionary_miss(main_text, definition_text):
            body = definition_text or main_text or dict_parsed["meta_description"]
            definitions = self._extract_definitions(body)
            summary = self._summarize(body, max_sentences=3)
            return {
                "word": word_key,
                "found": True,
                "source": "dictionary",
                "definitions": definitions,
                "summary": summary,
                "encyclopedia_summary": None,
                "pronunciations": dict_parsed.get("pronunciations") or [],
                "synonyms": dict_parsed.get("synonyms") or [],
                "etymology": dict_parsed.get("etymology") or "",
                "origin_language": dict_parsed.get("origin_language") or "",
                "title": dict_parsed["title"],
                "dictionary_url": dictionary_url,
                "encyclopedia_url": encyclopedia_url,
                "reason": "Found in TheFreeDictionary (dictionary)",
            }

        enc_html = self._fetch_html(encyclopedia_url)
        if not enc_html:
            return {
                "word": word_key,
                "found": False,
                "source": "none",
                "definitions": [],
                "summary": "",
                "encyclopedia_summary": None,
                "dictionary_url": dictionary_url,
                "encyclopedia_url": encyclopedia_url,
                "reason": "Not in dictionary; encyclopedia lookup failed",
            }

        enc_parsed = self._parse_page(enc_html, word_key)
        enc_body = (
            enc_parsed["definition_text"]
            or enc_parsed["main_text"]
            or enc_parsed["meta_description"]
        )
        enc_body = self._clean_text(enc_body)

        if not enc_body or "word not found" in enc_body.lower():
            return {
                "word": word_key,
                "found": False,
                "source": "none",
                "definitions": [],
                "summary": "",
                "encyclopedia_summary": None,
                "dictionary_url": dictionary_url,
                "encyclopedia_url": encyclopedia_url,
                "reason": "Word not found in dictionary or encyclopedia",
            }

        enc_summary = self._summarize(enc_body, max_sentences=3)
        return {
            "word": word_key,
            "found": True,
            "source": "encyclopedia",
            "definitions": [],
            "summary": enc_summary,
            "encyclopedia_summary": enc_summary,
            "pronunciations": enc_parsed.get("pronunciations") or [],
            "title": enc_parsed["title"],
            "dictionary_url": dictionary_url,
            "encyclopedia_url": encyclopedia_url,
            "reason": "Not in dictionary; summarized from encyclopedia (Wikipedia mirror)",
        }

    async def lookup_word(self, word: str) -> Dict[str, Any]:
        word_key = word.strip().lower()
        if not word_key:
            return {
                "word": "",
                "found": False,
                "source": "none",
                "definitions": [],
                "summary": "",
                "encyclopedia_summary": None,
                "reason": "Word cannot be empty",
            }

        if word_key in self.cache:
            return self.cache[word_key]

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self._lookup_sync, word)
        self.cache[word_key] = result
        return result

    async def validate_word(self, word: str) -> Dict[str, Any]:
        """Validate a word; shape matches other dictionary validators."""
        data = await self.lookup_word(word)
        word_key = data.get("word", word.strip().lower())
        found = bool(data.get("found"))
        definitions = data.get("definitions") or []
        summary = data.get("summary") or data.get("encyclopedia_summary") or ""
        if found and not definitions and summary:
            definitions = [summary]
        return {
            "word": word_key,
            "is_valid": found,
            "blocked": bool(data.get("blocked")),
            "definitions": definitions,
            "word_forms": [],
            "examples": [],
            "synonyms": list(data.get("synonyms") or []),
            "pronunciations": list(data.get("pronunciations") or []),
            "etymology": (data.get("etymology") or "").strip(),
            "origin_language": (data.get("origin_language") or "").strip(),
            "first_known_use": "",
            "dictionary_url": data.get("dictionary_url", ""),
            "encyclopedia_url": data.get("encyclopedia_url", ""),
            "reason": data.get("reason", "Found in TheFreeDictionary" if found else "Not found"),
            "source": data.get("source", "freedictionary" if found else "none"),
        }

    async def validate_words_batch(
        self, words: List[str], max_concurrent: int = 1
    ) -> Dict[str, Any]:
        if not words:
            return {
                "total_words": 0,
                "valid_words": 0,
                "invalid_words": 0,
                "results": [],
            }

        semaphore = asyncio.Semaphore(max(1, max_concurrent))

        async def _validate_one(item: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await self.validate_word(item)
                except FreeDictionaryBlockedError as exc:
                    return {
                        "word": item,
                        "is_valid": False,
                        "blocked": True,
                        "definitions": [],
                        "word_forms": [],
                        "examples": [],
                        "synonyms": [],
                        "reason": str(exc),
                    }

        raw = await asyncio.gather(
            *[_validate_one(word) for word in words],
            return_exceptions=True,
        )
        results: List[Dict[str, Any]] = []
        for index, item in enumerate(raw):
            if isinstance(item, Exception):
                word = words[index]
                logger.error("FreeDictionary exception for '%s': %s", word, item)
                results.append({
                    "word": word,
                    "is_valid": False,
                    "definitions": [],
                    "word_forms": [],
                    "examples": [],
                    "synonyms": [],
                    "reason": f"Exception: {item}",
                })
            else:
                results.append(item)

        valid_count = sum(1 for result in results if result["is_valid"])
        return {
            "total_words": len(results),
            "valid_words": valid_count,
            "invalid_words": len(results) - valid_count,
            "results": results,
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        return {"cached_words": len(self.cache)}
