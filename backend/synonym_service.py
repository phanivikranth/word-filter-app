"""
Synonym Service - Integrates multiple thesaurus APIs
Supports: DataMuse API, Merriam-Webster Thesaurus API, Oxford Dictionary
"""

import requests
import asyncio
import aiohttp
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SynonymService:
    """Service to fetch synonyms from multiple sources"""
    
    def __init__(self, merriam_webster_key: Optional[str] = None):
        """
        Initialize synonym service
        
        Args:
            merriam_webster_key: Optional API key for Merriam-Webster Thesaurus
                                Get free key at: https://dictionaryapi.com/register/index
        """
        self.merriam_webster_key = merriam_webster_key
        self.datamuse_url = "https://api.datamuse.com/words"
        self.merriam_webster_url = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json"
        self.cache = {}
        
    async def get_synonyms_datamuse(self, word: str, max_results: int = 10) -> List[str]:
        """
        Get synonyms from DataMuse API (free, no key required)
        
        Args:
            word: Word to find synonyms for
            max_results: Maximum number of synonyms to return
            
        Returns:
            List of synonyms
        """
        try:
            params = {
                'rel_syn': word,  # Words with similar meaning
                'max': max_results * 2  # Get more to filter
            }
            
            print(f"[DEBUG] Fetching synonyms from DataMuse for '{word}'...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.datamuse_url, params=params, timeout=5) as response:
                    print(f"[DEBUG] DataMuse response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"[DEBUG] DataMuse raw data: {data[:3] if len(data) > 3 else data}")
                        synonyms = [item['word'] for item in data if 'word' in item]
                        
                        # Filter to only single words (no phrases)
                        synonyms = [s for s in synonyms if ' ' not in s and s.isalpha()]
                        
                        print(f"[DEBUG] DataMuse filtered synonyms: {synonyms[:5]}")
                        logger.info(f"DataMuse API returned {len(synonyms)} synonyms for '{word}'")
                        return synonyms[:max_results]
                    else:
                        logger.warning(f"DataMuse API returned status {response.status}")
                        return []
                        
        except Exception as e:
            print(f"[DEBUG] DataMuse error: {str(e)}")
            logger.error(f"Error fetching synonyms from DataMuse: {str(e)}")
            return []
    
    async def get_synonyms_merriam_webster(self, word: str, max_results: int = 10) -> List[str]:
        """
        Get synonyms from Merriam-Webster Thesaurus API
        
        Args:
            word: Word to find synonyms for
            max_results: Maximum number of synonyms to return
            
        Returns:
            List of synonyms
        """
        if not self.merriam_webster_key:
            logger.debug("Merriam-Webster API key not provided, skipping")
            return []
        
        try:
            url = f"{self.merriam_webster_url}/{word}"
            params = {'key': self.merriam_webster_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        synonyms = []
                        
                        # Parse Merriam-Webster response
                        if isinstance(data, list) and len(data) > 0:
                            for entry in data:
                                if isinstance(entry, dict) and 'meta' in entry:
                                    # Get synonyms from meta.syns
                                    if 'syns' in entry['meta']:
                                        for syn_list in entry['meta']['syns']:
                                            synonyms.extend(syn_list)
                        
                        # Remove duplicates and filter
                        synonyms = list(set(synonyms))
                        synonyms = [s for s in synonyms if s.isalpha() and s.lower() != word.lower()]
                        
                        logger.info(f"Merriam-Webster API returned {len(synonyms)} synonyms for '{word}'")
                        return synonyms[:max_results]
                    else:
                        logger.warning(f"Merriam-Webster API returned status {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching synonyms from Merriam-Webster: {str(e)}")
            return []
    
    def get_synonyms_oxford(self, oxford_data: Dict) -> List[str]:
        """
        Extract synonyms from Oxford Dictionary data (already scraped)
        
        Args:
            oxford_data: Dictionary containing Oxford validation data
            
        Returns:
            List of synonyms
        """
        try:
            if oxford_data and 'synonyms' in oxford_data:
                synonyms = oxford_data['synonyms']
                if synonyms:
                    logger.info(f"Oxford returned {len(synonyms)} synonyms")
                    return synonyms
            return []
        except Exception as e:
            logger.error(f"Error extracting Oxford synonyms: {str(e)}")
            return []
    
    async def get_synonyms_combined(
        self, 
        word: str, 
        oxford_data: Optional[Dict] = None,
        max_results: int = 15,
        *,
        use_merriam: bool = True,
    ) -> Dict[str, any]:
        """
        Get synonyms from all available sources and combine them
        
        Args:
            word: Word to find synonyms for
            oxford_data: Optional Oxford Dictionary data
            max_results: Maximum number of synonyms to return
            
        Returns:
            Dictionary with synonyms and source information
        """
        print(f"\n[DEBUG] ===== get_synonyms_combined called for '{word}' =====")
        
        # Check cache
        cache_key = word.lower()
        if cache_key in self.cache:
            print(f"[DEBUG] Cache hit for '{word}'")
            logger.info(f"Cache hit for synonyms: {word}")
            return self.cache[cache_key]
        
        print(f"[DEBUG] Fetching from all sources...")
        
        # Fetch from available sources (DataMuse is free; Merriam-Webster uses daily quota)
        tasks = [self.get_synonyms_datamuse(word, max_results)]
        if use_merriam and self.merriam_webster_key:
            tasks.append(self.get_synonyms_merriam_webster(word, max_results))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"[DEBUG] Results received: {len(results)} sources")
        print(f"[DEBUG] Result 0 (DataMuse): {results[0] if not isinstance(results[0], Exception) else f'Exception: {results[0]}'}")
        if len(results) > 1:
            print(f"[DEBUG] Result 1 (Merriam): {results[1] if not isinstance(results[1], Exception) else f'Exception: {results[1]}'}")
        
        datamuse_synonyms = results[0] if not isinstance(results[0], Exception) else []
        merriam_synonyms = (
            results[1] if len(results) > 1 and not isinstance(results[1], Exception) else []
        )
        oxford_synonyms = self.get_synonyms_oxford(oxford_data) if oxford_data else []
        
        print(f"[DEBUG] DataMuse: {len(datamuse_synonyms)} synonyms")
        print(f"[DEBUG] Merriam: {len(merriam_synonyms)} synonyms")
        print(f"[DEBUG] Oxford: {len(oxford_synonyms)} synonyms")
        
        # Combine and deduplicate
        all_synonyms = []
        seen = set()
        
        # Prioritize: DataMuse > Merriam-Webster > Oxford
        for synonym_list in [datamuse_synonyms, merriam_synonyms, oxford_synonyms]:
            for syn in synonym_list:
                syn_lower = syn.lower()
                if syn_lower not in seen and syn_lower != word.lower():
                    all_synonyms.append(syn)
                    seen.add(syn_lower)
                    
                    if len(all_synonyms) >= max_results:
                        break
            
            if len(all_synonyms) >= max_results:
                break
        
        result = {
            'word': word,
            'synonyms': all_synonyms[:max_results],
            'count': len(all_synonyms[:max_results]),
            'sources': {
                'datamuse': len(datamuse_synonyms),
                'merriam_webster': len(merriam_synonyms),
                'oxford': len(oxford_synonyms)
            }
        }
        
        # Cache the result
        self.cache[cache_key] = result
        
        logger.info(f"Combined synonyms for '{word}': {result['count']} total "
                   f"(DataMuse: {result['sources']['datamuse']}, "
                   f"Merriam-Webster: {result['sources']['merriam_webster']}, "
                   f"Oxford: {result['sources']['oxford']})")
        
        return result
    
    def get_synonyms_sync(
        self, 
        word: str, 
        oxford_data: Optional[Dict] = None,
        max_results: int = 15
    ) -> Dict[str, any]:
        """
        Synchronous wrapper for get_synonyms_combined
        
        Args:
            word: Word to find synonyms for
            oxford_data: Optional Oxford Dictionary data
            max_results: Maximum number of synonyms to return
            
        Returns:
            Dictionary with synonyms and source information
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.get_synonyms_combined(word, oxford_data, max_results)
        )


# Global instance
_synonym_service = None


def get_synonym_service(merriam_webster_key: Optional[str] = None) -> SynonymService:
    """Get or create global synonym service instance"""
    global _synonym_service
    if _synonym_service is None:
        _synonym_service = SynonymService(merriam_webster_key)
    return _synonym_service
