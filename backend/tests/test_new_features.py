import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from main import app, words_list

client = TestClient(app)

def test_random_word_endpoint():
    # Setup test words
    global words_list
    original_words = words_list.copy()
    try:
        words_list.clear()
        words_list.extend(["happy", "sad", "good", "great", "apple", "banana"])
        
        response = client.get("/words/random?length=5")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["word"]) == 5
        
        # constraints
        response = client.get("/words/random?length=5&starts_with=h")
        assert response.status_code == 200
        assert response.json()["word"] == "happy"
        
        response = client.get("/words/random?length=5&starts_with=x")
        assert response.status_code == 404
    finally:
        words_list.clear()
        words_list.extend(original_words)

def test_puzzle_solver_endpoint():
    global words_list
    original_words = words_list.copy()
    try:
        words_list.clear()
        words_list.extend(["happy", "sad", "good", "great", "apple", "banana"])
        
        # Test vowel matching: @
        # "g@@d" should match "good"
        response = client.get("/words/puzzle", params={"pattern": "g@@d"})
        assert response.status_code == 200
        assert "good" in response.json()
        assert "great" not in response.json()
        
        # Test consonant matching: #
        # "ha##y" should match "happy"
        response = client.get("/words/puzzle", params={"pattern": "ha##y"})
        assert response.status_code == 200
        assert "happy" in response.json()
        
        # Test regex matching
        # "^a.p..$" should match "apple"
        response = client.get("/words/puzzle", params={"regex": "^a.p..$"})
        assert response.status_code == 200
        assert "apple" in response.json()
        
        # Test anagram matching
        # letters "yaphp" should match "happy"
        response = client.get("/words/puzzle", params={"anagram": "yaphp", "anagram_exact": "true"})
        assert response.status_code == 200
        assert "happy" in response.json()
    finally:
        words_list.clear()
        words_list.extend(original_words)

def test_metrics_request_tracker():
    initial_metrics = client.get("/metrics").text
    # find request count in metrics text
    assert "word_filter_api_requests_total" in initial_metrics
