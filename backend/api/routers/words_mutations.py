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

# OXFORD DICTIONARY & SYNONYM ENDPOINTS

@router.post("/words/validate")
async def validate_word(request: ValidateWordRequest):
    """Unified word lookup across all dictionary sources (UI-stable response)."""
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        if not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")

        lookup_result: dict = {}
        if request.skip_oxford:
            validation_result = deps.unified_lookup.to_ui_validation({
                "word": word.lower(),
                "is_valid": True,
                "definitions": [],
                "word_forms": [],
                "examples": [],
                "synonyms": [],
                "reason": "Dictionary validation skipped",
                "validation_source": "skipped",
            })
        else:
            lookup_result = await deps.word_lookup_orchestrator.lookup_for_ui(word)
            validation_result = deps.unified_lookup.to_ui_validation(lookup_result)

            if lookup_result.get("synonym_sources"):
                validation_result["synonym_sources"] = lookup_result["synonym_sources"]

        return {
            "success": True,
            "word": word.lower(),
            "oxford_validation": validation_result,
            "unified_validation": validation_result,
            "validation_source": validation_result.get("validation_source"),
            "source_details": lookup_result.get("source_details") if not request.skip_oxford else {},
            "message": f"Validation complete for '{word}'",
        }
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"Error validating word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/words/lookup")
async def unified_word_lookup_get(word: str = Query(..., min_length=1)):
    """Unified dictionary lookup (GET). Same logic as /words/validate."""
    request = ValidateWordRequest(word=word, skip_oxford=False)
    return await validate_word(request)

@router.post("/words/lookup")
async def unified_word_lookup_post(request: ValidateWordRequest):
    """Unified dictionary lookup (POST). Same logic as /words/validate."""
    return await validate_word(request)

@router.get("/words/search-basic")
async def search_basic_word(word: str):
    """Search for a word in our collection and all dictionary sources."""
    try:
        word_lower = word.strip().lower()
        if not word_lower or not word_lower.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")

        in_collection = word_lower in deps.words_set
        lookup_result = await deps.word_lookup_orchestrator.lookup_for_ui(word_lower)
        ui_result = deps.unified_lookup.to_ui_validation(lookup_result)

        # Always return a stable object so the UI never breaks on null.
        return BasicSearchResult(
            word=word_lower,
            inCollection=in_collection,
            oxford=ui_result,
        )
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"Error in basic search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/words/add-validated")
async def add_word_with_validation(request: ValidateWordRequest):
    """Add a word with Oxford Dictionary validation"""
    
    try:
        word = request.word.strip().lower()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        if not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        if word in deps.words_set:
            return AddWordResponse(
                success=True,
                message=f"Word '{word}' already exists in collection",
                word=word,
                was_new=False,
                total_words=len(deps.words_list)
            )
        
        if not request.skip_oxford:
            lookup_result = await deps.unified_lookup.lookup_word(word)
            if not lookup_result["is_valid"]:
                return AddWordResponse(
                    success=False,
                    message=f"Word '{word}' not found in dictionary sources: {lookup_result['reason']}",
                    word=word,
                    was_new=False,
                    total_words=len(deps.words_list)
                )
        
        success = await deps.word_manager.add_word(word)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add word to storage")
        
        # Align global lists
        deps.words_list = deps.word_manager.deps.words_list
        deps.words_set = deps.word_manager.deps.words_set
        
        lengths = [len(w) for w in deps.words_list]
        deps.word_stats["total_words"] = len(deps.words_list)
        if lengths:
            deps.word_stats["min_length"] = min(lengths)
            deps.word_stats["max_length"] = max(lengths)
            deps.word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return AddWordResponse(
            success=True,
            message=f"Word '{word}' added successfully",
            word=word,
            was_new=True,
            total_words=len(deps.words_list)
        )
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"Error adding validated word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# WORD MANAGEMENT ENDPOINTS (NEW ENDPOINTS CONSOLIDATED FROM CIVO/S3 IMPLEMENTATIONS)

