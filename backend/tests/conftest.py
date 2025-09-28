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
        "python", "programming", "project", "performance"
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
    async def get_words(limit: int = 100):
        return test_words[:limit]
    
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
