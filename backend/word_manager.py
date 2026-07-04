import boto3
import asyncio
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from oxford_validator import OxfordValidator
from merriam_webster_validator import MerriamWebsterValidator
from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator
from freedictionary_service import FreeDictionaryService
from unified_word_lookup import UnifiedWordLookup
from nhost_service import NhostWordService

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_WORDS_FILE = BACKEND_DIR / "words.txt"
SEED_WORDS_FILES = (
    BACKEND_DIR / "google-10k-common.txt",
    BACKEND_DIR / "words_seed.txt",
)


class WordManager:
    """
    Unified Word Manager supporting both Civo Object Store (S3-compatible) 
    and local file storage fallback.
    """
    
    def __init__(self):
        self.words_list = []
        self.words_set = set()
        self.s3_client = None
        self.storage_type = "unknown"
        self.storage_info = {}
        
        # Initialize dictionary validators
        self.oxford_validator = OxfordValidator()
        self.merriam_webster_validator = MerriamWebsterValidator(
            api_key=os.getenv("MERRIAM_WEBSTER_API_KEY")
        )
        self.oxford_dictionaries_api_validator = OxfordDictionariesApiValidator()
        self.freedictionary_service = FreeDictionaryService()
        self.unified_lookup = UnifiedWordLookup(
            self.oxford_validator,
            self.merriam_webster_validator,
            self.oxford_dictionaries_api_validator,
            self.freedictionary_service,
        )
        self.nhost_service = NhostWordService()
        
        # Initialize storage based on environment
        self._init_storage()
    
    def _init_storage(self):
        """Initialize storage based on environment variables"""
        try:
            storage_type = os.getenv("STORAGE_TYPE", "auto").lower()
            use_nhost_storage = (
                os.getenv("USE_NHOST", "false").lower() == "true"
                and storage_type == "nhost"
            )
            use_object_storage = os.getenv("USE_OBJECT_STORAGE", "false").lower() == "true"
            
            if use_nhost_storage and self.nhost_service.is_configured():
                self._init_nhost_storage()
            elif use_object_storage or storage_type in ["civo", "s3"]:
                self._init_object_store()
            else:
                self._init_file_storage()
                
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            self._init_file_storage()
    
    def _init_object_store(self):
        """Initialize Civo Object Store / S3-compatible client"""
        try:
            endpoint_url = os.getenv("S3_ENDPOINT", "")
            region = os.getenv("S3_REGION", os.getenv("AWS_REGION", "LON1"))
            access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
            
            # Set up custom endpoint URL if specified (required for S3-compatible storage like Civo)
            kwargs = {}
            if endpoint_url:
                kwargs['endpoint_url'] = endpoint_url
                kwargs['config'] = boto3.session.Config(
                    signature_version='s3v4',
                    s3={'addressing_style': 'virtual'}
                )
            
            if not all([access_key, secret_key]):
                logger.warning("Object storage credentials incomplete, falling back to local file storage")
                self._init_file_storage()
                return
            
            self.s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                **kwargs
            )
            
            self.bucket_name = os.getenv("WORDS_S3_BUCKET", "word-filter-storage")
            self.words_key = os.getenv("WORDS_S3_KEY", "words.txt")
            self.storage_type = "object_store"
            
            self.storage_info = {
                "provider": "civo" if "civo" in endpoint_url else "s3_compatible",
                "type": "object_store",
                "endpoint": endpoint_url or "s3.amazonaws.com",
                "region": region,
                "bucket": self.bucket_name,
                "key": self.words_key,
                "connected": True
            }
            
            logger.info(f"Initialized Object Store: {endpoint_url or 'S3'} / {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Object Store: {e}")
            self._init_file_storage()
    
    def _init_file_storage(self):
        """Initialize local file storage"""
        self.storage_type = "file"
        env_path = os.getenv("WORDS_FILE_PATH")
        if env_path:
            path = Path(env_path)
            self.words_file_path = str(path if path.is_absolute() else BACKEND_DIR / path)
        else:
            self.words_file_path = str(DEFAULT_WORDS_FILE)

        self.storage_info = {
            "provider": "local",
            "type": "file",
            "file_path": self.words_file_path,
            "connected": True
        }

        logger.info(f"Initialized local file storage: {self.words_file_path}")

    def _init_nhost_storage(self):
        """Initialize Nhost PostgreSQL as primary word list storage."""
        self.storage_type = "nhost"
        self.storage_info = {
            "provider": "nhost",
            "type": "nhost",
            "connected": self.nhost_service.is_configured(),
            "nhost": self.nhost_service.get_status(),
        }
        logger.info("Initialized Nhost storage for word list")
    
    async def load_words(self) -> List[str]:
        """Load words from either object store or local file based on current mode"""
        if self.storage_type == "nhost" and self.nhost_service.is_configured():
            try:
                return await self.load_words_from_nhost()
            except Exception as e:
                logger.error(f"Failed to load from Nhost, falling back to file: {e}")
                self._init_file_storage()

        if self.storage_type == "object_store" and self.s3_client:
            try:
                return await self.load_words_from_object_store()
            except Exception as e:
                logger.error(f"Failed to load from object store, falling back to file loading: {e}")
                self._init_file_storage()
        
        return await self.load_words_from_file()

    async def load_words_from_nhost(self) -> List[str]:
        """Load word keys from Nhost Postgres."""
        words = await self.nhost_service.load_all_words()
        self.words_list = words
        self.words_set = set(words)
        logger.info(f"Loaded {len(words)} words from Nhost")
        return words

    async def load_words_from_object_store(self) -> List[str]:
        """Load words from Object Store"""
        if not self.s3_client:
            raise Exception("Object store client not initialized")
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.s3_client.get_object(Bucket=self.bucket_name, Key=self.words_key)
            )
            
            content = response['Body'].read().decode('utf-8')
            words = [word.strip().lower() for word in content.split('\n') if word.strip()]
            
            self.words_list = words
            self.words_set = set(words)
            
            logger.info(f"Loaded {len(words)} words from Object Store")
            return words
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Words key {self.words_key} not found in bucket {self.bucket_name}. Creating empty words file.")
            await self._create_empty_words_file()
            return []
        except Exception as e:
            logger.error(f"Failed to load words from Object Store: {e}")
            self.storage_info["connected"] = False
            raise
    
    async def load_words_from_file(self) -> List[str]:
        """Load words from local file"""
        try:
            words_path = Path(self.words_file_path)
            
            if not words_path.exists() or words_path.stat().st_size == 0:
                logger.warning(
                    f"Local words file {self.words_file_path} missing or empty, bootstrapping from seed list"
                )
                await self._bootstrap_words_file()
            
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None,
                lambda: words_path.read_text(encoding='utf-8')
            )
            
            words = [word.strip().lower() for word in content.split('\n') if word.strip()]
            
            self.words_list = words
            self.words_set = set(words)
            
            logger.info(f"Loaded {len(words)} words from local file {self.words_file_path}")
            return words
            
        except Exception as e:
            logger.error(f"Failed to load words from local file: {e}")
            raise
    
    async def _create_empty_words_file(self):
        """Create empty words file in object store"""
        if not self.s3_client:
            return
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=self.words_key,
                    Body="",
                    ContentType="text/plain"
                )
            )
            logger.info("Created empty words file in Object Store")
        except Exception as e:
            logger.error(f"Failed to create empty words file: {e}")
    
    def _read_seed_words(self) -> List[str]:
        """Load seed words from bundled word lists, falling back to a small sample set."""
        for seed_path in SEED_WORDS_FILES:
            if not seed_path.exists():
                continue
            try:
                content = seed_path.read_text(encoding="utf-8", errors="ignore")
                words = [
                    word.strip().lower()
                    for word in content.splitlines()
                    if word.strip() and word.strip().isalpha()
                ]
                if words:
                    logger.info(f"Using {len(words)} seed words from {seed_path.name}")
                    return words
            except Exception as e:
                logger.warning(f"Could not read seed file {seed_path}: {e}")

        return [
            "apple", "banana", "cherry", "date", "elderberry",
            "fig", "grape", "honeydew", "kiwi", "lemon",
            "mango", "nectarine", "orange", "papaya", "quince",
            "raspberry", "strawberry", "tangerine", "ugli", "vanilla",
        ]

    async def _bootstrap_words_file(self):
        """Create words.txt locally from a bundled seed list when missing."""
        seed_words = self._read_seed_words()
        try:
            words_path = Path(self.words_file_path)
            words_path.parent.mkdir(parents=True, exist_ok=True)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: words_path.write_text("\n".join(seed_words), encoding="utf-8"),
            )
            logger.info(f"Created local words file with {len(seed_words)} words at {words_path}")
        except Exception as e:
            logger.error(f"Failed to bootstrap local words file: {e}")
    
    async def save_words_to_storage(self) -> bool:
        """Save current words list to storage"""
        try:
            content = '\n'.join(sorted(self.words_list))
            
            if self.storage_type == "object_store" and self.s3_client:
                return await self._save_to_object_store(content)
            else:
                return await self._save_to_file(content)
                
        except Exception as e:
            logger.error(f"Failed to save words to storage: {e}")
            return False
    
    async def _save_to_object_store(self, content: str) -> bool:
        """Save words to Object Store"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=self.words_key,
                    Body=content.encode('utf-8'),
                    ContentType="text/plain"
                )
            )
            logger.info(f"Saved {len(self.words_list)} words to Object Store")
            return True
        except Exception as e:
            logger.error(f"Failed to save words to Object Store: {e}")
            return False
    
    async def _save_to_file(self, content: str) -> bool:
        """Save words to local file"""
        try:
            words_path = Path(self.words_file_path)
            words_path.parent.mkdir(parents=True, exist_ok=True)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: words_path.write_text(content, encoding='utf-8')
            )
            logger.info(f"Saved {len(self.words_list)} words to local file")
            return True
        except Exception as e:
            logger.error(f"Failed to save words to local file: {e}")
            return False
    
    async def get_words_list(self) -> List[str]:
        """Get the current words list (loads from storage if empty)"""
        if not self.words_list:
            await self.load_words()
        return self.words_list
    
    async def get_word_count(self) -> int:
        """Get total number of words"""
        words = await self.get_words_list()
        return len(words)
    
    async def word_exists(self, word: str) -> bool:
        """Check if a word exists in the collection"""
        if not self.words_set:
            await self.get_words_list()
        return word.lower().strip() in self.words_set
    
    async def add_word(self, word: str) -> bool:
        """Add a single word to the collection"""
        try:
            word_lower = word.lower().strip()
            if word_lower and word_lower not in self.words_set:
                self.words_list.append(word_lower)
                self.words_set.add(word_lower)
                
                success = await self.save_words_to_storage()
                if not success:
                    # Rollback on save failure
                    self.words_list.remove(word_lower)
                    self.words_set.discard(word_lower)
                    return False
                
                logger.info(f"Added word: {word_lower}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add word {word}: {e}")
            return False
    
    async def add_words(self, words: List[str]) -> Tuple[int, int]:
        """Add multiple words to the collection"""
        try:
            added_count = 0
            total_count = len(words)
            new_words = []
            
            for word in words:
                word_lower = word.lower().strip()
                if word_lower and word_lower not in self.words_set:
                    new_words.append(word_lower)
                    self.words_set.add(word_lower)
                    added_count += 1
            
            if new_words:
                self.words_list.extend(new_words)
                success = await self.save_words_to_storage()
                if not success:
                    # Rollback on save failure
                    for word in new_words:
                        self.words_list.remove(word)
                        self.words_set.discard(word)
                    return 0, total_count
                logger.info(f"Added {added_count} new words out of {total_count} submitted")
            
            return added_count, total_count
        except Exception as e:
            logger.error(f"Failed to add words: {e}")
            return 0, len(words)
    
    async def remove_word(self, word: str) -> bool:
        """Remove a word from the collection"""
        try:
            word_lower = word.lower().strip()
            if word_lower in self.words_set:
                self.words_list.remove(word_lower)
                self.words_set.discard(word_lower)
                
                success = await self.save_words_to_storage()
                if not success:
                    # Rollback on save failure
                    self.words_list.append(word_lower)
                    self.words_set.add(word_lower)
                    return False
                
                logger.info(f"Removed word: {word_lower}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove word {word}: {e}")
            return False
    
    async def remove_words(self, words: List[str]) -> Tuple[int, int]:
        """Remove multiple words from the collection"""
        try:
            removed_count = 0
            total_count = len(words)
            removed_words = []
            
            for word in words:
                word_lower = word.lower().strip()
                if word_lower in self.words_set:
                    removed_words.append(word_lower)
                    self.words_list.remove(word_lower)
                    self.words_set.discard(word_lower)
                    removed_count += 1
            
            if removed_words:
                success = await self.save_words_to_storage()
                if not success:
                    # Rollback on save failure
                    for word in removed_words:
                        self.words_list.append(word)
                        self.words_set.add(word)
                    return 0, total_count
                logger.info(f"Removed {removed_count} words out of {total_count} submitted")
            
            return removed_count, total_count
        except Exception as e:
            logger.error(f"Failed to remove words: {e}")
            return 0, len(words)
    
    async def reload_words(self) -> List[str]:
        """Reload words from storage"""
        return await self.load_words()
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the current storage configuration"""
        return self.storage_info.copy()
    
    async def test_storage_connection(self) -> Dict[str, Any]:
        """Test the storage connection"""
        try:
            if self.storage_type == "object_store" and self.s3_client:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.s3_client.head_bucket(Bucket=self.bucket_name)
                )
                return {
                    "success": True,
                    "storage_type": self.storage_type,
                    "provider": self.storage_info.get("provider", "object_store"),
                    "message": "Object store connection successful",
                    "bucket": self.bucket_name
                }
            else:
                words_path = Path(self.words_file_path)
                accessible = words_path.parent.exists() and os.access(words_path.parent, os.W_OK)
                return {
                    "success": accessible,
                    "storage_type": self.storage_type,
                    "provider": "local",
                    "message": "Local file storage accessible" if accessible else "Local file storage not accessible",
                    "file_path": str(words_path)
                }
        except Exception as e:
            logger.error(f"Storage connection test failed: {e}")
            return {
                "success": False,
                "storage_type": self.storage_type,
                "message": f"Connection test failed: {str(e)}"
            }
    
    async def backup_words(self) -> Dict[str, Any]:
        """Create a backup of current words"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_key = f"backups/words-backup-{timestamp}.txt"
            content = '\n'.join(sorted(self.words_list))
            
            if self.storage_type == "object_store" and self.s3_client:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=backup_key,
                        Body=content.encode('utf-8'),
                        ContentType="text/plain",
                        Metadata={"backup_timestamp": timestamp}
                    )
                )
                return {
                    "success": True,
                    "backup_location": f"{self.bucket_name}/{backup_key}",
                    "word_count": len(self.words_list),
                    "timestamp": timestamp
                }
            else:
                backup_path = Path(f"{self.words_file_path}.backup.{timestamp}")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: backup_path.write_text(content, encoding='utf-8')
                )
                return {
                    "success": True,
                    "backup_location": str(backup_path),
                    "word_count": len(self.words_list),
                    "timestamp": timestamp
                }
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return {
                "success": False,
                "message": f"Backup failed: {str(e)}"
            }

    # Oxford Dictionary Integration Methods
    
    async def validate_word_with_oxford(self, word: str) -> Dict:
        """Validate a word using combined dictionary sources"""
        return await self.unified_lookup.lookup_word(word)
    
    async def add_word_with_validation(self, word: str, skip_oxford: bool = False) -> Dict:
        """Add a word with Oxford Dictionary validation"""
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
        if await self.word_exists(word):
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
            validation_result = await self.unified_lookup.lookup_word(word)
            if not validation_result["is_valid"]:
                return {
                    "success": False,
                    "word": word,
                    "was_new": False,
                    "oxford_validation": validation_result,
                    "message": f"Word '{word}' not found in dictionary sources: {validation_result['reason']}"
                }
            oxford_result = validation_result
        
        # Add to collection
        success = await self.add_word(word)
        return {
            "success": success,
            "word": word,
            "was_new": success,
            "oxford_validation": oxford_result,
            "message": f"Word '{word}' added successfully" if success else f"Failed to add word '{word}'"
        }
    
    async def validate_collection_with_oxford(self, batch_size: int = 20) -> Dict:
        """Validate entire word collection against Oxford Dictionary"""
        logger.info("Starting Oxford validation of entire word collection")
        words_list = await self.get_words_list()
        
        if not words_list:
            return {
                "total_words": 0,
                "valid_words": 0,
                "invalid_words": 0,
                "invalid_word_list": [],
                "validation_results": []
            }
        
        all_results = []
        invalid_words = []
        
        for i in range(0, len(words_list), batch_size):
            batch = words_list[i:i + batch_size]
            batch_result = await self.unified_lookup.validate_words_batch(batch)
            all_results.extend(batch_result["results"])
            
            for result in batch_result["results"]:
                if not result["is_valid"]:
                    invalid_words.append(result["word"])
            
            await asyncio.sleep(2)
        
        valid_count = len(words_list) - len(invalid_words)
        return {
            "total_words": len(words_list),
            "valid_words": valid_count,
            "invalid_words": len(invalid_words),
            "invalid_word_list": invalid_words,
            "validation_results": all_results
        }
    
    async def cleanup_invalid_words(self, auto_remove: bool = False) -> Dict:
        """Find and optionally remove invalid words from the collection"""
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
        """Get dictionary validator cache statistics"""
        return self.unified_lookup.get_dictionary_stats()