@router.post("/words/add")
async def add_single_word(request: AddWordReq):
    """Add a single word to the collection without Oxford validation"""
    
    try:
        word = request.word.strip().lower()
        if not word or not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        if word in deps.words_set:
            return {
                "success": True,
                "message": f"Word '{word}' already exists",
                "word": word,
                "was_new": False
            }
        
        success = await deps.word_manager.add_word(word)
        if success:
            deps.words_list = deps.word_manager.deps.words_list
            deps.words_set = deps.word_manager.deps.words_set
            
            lengths = [len(w) for w in deps.words_list]
            deps.word_stats["total_words"] = len(deps.words_list)
            if lengths:
                deps.word_stats["min_length"] = min(lengths)
                deps.word_stats["max_length"] = max(lengths)
                deps.word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
                
            return {
                "success": True,
                "message": f"Word '{word}' added successfully",
                "word": word,
                "was_new": True,
                "total_words": len(deps.words_list)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add word")
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"Error adding word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/words/add-batch")
async def add_multiple_words(request: AddWordsReq):
    """Add multiple words to the collection"""
    
    try:
        if not request.words:
            raise HTTPException(status_code=400, detail="Words list cannot be empty")
        
        invalid_words = [w for w in request.words if not w.strip() or not w.strip().isalpha()]
        if invalid_words:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid words (must contain only letters): {invalid_words[:5]}"
            )
        
        added_count, total_count = await deps.word_manager.add_words(request.words)
        
        deps.words_list = deps.word_manager.deps.words_list
        deps.words_set = deps.word_manager.deps.words_set
        
        lengths = [len(w) for w in deps.words_list]
        deps.word_stats["total_words"] = len(deps.words_list)
        if lengths:
            deps.word_stats["min_length"] = min(lengths)
            deps.word_stats["max_length"] = max(lengths)
            deps.word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return {
            "success": True,
            "added_count": added_count,
            "total_submitted": total_count,
            "skipped_count": total_count - added_count,
            "total_words": len(deps.words_list),
            "message": f"Added {added_count} new words out of {total_count} submitted"
        }
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"Error adding multiple words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/words/remove")
async def remove_single_word(request: RemoveWordReq):
    """Remove a single word from the collection"""
    
    try:
        word = request.word.strip().lower()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        
        success = await deps.word_manager.remove_word(word)
        if success:
            deps.words_list = deps.word_manager.deps.words_list
            deps.words_set = deps.word_manager.deps.words_set
            
            lengths = [len(w) for w in deps.words_list]
            deps.word_stats["total_words"] = len(deps.words_list)
            if lengths:
                deps.word_stats["min_length"] = min(lengths)
                deps.word_stats["max_length"] = max(lengths)
                deps.word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
                
            return {
                "success": True,
                "word": word,
                "message": f"Word '{word}' removed successfully",
                "total_words": len(deps.words_list)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to remove word")
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"Error removing word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/words/remove-batch")
async def remove_multiple_words(request: RemoveWordsReq):
    """Remove multiple words from the collection"""
    
    try:
        if not request.words:
            raise HTTPException(status_code=400, detail="Words list cannot be empty")
        
        removed_count, total_count = await deps.word_manager.remove_words(request.words)
        
        deps.words_list = deps.word_manager.deps.words_list
        deps.words_set = deps.word_manager.deps.words_set
        
        lengths = [len(w) for w in deps.words_list]
        deps.word_stats["total_words"] = len(deps.words_list)
        if lengths:
            deps.word_stats["min_length"] = min(lengths)
            deps.word_stats["max_length"] = max(lengths)
            deps.word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return {
            "success": True,
            "removed_count": removed_count,
            "total_submitted": total_count,
            "not_found_count": total_count - removed_count,
            "total_words": len(deps.words_list),
            "message": f"Removed {removed_count} words out of {total_count} submitted"
        }
    except HTTPException:
        raise
    except Exception as e:
        deps.logger.error(f"Error removing multiple words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/words/reload")
async def reload_words():
    """Reload words from storage"""
    
    try:
        words = await deps.word_manager.reload_words()
        deps.words_list = deps.word_manager.deps.words_list
        deps.words_set = deps.word_manager.deps.words_set
        
        lengths = [len(w) for w in deps.words_list]
        deps.word_stats["total_words"] = len(deps.words_list)
        if lengths:
            deps.word_stats["min_length"] = min(lengths)
            deps.word_stats["max_length"] = max(lengths)
            deps.word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return {
            "success": True,
            "message": "Words reloaded from storage",
            "total_words": len(words),
            "storage_provider": (await deps.word_manager.get_storage_info()).get("provider", "unknown")
        }
    except Exception as e:
        deps.logger.error(f"Error reloading words: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload words from storage")

@router.get("/words/all")
async def get_all_words(
    limit: Optional[int] = Query(1000, ge=1, le=10000, description="Maximum number of words to return")
):
    """Get all words (admin endpoint)"""
    try:
        return {
            "total_words": len(deps.words_list),
            "returned_words": min(len(deps.words_list), limit),
            "words": deps.words_list[:limit]
        }
    except Exception as e:
        deps.logger.error(f"Error getting all words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


