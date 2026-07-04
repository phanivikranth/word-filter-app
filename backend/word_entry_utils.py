"""
Shared helpers for merging dictionary lookup results into one Nhost-ready entry.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


ENRICHMENT_FIELDS = (
    "definitions",
    "synonyms",
    "pronunciations",
    "examples",
    "word_forms",
    "etymology",
    "origin_language",
    "first_known_use",
    "links",
)

# Filled in background; must not block UI or trigger a full API waterfall.
OPTIONAL_ENRICHMENT_FIELDS = frozenset(
    {"etymology", "origin_language", "first_known_use"}
)

# User-facing gaps that justify blocking enrichment when definitions are absent.
PRIORITY_ENRICHMENT_FIELDS = tuple(
    field for field in ENRICHMENT_FIELDS if field not in OPTIONAL_ENRICHMENT_FIELDS
)


def _dedupe_strings(values: List[str], *, limit: int = 0) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if limit and len(out) >= limit:
            break
    return out


def _merge_pronunciations(
    base: List[Dict[str, Any]], extra: List[Dict[str, Any]], *, limit: int = 4
) -> List[Dict[str, Any]]:
    merged = list(base or [])
    seen = {(p.get("prefix", ""), p.get("ipa", "")) for p in merged if p.get("ipa")}
    for item in extra or []:
        if not isinstance(item, dict) or not item.get("ipa"):
            continue
        key = (item.get("prefix", ""), item.get("ipa", ""))
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def build_links(result: Dict[str, Any]) -> Dict[str, str]:
    links: Dict[str, str] = dict(result.get("links") or {})
    for key, link_type in (
        ("dictionary_url", "dictionary"),
        ("encyclopedia_url", "encyclopedia"),
        ("source_url", "source"),
        ("oxford_url", "oxford"),
    ):
        url = (result.get(key) or "").strip()
        if url:
            links[link_type] = url
    return links


def missing_fields(result: Optional[Dict[str, Any]]) -> List[str]:
    if not result:
        return list(ENRICHMENT_FIELDS)
    missing: List[str] = []
    if not result.get("definitions"):
        missing.append("definitions")
    if not result.get("synonyms"):
        missing.append("synonyms")
    if not result.get("pronunciations"):
        missing.append("pronunciations")
    if not result.get("examples"):
        missing.append("examples")
    if not result.get("word_forms"):
        missing.append("word_forms")
    if not (result.get("etymology") or "").strip():
        missing.append("etymology")
    if not (result.get("origin_language") or "").strip():
        missing.append("origin_language")
    if not (result.get("first_known_use") or "").strip():
        missing.append("first_known_use")
    if not build_links(result):
        missing.append("links")
    return missing


def missing_required_fields(result: Optional[Dict[str, Any]]) -> List[str]:
    """Gaps that should block returning a 'complete' cache hit (excludes optional metadata)."""
    return [
        field
        for field in missing_fields(result)
        if field not in OPTIONAL_ENRICHMENT_FIELDS
    ]


def missing_optional_fields(result: Optional[Dict[str, Any]]) -> List[str]:
    return [
        field
        for field in missing_fields(result)
        if field in OPTIONAL_ENRICHMENT_FIELDS
    ]


def is_ui_ready(result: Optional[Dict[str, Any]]) -> bool:
    """Enough data to render the word card immediately."""
    return bool(result and result.get("definitions"))


def only_optional_gaps_remain(result: Optional[Dict[str, Any]]) -> bool:
    gaps = missing_fields(result)
    return bool(gaps) and all(field in OPTIONAL_ENRICHMENT_FIELDS for field in gaps)


def merge_word_entries(
    *entries: Optional[Dict[str, Any]],
    word: str = "",
) -> Dict[str, Any]:
    """Merge multiple partial lookup dicts; later entries fill gaps only."""
    merged: Dict[str, Any] = {
        "word": word.strip().lower(),
        "is_valid": False,
        "definitions": [],
        "synonyms": [],
        "pronunciations": [],
        "examples": [],
        "word_forms": [],
        "etymology": "",
        "origin_language": "",
        "first_known_use": "",
        "summary": "",
        "reason": "",
        "validation_source": "none",
        "links": {},
        "rhymes": [],
        "antonyms": [],
        "frequency": None,
        "frequency_details": {},
        "words_api_details": {},
    }

    for entry in entries:
        if not entry:
            continue
        if entry.get("word"):
            merged["word"] = str(entry["word"]).strip().lower()

        for key in ("definitions", "synonyms", "examples", "word_forms"):
            if not merged.get(key):
                merged[key] = _dedupe_strings(
                    list(entry.get(key) or []),
                    limit=15 if key == "synonyms" else 5,
                )

        if not merged.get("pronunciations"):
            merged["pronunciations"] = _merge_pronunciations(
                [], list(entry.get("pronunciations") or [])
            )
        else:
            merged["pronunciations"] = _merge_pronunciations(
                list(merged["pronunciations"]),
                list(entry.get("pronunciations") or []),
            )

        for key in ("etymology", "origin_language", "first_known_use", "summary"):
            if not (merged.get(key) or "").strip() and (entry.get(key) or "").strip():
                merged[key] = str(entry[key]).strip()

        if (entry.get("reason") or "").strip() and not merged.get("reason"):
            merged["reason"] = entry["reason"]
        if entry.get("validation_source") not in (None, "", "none"):
            if merged.get("validation_source") in (None, "", "none"):
                merged["validation_source"] = entry["validation_source"]

        merged["links"] = {**build_links(entry), **(merged.get("links") or {})}
        merged["is_valid"] = bool(merged.get("definitions")) or bool(
            entry.get("is_valid")
        )

        for key in ("rhymes", "antonyms"):
            if not merged.get(key):
                merged[key] = _dedupe_strings(list(entry.get(key) or []), limit=15)
            elif entry.get(key):
                merged[key] = _dedupe_strings(
                    list(merged[key]) + list(entry.get(key) or []), limit=15
                )

        if merged.get("frequency") is None and entry.get("frequency") is not None:
            merged["frequency"] = entry.get("frequency")
        if entry.get("frequency_details"):
            merged["frequency_details"] = {
                **(merged.get("frequency_details") or {}),
                **(entry.get("frequency_details") or {}),
            }
        if entry.get("words_api_details"):
            merged["words_api_details"] = {
                **(merged.get("words_api_details") or {}),
                **(entry.get("words_api_details") or {}),
            }

    if merged.get("definitions") and not merged.get("summary"):
        merged["summary"] = merged["definitions"][0]
    return merged
