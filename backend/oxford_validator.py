import requests
from bs4 import BeautifulSoup
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import time
import re

logger = logging.getLogger(__name__)

class OxfordValidator:
    """
    Word validator using Oxford Learner's Dictionary API
    Based on: https://github.com/NearHuscarl/oxford-dictionary-api
    """
    
    def __init__(self):
        self.base_url = "https://www.oxfordlearnersdictionaries.com/definition/english/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.executor = ThreadPoolExecutor(max_workers=3)  # Limit concurrent requests
        self.cache = {}  # Simple in-memory cache
        self.rate_limit_delay = 1  # 1 second between requests to be respectful
        self.last_request_time = 0
        
    async def validate_word(self, word: str) -> Dict:
        """
        Validate a single word using Oxford Dictionary
        
        Returns:
        {
            "word": "example",
            "is_valid": True,
            "definitions": ["definition1", "definition2"],
            "word_forms": ["noun", "verb"],
            "reason": "Found in Oxford Dictionary" or "Not found in Oxford Dictionary"
        }
        """
        word = word.strip().lower()
        
        if not word or not word.isalpha():
            return {
                "word": word,
                "is_valid": False,
                "definitions": [],
                "word_forms": [],
                "reason": "Invalid word format (must contain only letters)"
            }
        
        # Check cache first
        if word in self.cache:
            logger.info(f"Cache hit for word: {word}")
            return self.cache[word]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, self._fetch_word_sync, word)
            
            # Cache the result
            self.cache[word] = result
            return result
            
        except Exception as e:
            logger.error(f"Error validating word '{word}': {e}")
            return {
                "word": word,
                "is_valid": False,
                "definitions": [],
                "word_forms": [],
                "reason": f"Error during validation: {str(e)}"
            }
    
    def _fetch_word_sync(self, word: str) -> Dict:
        """Synchronous word fetching for use with ThreadPoolExecutor"""
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = time.time()
        
        url = f"{self.base_url}{word}"
        
        try:
            logger.info(f"Fetching word from Oxford: {word}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return self._parse_oxford_response(word, response.text)
            elif response.status_code == 404:
                return {
                    "word": word,
                    "is_valid": False,
                    "definitions": [],
                    "word_forms": [],
                    "reason": "Not found in Oxford Dictionary"
                }
            else:
                logger.warning(f"Unexpected status code {response.status_code} for word: {word}")
                return {
                    "word": word,
                    "is_valid": False,
                    "definitions": [],
                    "word_forms": [],
                    "reason": f"HTTP error: {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for word '{word}': {e}")
            return {
                "word": word,
                "is_valid": False,
                "definitions": [],
                "word_forms": [],
                "reason": f"Network error: {str(e)}"
            }
    
    def _parse_oxford_response(self, word: str, html_content: str) -> Dict:
        """Parse Oxford Dictionary HTML response"""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check if word exists (look for definition content)
            definitions_section = soup.find('div', {'class': 'entry'})
            
            if not definitions_section:
                return {
                    "word": word,
                    "is_valid": False,
                    "definitions": [],
                    "word_forms": [],
                    "reason": "No definition section found"
                }
            
            # Extract definitions
            definitions = []
            definition_elements = soup.find_all('span', {'class': 'def'})
            for def_elem in definition_elements[:5]:  # Limit to first 5 definitions
                definition_text = def_elem.get_text(strip=True)
                if definition_text:
                    definitions.append(definition_text)
            
            # Extract word forms (noun, verb, adjective, etc.)
            word_forms = []
            pos_elements = soup.find_all('span', {'class': 'pos'})
            for pos_elem in pos_elements:
                pos_text = pos_elem.get_text(strip=True)
                if pos_text and pos_text not in word_forms:
                    word_forms.append(pos_text)
            
            is_valid = len(definitions) > 0
            reason = f"Found in Oxford Dictionary with {len(definitions)} definition(s)" if is_valid else "No definitions found"
            
            return {
                "word": word,
                "is_valid": is_valid,
                "definitions": definitions,
                "word_forms": word_forms,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Error parsing HTML for word '{word}': {e}")
            return {
                "word": word,
                "is_valid": False,
                "definitions": [],
                "word_forms": [],
                "reason": f"HTML parsing error: {str(e)}"
            }
    
    async def validate_words_batch(self, words: List[str], max_concurrent: int = 3) -> Dict:
        """
        Validate multiple words with concurrency control
        
        Returns:
        {
            "total_words": 10,
            "valid_words": 7,
            "invalid_words": 3,
            "results": [{"word": "test", "is_valid": True, ...}, ...]
        }
        """
        if not words:
            return {
                "total_words": 0,
                "valid_words": 0,
                "invalid_words": 0,
                "results": []
            }
        
        logger.info(f"Validating {len(words)} words in batch")
        
        # Process words in chunks to avoid overwhelming the server
        chunk_size = min(max_concurrent, 5)
        results = []
        
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            
            # Process chunk concurrently
            tasks = [self.validate_word(word) for word in chunk]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            for j, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    logger.error(f"Exception validating word '{chunk[j]}': {result}")
                    results.append({
                        "word": chunk[j],
                        "is_valid": False,
                        "definitions": [],
                        "word_forms": [],
                        "reason": f"Exception: {str(result)}"
                    })
                else:
                    results.append(result)
            
            # Small delay between chunks
            if i + chunk_size < len(words):
                await asyncio.sleep(0.5)
        
        # Calculate summary
        valid_count = sum(1 for r in results if r["is_valid"])
        invalid_count = len(results) - valid_count
        
        return {
            "total_words": len(results),
            "valid_words": valid_count,
            "invalid_words": invalid_count,
            "results": results
        }
    
    async def get_inappropriate_words(self, words: List[str]) -> List[str]:
        """
        Filter out words that might be inappropriate for a word game
        Based on basic heuristics and word patterns
        """
        inappropriate = []
        
        # Simple heuristics for inappropriate words
        inappropriate_patterns = [
            r'^(.)\1{3,}',  # Words with 4+ repeated characters (aaaa, bbbb)
            r'^[a-z]$',     # Single letters
            r'^[a-z]{1,2}$', # Very short words (1-2 letters)
        ]
        
        # Common inappropriate or non-game words
        excluded_categories = {
            'profanity', 'slang', 'proper noun', 'abbreviation', 
            'interjection', 'exclamation'
        }
        
        for word in words:
            word = word.strip().lower()
            
            # Check patterns
            if any(re.match(pattern, word) for pattern in inappropriate_patterns):
                inappropriate.append(word)
                continue
            
            # Validate with Oxford to get word forms
            validation = await self.validate_word(word)
            
            if validation["is_valid"]:
                # Check if any word forms suggest inappropriateness
                word_forms = [form.lower() for form in validation["word_forms"]]
                if any(cat in ' '.join(word_forms) for cat in excluded_categories):
                    inappropriate.append(word)
        
        return inappropriate
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "cached_words": len(self.cache),
            "cache_hit_rate": "Not tracked",  # Could be enhanced
            "total_requests": "Not tracked"   # Could be enhanced
        }
