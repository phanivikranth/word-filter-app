from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import functools
import time
from pathlib import Path
import uuid
import os
from pydantic import BaseModel
from dotenv import load_dotenv

from oxford_validator import OxfordValidator
from synonym_service import get_synonym_service
from word_manager import WordManager
from puzzle_solver import match_pattern as advanced_match_pattern, match_regex, match_anagram

# Import logging configuration
from logger_config import (
    setup_logging, get_logger, log_performance, log_api_call,
    monitor_performance, monitor_async_performance, LoggerMixin
)

# Initialize logging
setup_logging()
logger = get_logger("word_filter.main")

# Load environment variables
load_dotenv()

# Pydantic models
class ValidateWordRequest(BaseModel):
    word: str
    skip_oxford: bool = False

class BasicSearchResult(BaseModel):
    word: str
    inCollection: bool
    oxford: Optional[dict] = None

class AddWordResponse(BaseModel):
    success: bool
    message: str
    word: Optional[str] = None
    was_new: bool = False
    total_words: Optional[int] = None

class AddWordReq(BaseModel):
    word: str

class AddWordsReq(BaseModel):
    words: List[str]

class RemoveWordReq(BaseModel):
    word: str

class RemoveWordsReq(BaseModel):
    words: List[str]

class CleanupReq(BaseModel):
    auto_remove: bool = False

app = FastAPI(
    title="Word Filter API - Unified", 
    description="API for filtering words with local file and Object Store storage options",
    version="2.2.0"
)

