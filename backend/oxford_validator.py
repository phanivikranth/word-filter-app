import requests
from bs4 import BeautifulSoup
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
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
        self.executor = ThreadPoolExecutor(max_workers=30)
        self.cache = {}  # Simple in-memory cache
        self.cache_hits = 0
        self.cache_misses = 0
        
    def set_concurrency(self, max_concurrent: int) -> None:
        """Resize thread pool for parallel Oxford web lookups."""
        workers = max(1, min(max_concurrent, 50))
        if getattr(self.executor, "_max_workers", 0) != workers:
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.executor = ThreadPoolExecutor(max_workers=workers)
        
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
            return self._empty_word_result(
                word,
                reason="Invalid word format (must contain only letters)",
            )
        
        # Check cache first
        if word in self.cache:
            self.cache_hits += 1
            logger.info(f"Cache hit for word: {word}")
            return self.cache[word]
        
        self.cache_misses += 1
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, self._fetch_word_sync, word)
            
            # Cache the result
            self.cache[word] = result
            return result
            
        except Exception as e:
            logger.error(f"Error validating word '{word}': {e}")
            return self._empty_word_result(
                word,
                reason=f"Error during validation: {str(e)}",
            )
    
    def _pronunciation_label(self, geo: str) -> str:
        mapping = {"br": "BrE", "n_am": "NAmE", "us": "NAmE", "uk": "BrE"}
        return mapping.get(geo, geo.upper() if geo else "Standard")

    def _extract_pronunciations(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        pronunciations: List[Dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for block in soup.select("div.phons_br, div.phons_n_am, div[class*='phons_']"):
            phon = block.select_one("span.phon")
            if not phon:
                continue
            ipa = phon.get_text(strip=True).strip("/")
            if not ipa:
                continue

            audio_el = block.select_one("[data-src-mp3], a.icon-audio, div.sound")
            audio_url = ""
            if audio_el:
                audio_url = (
                    audio_el.get("data-src-mp3")
                    or audio_el.get("href")
                    or ""
                ).strip()
                if audio_url.startswith("//"):
                    audio_url = f"https:{audio_url}"

            geo = block.get("geo") or ""
            if not geo and block.get("class"):
                for cls in block.get("class", []):
                    if cls.startswith("phons_"):
                        geo = cls.replace("phons_", "")
                        break

            prefix = self._pronunciation_label(str(geo))
            key = (prefix, ipa)
            if key in seen:
                continue
            seen.add(key)
            pronunciations.append({"prefix": prefix, "ipa": ipa, "url": audio_url})

        return pronunciations[:4]

    def _extract_etymology(
        self, soup: BeautifulSoup
    ) -> tuple[str, str, str]:
        etymology = ""
        origin_language = ""
        first_known_use = ""

        for selector in (
            "span.etym",
            "div.etym",
            "span[class*='etym']",
            "div[class*='etym']",
            "p.etym",
        ):
            for elem in soup.select(selector):
                text = elem.get_text(" ", strip=True)
                if text and len(text) > 4:
                    etymology = text
                    break
            if etymology:
                break

        if not etymology:
            for elem in soup.find_all(string=re.compile(r"\borigin\b", re.I)):
                parent = elem.parent
                if parent:
                    text = parent.get_text(" ", strip=True)
                    if len(text) > 10:
                        etymology = text
                        break

        if etymology:
            from_match = re.search(
                r"(?:from|via)\s+([A-Za-zÀ-ÿ][\w\s-]{1,40})",
                etymology,
                flags=re.IGNORECASE,
            )
            if from_match:
                origin_language = from_match.group(1).strip().rstrip(".,;")

        date_match = re.search(
            r"(?:first recorded|first known use|since)\s+(\d{4}(?:\s*[-–]\s*\d{4})?)",
            etymology,
            flags=re.IGNORECASE,
        )
        if date_match:
            first_known_use = date_match.group(1).strip()

        return etymology, origin_language, first_known_use

    def _empty_word_result(self, word: str, **kwargs) -> Dict:
        base = {
            "word": word,
            "is_valid": False,
            "definitions": [],
            "word_forms": [],
            "examples": [],
            "synonyms": [],
            "pronunciations": [],
            "etymology": "",
            "origin_language": "",
            "first_known_use": "",
            "source_url": "",
        }
        base.update(kwargs)
        return base

    def _fetch_word_sync(self, word: str) -> Dict:
        """Synchronous word fetching for use with ThreadPoolExecutor"""
        url = f"{self.base_url}{word}"
        
        try:
            logger.info(f"Fetching word from Oxford: {word}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return self._parse_oxford_response(word, response.text)
            elif response.status_code == 404:
                return self._empty_word_result(
                    word,
                    reason="Not found in Oxford Dictionary",
                )
            else:
                logger.warning(f"Unexpected status code {response.status_code} for word: {word}")
                return self._empty_word_result(
                    word,
                    reason=f"HTTP error: {response.status_code}",
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for word '{word}': {e}")
            return self._empty_word_result(
                word,
                reason=f"Network error: {str(e)}",
            )
    
    def _parse_oxford_response(self, word: str, html_content: str) -> Dict:
        """Parse Oxford Dictionary HTML response"""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check if word exists (look for definition content)
            definitions_section = soup.find('div', {'class': 'entry'})
            
            if not definitions_section:
                return self._empty_word_result(
                    word,
                    reason="No definition section found",
                )

            pronunciations = self._extract_pronunciations(soup)
            etymology, origin_language, first_known_use = self._extract_etymology(soup)
            source_url = f"{self.base_url}{word}"
            
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
            
            # Extract synonyms from Oxford Dictionary
            synonyms = []
            synonym_selectors = [
                'span.syn',  # Synonym class
                'div.synonyms span',  # Synonyms in div
                'span[class*="syn"]',  # Any span with class containing 'syn'
                'div[class*="synonym"] span',  # Synonym divs
            ]
            
            for selector in synonym_selectors:
                synonym_elements = soup.select(selector)
                for syn_elem in synonym_elements[:10]:  # Limit to first 10 synonyms
                    synonym_text = syn_elem.get_text(strip=True)
                    if synonym_text and len(synonym_text) > 1 and synonym_text.lower() != word.lower() and synonym_text not in synonyms:
                        # Clean up the synonym text
                        synonym_text = synonym_text.replace('•', '').strip()
                        if synonym_text and synonym_text.isalpha():
                            synonyms.append(synonym_text)
            
            # Extract examples from Oxford Dictionary
            examples = []
            
            # Look for example sentences in various possible selectors
            example_selectors = [
                'span.x',  # Oxford Learner's Dictionary example class
                'span.x-g',  # Another possible example class
                'div.x',  # Example div
                'span[class*="x"]',  # Any span with class containing 'x'
                'div[class*="example"]',  # Any div with class containing 'example'
                'span[class*="example"]',  # Any span with class containing 'example'
                'li.x',  # Example in list item
                'p.x'  # Example in paragraph
            ]
            
            for selector in example_selectors:
                example_elements = soup.select(selector)
                for example_elem in example_elements[:3]:  # Limit to first 3 examples per selector
                    example_text = example_elem.get_text(strip=True)
                    if example_text and len(example_text) > 10 and example_text not in examples:
                        # Clean up the example text
                        example_text = example_text.replace('•', '').strip()
                        if example_text:
                            examples.append(example_text)
            
            # If no examples found with specific selectors, try a broader search
            if not examples:
                # Look for any text that might be examples (contains the word and is in quotes or italics)
                all_text_elements = soup.find_all(['span', 'div', 'p', 'li'])
                for elem in all_text_elements:
                    text = elem.get_text(strip=True)
                    if (text and len(text) > 15 and len(text) < 200 and 
                        word.lower() in text.lower() and 
                        ('"' in text or "'" in text or text.endswith('.')) and
                        text not in examples):
                        examples.append(text)
            
            # Limit total examples to 5
            examples = examples[:5]
            
            # Limit total synonyms to 10
            synonyms = synonyms[:10]
            
            is_valid = len(definitions) > 0
            reason = f"Found in Oxford Dictionary with {len(definitions)} definition(s)"
            if examples:
                reason += f" and {len(examples)} example(s)"
            if synonyms:
                reason += f" and {len(synonyms)} synonym(s)"
            if pronunciations:
                reason += f" and {len(pronunciations)} pronunciation(s)"
            
            return {
                "word": word,
                "is_valid": is_valid,
                "definitions": definitions,
                "word_forms": word_forms,
                "examples": examples,
                "synonyms": synonyms,
                "pronunciations": pronunciations,
                "etymology": etymology,
                "origin_language": origin_language,
                "first_known_use": first_known_use,
                "source_url": source_url,
                "oxford_url": source_url,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Error parsing HTML for word '{word}': {e}")
            return self._empty_word_result(
                word,
                reason=f"HTML parsing error: {str(e)}",
            )
    
    async def validate_words_batch(self, words: List[str], max_concurrent: int = 20) -> Dict:
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

        logger.info("Validating %s words (up to %s in parallel)", len(words), max_concurrent)
        semaphore = asyncio.Semaphore(max(1, max_concurrent))

        async def _validate_one(item: str) -> Dict:
            async with semaphore:
                return await self.validate_word(item)

        chunk_results = await asyncio.gather(
            *[_validate_one(word) for word in words],
            return_exceptions=True,
        )

        results: List[Dict] = []
        for index, result in enumerate(chunk_results):
            if isinstance(result, Exception):
                word = words[index]
                logger.error("Exception validating word '%s': %s", word, result)
                results.append({
                    "word": word,
                    "is_valid": False,
                    "definitions": [],
                    "word_forms": [],
                    "examples": [],
                    "synonyms": [],
                    "reason": f"Exception: {str(result)}"
                })
            else:
                results.append(result)
        
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
        total = self.cache_hits + self.cache_misses
        rate = f"{(self.cache_hits / total * 100):.1f}%" if total > 0 else "0.0%"
        return {
            "cached_words": len(self.cache),
            "cached_words_count": len(self.cache),
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "cache_hit_rate": rate,
            "total_requests": total
        }
