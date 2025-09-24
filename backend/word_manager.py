import boto3
import os
import logging
from typing import List, Set, Dict, Tuple
from botocore.exceptions import ClientError, NoCredentialsError
import asyncio
from concurrent.futures import ThreadPoolExecutor
from oxford_validator import OxfordValidator

logger = logging.getLogger(__name__)

class WordManager:
    def __init__(self):
        self.s3_client = None
        self.bucket_name = os.getenv('WORDS_S3_BUCKET', 'word-filter-storage')
        self.words_key = os.getenv('WORDS_S3_KEY', 'words/words.txt')
        self.words_set: Set[str] = set()
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Initialize Oxford validator
        self.oxford_validator = OxfordValidator()
        logger.info("Oxford validator initialized")
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION', 'us-west-2')
            )
            logger.info("S3 client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize S3 client: {e}")
            self.s3_client = None

    async def load_words_from_s3(self) -> List[str]:
        """Load words from S3 bucket"""
        if not self.s3_client:
            return await self._load_local_fallback()
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.s3_client.get_object(Bucket=self.bucket_name, Key=self.words_key)
            )
            
            content = response['Body'].read().decode('utf-8')
            words = [word.strip().lower() for word in content.splitlines() if word.strip()]
            self.words_set = set(words)
            
            logger.info(f"Loaded {len(words)} words from S3: {self.bucket_name}/{self.words_key}")
            return words
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.warning(f"Bucket {self.bucket_name} does not exist. Creating...")
                await self._create_bucket_and_initial_file()
                return await self.load_words_from_s3()  # Retry
            elif error_code == 'NoSuchKey':
                logger.warning(f"Words file not found in S3. Creating initial file...")
                await self._create_initial_words_file()
                return await self.load_words_from_s3()  # Retry
            else:
                logger.error(f"Failed to load words from S3: {e}")
                return await self._load_local_fallback()
        except Exception as e:
            logger.error(f"Unexpected error loading from S3: {e}")
            return await self._load_local_fallback()

    async def _load_local_fallback(self) -> List[str]:
        """Fallback to local file or default words"""
        try:
            with open("words.txt", "r", encoding="utf-8") as file:
                words = [word.strip().lower() for word in file.readlines() if word.strip()]
                self.words_set = set(words)
                logger.info(f"Loaded {len(words)} words from local file")
                return words
        except FileNotFoundError:
            logger.warning("No local words.txt found. Using default words.")
            default_words = [
                "apple", "banana", "cherry", "date", "elderberry",
                "fig", "grape", "honeydew", "kiwi", "lemon",
                "mango", "nectarine", "orange", "papaya", "quince",
                "raspberry", "strawberry", "tangerine", "ugli", "vanilla",
                "word", "filter", "puzzle", "search", "game"
            ]
            self.words_set = set(default_words)
            # Try to save default words to S3
            await self._save_words_to_s3(default_words)
            return default_words

    async def _create_bucket_and_initial_file(self):
        """Create S3 bucket and initial words file"""
        if not self.s3_client:
            return
        
        try:
            loop = asyncio.get_event_loop()
            
            # Create bucket
            await loop.run_in_executor(
                self.executor,
                lambda: self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': os.getenv('AWS_REGION', 'us-west-2')}
                )
            )
            logger.info(f"Created S3 bucket: {self.bucket_name}")
            
            # Create initial words file
            await self._create_initial_words_file()
            
        except Exception as e:
            logger.error(f"Failed to create S3 bucket: {e}")

    async def _create_initial_words_file(self):
        """Create initial words file in S3"""
        default_words = await self._load_local_fallback()
        await self._save_words_to_s3(default_words)

    async def add_word(self, word: str) -> bool:
        """Add a new word to the collection"""
        word = word.strip().lower()
        
        if not word or not word.isalpha():
            return False
        
        if word in self.words_set:
            logger.info(f"Word '{word}' already exists")
            return True  # Already exists, consider it success
        
        # Add to local set
        self.words_set.add(word)
        
        # Save to S3
        words_list = sorted(list(self.words_set))
        success = await self._save_words_to_s3(words_list)
        
        if success:
            logger.info(f"Added new word: {word}")
            return True
        else:
            # Rollback local change if S3 save failed
            self.words_set.discard(word)
            return False

    async def add_words(self, words: List[str]) -> tuple[int, int]:
        """Add multiple words. Returns (added_count, total_count)"""
        added_count = 0
        original_size = len(self.words_set)
        
        for word in words:
            word = word.strip().lower()
            if word and word.isalpha() and word not in self.words_set:
                self.words_set.add(word)
                added_count += 1
        
        if added_count > 0:
            words_list = sorted(list(self.words_set))
            success = await self._save_words_to_s3(words_list)
            
            if not success:
                # Rollback changes
                self.words_set = {word for word in self.words_set if len(self.words_set) <= original_size + added_count}
                added_count = 0
            else:
                logger.info(f"Added {added_count} new words")
        
        return added_count, len(words)

    async def _save_words_to_s3(self, words: List[str]) -> bool:
        """Save words list to S3"""
        if not self.s3_client:
            logger.warning("No S3 client available, skipping save")
            return False
        
        try:
            content = '\n'.join(sorted(words))
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                self.executor,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=self.words_key,
                    Body=content.encode('utf-8'),
                    ContentType='text/plain',
                    Metadata={
                        'word_count': str(len(words)),
                        'last_updated': str(int(asyncio.get_event_loop().time()))
                    }
                )
            )
            
            logger.info(f"Saved {len(words)} words to S3")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save words to S3: {e}")
            return False

    async def get_words_list(self) -> List[str]:
        """Get current words list"""
        return sorted(list(self.words_set))

    async def word_exists(self, word: str) -> bool:
        """Check if word exists in collection"""
        return word.strip().lower() in self.words_set

    async def get_word_count(self) -> int:
        """Get total word count"""
        return len(self.words_set)

    async def reload_words(self) -> List[str]:
        """Reload words from S3"""
        return await self.load_words_from_s3()
    
    # Oxford Dictionary Integration Methods
    
    async def validate_word_with_oxford(self, word: str) -> Dict:
        """Validate a word using Oxford Dictionary API"""
        return await self.oxford_validator.validate_word(word)
    
    async def add_word_with_validation(self, word: str, skip_oxford: bool = False) -> Dict:
        """
        Add a word with Oxford Dictionary validation
        
        Returns:
        {
            "success": bool,
            "word": str,
            "was_new": bool,
            "oxford_validation": {...},
            "message": str
        }
        """
        word = word.strip().lower()
        
        if not word or not word.isalpha():
            return {
                "success": False,
                "word": word,
                "was_new": False,
                "oxford_validation": None,
                "message": "Invalid word format (must contain only letters)"
            }
        
        # Check if word already exists
        if word in self.words_set:
            return {
                "success": True,
                "word": word,
                "was_new": False,
                "oxford_validation": None,
                "message": f"Word '{word}' already exists in collection"
            }
        
        # Validate with Oxford Dictionary if requested
        oxford_result = None
        if not skip_oxford:
            oxford_result = await self.oxford_validator.validate_word(word)
            if not oxford_result["is_valid"]:
                return {
                    "success": False,
                    "word": word,
                    "was_new": False,
                    "oxford_validation": oxford_result,
                    "message": f"Word '{word}' not found in Oxford Dictionary: {oxford_result['reason']}"
                }
        
        # Add to collection
        success = await self.add_word(word)
        
        return {
            "success": success,
            "word": word,
            "was_new": success,
            "oxford_validation": oxford_result,
            "message": f"Word '{word}' added successfully" if success else f"Failed to add word '{word}'"
        }
    
    async def remove_word(self, word: str) -> bool:
        """Remove a word from the collection"""
        word = word.strip().lower()
        
        if word not in self.words_set:
            logger.info(f"Word '{word}' not found in collection")
            return True  # Consider it success if word doesn't exist
        
        # Remove from local set
        self.words_set.discard(word)
        
        # Save to S3
        words_list = sorted(list(self.words_set))
        success = await self._save_words_to_s3(words_list)
        
        if success:
            logger.info(f"Removed word: {word}")
            return True
        else:
            # Rollback local change if S3 save failed
            self.words_set.add(word)
            return False
    
    async def remove_words(self, words: List[str]) -> Tuple[int, int]:
        """Remove multiple words. Returns (removed_count, total_count)"""
        removed_count = 0
        original_words = self.words_set.copy()
        
        for word in words:
            word = word.strip().lower()
            if word in self.words_set:
                self.words_set.discard(word)
                removed_count += 1
        
        if removed_count > 0:
            words_list = sorted(list(self.words_set))
            success = await self._save_words_to_s3(words_list)
            
            if not success:
                # Rollback changes
                self.words_set = original_words
                removed_count = 0
            else:
                logger.info(f"Removed {removed_count} words")
        
        return removed_count, len(words)
    
    async def validate_collection_with_oxford(self, batch_size: int = 20) -> Dict:
        """
        Validate entire word collection against Oxford Dictionary
        
        Returns:
        {
            "total_words": int,
            "valid_words": int,
            "invalid_words": int,
            "invalid_word_list": [str],
            "validation_results": [Dict]
        }
        """
        logger.info("Starting Oxford validation of entire word collection")
        
        words_list = sorted(list(self.words_set))
        if not words_list:
            return {
                "total_words": 0,
                "valid_words": 0,
                "invalid_words": 0,
                "invalid_word_list": [],
                "validation_results": []
            }
        
        # Process in batches to avoid overwhelming Oxford API
        all_results = []
        invalid_words = []
        
        for i in range(0, len(words_list), batch_size):
            batch = words_list[i:i + batch_size]
            logger.info(f"Validating batch {i//batch_size + 1} ({len(batch)} words)")
            
            batch_result = await self.oxford_validator.validate_words_batch(batch)
            all_results.extend(batch_result["results"])
            
            # Collect invalid words
            for result in batch_result["results"]:
                if not result["is_valid"]:
                    invalid_words.append(result["word"])
            
            # Small delay between batches to be respectful to Oxford API
            await asyncio.sleep(2)
        
        valid_count = len(words_list) - len(invalid_words)
        
        logger.info(f"Validation complete: {valid_count}/{len(words_list)} words are valid")
        
        return {
            "total_words": len(words_list),
            "valid_words": valid_count,
            "invalid_words": len(invalid_words),
            "invalid_word_list": invalid_words,
            "validation_results": all_results
        }
    
    async def cleanup_invalid_words(self, auto_remove: bool = False) -> Dict:
        """
        Find and optionally remove invalid words from the collection
        
        Args:
            auto_remove: If True, automatically remove invalid words
        
        Returns:
        {
            "found_invalid": int,
            "removed_count": int,
            "invalid_words": [str],
            "action_taken": str
        }
        """
        logger.info("Starting cleanup of invalid words")
        
        validation_result = await self.validate_collection_with_oxford()
        invalid_words = validation_result["invalid_word_list"]
        
        if not invalid_words:
            return {
                "found_invalid": 0,
                "removed_count": 0,
                "invalid_words": [],
                "action_taken": "No invalid words found"
            }
        
        removed_count = 0
        action_taken = f"Found {len(invalid_words)} invalid words"
        
        if auto_remove:
            removed_count, _ = await self.remove_words(invalid_words)
            action_taken = f"Removed {removed_count} invalid words"
            logger.info(f"Automatically removed {removed_count} invalid words")
        
        return {
            "found_invalid": len(invalid_words),
            "removed_count": removed_count,
            "invalid_words": invalid_words,
            "action_taken": action_taken
        }
    
    async def get_oxford_cache_stats(self) -> Dict:
        """Get Oxford validator cache statistics"""
        return self.oxford_validator.get_cache_stats()