# Request logging middleware
total_api_requests = 0

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with performance monitoring"""
    global total_api_requests
    total_api_requests += 1
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Add request ID to request state
    request.state.request_id = request_id
    
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={"extra_fields": {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        }}
    )
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log API call
        log_api_call(
            request.method,
            request.url.path,
            response.status_code,
            duration,
            request_id=request_id,
            response_size=response.headers.get("content-length", 0)
        )
        
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} - {str(e)}",
            exc_info=True,
            extra={"extra_fields": {
                "request_id": request_id,
                "duration_seconds": duration,
                "error": str(e)
            }}
        )
        raise

# Configure CORS to allow Angular frontend
_default_origins = [
    "http://localhost:4200",
    "http://localhost:4201",
    "https://word-dol.pages.dev",  # Cloudflare Pages production
    "https://word-filter-app.pages.dev",  # Cloudflare Pages default domain
]
_cors_env = os.getenv("CORS_ORIGINS", "").strip()
if _cors_env == "*":
    # Allow all origins (without credentials to avoid browser CORS errors)
    cors_origins = ["*"]
    _cors_credentials = False
elif _cors_env:
    cors_origins = [
        origin.strip()
        for origin in _cors_env.split(",")
        if origin.strip()
    ] or _default_origins
    _cors_credentials = True
else:
    cors_origins = _default_origins
    _cors_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage and validation instances
word_manager = WordManager()
oxford_validator = OxfordValidator()

# Global variables to store words (for fast/optimized concurrent filtering read paths)
words_list = []
words_set = set()
word_stats = {}

# Thread and Process pool for concurrent filtering operations
thread_pool = ThreadPoolExecutor(max_workers=4)
process_pool = ProcessPoolExecutor(max_workers=2)

# Initialize synonym service
MERRIAM_WEBSTER_KEY = os.getenv('MERRIAM_WEBSTER_API_KEY')
synonym_service = get_synonym_service(MERRIAM_WEBSTER_KEY)

@monitor_async_performance("load_words_concurrent")
async def load_words_concurrent():
    """Load words from storage using unified WordManager and update globals"""
    global words_list, words_set, word_stats
    
    logger.info("Initiating concurrent words load from word_manager")
    start_time = time.time()
    
    # Load using unified WordManager
    loaded_words = await word_manager.load_words()
    
    words_list = word_manager.words_list
    words_set = word_manager.words_set
    
    # Calculate statistics
    lengths = [len(word) for word in words_list]
    word_stats = {
        "total_words": len(words_list),
        "min_length": min(lengths) if lengths else 0,
        "max_length": max(lengths) if lengths else 0,
        "avg_length": round(sum(lengths) / len(lengths), 2) if lengths else 0
    }
    
    load_time = time.time() - start_time
    logger.info(f"Loaded {len(words_list):,} words concurrently in {load_time:.2f}s")
    return words_list, words_set, word_stats

def filter_words_chunk(chunk_data):
    """Filter a chunk of words - designed for parallel processing"""
    words_chunk, filters = chunk_data
    filtered = []
    
    contains = filters.get('contains', '').lower() if filters.get('contains') else None
    starts_with = filters.get('starts_with', '').lower() if filters.get('starts_with') else None
    ends_with = filters.get('ends_with', '').lower() if filters.get('ends_with') else None
    min_length = filters.get('min_length')
    max_length = filters.get('max_length')
    exact_length = filters.get('exact_length')
    
    for word in words_chunk:
        if contains and contains not in word:
            continue
        if starts_with and not word.startswith(starts_with):
            continue
        if ends_with and not word.endswith(ends_with):
            continue
        if exact_length and len(word) != exact_length:
            continue
        elif not exact_length:
            if min_length and len(word) < min_length:
                continue
            if max_length and len(word) > max_length:
                continue
        filtered.append(word)
        
    return filtered

async def filter_words_concurrent(filters: dict, limit: int = 100):
    """Filter words using concurrent processing for better performance"""
    if not words_list:
        return []
    
    if len(words_list) < 10000 or not any(filters.values()):
        return filter_words_simple(filters, limit)
    
    chunk_size = max(1000, len(words_list) // 4)
    chunks = []
    for i in range(0, len(words_list), chunk_size):
        chunk = words_list[i:i + chunk_size]
        chunks.append((chunk, filters))
    
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(process_pool, filter_words_chunk, chunk_data)
        for chunk_data in chunks
    ]
    results = await asyncio.gather(*tasks)
    
    filtered_words = []
    for result in results:
        filtered_words.extend(result)
        if len(filtered_words) >= limit:
            break
            
    return filtered_words[:limit]

def filter_words_simple(filters: dict, limit: int = 100):
    """Simple synchronous filtering for small datasets"""
    filtered = []
    contains = filters.get('contains', '').lower() if filters.get('contains') else None
    starts_with = filters.get('starts_with', '').lower() if filters.get('starts_with') else None
    ends_with = filters.get('ends_with', '').lower() if filters.get('ends_with') else None
    min_length = filters.get('min_length')
    max_length = filters.get('max_length')
    exact_length = filters.get('exact_length')
    
    for word in words_list:
        if len(filtered) >= limit:
            break
        if contains and contains not in word:
            continue
        if starts_with and not word.startswith(starts_with):
            continue
        if ends_with and not word.endswith(ends_with):
            continue
        if exact_length and len(word) != exact_length:
            continue
        elif not exact_length:
            if min_length and len(word) < min_length:
                continue
            if max_length and len(word) > max_length:
                continue
        filtered.append(word)
        
    return filtered

@app.on_event("startup")
async def startup_event():
    """Load words on startup using concurrent processing"""
    logger.info("Application startup initiated")
    try:
        await load_words_concurrent()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error("Application startup failed", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup thread pools on shutdown"""
    logger.info("Application shutdown initiated")
    try:
        thread_pool.shutdown(wait=True)
        process_pool.shutdown(wait=True)
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error("Error during application shutdown", exc_info=True)

# HEALTH ENDPOINTS

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Word Filter API - Optimized", "total_words": len(words_list)}

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes/Railway"""
    try:
        word_count = await word_manager.get_word_count()
        storage_info = await word_manager.get_storage_info()
        return {
            "status": "healthy",
            "word_count": word_count,
            "storage_connected": storage_info.get("connected", False),
            "storage_provider": storage_info.get("provider", "unknown"),
            "storage_type": storage_info.get("type", "unknown"),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/health/ready")
async def readiness_check():
    """Readiness probe for deployment orchestrators"""
    try:
        # Check if word database is accessible and loaded
        if not words_list:
            await load_words_concurrent()
        
        if not words_list:
            raise Exception("Word database not loaded")
        
        return {
            "ready": True,
            "words_loaded": len(words_list),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Not ready")

@app.get("/health/live")
async def liveness_check():
    """Liveness probe for deployment orchestrators"""
    try:
        # Simple check that the service is running
        return {
            "alive": True,
            "uptime": time.time(),
            "version": "2.2.0"
        }
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service dead")

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint for monitoring"""
    try:
        metrics = [
            f"# HELP word_filter_total_words Total number of words in database",
            f"# TYPE word_filter_total_words gauge",
            f"word_filter_total_words {len(words_list)}",
            f"# HELP word_filter_api_requests_total Total API requests",
            f"# TYPE word_filter_api_requests_total counter",
            f"word_filter_api_requests_total {total_api_requests}"
        ]
        return "\n".join(metrics) + "\n"
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")

