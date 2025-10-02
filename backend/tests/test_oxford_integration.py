"""
Oxford Dictionary integration tests
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
import json
from unittest.mock import patch, MagicMock


class TestOxfordDictionaryIntegration:
    """Test Oxford Dictionary integration endpoints"""
    
    def test_validate_word_endpoint(self, sync_client):
        """Test word validation with Oxford Dictionary"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "fantastic",
                "is_valid": True,
                "definitions": ["extremely good; excellent"],
                "word_forms": ["adjective"],
                "examples": ["He's done a fantastic job."],
                "reason": "Found in Oxford Dictionary with 1 definition(s) and 1 example(s)"
            }
            
            response = sync_client.post(
                "/words/validate",
                json={"word": "fantastic", "skip_oxford": False}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] == True
            assert data["word"] == "fantastic"
            assert "oxford_validation" in data
            assert data["oxford_validation"]["is_valid"] == True
            assert len(data["oxford_validation"]["definitions"]) > 0
            assert len(data["oxford_validation"]["examples"]) > 0

    def test_validate_word_not_found(self, sync_client):
        """Test word validation when word is not found in Oxford Dictionary"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "xyzzyx123",
                "is_valid": False,
                "definitions": [],
                "word_forms": [],
                "examples": [],
                "reason": "Not found in Oxford Dictionary"
            }
            
            response = sync_client.post(
                "/words/validate",
                json={"word": "xyzzyx123", "skip_oxford": False}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] == True
            assert data["word"] == "xyzzyx123"
            assert data["oxford_validation"]["is_valid"] == False
            assert data["oxford_validation"]["reason"] == "Not found in Oxford Dictionary"

    def test_search_basic_word_endpoint(self, sync_client):
        """Test basic word search with Oxford Dictionary integration"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "beautiful",
                "is_valid": True,
                "definitions": ["having beauty; giving pleasure to the senses"],
                "word_forms": ["adjective"],
                "examples": ["a beautiful woman", "What a beautiful day!"],
                "reason": "Found in Oxford Dictionary with 1 definition(s) and 2 example(s)"
            }
            
            response = sync_client.get("/words/search-basic?word=beautiful")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["word"] == "beautiful"
            assert "inCollection" in data
            assert "oxford" in data
            assert data["oxford"]["is_valid"] == True
            assert len(data["oxford"]["definitions"]) > 0
            assert len(data["oxford"]["examples"]) > 0

    def test_search_basic_word_not_in_oxford(self, sync_client):
        """Test basic word search when word is not in Oxford Dictionary"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "testword123",
                "is_valid": False,
                "definitions": [],
                "word_forms": [],
                "examples": [],
                "reason": "Not found in Oxford Dictionary"
            }
            
            response = sync_client.get("/words/search-basic?word=testword123")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["word"] == "testword123"
            assert data["oxford"] is None  # Should be None when not valid

    def test_add_word_with_validation_success(self, sync_client, temp_words_file):
        """Test adding a word with Oxford Dictionary validation"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "amazing",
                "is_valid": True,
                "definitions": ["causing great surprise or wonder"],
                "word_forms": ["adjective"],
                "examples": ["The view was amazing."],
                "reason": "Found in Oxford Dictionary with 1 definition(s) and 1 example(s)"
            }
            
            response = sync_client.post(
                "/words/add-validated",
                json={"word": "amazing", "skip_oxford": False}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] == True
            assert data["word"] == "amazing"
            assert data["message"] == "Word 'amazing' added successfully"
            
            # Verify word was added to file
            with open("words.txt", "r") as f:
                words_content = f.read()
                assert "amazing" in words_content

    def test_add_word_with_validation_oxford_failure(self, sync_client):
        """Test adding a word when Oxford Dictionary validation fails"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "invalidword123",
                "is_valid": False,
                "definitions": [],
                "word_forms": [],
                "examples": [],
                "reason": "Not found in Oxford Dictionary"
            }
            
            response = sync_client.post(
                "/words/add-validated",
                json={"word": "invalidword123", "skip_oxford": False}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] == False
            assert data["word"] == "invalidword123"
            assert "not found in Oxford Dictionary" in data["message"]

    def test_add_word_skip_oxford_validation(self, sync_client, temp_words_file):
        """Test adding a word while skipping Oxford Dictionary validation"""
        response = sync_client.post(
            "/words/add-validated",
            json={"word": "skippedword", "skip_oxford": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["word"] == "skippedword"
        assert data["message"] == "Word 'skippedword' added successfully"
        
        # Verify word was added to file
        with open("words.txt", "r") as f:
            words_content = f.read()
            assert "skippedword" in words_content

    def test_add_word_already_exists(self, sync_client):
        """Test adding a word that already exists in collection"""
        response = sync_client.post(
            "/words/add-validated",
            json={"word": "apple", "skip_oxford": True}  # apple should exist in test data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["word"] == "apple"
        assert "already exists in collection" in data["message"]

    def test_add_word_invalid_format(self, sync_client):
        """Test adding a word with invalid format"""
        response = sync_client.post(
            "/words/add-validated",
            json={"word": "123invalid", "skip_oxford": True}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Word must contain only letters" in data["detail"]

    def test_add_word_empty_word(self, sync_client):
        """Test adding an empty word"""
        response = sync_client.post(
            "/words/add-validated",
            json={"word": "", "skip_oxford": True}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Word cannot be empty" in data["detail"]

    @pytest.mark.asyncio
    async def test_async_oxford_validation(self, async_client: AsyncClient):
        """Test Oxford Dictionary validation with async client"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "fantastic",
                "is_valid": True,
                "definitions": ["extremely good; excellent"],
                "word_forms": ["adjective"],
                "examples": ["He's done a fantastic job."],
                "reason": "Found in Oxford Dictionary"
            }
            
            response = await async_client.post(
                "/words/validate",
                json={"word": "fantastic", "skip_oxford": False}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["oxford_validation"]["is_valid"] == True

    def test_oxford_validation_error_handling(self, sync_client):
        """Test error handling in Oxford Dictionary validation"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.side_effect = Exception("Network error")
            
            response = sync_client.post(
                "/words/validate",
                json={"word": "testword", "skip_oxford": False}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["oxford_validation"]["is_valid"] == False
            assert "Error during validation" in data["oxford_validation"]["reason"]

    def test_file_writing_error_handling(self, sync_client):
        """Test error handling when file writing fails"""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with patch('main.oxford_validator.validate_word') as mock_validate:
                mock_validate.return_value = {
                    "word": "testword",
                    "is_valid": True,
                    "definitions": ["test definition"],
                    "word_forms": ["noun"],
                    "examples": ["This is a test."],
                    "reason": "Found in Oxford Dictionary"
                }
                
                response = sync_client.post(
                    "/words/add-validated",
                    json={"word": "testword", "skip_oxford": False}
                )
                
                # Should still succeed because word was added to memory
                assert response.status_code == 200
                data = response.json()
                assert data["success"] == True
                assert data["message"] == "Word 'testword' added successfully"


class TestOxfordValidatorIntegration:
    """Test Oxford Dictionary validator integration"""
    
    def test_oxford_validator_initialization(self, sync_client):
        """Test that Oxford validator is properly initialized"""
        # This test ensures the Oxford validator is available
        response = sync_client.get("/performance/stats")
        assert response.status_code == 200
        
        # The validator should be initialized in main.py
        # We can't directly test the validator object, but we can test its usage
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "test",
                "is_valid": True,
                "definitions": ["test definition"],
                "word_forms": ["noun"],
                "examples": ["This is a test."],
                "reason": "Found in Oxford Dictionary"
            }
            
            response = sync_client.post(
                "/words/validate",
                json={"word": "test", "skip_oxford": False}
            )
            
            assert response.status_code == 200
            mock_validate.assert_called_once_with("test")

    def test_oxford_cache_functionality(self, sync_client):
        """Test that Oxford Dictionary results are cached"""
        with patch('main.oxford_validator.validate_word') as mock_validate:
            mock_validate.return_value = {
                "word": "cachedword",
                "is_valid": True,
                "definitions": ["cached definition"],
                "word_forms": ["noun"],
                "examples": ["This is cached."],
                "reason": "Found in Oxford Dictionary"
            }
            
            # First call
            response1 = sync_client.post(
                "/words/validate",
                json={"word": "cachedword", "skip_oxford": False}
            )
            assert response1.status_code == 200
            
            # Second call should use cache
            response2 = sync_client.post(
                "/words/validate",
                json={"word": "cachedword", "skip_oxford": False}
            )
            assert response2.status_code == 200
            
            # Should only be called once due to caching
            assert mock_validate.call_count == 1
