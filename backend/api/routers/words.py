"""Route handlers (split from legacy main.py)."""
from typing import List, Optional
import asyncio
import random
import time

from fastapi import APIRouter, HTTPException, Query

from api import dependencies as deps
from api.schemas.word import (
    AddWordReq,
    AddWordResponse,
    AddWordsReq,
    BasicSearchResult,
    CleanupReq,
    FreeDictionaryLookupRequest,
    RemoveWordReq,
    RemoveWordsReq,
    ValidateWordRequest,
)
from dictionary_source_config import get_enrich_source_flags, get_portal_source_flags
from puzzle_solver import match_anagram, match_regex
from puzzle_solver import match_pattern as advanced_match_pattern

router = APIRouter()

# WORD QUERY ENDPOINTS

@router.get("/words", response_model=List[str])
async def get_filtered_words(
    contains: Optional[str] = Query(None, description="Letters the word should contain"),
    starts_with: Optional[str] = Query(None, description="Letters the word should start with"),
    ends_with: Optional[str] = Query(None, description="Letters the word should end with"),
    min_length: Optional[int] = Query(None, ge=1, description="Minimum word length"),
    max_length: Optional[int] = Query(None, ge=1, description="Maximum word length"),
    exact_length: Optional[int] = Query(None, ge=1, description="Exact word length"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """Filter words based on various criteria using concurrent processing"""
    filters = {
        'contains': contains,
        'starts_with': starts_with,
        'ends_with': ends_with,
        'min_length': min_length,
        'max_length': max_length,
        'exact_length': exact_length
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    return await deps.filter_words_concurrent(filters, limit)

@router.get("/words/advanced-filter")
async def get_advanced_filtered_words(
    contains: Optional[str] = Query(None, description="Letters the word should contain"),
    starts_with: Optional[str] = Query(None, description="Letters the word should start with"),
    ends_with: Optional[str] = Query(None, description="Letters the word should end with"),
    min_length: Optional[int] = Query(None, ge=1, alias="minLength"),
    max_length: Optional[int] = Query(None, ge=1, alias="maxLength"),
    exact_length: Optional[int] = Query(None, ge=1, alias="exactLength"),
    letter_pattern: Optional[str] = Query(None, alias="letterPattern"),
    limit: Optional[int] = Query(100, ge=1, le=100),
):
    """
    Advanced filter via Words API (letterPattern, letters, lettersMin, lettersMax, limit)
    with Word Game DB fallback. Empty filters return ~100 browse/random words.
    """
    result = await deps.advanced_word_filter_service.filter_words(
        contains=contains,
        starts_with=starts_with,
        ends_with=ends_with,
        exact_length=exact_length,
        min_length=min_length,
        max_length=max_length,
        letter_pattern=letter_pattern,
        limit=limit or 100,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=result.get("error") or "Advanced word filter unavailable",
        )
    return result

@router.get("/words/stats")
async def get_word_stats():
    """Get statistics about the word collection"""
    return deps.word_stats

@router.get("/words/check")
async def check_word(word: str):
    """Fast word lookup using set for O(1) performance"""
    word_lower = word.lower().strip()
    exists = word_lower in deps.words_set
    return {"word": word_lower, "exists": exists}

@router.post("/words/check")
async def check_word_post(request: AddWordReq):
    """Fast word lookup via POST using set for O(1) performance"""
    word_lower = request.word.lower().strip()
    exists = word_lower in deps.words_set
    return {"word": word_lower, "exists": exists}

@router.get("/words/by-length/{length}")
async def get_words_by_exact_length(length: int):
    """Get all words of a specific length using concurrent processing"""
    filters = {'exact_length': length}
    words = await deps.filter_words_concurrent(filters, limit=1000)
    return {
        "length": length,
        "count": len(words),
        "words": words
    }

@router.get("/words/interactive", response_model=List[str])
async def get_interactive_words(
    length: int = Query(..., description="Exact word length"),
    pattern: str = Query(..., description="Pattern with known letters (use ? for unknown positions)")
):
    """Find words matching a pattern for interactive word puzzles"""
    if length < 1 or length > 50:
        return []
    
    def match_pattern_chunk(chunk_data):
        words_chunk, target_length, target_pattern = chunk_data
        matched = []
        for word in words_chunk:
            if len(word) != target_length:
                continue
            match = True
            for i, (pattern_char, word_char) in enumerate(zip(target_pattern, word)):
                if pattern_char != '?' and pattern_char.lower() != word_char.lower():
                    match = False
                    break
            if match:
                matched.append(word)
        return matched
    
    length_filtered = [word for word in deps.words_list if len(word) == length]
    
    if len(length_filtered) < 1000:
        matched_words = []
        for word in length_filtered:
            match = True
            for i, (pattern_char, word_char) in enumerate(zip(pattern, word)):
                if pattern_char != '?' and pattern_char.lower() != word_char.lower():
                    match = False
                    break
            if match:
                matched_words.append(word)
        return matched_words[:500]
    
    chunk_size = max(100, len(length_filtered) // 4)
    chunks = []
    for i in range(0, len(length_filtered), chunk_size):
        chunk = length_filtered[i:i + chunk_size]
        chunks.append((chunk, length, pattern))
    
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(deps.thread_pool, match_pattern_chunk, chunk_data)
        for chunk_data in chunks
    ]
    results = await asyncio.gather(*tasks)
    
    matched_words = []
    for result in results:
        matched_words.extend(result)
        
    return matched_words[:500]

@router.get("/words/puzzle", response_model=List[str])
async def get_puzzle_words(
    pattern: Optional[str] = Query(None, description="Pattern with known letters, ? for any, @ for vowels, # for consonants"),
    regex: Optional[str] = Query(None, description="Regular expression pattern to match"),
    anagram: Optional[str] = Query(None, description="Letters to match anagrams from"),
    anagram_exact: bool = Query(False, description="Whether to require exact anagram match"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    sp: Optional[str] = Query(None, description="DataMuse spelled-like pattern (e.g. ???? for 4-letter words)"),
    ml: Optional[str] = Query(None, description="DataMuse means-like query"),
    sl: Optional[str] = Query(None, description="DataMuse sounds-like query"),
    rel_syn: Optional[str] = Query(None, description="DataMuse related synonym"),
    rel_trg: Optional[str] = Query(None, description="DataMuse related trigger word"),
    rel_jja: Optional[str] = Query(None, description="DataMuse adjective modifier of noun"),
    rel_jjb: Optional[str] = Query(None, description="DataMuse adjective described by noun"),
    include_datamuse: bool = Query(True, description="Merge DataMuse results when query params are provided"),
):
    """Find words matching advanced puzzle filters (wildcards, regex, anagrams, and DataMuse)."""
    candidates = list(deps.words_list)
    datamuse_words: List[str] = []

    dm_params: dict = {}
    if sp:
        dm_params["sp"] = sp
    if ml:
        dm_params["ml"] = ml
    if sl:
        dm_params["sl"] = sl
    if rel_syn:
        dm_params["rel_syn"] = rel_syn
    if rel_trg:
        dm_params["rel_trg"] = rel_trg
    if rel_jja:
        dm_params["rel_jja"] = rel_jja
    if rel_jjb:
        dm_params["rel_jjb"] = rel_jjb

    if dm_params and include_datamuse and deps.datamuse_service.is_configured():
        dm_params["max"] = min(limit * 2, 1000)
        datamuse_words = await deps.datamuse_service.find_words_for_puzzle(**dm_params)

    if anagram:
        candidates = [w for w in candidates if match_anagram(w, anagram, exact=anagram_exact)]
        if datamuse_words:
            datamuse_words = [
                w for w in datamuse_words if match_anagram(w, anagram, exact=anagram_exact)
            ]

    if pattern:
        candidates = [w for w in candidates if advanced_match_pattern(w, pattern)]
        if datamuse_words and not sp:
            datamuse_words = [
                w for w in datamuse_words if advanced_match_pattern(w, pattern)
            ]

    if regex:
        candidates = [w for w in candidates if match_regex(w, regex)]
        if datamuse_words:
            datamuse_words = [w for w in datamuse_words if match_regex(w, regex)]

    merged: List[str] = []
    seen: set = set()
    for word in candidates + datamuse_words:
        key = word.lower()
        if key not in seen:
            seen.add(key)
            merged.append(key)

    return merged[:limit]

@router.get("/words/random")
async def get_random_word(
    length: int = Query(5, ge=1, le=50, description="Length of the random word"),
    starts_with: Optional[str] = Query(None, description="Word starts with letter"),
    ends_with: Optional[str] = Query(None, description="Word ends with letter")
):
    """Get a random word from the dictionary matching constraints"""
    import random
    filtered = [w for w in deps.words_list if len(w) == length]
    if starts_with:
        starts_with = starts_with.lower()
        filtered = [w for w in filtered if w.startswith(starts_with)]
    if ends_with:
        ends_with = ends_with.lower()
        filtered = [w for w in filtered if w.endswith(ends_with)]
        
    if not filtered:
        raise HTTPException(status_code=404, detail="No matching words found")
        
    return {
        "success": True,
        "word": random.choice(filtered)
    }

@router.get("/performance/stats")
async def get_performance_stats():
    """Get performance statistics"""
    return {
        "words_loaded": len(deps.words_list),
        "memory_usage": {
            "words_list_size": len(deps.words_list),
            "words_set_size": len(deps.words_set)
        },
        "thread_pool_workers": deps.thread_pool._max_workers,
        "process_pool_workers": deps.process_pool._max_workers,
        "optimization_features": [
            "Concurrent file loading",
            "Parallel word filtering",
            "Fast O(1) word lookup",
            "Chunked processing",
            "Memory-efficient file reading"
        ]
    }