# WORD QUERY ENDPOINTS

@app.get("/words", response_model=List[str])
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
    return await filter_words_concurrent(filters, limit)

@app.get("/words/stats")
async def get_word_stats():
    """Get statistics about the word collection"""
    return word_stats

@app.get("/words/check")
async def check_word(word: str):
    """Fast word lookup using set for O(1) performance"""
    word_lower = word.lower().strip()
    exists = word_lower in words_set
    return {"word": word_lower, "exists": exists}

@app.post("/words/check")
async def check_word_post(request: AddWordReq):
    """Fast word lookup via POST using set for O(1) performance"""
    word_lower = request.word.lower().strip()
    exists = word_lower in words_set
    return {"word": word_lower, "exists": exists}

@app.get("/words/by-length/{length}")
async def get_words_by_exact_length(length: int):
    """Get all words of a specific length using concurrent processing"""
    filters = {'exact_length': length}
    words = await filter_words_concurrent(filters, limit=1000)
    return {
        "length": length,
        "count": len(words),
        "words": words
    }

@app.get("/words/interactive", response_model=List[str])
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
    
    length_filtered = [word for word in words_list if len(word) == length]
    
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
        loop.run_in_executor(thread_pool, match_pattern_chunk, chunk_data)
        for chunk_data in chunks
    ]
    results = await asyncio.gather(*tasks)
    
    matched_words = []
    for result in results:
        matched_words.extend(result)
        
    return matched_words[:500]

