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

@router.get("/word-game-db/categories")
async def word_game_db_categories():
    """Word Game DB: list categories."""
    if not deps.word_game_db_service.is_configured():
        raise HTTPException(status_code=503, detail="Word Game DB is disabled")
    payload = await deps.word_game_db_service.get_categories()
    if not payload.get("ok"):
        raise HTTPException(
            status_code=payload.get("status") or 502,
            detail=payload.get("error") or "Word Game DB categories failed",
        )
    return {"success": True, "categories": payload["data"]}

@router.get("/word-game-db/random")
async def word_game_db_random():
    """Word Game DB: random word."""
    if not deps.word_game_db_service.is_configured():
        raise HTTPException(status_code=503, detail="Word Game DB is disabled")
    payload = await deps.word_game_db_service.get_random_word()
    if not payload.get("ok"):
        raise HTTPException(
            status_code=payload.get("status") or 502,
            detail=payload.get("error") or "Word Game DB random failed",
        )
    data = payload["data"]
    word = str((data or {}).get("word") or "").strip().lower()
    hint = str((data or {}).get("hint") or "").strip()
    return {
        "success": True,
        "word": word,
        "definition": hint,
        "data": data,
    }

@router.get("/word-game-db/words")
async def word_game_db_words(
    min_letters: Optional[int] = Query(None, alias="minLetters"),
    max_letters: Optional[int] = Query(None, alias="maxLetters"),
    min_syllables: Optional[int] = Query(None, alias="minSyllables"),
    max_syllables: Optional[int] = Query(None, alias="maxSyllables"),
    limit: Optional[int] = Query(10, ge=1, le=100),
    offset: Optional[int] = Query(0, ge=0),
    category: Optional[str] = None,
):
    """Word Game DB: filtered word list with pagination."""
    if not deps.word_game_db_service.is_configured():
        raise HTTPException(status_code=503, detail="Word Game DB is disabled")
    payload = await deps.word_game_db_service.list_words(
        min_letters=min_letters,
        max_letters=max_letters,
        min_syllables=min_syllables,
        max_syllables=max_syllables,
        limit=limit,
        offset=offset,
        category=category,
    )
    if not payload.get("ok"):
        raise HTTPException(
            status_code=payload.get("status") or 502,
            detail=payload.get("error") or "Word Game DB words query failed",
        )
    return {"success": True, **payload["data"]}

@router.get("/words-api/search")
async def words_api_search(
    letter_pattern: str = Query(..., alias="letterPattern"),
):
    """Words API (RapidAPI): search by letter pattern, e.g. ^a.{4}$"""
    if not deps.words_api_rapidapi_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Words API (RapidAPI) is not configured (WORDS_API_RAPIDAPI_KEY)",
        )
    payload = await deps.words_api_rapidapi_service.search_words(
        letter_pattern=letter_pattern
    )
    if not payload.get("ok"):
        raise HTTPException(
            status_code=payload.get("status") or 502,
            detail=payload.get("error") or "Words API search failed",
        )
    return {"success": True, "letterPattern": letter_pattern, "data": payload["data"]}

@router.get("/words-api/random")
async def words_api_random():
    """Words API (RapidAPI): random word with definition (Daily Safe Word)."""
    if not deps.words_api_rapidapi_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Words API (RapidAPI) is not configured (WORDS_API_RAPIDAPI_KEY)",
        )
    payload = await deps.words_api_rapidapi_service.get_random_daily_word()
    if not payload.get("ok"):
        raise HTTPException(
            status_code=payload.get("status") or 502,
            detail=payload.get("error") or "Words API random word failed",
        )
    return {
        "success": True,
        "word": payload.get("word", ""),
        "definition": payload.get("definition", ""),
        "data": payload.get("data"),
    }

@router.get("/words-api/{word}/{detail}")
async def words_api_lookup_detail(word: str, detail: str):
    """Words API (RapidAPI): detail endpoint (synonyms, rhymes, frequency, etc.)."""
    if not deps.words_api_rapidapi_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Words API (RapidAPI) is not configured (WORDS_API_RAPIDAPI_KEY)",
        )
    clean = word.strip().lower()
    if not clean or not clean.isalpha():
        raise HTTPException(status_code=400, detail="Word must contain only letters")
    payload = await deps.words_api_rapidapi_service.get_word_detail(clean, detail)
    if not payload.get("ok"):
        raise HTTPException(
            status_code=payload.get("status") or 502,
            detail=payload.get("error") or "Words API request failed",
        )
    return {"success": True, "word": clean, "detail": detail, "data": payload["data"]}

@router.get("/words-api/{word}")
async def words_api_lookup_word(word: str):
    """Words API (RapidAPI): full word lookup with synonyms, rhymes, frequency."""
    if not deps.words_api_rapidapi_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Words API (RapidAPI) is not configured (WORDS_API_RAPIDAPI_KEY)",
        )
    clean = word.strip().lower()
    if not clean or not clean.isalpha():
        raise HTTPException(status_code=400, detail="Word must contain only letters")
    result = await deps.words_api_rapidapi_service.validate_word(clean)
    return {"success": bool(result.get("is_valid")), **result}

@router.get("/words/freedictionary")
async def lookup_freedictionary_word(word: str = Query(..., min_length=1)):
    """Look up a word on TheFreeDictionary (dictionary, with encyclopedia fallback)."""
    try:
        clean = word.strip()
        if not clean:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        result = await deps.freedictionary_service.lookup_word(clean)
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"FreeDictionary lookup failed for '{word}': {e}")
        raise HTTPException(status_code=500, detail="FreeDictionary lookup failed")

@router.post("/words/freedictionary")
async def lookup_freedictionary_word_post(request: FreeDictionaryLookupRequest):
    """Look up a word on TheFreeDictionary (POST body: {\"word\": \"...\"})."""
    try:
        clean = request.word.strip()
        if not clean:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        result = await deps.freedictionary_service.lookup_word(clean)
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"FreeDictionary lookup failed for '{request.word}': {e}")
        raise HTTPException(status_code=500, detail="FreeDictionary lookup failed")


