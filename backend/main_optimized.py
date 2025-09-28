from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import functools
import time
from pathlib import Path

app = FastAPI(title="Word Filter API - Optimized", description="API for filtering words by letters and size with concurrent processing")

# Configure CORS to allow Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:4201"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store words
words_list = []
words_set = set()  # For faster lookups
word_stats = {}

# Thread pool for IO operations
thread_pool = ThreadPoolExecutor(max_workers=4)
process_pool = ProcessPoolExecutor(max_workers=2)

async def load_words_concurrent():
    """Load words from words.txt file using concurrent processing"""
    global words_list, words_set, word_stats
    
    def read_and_process_file(filename: str):
        """Read and process words file in a separate thread"""
        try:
            start_time = time.time()
            print(f"[LOADING] Reading words from {filename}...")
            
            with open(filename, "r", encoding="utf-8") as file:
                # Read in chunks for better memory usage
                chunk_size = 10000
                words = []
                
                while True:
                    lines = file.readlines(chunk_size)
                    if not lines:
                        break
                    
                    chunk_words = [word.strip().lower() for word in lines if word.strip()]
                    words.extend(chunk_words)
            
            # Calculate statistics
            lengths = [len(word) for word in words]
            stats = {
                "total_words": len(words),
                "min_length": min(lengths) if lengths else 0,
                "max_length": max(lengths) if lengths else 0,
                "avg_length": round(sum(lengths) / len(lengths), 2) if lengths else 0
            }
            
            load_time = time.time() - start_time
            print(f"[SUCCESS] Loaded {len(words):,} words in {load_time:.2f}s")
            
            return words, set(words), stats
            
        except FileNotFoundError:
            print("[WARNING] words.txt not found. Using sample words.")
            sample_words = [
                "apple", "banana", "cherry", "date", "elderberry",
                "fig", "grape", "honeydew", "kiwi", "lemon",
                "mango", "nectarine", "orange", "papaya", "quince",
                "raspberry", "strawberry", "tangerine", "ugli", "vanilla"
            ]
            stats = {
                "total_words": len(sample_words),
                "min_length": min(len(w) for w in sample_words),
                "max_length": max(len(w) for w in sample_words),
                "avg_length": round(sum(len(w) for w in sample_words) / len(sample_words), 2)
            }
            return sample_words, set(sample_words), stats
    
    # Run file loading in thread pool
    loop = asyncio.get_event_loop()
    words_list, words_set, word_stats = await loop.run_in_executor(
        thread_pool, read_and_process_file, "words.txt"
    )

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
        # Apply filters
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
    
    # For small datasets or simple filters, use single thread
    if len(words_list) < 10000 or not any(filters.values()):
        return filter_words_simple(filters, limit)
    
    # Split words into chunks for parallel processing
    chunk_size = max(1000, len(words_list) // 4)  # 4 chunks
    chunks = []
    
    for i in range(0, len(words_list), chunk_size):
        chunk = words_list[i:i + chunk_size]
        chunks.append((chunk, filters))
    
    # Process chunks in parallel
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(process_pool, filter_words_chunk, chunk_data)
        for chunk_data in chunks
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Combine results
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
            
        # Apply filters
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
    await load_words_concurrent()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup thread pools on shutdown"""
    thread_pool.shutdown(wait=True)
    process_pool.shutdown(wait=True)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Word Filter API - Optimized", "total_words": len(words_list)}

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
    
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    # Use concurrent filtering for better performance
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
        """Match pattern in a chunk of words"""
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
    
    # Filter by length first for efficiency
    length_filtered = [word for word in words_list if len(word) == length]
    
    if len(length_filtered) < 1000:
        # Use simple processing for small datasets
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
    
    # Use concurrent processing for large datasets
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
    
    # Combine results
    matched_words = []
    for result in results:
        matched_words.extend(result)
    
    return matched_words[:500]

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
