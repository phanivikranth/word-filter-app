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

@router.get("/datamuse/words")
async def datamuse_words(
    sp: Optional[str] = Query(None, description="Spelled like"),
    ml: Optional[str] = Query(None, description="Means like"),
    sl: Optional[str] = Query(None, description="Sounds like"),
    rel_syn: Optional[str] = Query(None),
    rel_trg: Optional[str] = Query(None),
    rel_jja: Optional[str] = Query(None),
    rel_jjb: Optional[str] = Query(None),
    topics: Optional[str] = Query(None),
    max_results: int = Query(100, alias="max", ge=1, le=1000),
    md: Optional[str] = Query(None, description="Metadata flags, e.g. d for definitions"),
):
    """DataMuse word-finding API proxy."""
    if not deps.datamuse_service.is_configured():
        raise HTTPException(status_code=503, detail="DataMuse is disabled")
    params = {
        "sp": sp,
        "ml": ml,
        "sl": sl,
        "rel_syn": rel_syn,
        "rel_trg": rel_trg,
        "rel_jja": rel_jja,
        "rel_jjb": rel_jjb,
        "topics": topics,
        "max": max_results,
        "md": md,
    }
    payload = await deps.datamuse_service.query_words(**params)
    if not payload.get("ok"):
        raise HTTPException(
            status_code=payload.get("status") or 502,
            detail=payload.get("error") or "DataMuse query failed",
        )
    return {"success": True, "words": payload["data"]}

@router.get("/datamuse/sug")
async def datamuse_suggest(
    s: str = Query(..., min_length=1, description="Prefix for autocomplete"),
    max_results: int = Query(10, alias="max", ge=1, le=100),
):
    """DataMuse autocomplete suggestions."""
    if not deps.datamuse_service.is_configured():
        raise HTTPException(status_code=503, detail="DataMuse is disabled")
    payload = await deps.datamuse_service.suggest(s, max_results=max_results)
    if not payload.get("ok"):
        raise HTTPException(
            status_code=payload.get("status") or 502,
            detail=payload.get("error") or "DataMuse suggest failed",
        )
    return {"success": True, "suggestions": payload["data"]}

@router.get("/datamuse/daily-safe-explore")
async def datamuse_daily_safe_explore():
    """Daily Safe Words to Explore — 8-letter DataMuse words (cached per day)."""
    result = await deps.daily_safe_explore_service.get_daily_words()
    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=result.get("error") or "Daily safe explore words unavailable",
        )
    return {
        "success": True,
        "date": result["date"],
        "words": result["words"],
        "source": result.get("source", "datamuse"),
        "cached": result.get("cached", False),
    }

@router.get("/datamuse/daily-word-challenge")
async def datamuse_daily_word_challenge():
    """Daily Word Challenge cards — 4 education-topic DataMuse words (cached per day)."""
    result = await deps.daily_word_challenge_service.get_daily_challenge()
    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=result.get("error") or "Daily word challenge unavailable",
        )
    return {
        "success": True,
        "date": result["date"],
        "items": result["items"],
        "source": result.get("source", "datamuse"),
        "cached": result.get("cached", False),
    }

@router.get("/puzzle/daily-scramble")
async def get_daily_scramble_puzzle():
    """Daily scrambled-word puzzle (cached per calendar day)."""
    result = await deps.daily_scramble_service.get_daily_scramble(local_words=deps.words_list)
    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=result.get("error") or "Daily scramble unavailable",
        )
    return {
        "success": True,
        "date": result["date"],
        "scrambled": result["scrambled"],
        "hint": result.get("hint", ""),
        "source": result.get("source", ""),
        "cached": result.get("cached", False),
        # Answer included for client-side validation; same for all users each day.
        "word": result["word"],
    }


