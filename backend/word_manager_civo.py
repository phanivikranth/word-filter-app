import boto3
import asyncio
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
import aiohttp
import json
from datetime import datetime
import tempfile
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class CivoWordManager:
    """
    Word manager that supports both Civo Object Store and local file storage
    Compatible with AWS S3 API (Civo Object Store is S3-compatible)
    """
    
    def __init__(self):
        self.words_list = []
        self.words_set = set()
        self.s3_client = None
        self.storage_type = "unknown"
        self.storage_info = {}
        
        # Initialize storage based on environment
        self._init_storage()
    
    def _init_storage(self):
        """Initialize storage based on environment variables"""
        try:
            use_object_storage = os.getenv("USE_OBJECT_STORAGE", "false").lower() == "true"
            storage_type = os.getenv("STORAGE_TYPE", "auto")
            
            if use_object_storage or storage_type == "civo":
                self._init_object_store()
            else:
                self._init_file_storage()
                
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
            # Fallback to file storage
            self._init_file_storage()
    
    def _init_object_store(self):
        """Initialize Civo Object Store (S3-compatible) client"""
        try:
            # Get Civo Object Store configuration
            endpoint_url = os.getenv("S3_ENDPOINT", "")
            region = os.getenv("S3_REGION", "LON1")
            access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
            
            if not all([endpoint_url, access_key, secret_key]):
                logger.warning("Civo Object Store credentials incomplete, falling back to file storage")
                self._init_file_storage()
                return
            
            # Create S3 client for Civo Object Store
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=boto3.session.Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'virtual'
                    }
                )
            )
            
            self.bucket_name = os.getenv("WORDS_S3_BUCKET", "word-filter-storage")
            self.words_key = os.getenv("WORDS_S3_KEY", "words.txt")
            self.storage_type = "civo_object_store"
            
            self.storage_info = {
                "provider": "civo",
                "type": "object_store",
                "endpoint": endpoint_url,
                "region": region,
                "bucket": self.bucket_name,
                "key": self.words_key,
                "connected": True
            }
            
            logger.info(f"Initialized Civo Object Store: {endpoint_url}/{self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Civo Object Store: {e}")
            self._init_file_storage()
    
    def _init_file_storage(self):
        """Initialize local file storage"""
        self.storage_type = "file"
        self.words_file_path = os.getenv("WORDS_FILE_PATH", "words.txt")
        
        self.storage_info = {
            "provider": "local",
            "type": "file",
            "file_path": self.words_file_path,
            "connected": True
        }
        
        logger.info(f"Initialized file storage: {self.words_file_path}")
    
    async def load_words_from_object_store(self) -> List[str]:
        """Load words from Civo Object Store"""
        if not self.s3_client:
            raise Exception("Object store client not initialized")
        
        try:
            # Run S3 operation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.s3_client.get_object(Bucket=self.bucket_name, Key=self.words_key)
            )
            
            # Read and process the content
            content = response['Body'].read().decode('utf-8')
            words = [word.strip().lower() for word in content.split('\n') if word.strip()]
            
            self.words_list = words
            self.words_set = set(words)
            
            logger.info(f"Loaded {len(words)} words from Civo Object Store")
            return words
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Words file {self.words_key} not found in bucket {self.bucket_name}")
            # Create empty file
            await self._create_empty_words_file()
            return []
        except Exception as e:
            logger.error(f"Failed to load words from Civo Object Store: {e}")
            self.storage_info["connected"] = False
            raise
    
    async def load_words_from_file(self) -> List[str]:
        """Load words from local file"""
        try:
            words_path = Path(self.words_file_path)
            
            if not words_path.exists():
                logger.warning(f"Words file {self.words_file_path} not found, creating with sample words")
                await self._create_sample_words_file()
            
            # Read file asynchronously
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None,
                lambda: words_path.read_text(encoding='utf-8')
            )
            
            words = [word.strip().lower() for word in content.split('\n') if word.strip()]
            
            self.words_list = words
            self.words_set = set(words)
            
            logger.info(f"Loaded {len(words)} words from file {self.words_file_path}")
            return words
            
        except Exception as e:
            logger.error(f"Failed to load words from file: {e}")
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
            logger.info("Created empty words file in Civo Object Store")
        except Exception as e:
            logger.error(f"Failed to create empty words file: {e}")
    
    async def _create_sample_words_file(self):
        """Create sample words file locally"""
        sample_words = [
            "apple", "banana", "cherry", "date", "elderberry",
            "fig", "grape", "honeydew", "kiwi", "lemon",
            "mango", "nectarine", "orange", "papaya", "quince",
            "raspberry", "strawberry", "tangerine", "ugli", "vanilla"
        ]
        
        try:
            words_path = Path(self.words_file_path)
            words_path.parent.mkdir(parents=True, exist_ok=True)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: words_path.write_text('\n'.join(sample_words), encoding='utf-8')
            )
            
            logger.info(f"Created sample words file with {len(sample_words)} words")
        except Exception as e:
            logger.error(f"Failed to create sample words file: {e}")
    
    async def save_words_to_storage(self) -> bool:
        """Save current words list to storage"""
        try:
            content = '\n'.join(sorted(self.words_list))
            
            if self.storage_type == "civo_object_store" and self.s3_client:
                return await self._save_to_object_store(content)
            else:
                return await self._save_to_file(content)
                
        except Exception as e:
            logger.error(f"Failed to save words to storage: {e}")
            return False
    
    async def _save_to_object_store(self, content: str) -> bool:
        """Save words to Civo Object Store"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=self.words_key,
                    Body=content,
                    ContentType="text/plain"
                )
            )
            
            logger.info(f"Saved {len(self.words_list)} words to Civo Object Store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save words to Civo Object Store: {e}")
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
            
            logger.info(f"Saved {len(self.words_list)} words to file")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save words to file: {e}")
            return False
    
    async def get_words_list(self) -> List[str]:
        """Get the current words list"""
        if not self.words_list:
            # Try to load if empty
            try:
                if self.storage_type == "civo_object_store":
                    await self.load_words_from_object_store()
                else:
                    await self.load_words_from_file()
            except Exception as e:
                logger.warning(f"Failed to load words: {e}")
        
        return self.words_list
    
    async def get_word_count(self) -> int:
        """Get total number of words"""
        words = await self.get_words_list()
        return len(words)
    
    async def word_exists(self, word: str) -> bool:
        """Check if a word exists in the collection"""
        if not self.words_set:
            await self.get_words_list()
        return word.lower() in self.words_set
    
    async def add_word(self, word: str) -> bool:
        """Add a single word to the collection"""
        try:
            word_lower = word.lower().strip()
            if word_lower and word_lower not in self.words_set:
                self.words_list.append(word_lower)
                self.words_set.add(word_lower)
                
                # Save to storage
                success = await self.save_words_to_storage()
                if not success:
                    # Rollback on save failure
                    self.words_list.remove(word_lower)
                    self.words_set.discard(word_lower)
                    return False
                
                logger.info(f"Added word: {word_lower}")
                return True
            
            return False  # Word already exists or is invalid
            
        except Exception as e:
            logger.error(f"Failed to add word {word}: {e}")
            return False
    
    async def add_words(self, words: List[str]) -> Tuple[int, int]:
        """Add multiple words to the collection"""
        try:
            added_count = 0
            total_count = len(words)
            
            # Process words
            new_words = []
            for word in words:
                word_lower = word.lower().strip()
                if word_lower and word_lower not in self.words_set:
                    new_words.append(word_lower)
                    self.words_set.add(word_lower)
                    added_count += 1
            
            if new_words:
                self.words_list.extend(new_words)
                
                # Save to storage
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
                
                # Save to storage
                success = await self.save_words_to_storage()
                if not success:
                    # Rollback on save failure
                    self.words_list.append(word_lower)
                    self.words_set.add(word_lower)
                    return False
                
                logger.info(f"Removed word: {word_lower}")
                return True
            
            return False  # Word doesn't exist
            
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
                # Save to storage
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
        try:
            if self.storage_type == "civo_object_store":
                return await self.load_words_from_object_store()
            else:
                return await self.load_words_from_file()
        except Exception as e:
            logger.error(f"Failed to reload words: {e}")
            raise
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the current storage configuration"""
        return self.storage_info.copy()
    
    async def test_storage_connection(self) -> Dict[str, Any]:
        """Test the storage connection"""
        try:
            if self.storage_type == "civo_object_store" and self.s3_client:
                # Test object store connection
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.s3_client.head_bucket(Bucket=self.bucket_name)
                )
                
                return {
                    "success": True,
                    "storage_type": self.storage_type,
                    "provider": "civo",
                    "message": "Object store connection successful",
                    "bucket": self.bucket_name
                }
            else:
                # Test file storage
                words_path = Path(self.words_file_path)
                accessible = words_path.parent.exists() and os.access(words_path.parent, os.W_OK)
                
                return {
                    "success": accessible,
                    "storage_type": self.storage_type,
                    "provider": "local",
                    "message": "File storage accessible" if accessible else "File storage not accessible",
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
            timestamp = datetime.now().isoformat()
            backup_key = f"backups/words-backup-{timestamp}.txt"
            
            if self.storage_type == "civo_object_store" and self.s3_client:
                # Backup to object store
                content = '\n'.join(sorted(self.words_list))
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=backup_key,
                        Body=content,
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
                # Backup to local file
                backup_path = Path(f"{self.words_file_path}.backup.{timestamp}")
                content = '\n'.join(sorted(self.words_list))
                
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