@app.get("/words/puzzle", response_model=List[str])
async def get_puzzle_words(
    pattern: Optional[str] = Query(None, description="Pattern with known letters, ? for any, @ for vowels, # for consonants"),
    regex: Optional[str] = Query(None, description="Regular expression pattern to match"),
    anagram: Optional[str] = Query(None, description="Letters to match anagrams from"),
    anagram_exact: bool = Query(False, description="Whether to require exact anagram match"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return")
):
    """Find words matching advanced puzzle filters (wildcards, regex, and anagrams)"""
    candidates = words_list
    
    if anagram:
        candidates = [w for w in candidates if match_anagram(w, anagram, exact=anagram_exact)]
        
    if pattern:
        candidates = [w for w in candidates if advanced_match_pattern(w, pattern)]
        
    if regex:
        candidates = [w for w in candidates if match_regex(w, regex)]
        
    return candidates[:limit]

@app.get("/words/random")
async def get_random_word(
    length: int = Query(5, ge=1, le=50, description="Length of the random word"),
    starts_with: Optional[str] = Query(None, description="Word starts with letter"),
    ends_with: Optional[str] = Query(None, description="Word ends with letter")
):
    """Get a random word from the dictionary matching constraints"""
    import random
    filtered = [w for w in words_list if len(w) == length]
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

@app.get("/performance/stats")
async def get_performance_stats():
    """Get performance statistics"""
    return {
        "words_loaded": len(words_list),
        "memory_usage": {
            "words_list_size": len(words_list),
            "words_set_size": len(words_set)
        },
        "thread_pool_workers": thread_pool._max_workers,
        "process_pool_workers": process_pool._max_workers,
        "optimization_features": [
            "Concurrent file loading",
            "Parallel word filtering",
            "Fast O(1) word lookup",
            "Chunked processing",
            "Memory-efficient file reading"
        ]
    }

# OXFORD DICTIONARY & SYNONYM ENDPOINTS

@app.post("/words/validate")
async def validate_word(request: ValidateWordRequest):
    """Validate a word using Oxford Dictionary and fetch synonyms from multiple sources"""
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        if not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        validation_result = await oxford_validator.validate_word(word)
        synonym_data = await synonym_service.get_synonyms_combined(word, validation_result, max_results=15)
        
        validation_result['synonyms'] = synonym_data['synonyms']
        validation_result['synonym_sources'] = synonym_data['sources']
        
        if synonym_data['count'] > 0:
            if 'synonym' not in validation_result['reason']:
                validation_result['reason'] += f" and {synonym_data['count']} synonym(s) from multiple sources"
        
        return {
            "success": True,
            "word": word.lower(),
            "oxford_validation": validation_result,
            "message": f"Validation complete for '{word}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/words/search-basic")
async def search_basic_word(word: str):
    """Search for a word in our collection and Oxford Dictionary"""
    try:
        word_lower = word.strip().lower()
        if not word_lower or not word_lower.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        in_collection = word_lower in words_set
        oxford_result = await oxford_validator.validate_word(word_lower)
        
        return BasicSearchResult(
            word=word_lower,
            inCollection=in_collection,
            oxford=oxford_result if oxford_result["is_valid"] else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in basic search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/add-validated")
async def add_word_with_validation(request: ValidateWordRequest):
    """Add a word with Oxford Dictionary validation"""
    global words_list, words_set, word_stats
    try:
        word = request.word.strip().lower()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        if not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        if word in words_set:
            return AddWordResponse(
                success=True,
                message=f"Word '{word}' already exists in collection",
                word=word,
                was_new=False,
                total_words=len(words_list)
            )
        
        if not request.skip_oxford:
            oxford_result = await oxford_validator.validate_word(word)
            if not oxford_result["is_valid"]:
                return AddWordResponse(
                    success=False,
                    message=f"Word '{word}' not found in Oxford Dictionary: {oxford_result['reason']}",
                    word=word,
                    was_new=False,
                    total_words=len(words_list)
                )
        
        success = await word_manager.add_word(word)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add word to storage")
        
        # Align global lists
        words_list = word_manager.words_list
        words_set = word_manager.words_set
        
        lengths = [len(w) for w in words_list]
        word_stats["total_words"] = len(words_list)
        if lengths:
            word_stats["min_length"] = min(lengths)
            word_stats["max_length"] = max(lengths)
            word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return AddWordResponse(
            success=True,
            message=f"Word '{word}' added successfully",
            word=word,
            was_new=True,
            total_words=len(words_list)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding validated word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# WORD MANAGEMENT ENDPOINTS (NEW ENDPOINTS CONSOLIDATED FROM CIVO/S3 IMPLEMENTATIONS)

@app.post("/words/add")
async def add_single_word(request: AddWordReq):
    """Add a single word to the collection without Oxford validation"""
    global words_list, words_set, word_stats
    try:
        word = request.word.strip().lower()
        if not word or not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        if word in words_set:
            return {
                "success": True,
                "message": f"Word '{word}' already exists",
                "word": word,
                "was_new": False
            }
        
        success = await word_manager.add_word(word)
        if success:
            words_list = word_manager.words_list
            words_set = word_manager.words_set
            
            lengths = [len(w) for w in words_list]
            word_stats["total_words"] = len(words_list)
            if lengths:
                word_stats["min_length"] = min(lengths)
                word_stats["max_length"] = max(lengths)
                word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
                
            return {
                "success": True,
                "message": f"Word '{word}' added successfully",
                "word": word,
                "was_new": True,
                "total_words": len(words_list)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add word")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/add-batch")
async def add_multiple_words(request: AddWordsReq):
    """Add multiple words to the collection"""
    global words_list, words_set, word_stats
    try:
        if not request.words:
            raise HTTPException(status_code=400, detail="Words list cannot be empty")
        
        invalid_words = [w for w in request.words if not w.strip() or not w.strip().isalpha()]
        if invalid_words:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid words (must contain only letters): {invalid_words[:5]}"
            )
        
        added_count, total_count = await word_manager.add_words(request.words)
        
        words_list = word_manager.words_list
        words_set = word_manager.words_set
        
        lengths = [len(w) for w in words_list]
        word_stats["total_words"] = len(words_list)
        if lengths:
            word_stats["min_length"] = min(lengths)
            word_stats["max_length"] = max(lengths)
            word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return {
            "success": True,
            "added_count": added_count,
            "total_submitted": total_count,
            "skipped_count": total_count - added_count,
            "total_words": len(words_list),
            "message": f"Added {added_count} new words out of {total_count} submitted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding multiple words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/remove")
async def remove_single_word(request: RemoveWordReq):
    """Remove a single word from the collection"""
    global words_list, words_set, word_stats
    try:
        word = request.word.strip().lower()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        
        success = await word_manager.remove_word(word)
        if success:
            words_list = word_manager.words_list
            words_set = word_manager.words_set
            
            lengths = [len(w) for w in words_list]
            word_stats["total_words"] = len(words_list)
            if lengths:
                word_stats["min_length"] = min(lengths)
                word_stats["max_length"] = max(lengths)
                word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
                
            return {
                "success": True,
                "word": word,
                "message": f"Word '{word}' removed successfully",
                "total_words": len(words_list)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to remove word")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/remove-batch")
async def remove_multiple_words(request: RemoveWordsReq):
    """Remove multiple words from the collection"""
    global words_list, words_set, word_stats
    try:
        if not request.words:
            raise HTTPException(status_code=400, detail="Words list cannot be empty")
        
        removed_count, total_count = await word_manager.remove_words(request.words)
        
        words_list = word_manager.words_list
        words_set = word_manager.words_set
        
        lengths = [len(w) for w in words_list]
        word_stats["total_words"] = len(words_list)
        if lengths:
            word_stats["min_length"] = min(lengths)
            word_stats["max_length"] = max(lengths)
            word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return {
            "success": True,
            "removed_count": removed_count,
            "total_submitted": total_count,
            "not_found_count": total_count - removed_count,
            "total_words": len(words_list),
            "message": f"Removed {removed_count} words out of {total_count} submitted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing multiple words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/reload")
async def reload_words():
    """Reload words from storage"""
    global words_list, words_set, word_stats
    try:
        words = await word_manager.reload_words()
        words_list = word_manager.words_list
        words_set = word_manager.words_set
        
        lengths = [len(w) for w in words_list]
        word_stats["total_words"] = len(words_list)
        if lengths:
            word_stats["min_length"] = min(lengths)
            word_stats["max_length"] = max(lengths)
            word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return {
            "success": True,
            "message": "Words reloaded from storage",
            "total_words": len(words),
            "storage_provider": (await word_manager.get_storage_info()).get("provider", "unknown")
        }
    except Exception as e:
        logger.error(f"Error reloading words: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload words from storage")

@app.get("/words/all")
async def get_all_words(
    limit: Optional[int] = Query(1000, ge=1, le=10000, description="Maximum number of words to return")
):
    """Get all words (admin endpoint)"""
    try:
        return {
            "total_words": len(words_list),
            "returned_words": min(len(words_list), limit),
            "words": words_list[:limit]
        }
    except Exception as e:
        logger.error(f"Error getting all words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# STORAGE & CLOUD CONFIGURATION ENDPOINTS

@app.get("/storage/info")
async def get_storage_info():
    """Get information about the current storage configuration"""
    try:
        storage_info = await word_manager.get_storage_info()
        return {
            "success": True,
            "storage_info": storage_info
        }
    except Exception as e:
        logger.error(f"Error getting storage info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/storage/test")
async def test_storage_connection():
    """Test storage connection (admin endpoint)"""
    try:
        result = await word_manager.test_storage_connection()
        return {
            "success": True,
            "connection_test": result
        }
    except Exception as e:
        logger.error(f"Error testing storage connection: {e}")
        raise HTTPException(status_code=500, detail="Storage connection test failed")

@app.get("/cloud/info")
async def get_cloud_info():
    """Get information about the cloud provider"""
    storage_info = await word_manager.get_storage_info()
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

@app.post("/words/cleanup")
async def cleanup_invalid_words(request: CleanupReq):
    """Find and optionally remove invalid words from the collection"""
    global words_list, words_set, word_stats
    try:
        result = await word_manager.cleanup_invalid_words(auto_remove=request.auto_remove)
        words_list = word_manager.words_list
        words_set = word_manager.words_set
        
        lengths = [len(w) for w in words_list]
        word_stats["total_words"] = len(words_list)
        if lengths:
            word_stats["min_length"] = min(lengths)
            word_stats["max_length"] = max(lengths)
            word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)
            
        return {
            "success": True,
            "cleanup_summary": {
                "found_invalid": result["found_invalid"],
                "removed_count": result["removed_count"],
                "action_taken": result["action_taken"]
            },
            "invalid_words": result["invalid_words"],
            "total_words": len(words_list),
            "message": result["action_taken"]
        }
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/words/oxford-stats")
async def get_oxford_cache_statistics():
    """Get Oxford Dictionary API cache statistics"""
    try:
        stats = await word_manager.get_oxford_cache_stats()
        return {
            "success": True,
            "oxford_cache": stats,
            "message": "Oxford cache statistics retrieved"
        }
    except Exception as e:
        logger.error(f"Error getting Oxford stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
