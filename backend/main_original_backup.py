from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import re

app = FastAPI(title="Word Filter API", description="API for filtering words by letters and size")

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

def load_words():
    """Load words from words.txt file"""
    global words_list
    try:
        with open("words.txt", "r", encoding="utf-8") as file:
            words_list = [word.strip().lower() for word in file.readlines() if word.strip()]
        print(f"Loaded {len(words_list)} words from words.txt")
    except FileNotFoundError:
        print("words.txt not found. Using sample words.")
        words_list = [
            "apple", "banana", "cherry", "date", "elderberry",
            "fig", "grape", "honeydew", "kiwi", "lemon",
            "mango", "nectarine", "orange", "papaya", "quince",
            "raspberry", "strawberry", "tangerine", "ugli", "vanilla"
        ]

@app.on_event("startup")
async def startup_event():
    """Load words on startup"""
    load_words()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Word Filter API", "total_words": len(words_list)}

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

@app.get("/words/stats")
async def get_word_stats():
    """Get statistics about the word collection"""
    if not words_list:
        return {"total_words": 0}
    
    lengths = [len(word) for word in words_list]
    return {
        "total_words": len(words_list),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "avg_length": round(sum(lengths) / len(lengths), 2)
    }

@app.get("/words/by-length/{length}")
async def get_words_by_exact_length(length: int):
    """Get all words of a specific length"""
    filtered_words = [word for word in words_list if len(word) == length]
    return {
        "length": length,
        "count": len(filtered_words),
        "words": filtered_words
    }

@app.get("/words/interactive", response_model=List[str])
async def get_interactive_words(
    length: int = Query(..., description="Exact word length"),
    pattern: str = Query(..., description="Pattern with known letters (use ? for unknown positions)")
):
    """Find words matching a pattern for interactive word puzzles"""
    if length < 1 or length > 50:
        return []
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
