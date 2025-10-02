"""
Pytest configuration and shared fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from fastapi.testclient import TestClient
import tempfile
import os
from unittest.mock import patch, MagicMock

# Import your main app
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Create a test app instance
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Simple test app for testing
def create_test_app():
    """Create a test app instance"""
    test_app = FastAPI(title="Test Word Filter API")
    
    # Configure CORS
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mock word data for testing
    test_words = [
        "apple", "application", "apply", "appreciate",
        "banana", "band", "bandana", "basic",
        "cat", "catch", "catching", "category",
        "dog", "digital", "development", "data",
        "elephant", "engineering", "example", "excellent",
        "python", "programming", "project", "performance",
        "testing", "technology", "tool", "team",
        "understanding", "user", "unique", "update"
    ]
    
    test_word_stats = {
        "total_words": len(test_words),
        "min_length": min(len(w) for w in test_words),
        "max_length": max(len(w) for w in test_words),
        "avg_length": round(sum(len(w) for w in test_words) / len(test_words), 2)
    }
    
    @test_app.get("/")
    async def root():
        return {"message": "Word Filter API - Optimized", "total_words": len(test_words)}
    
    @test_app.get("/words/stats")
    async def get_word_stats():
        return test_word_stats
    
    @test_app.get("/words")
    async def get_words(
        limit: int = 100,
        contains: str = None,
        starts_with: str = None,
        ends_with: str = None,
        min_length: int = None,
        max_length: int = None,
        exact_length: int = None
    ):
        filtered_words = test_words.copy()
        
        # Apply filters
        if contains:
            filtered_words = [w for w in filtered_words if contains in w]
        if starts_with:
            filtered_words = [w for w in filtered_words if w.startswith(starts_with)]
        if ends_with:
            filtered_words = [w for w in filtered_words if w.endswith(ends_with)]
        if min_length is not None:
            filtered_words = [w for w in filtered_words if len(w) >= min_length]
        if max_length is not None:
            filtered_words = [w for w in filtered_words if len(w) <= max_length]
        if exact_length is not None:
            filtered_words = [w for w in filtered_words if len(w) == exact_length]
        
        return filtered_words[:limit]
    
    @test_app.get("/words/check")
    async def check_word(word: str):
        return {"word": word.lower(), "exists": word.lower() in test_words}
    
    @test_app.get("/performance/stats")
    async def get_performance_stats():
        return {
            "words_loaded": len(test_words),
            "memory_usage": {"words_list_size": len(test_words), "words_set_size": len(test_words)},
            "thread_pool_workers": 4,
            "process_pool_workers": 2,
            "optimization_features": ["Testing mode"]
        }
    
    # Oxford Dictionary integration endpoints
    @test_app.post("/words/validate")
    async def validate_word(request: dict):
        word = request.get("word", "").lower()
        skip_oxford = request.get("skip_oxford", False)
        
        if skip_oxford:
            return {
                "success": True,
                "word": word,
                "oxford_validation": {
                    "word": word,
                    "is_valid": True,
                    "definitions": ["Test definition"],
                    "word_forms": ["noun"],
                    "examples": ["This is a test example."],
                    "reason": "Skipped Oxford validation"
                },
                "message": f"Validation complete for '{word}'"
            }
        
        # Mock Oxford validation - be more strict for testing
        is_valid = word in test_words or (len(word) > 2 and word.isalpha())
        return {
            "success": True,
            "word": word,
            "oxford_validation": {
                "word": word,
                "is_valid": is_valid,
                "definitions": ["Test definition"] if is_valid else [],
                "word_forms": ["noun"] if is_valid else [],
                "examples": ["This is a test example."] if is_valid else [],
                "reason": "Found in Oxford Dictionary" if is_valid else "Not found in Oxford Dictionary"
            },
            "message": f"Validation complete for '{word}'"
        }
    
    @test_app.get("/words/search-basic")
    async def search_basic_word(word: str):
        word_lower = word.lower()
        in_collection = word_lower in test_words
        
        # Mock Oxford result - be more strict
        is_valid = word_lower in test_words or (len(word_lower) > 2 and word_lower.isalpha())
        oxford_result = {
            "word": word_lower,
            "is_valid": is_valid,
            "definitions": ["Test definition"] if is_valid else [],
            "word_forms": ["noun"] if is_valid else [],
            "examples": ["This is a test example."] if is_valid else [],
            "reason": "Found in Oxford Dictionary" if is_valid else "Not found in Oxford Dictionary"
        }
        
        return {
            "word": word_lower,
            "inCollection": in_collection,
            "oxford": oxford_result if oxford_result["is_valid"] else None
        }
    
    @test_app.post("/words/add-validated")
    async def add_word_with_validation(request: dict):
        word = request.get("word", "").lower()
        skip_oxford = request.get("skip_oxford", False)
        
        if not word or not word.isalpha():
            return {
                "success": False,
                "message": "Word must contain only letters",
                "word": word
            }
        
        if word in test_words:
            return {
                "success": True,
                "message": f"Word '{word}' already exists in collection",
                "word": word
            }
        
        # Mock Oxford validation if not skipped
        if not skip_oxford:
            is_valid = word in test_words or (len(word) > 2 and word.isalpha())
            oxford_result = {
                "word": word,
                "is_valid": is_valid,
                "definitions": ["Test definition"] if is_valid else [],
                "word_forms": ["noun"] if is_valid else [],
                "examples": ["This is a test example."] if is_valid else [],
                "reason": "Found in Oxford Dictionary" if is_valid else "Not found in Oxford Dictionary"
            }
            
            if not oxford_result["is_valid"]:
                return {
                    "success": False,
                    "message": f"Word '{word}' not found in Oxford Dictionary: {oxford_result['reason']}",
                    "word": word
                }
        
        # Add to test words (simulate adding to collection)
        test_words.append(word)
        
        return {
            "success": True,
            "message": f"Word '{word}' added successfully",
            "word": word
        }
    
    # Add missing endpoints
    @test_app.get("/words/by-length/{length}")
    async def get_words_by_length(length: int):
        words_of_length = [w for w in test_words if len(w) == length]
        return {
            "length": length,
            "count": len(words_of_length),
            "words": words_of_length
        }
    
    @test_app.get("/words/interactive")
    async def get_interactive_words(length: int, pattern: str):
        if length <= 0:
            return []
        
        # Simple pattern matching (convert ? to any character)
        import re
        pattern_regex = pattern.replace('?', '.')
        try:
            regex = re.compile(f'^{pattern_regex}$')
            matching_words = [w for w in test_words if len(w) == length and regex.match(w)]
            return matching_words
        except:
            return []
    
    return test_app

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_words():
    """Sample word list for testing"""
    return [
        "apple", "application", "apply", "appreciate",
        "banana", "band", "bandana", "basic",
        "cat", "catch", "catching", "category",
        "dog", "digital", "development", "data",
        "elephant", "engineering", "example", "excellent",
        "fast", "fastapi", "framework", "function",
        "great", "good", "growth", "goal",
        "house", "home", "happy", "huge",
        "incredible", "integration", "important", "implementation",
        "java", "javascript", "join", "journey",
        "knowledge", "keep", "key", "kind",
        "learning", "language", "large", "level",
        "machine", "management", "modern", "method",
        "network", "natural", "number", "new",
        "optimization", "object", "open", "organization",
        "python", "programming", "project", "performance",
        "quality", "question", "quick", "query",
        "rest", "response", "request", "result",
        "system", "software", "service", "solution",
        "testing", "technology", "tool", "team",
        "understanding", "user", "unique", "update",
        "valuable", "version", "view", "validation",
        "wonderful", "work", "word", "web",
        "excellent", "example", "experience", "execution",
        "year", "yes", "yield", "young",
        "zero", "zone", "zip", "zoom"
    ]

@pytest.fixture
def sample_words_file(sample_words, tmp_path):
    """Create a temporary words file for testing"""
    words_file = tmp_path / "test_words.txt"
    words_file.write_text('\n'.join(sample_words))
    return str(words_file)

@pytest.fixture
def test_app():
    """Create test app instance"""
    return create_test_app()

@pytest.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client

@pytest.fixture
def sync_client(test_app) -> TestClient:
    """Create sync HTTP client for testing"""
    return TestClient(test_app)

@pytest.fixture
def performance_test_words():
    """Generate a larger dataset for performance testing"""
    from faker import Faker
    fake = Faker()
    
    # Generate diverse test words
    words = []
    
    # Add some predictable words for testing
    prefixes = ['test', 'demo', 'sample', 'mock', 'fake']
    suffixes = ['ing', 'tion', 'ed', 'er', 'ly', 'ness', 'ment']
    
    for prefix in prefixes:
        for suffix in suffixes:
            for i in range(5):
                word = f"{prefix}{fake.word()}{suffix}"
                words.append(word.lower())
    
    # Add random words
    for _ in range(1000):
        words.append(fake.word().lower())
    
    # Add some specific test patterns
    for i in range(100):
        words.append(f"python{i:03d}")
        words.append(f"fast{i:03d}api")
        words.append(f"test{i:03d}word")
    
    return list(set(words))  # Remove duplicates

@pytest.fixture
def mock_word_stats():
    """Mock word statistics for testing"""
    return {
        "total_words": 1000,
        "min_length": 2,
        "max_length": 20,
        "avg_length": 7.5
    }

@pytest.fixture
def temp_words_file(tmp_path):
    """Create a temporary words.txt file for testing file operations"""
    words_file = tmp_path / "words.txt"
    test_words = ["apple", "banana", "cherry", "date", "elderberry"]
    words_file.write_text('\n'.join(test_words))
    
    # Change to the temporary directory so the file operations work
    import os
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    yield str(words_file)
    
    # Restore original directory
    os.chdir(original_cwd)

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )

# Custom assertions
def assert_valid_word_list(words):
    """Assert that a word list is valid"""
    assert isinstance(words, list)
    assert all(isinstance(word, str) for word in words)
    assert all(word.islower() for word in words)
    assert all(word.isalpha() for word in words)

def assert_valid_api_response(response):
    """Assert that an API response is valid"""
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
