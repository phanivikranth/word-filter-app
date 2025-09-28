"""
API endpoint tests
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
import json


class TestBasicEndpoints:
    """Test basic API endpoints"""
    
    def test_root_endpoint(self, sync_client):
        """Test the root endpoint"""
        response = sync_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "total_words" in data
        assert data["message"] == "Word Filter API - Optimized"
        assert isinstance(data["total_words"], int)
        assert data["total_words"] > 0

    @pytest.mark.asyncio
    async def test_root_endpoint_async(self, async_client: AsyncClient):
        """Test the root endpoint asynchronously"""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "total_words" in data

    def test_word_stats_endpoint(self, sync_client):
        """Test word statistics endpoint"""
        response = sync_client.get("/words/stats")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["total_words", "min_length", "max_length", "avg_length"]
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], (int, float))
        
        assert data["total_words"] > 0
        assert data["min_length"] > 0
        assert data["max_length"] >= data["min_length"]
        assert data["avg_length"] > 0

    def test_performance_stats_endpoint(self, sync_client):
        """Test performance statistics endpoint"""
        response = sync_client.get("/performance/stats")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["words_loaded", "memory_usage", "thread_pool_workers", 
                          "process_pool_workers", "optimization_features"]
        for field in required_fields:
            assert field in data
        
        assert isinstance(data["optimization_features"], list)
        assert len(data["optimization_features"]) > 0


class TestWordFiltering:
    """Test word filtering endpoints"""
    
    def test_get_all_words_default_limit(self, sync_client):
        """Test getting words with default limit"""
        response = sync_client.get("/words")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        assert len(words) <= 100  # Default limit
        for word in words:
            assert isinstance(word, str)
            assert word.islower()

    def test_get_words_with_custom_limit(self, sync_client):
        """Test getting words with custom limit"""
        limit = 20
        response = sync_client.get(f"/words?limit={limit}")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        assert len(words) <= limit

    def test_filter_words_by_contains(self, sync_client):
        """Test filtering words by contains parameter"""
        response = sync_client.get("/words?contains=app&limit=50")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        for word in words:
            assert "app" in word

    def test_filter_words_by_starts_with(self, sync_client):
        """Test filtering words by starts_with parameter"""
        response = sync_client.get("/words?starts_with=cat&limit=50")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        for word in words:
            assert word.startswith("cat")

    def test_filter_words_by_ends_with(self, sync_client):
        """Test filtering words by ends_with parameter"""
        response = sync_client.get("/words?ends_with=ing&limit=50")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        for word in words:
            assert word.endswith("ing")

    def test_filter_words_by_length(self, sync_client):
        """Test filtering words by length parameters"""
        # Test exact length
        response = sync_client.get("/words?exact_length=5&limit=50")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        for word in words:
            assert len(word) == 5

    def test_filter_words_by_min_max_length(self, sync_client):
        """Test filtering words by min and max length"""
        min_len, max_len = 6, 10
        response = sync_client.get(f"/words?min_length={min_len}&max_length={max_len}&limit=50")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        for word in words:
            assert min_len <= len(word) <= max_len

    def test_complex_filter_combination(self, sync_client):
        """Test combining multiple filters"""
        response = sync_client.get(
            "/words?contains=a&starts_with=app&min_length=4&max_length=15&limit=20"
        )
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        for word in words:
            assert "a" in word
            assert word.startswith("app")
            assert 4 <= len(word) <= 15

    @pytest.mark.asyncio
    async def test_async_word_filtering(self, async_client: AsyncClient):
        """Test word filtering with async client"""
        response = await async_client.get("/words?contains=test&limit=10")
        assert response.status_code == 200
        words = response.json()
        assert isinstance(words, list)


class TestWordCheck:
    """Test word existence checking"""
    
    def test_check_existing_word(self, sync_client):
        """Test checking if a word exists"""
        response = sync_client.get("/words/check?word=apple")
        assert response.status_code == 200
        data = response.json()
        
        assert "word" in data
        assert "exists" in data
        assert data["word"] == "apple"
        assert isinstance(data["exists"], bool)

    def test_check_non_existing_word(self, sync_client):
        """Test checking if a non-existing word exists"""
        response = sync_client.get("/words/check?word=xyzzyx123")
        assert response.status_code == 200
        data = response.json()
        
        assert data["word"] == "xyzzyx123"
        assert data["exists"] == False

    def test_check_word_case_insensitive(self, sync_client):
        """Test that word checking is case insensitive"""
        response = sync_client.get("/words/check?word=APPLE")
        assert response.status_code == 200
        data = response.json()
        
        assert data["word"] == "apple"  # Should be converted to lowercase


class TestWordsByLength:
    """Test getting words by specific length"""
    
    def test_get_words_by_length(self, sync_client):
        """Test getting words by specific length"""
        length = 5
        response = sync_client.get(f"/words/by-length/{length}")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["length", "count", "words"]
        for field in required_fields:
            assert field in data
        
        assert data["length"] == length
        assert isinstance(data["count"], int)
        assert isinstance(data["words"], list)
        
        for word in data["words"]:
            assert len(word) == length

    def test_get_words_by_invalid_length(self, sync_client):
        """Test getting words by invalid length"""
        response = sync_client.get("/words/by-length/0")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["words"] == []


class TestInteractiveWords:
    """Test interactive word puzzle endpoint"""
    
    def test_interactive_words_basic_pattern(self, sync_client):
        """Test interactive words with basic pattern"""
        response = sync_client.get("/words/interactive?length=5&pattern=?????")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        for word in words:
            assert len(word) == 5

    def test_interactive_words_partial_pattern(self, sync_client):
        """Test interactive words with partial pattern"""
        response = sync_client.get("/words/interactive?length=5&pattern=a???e")
        assert response.status_code == 200
        words = response.json()
        
        assert isinstance(words, list)
        for word in words:
            assert len(word) == 5
            assert word[0] == 'a'
            assert word[4] == 'e'

    def test_interactive_words_invalid_length(self, sync_client):
        """Test interactive words with invalid length"""
        response = sync_client.get("/words/interactive?length=0&pattern=")
        assert response.status_code == 200
        words = response.json()
        assert words == []


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_query_parameters(self, sync_client):
        """Test handling of invalid query parameters"""
        response = sync_client.get("/words?limit=abc")
        assert response.status_code == 422  # Validation error

    def test_negative_length_parameters(self, sync_client):
        """Test handling of negative length parameters"""
        response = sync_client.get("/words?min_length=-1")
        assert response.status_code == 422  # Validation error

    def test_excessive_limit(self, sync_client):
        """Test handling of excessive limit"""
        response = sync_client.get("/words?limit=10000")
        assert response.status_code == 422  # Should exceed max limit

    def test_missing_required_parameters(self, sync_client):
        """Test handling of missing required parameters"""
        response = sync_client.get("/words/interactive")
        assert response.status_code == 422  # Missing required parameters


@pytest.mark.integration
class TestIntegrationWorkflow:
    """Test complete workflows and integration scenarios"""
    
    def test_complete_search_workflow(self, sync_client):
        """Test a complete search workflow"""
        # 1. Get word stats
        stats_response = sync_client.get("/words/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # 2. Search for words
        search_response = sync_client.get("/words?contains=app&limit=10")
        assert search_response.status_code == 200
        words = search_response.json()
        
        # 3. Check if first word exists
        if words:
            check_response = sync_client.get(f"/words/check?word={words[0]}")
            assert check_response.status_code == 200
            check_data = check_response.json()
            assert check_data["exists"] == True

    def test_puzzle_solving_workflow(self, sync_client):
        """Test interactive puzzle solving workflow"""
        # 1. Get words of specific length
        length = 5
        length_response = sync_client.get(f"/words/by-length/{length}")
        assert length_response.status_code == 200
        
        # 2. Use interactive search with pattern
        pattern_response = sync_client.get(f"/words/interactive?length={length}&pattern=?????")
        assert pattern_response.status_code == 200
        
        # Results should be consistent
        length_data = length_response.json()
        pattern_words = pattern_response.json()
        
        # Pattern search should return subset of length search
        assert len(pattern_words) <= length_data["count"]
