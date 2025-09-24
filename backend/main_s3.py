from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import re
import logging
from word_manager import WordManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Word Filter API", 
    description="API for filtering words by letters and size with S3 integration",
    version="2.0.0"
)

# Configure CORS to allow Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global word manager instance
word_manager = WordManager()

# Pydantic models for request bodies
class AddWordRequest(BaseModel):
    word: str

class AddWordsRequest(BaseModel):
    words: List[str]

class WordSearchResponse(BaseModel):
    words: List[str]
    total_count: int
    search_time_ms: float

class ValidateWordRequest(BaseModel):
    word: str
    skip_oxford: bool = False

class RemoveWordRequest(BaseModel):
    word: str

class RemoveWordsRequest(BaseModel):
    words: List[str]

class CleanupRequest(BaseModel):
    auto_remove: bool = False
    batch_size: int = 20

@app.on_event("startup")
async def startup_event():
    """Load words on startup"""
    logger.info("Starting Word Filter API...")
    try:
        words = await word_manager.load_words_from_s3()
        logger.info(f"Successfully loaded {len(words)} words")
    except Exception as e:
        logger.error(f"Failed to load words during startup: {e}")

@app.get("/")
async def root():
    """Root endpoint with system info"""
    word_count = await word_manager.get_word_count()
    return {
        "message": "Word Filter API with S3 Integration", 
        "version": "2.0.0",
        "total_words": word_count,
        "features": ["word_filtering", "puzzle_solving", "dynamic_word_management"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes"""
    try:
        word_count = await word_manager.get_word_count()
        return {
            "status": "healthy",
            "word_count": word_count,
            "s3_connected": word_manager.s3_client is not None
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

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
    """Filter words based on various criteria"""
    try:
        words_list = await word_manager.get_words_list()
        filtered_words = words_list.copy()
        
        # Filter by contains letters
        if contains:
            contains_lower = contains.lower()
            filtered_words = [word for word in filtered_words if contains_lower in word]
        
        # Filter by starts with
        if starts_with:
            starts_with_lower = starts_with.lower()
            filtered_words = [word for word in filtered_words if word.startswith(starts_with_lower)]
        
        # Filter by ends with
        if ends_with:
            ends_with_lower = ends_with.lower()
            filtered_words = [word for word in filtered_words if word.endswith(ends_with_lower)]
        
        # Filter by exact length
        if exact_length:
            filtered_words = [word for word in filtered_words if len(word) == exact_length]
        else:
            # Filter by min/max length
            if min_length:
                filtered_words = [word for word in filtered_words if len(word) >= min_length]
            if max_length:
                filtered_words = [word for word in filtered_words if len(word) <= max_length]
        
        # Limit results
        filtered_words = filtered_words[:limit]
        
        return filtered_words
        
    except Exception as e:
        logger.error(f"Error in word filtering: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during word filtering")

@app.get("/words/stats")
async def get_word_stats():
    """Get statistics about the word collection"""
    try:
        words_list = await word_manager.get_words_list()
        
        if not words_list:
            return {"total_words": 0}
        
        lengths = [len(word) for word in words_list]
        return {
            "total_words": len(words_list),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "avg_length": round(sum(lengths) / len(lengths), 2),
            "unique_words": len(set(words_list)),
            "s3_connected": word_manager.s3_client is not None
        }
        
    except Exception as e:
        logger.error(f"Error getting word stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting statistics")

@app.get("/words/by-length/{length}")
async def get_words_by_exact_length(length: int):
    """Get all words of a specific length"""
    try:
        if length < 1 or length > 50:
            raise HTTPException(status_code=400, detail="Length must be between 1 and 50")
            
        words_list = await word_manager.get_words_list()
        filtered_words = [word for word in words_list if len(word) == length]
        
        return {
            "length": length,
            "count": len(filtered_words),
            "words": filtered_words
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting words by length: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/words/interactive", response_model=List[str])
async def get_interactive_words(
    length: int = Query(..., description="Exact word length"),
    pattern: str = Query(..., description="Pattern with known letters (use ? for unknown positions)")
):
    """Find words matching a pattern for interactive word puzzles"""
    try:
        if length < 1 or length > 50:
            return []
        
        words_list = await word_manager.get_words_list()
        
        # Filter words by exact length first
        length_filtered = [word for word in words_list if len(word) == length]
        
        # Convert pattern to regex-like matching
        matched_words = []
        for word in length_filtered:
            match = True
            for i, (pattern_char, word_char) in enumerate(zip(pattern, word)):
                # If pattern has a specific letter, word must match
                if pattern_char != '?' and pattern_char.lower() != word_char.lower():
                    match = False
                    break
            
            if match:
                matched_words.append(word)
        
        # Limit results for performance
        return matched_words[:500]
        
    except Exception as e:
        logger.error(f"Error in interactive word search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during pattern matching")

# New endpoints for word management

@app.post("/words/add")
async def add_single_word(request: AddWordRequest):
    """Add a single word to the collection"""
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        
        if not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        # Check if word already exists
        if await word_manager.word_exists(word):
            return {
                "success": True,
                "message": f"Word '{word}' already exists",
                "word": word.lower(),
                "was_new": False
            }
        
        success = await word_manager.add_word(word)
        
        if success:
            return {
                "success": True,
                "message": f"Word '{word}' added successfully",
                "word": word.lower(),
                "was_new": True,
                "total_words": await word_manager.get_word_count()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add word")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/add-batch")
async def add_multiple_words(request: AddWordsRequest):
    """Add multiple words to the collection"""
    try:
        if not request.words:
            raise HTTPException(status_code=400, detail="Words list cannot be empty")
        
        # Validate words
        invalid_words = [w for w in request.words if not w.strip() or not w.strip().isalpha()]
        if invalid_words:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid words (must contain only letters): {invalid_words[:5]}"
            )
        
        added_count, total_count = await word_manager.add_words(request.words)
        
        return {
            "success": True,
            "added_count": added_count,
            "total_submitted": total_count,
            "skipped_count": total_count - added_count,
            "total_words": await word_manager.get_word_count(),
            "message": f"Added {added_count} new words out of {total_count} submitted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding multiple words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/check")
async def check_word_exists(request: AddWordRequest):
    """Check if a word exists in the collection"""
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        
        exists = await word_manager.word_exists(word)
        
        return {
            "word": word.lower(),
            "exists": exists,
            "message": f"Word '{word}' {'exists' if exists else 'does not exist'} in collection"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/reload")
async def reload_words_from_s3():
    """Reload words from S3 (admin endpoint)"""
    try:
        words = await word_manager.reload_words()
        return {
            "success": True,
            "message": "Words reloaded from S3",
            "total_words": len(words)
        }
        
    except Exception as e:
        logger.error(f"Error reloading words: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload words from S3")

@app.get("/words/all")
async def get_all_words(
    limit: Optional[int] = Query(1000, ge=1, le=10000, description="Maximum number of words to return")
):
    """Get all words (admin endpoint) - use with caution for large datasets"""
    try:
        words_list = await word_manager.get_words_list()
        return {
            "total_words": len(words_list),
            "returned_words": min(len(words_list), limit),
            "words": words_list[:limit]
        }
        
    except Exception as e:
        logger.error(f"Error getting all words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Oxford Dictionary Validation Endpoints

@app.post("/words/validate")
async def validate_word(request: ValidateWordRequest):
    """Validate a word using Oxford Dictionary API"""
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        
        if not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        validation_result = await word_manager.validate_word_with_oxford(word)
        
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

@app.post("/words/add-validated")
async def add_word_with_oxford_validation(request: ValidateWordRequest):
    """Add a word with Oxford Dictionary validation"""
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        
        if not word.isalpha():
            raise HTTPException(status_code=400, detail="Word must contain only letters")
        
        result = await word_manager.add_word_with_validation(word, skip_oxford=request.skip_oxford)
        
        if result["success"]:
            return {
                **result,
                "total_words": await word_manager.get_word_count()
            }
        else:
            # Return 400 for validation failures, not 500
            status_code = 400 if result.get("oxford_validation") else 500
            raise HTTPException(status_code=status_code, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding validated word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/remove")
async def remove_single_word(request: RemoveWordRequest):
    """Remove a single word from the collection"""
    try:
        word = request.word.strip()
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        
        success = await word_manager.remove_word(word)
        
        if success:
            return {
                "success": True,
                "word": word.lower(),
                "message": f"Word '{word}' removed successfully",
                "total_words": await word_manager.get_word_count()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to remove word")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing word: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/remove-batch")
async def remove_multiple_words(request: RemoveWordsRequest):
    """Remove multiple words from the collection"""
    try:
        if not request.words:
            raise HTTPException(status_code=400, detail="Words list cannot be empty")
        
        removed_count, total_count = await word_manager.remove_words(request.words)
        
        return {
            "success": True,
            "removed_count": removed_count,
            "total_submitted": total_count,
            "not_found_count": total_count - removed_count,
            "total_words": await word_manager.get_word_count(),
            "message": f"Removed {removed_count} words out of {total_count} submitted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing multiple words: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/validate-collection")
async def validate_entire_collection():
    """Validate entire word collection against Oxford Dictionary (admin endpoint)"""
    try:
        result = await word_manager.validate_collection_with_oxford()
        
        return {
            "success": True,
            "validation_summary": {
                "total_words": result["total_words"],
                "valid_words": result["valid_words"],
                "invalid_words": result["invalid_words"],
                "validity_percentage": round((result["valid_words"] / result["total_words"]) * 100, 2) if result["total_words"] > 0 else 0
            },
            "invalid_words": result["invalid_word_list"],
            "message": f"Validation complete: {result['valid_words']}/{result['total_words']} words are valid"
        }
        
    except Exception as e:
        logger.error(f"Error validating collection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/words/cleanup")
async def cleanup_invalid_words(request: CleanupRequest):
    """Find and optionally remove invalid words from the collection"""
    try:
        result = await word_manager.cleanup_invalid_words(auto_remove=request.auto_remove)
        
        return {
            "success": True,
            "cleanup_summary": {
                "found_invalid": result["found_invalid"],
                "removed_count": result["removed_count"],
                "action_taken": result["action_taken"]
            },
            "invalid_words": result["invalid_words"],
            "total_words": await word_manager.get_word_count(),
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
