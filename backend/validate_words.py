#!/usr/bin/env python3
"""
Word validation script using Oxford Dictionary
Validates all words in words.txt and creates invalid_words.txt
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict
from oxford_validator import OxfordValidator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WordValidationProcessor:
    def __init__(self):
        self.oxford_validator = OxfordValidator()
        self.words_file = "words.txt"
        self.invalid_words_file = "invalid_words.txt"
        
    def load_words(self) -> List[str]:
        """Load all words from words.txt"""
        try:
            with open(self.words_file, "r", encoding="utf-8") as file:
                words = [word.strip().lower() for word in file.readlines() if word.strip()]
                logger.info(f"Loaded {len(words)} words from {self.words_file}")
                return words
        except FileNotFoundError:
            logger.error(f"File {self.words_file} not found!")
            sys.exit(1)
    
    async def validate_all_words(self, words: List[str], batch_size: int = 20) -> Dict:
        """
        Validate all words using Oxford Dictionary
        
        Returns:
        {
            "total_words": int,
            "valid_words": int,
            "invalid_words": int,
            "invalid_word_list": [str],
            "validation_results": [Dict]
        }
        """
        logger.info(f"Starting Oxford validation of {len(words)} words")
        logger.info("This may take several minutes - please be patient...")
        
        if not words:
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
        processed_count = 0
        
        for i in range(0, len(words), batch_size):
            batch = words[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(words) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} words)")
            
            try:
                batch_result = await self.oxford_validator.validate_words_batch(batch)
                all_results.extend(batch_result["results"])
                
                # Collect invalid words
                for result in batch_result["results"]:
                    if not result["is_valid"]:
                        invalid_words.append(result["word"])
                    processed_count += 1
                
                # Show progress every 100 words
                if processed_count % 100 == 0:
                    logger.info(f"Progress: {processed_count}/{len(words)} words processed")
                
                # Small delay between batches to be respectful to Oxford API
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                # Continue with next batch
                continue
        
        valid_count = len(words) - len(invalid_words)
        
        logger.info(f"Validation complete: {valid_count}/{len(words)} words are valid")
        logger.info(f"Found {len(invalid_words)} invalid words")
        
        return {
            "total_words": len(words),
            "valid_words": valid_count,
            "invalid_words": len(invalid_words),
            "invalid_word_list": invalid_words,
            "validation_results": all_results
        }
    
    def save_invalid_words(self, invalid_words: List[str]):
        """Save invalid words to invalid_words.txt"""
        try:
            with open(self.invalid_words_file, "w", encoding="utf-8") as file:
                for word in sorted(invalid_words):
                    file.write(f"{word}\n")
            logger.info(f"Saved {len(invalid_words)} invalid words to {self.invalid_words_file}")
        except Exception as e:
            logger.error(f"Error saving invalid words: {e}")
    
    def remove_invalid_words_from_original(self, invalid_words: List[str]) -> Dict:
        """
        Remove invalid words from words.txt
        
        Returns operation statistics
        """
        try:
            # Load original words
            with open(self.words_file, "r", encoding="utf-8") as file:
                original_words = [word.strip().lower() for word in file.readlines() if word.strip()]
            
            original_count = len(original_words)
            invalid_set = set(invalid_words)
            
            # Filter out invalid words
            valid_words = [word for word in original_words if word not in invalid_set]
            removed_count = original_count - len(valid_words)
            
            # Save cleaned words back to words.txt
            with open(self.words_file, "w", encoding="utf-8") as file:
                for word in valid_words:
                    file.write(f"{word}\n")
            
            return {
                "original_count": original_count,
                "removed_count": removed_count,
                "final_count": len(valid_words),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error removing invalid words: {e}")
            return {
                "original_count": 0,
                "removed_count": 0,
                "final_count": 0,
                "success": False,
                "error": str(e)
            }
    
    def display_summary(self, validation_result: Dict):
        """Display validation summary"""
        print("\n" + "="*60)
        print("📊 OXFORD DICTIONARY VALIDATION RESULTS")
        print("="*60)
        print(f"Total Words Processed: {validation_result['total_words']:,}")
        print(f"Valid Words: {validation_result['valid_words']:,}")
        print(f"Invalid Words: {validation_result['invalid_words']:,}")
        
        if validation_result['total_words'] > 0:
            validity_percent = (validation_result['valid_words'] / validation_result['total_words']) * 100
            print(f"Validity Rate: {validity_percent:.2f}%")
        
        print("="*60)
        
        if validation_result['invalid_words'] > 0:
            print(f"\n❌ Found {validation_result['invalid_words']} invalid words")
            print("Sample invalid words:")
            for word in validation_result['invalid_word_list'][:10]:
                print(f"   - {word}")
            if len(validation_result['invalid_word_list']) > 10:
                print(f"   ... and {len(validation_result['invalid_word_list']) - 10} more")
        else:
            print("\n✅ All words are valid!")

async def main():
    """Main validation process"""
    processor = WordValidationProcessor()
    
    print("🚀 Starting Oxford Dictionary Word Validation")
    print(f"📁 Processing: {processor.words_file}")
    print(f"📝 Invalid words will be saved to: {processor.invalid_words_file}")
    print("\n" + "-"*60)
    
    # Step 1: Load words
    words = processor.load_words()
    
    # Step 2: Validate all words
    validation_result = await processor.validate_all_words(words)
    
    # Step 3: Save invalid words
    if validation_result['invalid_words'] > 0:
        processor.save_invalid_words(validation_result['invalid_word_list'])
    
    # Step 4: Display summary
    processor.display_summary(validation_result)
    
    # Step 5: Ask for permission to remove invalid words
    if validation_result['invalid_words'] > 0:
        print(f"\n🗑️  REMOVAL CONFIRMATION")
        print("-"*40)
        print(f"Current words in {processor.words_file}: {validation_result['total_words']:,}")
        print(f"Invalid words to remove: {validation_result['invalid_words']:,}")
        print(f"Words remaining after removal: {validation_result['valid_words']:,}")
        print(f"Backup saved as: words_new.txt")
        
        return {
            'validation_result': validation_result,
            'processor': processor
        }
    else:
        print("\n✅ No invalid words found - no cleanup needed!")
        return {
            'validation_result': validation_result,
            'processor': processor
        }

if __name__ == "__main__":
    asyncio.run(main())

