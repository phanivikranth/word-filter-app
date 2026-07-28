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

# STORAGE & CLOUD CONFIGURATION ENDPOINTS

@router.get("/storage/info")
async def get_storage_info():
    """Get information about the current storage configuration"""
    try:
        storage_info = await deps.word_manager.get_storage_info()
        return {
            "success": True,
            "storage_info": storage_info,
            "nhost": deps.nhost_service.get_status(),
            "dictionary_sources": {
                "portal": get_portal_source_flags().as_dict(),
                "enrich": get_enrich_source_flags().as_dict(),
            },
        }
    except Exception as e:
        deps.logger.error(f"Error getting storage info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/storage/test")
async def test_storage_connection():
    """Test storage connection (admin endpoint)"""
    try:
        result = await deps.word_manager.test_storage_connection()
        return {
            "success": True,
            "connection_test": result
        }
    except Exception as e:
        deps.logger.error(f"Error testing storage connection: {e}")
        raise HTTPException(status_code=500, detail="Storage connection test failed")

@router.get("/cloud/info")
async def get_cloud_info():
    """Get information about the cloud provider"""
    storage_info = await deps.word_manager.get_storage_info()
    return {
        "cloud_provider": storage_info.get("provider", "local"),
        "region": storage_info.get("region", "N/A"),
        "storage_type": storage_info.get("type", "file"),
        "features": [
            "object_store",
            "load_balancer", 
            "auto_scaling",
            "monitoring",
            "cost_optimization"
        ]
    }

@router.post("/words/cleanup")
async def cleanup_invalid_words(request: CleanupReq):
    """Find and optionally remove invalid words from the collection"""
    
    try:
        result = await deps.word_manager.cleanup_invalid_words(auto_remove=request.auto_remove)
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
            "cleanup_summary": {
                "found_invalid": result["found_invalid"],
                "removed_count": result["removed_count"],
                "action_taken": result["action_taken"]
            },
            "invalid_words": result["invalid_words"],
            "total_words": len(deps.words_list),
            "message": result["action_taken"]
        }
    except Exception as e:
        deps.logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/words/oxford-stats")
async def get_oxford_cache_statistics():
    """Get Oxford Dictionary API cache statistics"""
    try:
        stats = await deps.word_manager.get_oxford_cache_stats()
        return {
            "success": True,
            "oxford_cache": stats,
            "message": "Oxford cache statistics retrieved"
        }
    except Exception as e:
        deps.logger.error(f"Error getting Oxford stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/words/dictionary-stats")
async def get_dictionary_statistics():
    """Get combined dictionary API usage (Merriam-Webster quota + Oxford cache)"""
    try:
        stats = deps.unified_lookup.get_dictionary_stats()
        stats["freedictionary"] = deps.freedictionary_service.get_cache_stats()
        return {
            "success": True,
            "dictionary_stats": stats,
            "message": "Dictionary API statistics retrieved"
        }
    except Exception as e:
        deps.logger.error(f"Error getting dictionary stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


