#!/usr/bin/env python3
"""
Word validation script using Merriam-Webster + Oxford Dictionary APIs
Validates all words in words.txt and creates valid_words.txt and invalid_words.txt
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict

# Run from backend/ regardless of current working directory.
BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from oxford_validator import OxfordValidator
    from merriam_webster_validator import MerriamWebsterValidator
    from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator
    from freedictionary_service import FreeDictionaryService, FreeDictionaryBlockedError
    from dictionary_api_dev_service import DictionaryApiDevService
    from freedictionary_api_com_service import FreeDictionaryApiComService
    from unified_word_lookup import UnifiedWordLookup, BULK_VALIDATE_SOURCE_ORDER
except ModuleNotFoundError as exc:
    print(
        "Missing Python dependencies. Use the project virtualenv:\n"
        "  cd backend\n"
        "  venv\\Scripts\\python.exe validate_words.py --fresh\n"
        f"\nOriginal error: {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHECKPOINT_FILE = "validation_checkpoint.json"
API_CHOICES = (
    "combined",
    "oxford",
    "oxford-api",
    "merriam",
    "freedictionary",
    "dictionary-api-dev",
    "freedictionary-api-com",
    "free-apis",
)
# Free REST APIs only — no scrapers, avoids TheFreeDictionary 403 blocks.
FREE_API_SOURCE_ORDER = (
    "dictionary_api_dev",
    "freedictionary_api_com",
    "datamuse",
    "word_game_db",
)


def resolve_word_file_paths(
    input_file: str,
    valid_output: str | None = None,
    invalid_output: str | None = None,
    checkpoint_file: str | None = None,
) -> Dict[str, str]:
    """Derive input/output/checkpoint paths from an input word list file."""
    input_path = Path(input_file)
    if not input_path.is_absolute():
        input_path = (BACKEND_DIR / input_path).resolve()

    stem = input_path.stem
    parent = input_path.parent

    valid_path = Path(valid_output) if valid_output else parent / f"{stem}_valid.txt"
    invalid_path = Path(invalid_output) if invalid_output else parent / f"{stem}_invalid.txt"
    if not valid_output and input_path.name == "words.txt":
        valid_path = parent / "valid_words.txt"
        invalid_path = parent / "invalid_words.txt"
    checkpoint_path = (
        Path(checkpoint_file)
        if checkpoint_file
        else parent / f"validation_checkpoint_{stem}.json"
    )
    if not checkpoint_file and input_path.name == "words.txt":
        checkpoint_path = parent / CHECKPOINT_FILE

    def _resolve(path: Path) -> Path:
        return path.resolve() if path.is_absolute() else (BACKEND_DIR / path).resolve()

    return {
        "words_file": str(_resolve(input_path)),
        "valid_words_file": str(_resolve(valid_path)),
        "invalid_words_file": str(_resolve(invalid_path)),
        "checkpoint_file": str(_resolve(checkpoint_path)),
    }


class WordValidationProcessor:
    def __init__(
        self,
        api_mode: str = "combined",
        concurrency: int = 20,
        *,
        words_file: str = "words.txt",
        valid_words_file: str | None = None,
        invalid_words_file: str | None = None,
        checkpoint_file: str | None = None,
        request_delay: float = 2.0,
        blocked_backoff: float = 15.0,
        blocked_pause_after: int = 3,
    ):
        if api_mode not in API_CHOICES:
            raise ValueError(f"api_mode must be one of {API_CHOICES}")

        paths = resolve_word_file_paths(
            words_file,
            valid_output=valid_words_file,
            invalid_output=invalid_words_file,
            checkpoint_file=checkpoint_file,
        )

        self.api_mode = api_mode
        self.concurrency = max(1, min(concurrency, 50))
        self.request_delay = max(0.0, request_delay)
        self.blocked_backoff = max(1.0, blocked_backoff)
        self.blocked_pause_after = max(1, blocked_pause_after)
        self.words_file = paths["words_file"]
        self.valid_words_file = paths["valid_words_file"]
        self.invalid_words_file = paths["invalid_words_file"]
        self.checkpoint_file = paths["checkpoint_file"]

        self.oxford_validator = OxfordValidator()
        self.oxford_validator.set_concurrency(self.concurrency)
        self.merriam_validator = MerriamWebsterValidator(
            api_key=os.getenv("MERRIAM_WEBSTER_API_KEY")
        )
        self.oxford_api_validator = OxfordDictionariesApiValidator()
        self.freedictionary_service = FreeDictionaryService(
            request_delay=self.request_delay
        )
        self.freedictionary_service.set_concurrency(self.concurrency)
        self.freedictionary_service.set_blocked_backoff(self.blocked_backoff)
        self.freedictionary_service.set_blocked_pause_after(self.blocked_pause_after)
        self.dictionary_api_dev_service = DictionaryApiDevService()
        self.freedictionary_api_com_service = FreeDictionaryApiComService()
        self.unified_lookup = UnifiedWordLookup(
            self.oxford_validator,
            self.merriam_validator,
            self.oxford_api_validator,
            self.dictionary_api_dev_service,
            self.freedictionary_api_com_service,
            freedictionary_service=self.freedictionary_service,
        )

    async def _validate_batch(self, batch: List[str]) -> Dict:
        """Validate a batch using the selected API mode."""
        concurrent = self.concurrency
        if self.api_mode == "oxford":
            return await self.oxford_validator.validate_words_batch(
                batch, max_concurrent=concurrent
            )
        if self.api_mode == "oxford-api":
            return await self.oxford_api_validator.validate_words_batch(
                batch, max_concurrent=concurrent
            )
        if self.api_mode == "merriam":
            return await self.merriam_validator.validate_words_batch(
                batch, max_concurrent=concurrent
            )
        if self.api_mode == "freedictionary":
            return await self.freedictionary_service.validate_words_batch(
                batch, max_concurrent=concurrent
            )
        if self.api_mode == "dictionary-api-dev":
            return await self.dictionary_api_dev_service.validate_words_batch(
                batch, max_concurrent=concurrent
            )
        if self.api_mode == "freedictionary-api-com":
            return await self.freedictionary_api_com_service.validate_words_batch(
                batch, max_concurrent=concurrent
            )
        if self.api_mode == "free-apis":
            return await self.unified_lookup.validate_words_batch(
                batch,
                source_order=FREE_API_SOURCE_ORDER,
                max_concurrent=concurrent,
            )
        return await self.unified_lookup.validate_words_batch(
            batch,
            source_order=BULK_VALIDATE_SOURCE_ORDER,
            max_concurrent=concurrent,
        )

    def _log_api_mode(self) -> None:
        if self.api_mode == "oxford":
            logger.info("API mode: Oxford web only (Merriam-Webster and Oxford API disabled)")
        elif self.api_mode == "oxford-api":
            stats = self.oxford_api_validator.get_usage_stats()
            logger.info(
                "API mode: Oxford Dictionaries API only — %s/%s requests remaining today",
                stats["remaining_today"],
                stats["daily_limit"],
            )
        elif self.api_mode == "merriam":
            stats = self.merriam_validator.get_usage_stats()
            logger.info(
                "API mode: Merriam-Webster only (Oxford disabled) — %s/%s requests remaining today",
                stats["remaining_today"],
                stats["daily_limit"],
            )
        elif self.api_mode == "freedictionary":
            logger.info(
                "API mode: TheFreeDictionary scraper — delay %.1fs, blocked backoff %.0fs, pause after %s blocks",
                self.request_delay,
                self.blocked_backoff,
                self.blocked_pause_after,
            )
        elif self.api_mode == "dictionary-api-dev":
            logger.info(
                "API mode: dictionaryapi.dev (free REST API, no scraping)"
            )
        elif self.api_mode == "freedictionary-api-com":
            logger.info(
                "API mode: freedictionaryapi.com (free REST API, no scraping)"
            )
        elif self.api_mode == "free-apis":
            logger.info(
                "API mode: free REST APIs only (%s)",
                " -> ".join(FREE_API_SOURCE_ORDER),
            )
        else:
            mw_stats = self.merriam_validator.get_usage_stats()
            oda_stats = self.oxford_api_validator.get_usage_stats()
            logger.info(
                "API mode: Combined — Oxford web -> TheFreeDictionary -> "
                "Merriam-Webster (%s/%s) -> Oxford API (%s/%s)",
                mw_stats["remaining_today"],
                mw_stats["daily_limit"],
                oda_stats["remaining_today"],
                oda_stats["daily_limit"],
            )
        
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
    
    async def validate_all_words(
        self,
        words: List[str],
        batch_size: int = 20,
        resume: bool = True,
        batch_delay: float = 1.0,
    ) -> Dict:
        """
        Validate words using the selected API (--api).

        combined: Oxford web -> TheFreeDictionary -> Merriam-Webster -> Oxford Dictionaries API
        oxford:   Oxford Learner's web scraper only
        oxford-api: Official Oxford Dictionaries API only (500/day)
        merriam:  Merriam-Webster only (1,000/day)
        
        Returns:
        {
            "total_words": int,
            "valid_words": int,
            "invalid_words": int,
            "invalid_word_list": [str],
            "valid_word_list": [str],
            "validation_results": [Dict]
        }
        """
        logger.info(f"Starting dictionary validation of {len(words)} words")
        self._log_api_mode()
        logger.info(
            "Parallel lookups: up to %s words at a time (batch size: %s)",
            self.concurrency,
            batch_size,
        )
        logger.info("This may take several minutes - please be patient...")
        
        if not words:
            return {
                "total_words": 0,
                "valid_words": 0,
                "invalid_words": 0,
                "invalid_word_list": [],
                "valid_word_list": [],
                "validation_results": []
            }

        start_index = 0
        valid_words: List[str] = []
        invalid_words: List[str] = []

        if resume:
            checkpoint = self.load_checkpoint()
            checkpoint_api = checkpoint.get("api", "combined")
            checkpoint_concurrency = checkpoint.get("concurrency", self.concurrency)
            checkpoint_input = checkpoint.get("input_file", self.words_file)
            if checkpoint.get("processed_index", 0) > 0 and checkpoint_api != self.api_mode:
                logger.error(
                    "Checkpoint was created with --api %s but you requested --api %s. "
                    "Use the same --api or run with --fresh to start over.",
                    checkpoint_api,
                    self.api_mode,
                )
                sys.exit(1)
            if (
                checkpoint.get("processed_index", 0) > 0
                and str(Path(checkpoint_input).resolve())
                != str(Path(self.words_file).resolve())
            ):
                logger.error(
                    "Checkpoint was created for input file %s but you requested %s. "
                    "Use the same --input or run with --fresh to start over.",
                    checkpoint_input,
                    self.words_file,
                )
                sys.exit(1)
            if (
                checkpoint.get("processed_index", 0) > 0
                and checkpoint_concurrency != self.concurrency
            ):
                logger.error(
                    "Checkpoint was created with --concurrency %s but you requested %s. "
                    "Use the same --concurrency or run with --fresh to start over.",
                    checkpoint_concurrency,
                    self.concurrency,
                )
                sys.exit(1)
            start_index = checkpoint.get("processed_index", 0)
            if start_index > 0:
                logger.info(
                    f"Resuming from checkpoint at word {start_index}/{len(words)} "
                    f"({checkpoint.get('valid_count', 0)} valid, "
                    f"{checkpoint.get('invalid_count', 0)} invalid so far)"
                )
                if Path(self.valid_words_file).exists():
                    with open(self.valid_words_file, "r", encoding="utf-8") as file:
                        valid_words = [line.strip() for line in file if line.strip()]
                if Path(self.invalid_words_file).exists():
                    with open(self.invalid_words_file, "r", encoding="utf-8") as file:
                        invalid_words = [line.strip() for line in file if line.strip()]
        else:
            for path in (
                self.valid_words_file,
                self.invalid_words_file,
                self.checkpoint_file,
            ):
                p = Path(path)
                if p.exists():
                    p.unlink()
        
        # Process in batches to avoid overwhelming Oxford API
        all_results = []
        processed_count = start_index
        
        for i in range(start_index, len(words), batch_size):
            batch = words[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(words) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} words)")
            
            try:
                batch_result = await self._validate_batch(batch)

                batch_valid: List[str] = []
                batch_invalid: List[str] = []
                stopped_on_block = False
                for result in batch_result["results"]:
                    if result.get("blocked"):
                        stopped_on_block = True
                        logger.error(
                            "TheFreeDictionary blocked at word '%s' (index %s). "
                            "Checkpoint saved — wait and resume, or use "
                            "--api dictionary-api-dev / free-apis. %s",
                            result.get("word"),
                            processed_count,
                            result.get("reason", ""),
                        )
                        break
                    if result["is_valid"]:
                        batch_valid.append(result["word"])
                        valid_words.append(result["word"])
                    else:
                        batch_invalid.append(result["word"])
                        invalid_words.append(result["word"])
                    all_results.append(result)
                    processed_count += 1

                if batch_valid or batch_invalid:
                    self.append_word_lists(batch_valid, batch_invalid)
                    self.save_checkpoint(
                        processed_count, len(valid_words), len(invalid_words)
                    )

                if stopped_on_block:
                    return {
                        "total_words": len(words),
                        "valid_words": len(valid_words),
                        "invalid_words": len(invalid_words),
                        "invalid_word_list": invalid_words,
                        "valid_word_list": valid_words,
                        "validation_results": all_results,
                        "blocked": True,
                        "blocked_at_index": processed_count,
                    }

                # Show progress every 100 words
                if processed_count % 100 == 0:
                    logger.info(
                        f"Progress: {processed_count}/{len(words)} words processed "
                        f"({len(valid_words)} valid, {len(invalid_words)} invalid)"
                    )
                
                # Optional pause between batches (rate-limit friendly)
                if batch_delay > 0:
                    await asyncio.sleep(batch_delay)
                
            except FreeDictionaryBlockedError as exc:
                logger.error(
                    "Stopped at batch %s (word index %s): %s",
                    batch_num,
                    processed_count,
                    exc,
                )
                self.save_checkpoint(
                    processed_count, len(valid_words), len(invalid_words)
                )
                return {
                    "total_words": len(words),
                    "valid_words": len(valid_words),
                    "invalid_words": len(invalid_words),
                    "invalid_word_list": invalid_words,
                    "valid_word_list": valid_words,
                    "validation_results": all_results,
                    "blocked": True,
                    "blocked_at_index": processed_count,
                }
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                # Continue with next batch
                continue
        
        valid_count = len(valid_words)
        
        logger.info(f"Validation complete: {valid_count}/{len(words)} words are valid")
        logger.info(f"Found {len(invalid_words)} invalid words")
        
        self.clear_checkpoint()
        # Rewrite sorted final files
        self.save_word_lists(valid_words, invalid_words)
        
        return {
            "total_words": len(words),
            "valid_words": valid_count,
            "invalid_words": len(invalid_words),
            "invalid_word_list": invalid_words,
            "valid_word_list": valid_words,
            "validation_results": all_results
        }
    
    def save_word_lists(self, valid_words: List[str], invalid_words: List[str]):
        """Save valid and invalid words to separate files"""
        try:
            with open(self.valid_words_file, "w", encoding="utf-8") as file:
                for word in sorted(valid_words):
                    file.write(f"{word}\n")
            logger.info(f"Saved {len(valid_words)} valid words to {self.valid_words_file}")

            with open(self.invalid_words_file, "w", encoding="utf-8") as file:
                for word in sorted(invalid_words):
                    file.write(f"{word}\n")
            logger.info(f"Saved {len(invalid_words)} invalid words to {self.invalid_words_file}")
        except Exception as e:
            logger.error(f"Error saving word lists: {e}")

    def append_word_lists(self, valid_words: List[str], invalid_words: List[str]):
        """Append batch results to output files"""
        if valid_words:
            with open(self.valid_words_file, "a", encoding="utf-8") as file:
                for word in valid_words:
                    file.write(f"{word}\n")
        if invalid_words:
            with open(self.invalid_words_file, "a", encoding="utf-8") as file:
                for word in invalid_words:
                    file.write(f"{word}\n")

    def load_checkpoint(self) -> Dict:
        path = Path(self.checkpoint_file)
        if not path.exists():
            return {
                "processed_index": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "api": self.api_mode,
                "concurrency": self.concurrency,
                "input_file": self.words_file,
                "request_delay": self.request_delay,
            }
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if "api" not in data:
            data["api"] = "combined"
        if "concurrency" not in data:
            data["concurrency"] = self.concurrency
        if "input_file" not in data:
            data["input_file"] = self.words_file
        return data

    def save_checkpoint(self, processed_index: int, valid_count: int, invalid_count: int):
        with open(self.checkpoint_file, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "processed_index": processed_index,
                    "valid_count": valid_count,
                    "invalid_count": invalid_count,
                    "api": self.api_mode,
                    "concurrency": self.concurrency,
                    "input_file": self.words_file,
                    "request_delay": self.request_delay,
                },
                file,
            )

    def clear_checkpoint(self):
        path = Path(self.checkpoint_file)
        if path.exists():
            path.unlink()
    
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
        print("DICTIONARY VALIDATION RESULTS")
        print("="*60)
        print(f"Total Words Processed: {validation_result['total_words']:,}")
        print(f"Valid Words: {validation_result['valid_words']:,}")
        print(f"Invalid Words: {validation_result['invalid_words']:,}")
        
        if validation_result['total_words'] > 0:
            validity_percent = (validation_result['valid_words'] / validation_result['total_words']) * 100
            print(f"Validity Rate: {validity_percent:.2f}%")
        
        print("="*60)
        
        if validation_result['invalid_words'] > 0:
            print(f"\nFound {validation_result['invalid_words']} invalid words")
            print("Sample invalid words:")
            for word in validation_result['invalid_word_list'][:10]:
                print(f"   - {word}")
            if len(validation_result['invalid_word_list']) > 10:
                print(f"   ... and {len(validation_result['invalid_word_list']) - 10} more")
        else:
            print("\nAll words are valid!")

        if validation_result.get("blocked"):
            print(
                f"\n*** STOPPED: IP blocked at word index "
                f"{validation_result.get('blocked_at_index', '?')} ***"
            )
            print(
                "Resume later with the same command (no --fresh), or switch API:\n"
                "  validate_words.cmd --api dictionary-api-dev --input invalid_words.txt "
                "--concurrency 3 --batch-size 50 --batch-delay 1"
            )

async def main():
    """Main validation process"""
    parser = argparse.ArgumentParser(
        description="Validate a word list using dictionary APIs"
    )
    parser.add_argument(
        "--input",
        "-i",
        default="words.txt",
        help="Input word list file (default: words.txt). Outputs: <stem>_valid.txt and <stem>_invalid.txt",
    )
    parser.add_argument(
        "--valid-output",
        help="Override valid-words output path (default: <input_stem>_valid.txt)",
    )
    parser.add_argument(
        "--invalid-output",
        help="Override invalid-words output path (default: <input_stem>_invalid.txt)",
    )
    parser.add_argument("--fresh", action="store_true", help="Start over (ignore checkpoint)")
    parser.add_argument("--batch-size", type=int, default=20, help="Words per checkpoint batch (default: 20)")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Max parallel word lookups per batch (default: 1 for freedictionary, 20 otherwise; max: 50)",
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=None,
        help="Seconds between batches (default: 5 for freedictionary, 1 otherwise; use 0 for none)",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=None,
        help="Seconds between TheFreeDictionary HTTP requests (default: 4 for freedictionary API mode)",
    )
    parser.add_argument(
        "--blocked-backoff",
        type=float,
        default=15.0,
        help="Seconds to wait on TheFreeDictionary 403/429 before retry (default: 15, was 60)",
    )
    parser.add_argument(
        "--blocked-pause-after",
        type=int,
        default=3,
        help="Stop run after this many consecutive blocked responses (default: 3)",
    )
    parser.add_argument(
        "--api",
        choices=API_CHOICES,
        default="combined",
        help=(
            "API: combined, oxford, oxford-api, merriam, freedictionary (scraper, may 403), "
            "dictionary-api-dev (recommended), freedictionary-api-com, free-apis"
        ),
    )
    args = parser.parse_args()

    slow_scrape_apis = {"freedictionary"}
    free_rest_apis = {"dictionary-api-dev", "freedictionary-api-com", "free-apis"}

    if args.concurrency is None:
        args.concurrency = 1 if args.api in slow_scrape_apis else 10
    if args.batch_delay is None:
        args.batch_delay = 5.0 if args.api in slow_scrape_apis else 0.5
    if args.request_delay is None:
        args.request_delay = 4.0 if args.api in slow_scrape_apis else 2.0

    if args.concurrency < 1 or args.concurrency > 50:
        parser.error("--concurrency must be between 1 and 50")
    if args.batch_delay < 0:
        parser.error("--batch-delay must be >= 0")
    if args.request_delay < 0:
        parser.error("--request-delay must be >= 0")
    if args.blocked_backoff < 1:
        parser.error("--blocked-backoff must be >= 1")
    if args.blocked_pause_after < 1:
        parser.error("--blocked-pause-after must be >= 1")

    processor = WordValidationProcessor(
        api_mode=args.api,
        concurrency=args.concurrency,
        words_file=args.input,
        valid_words_file=args.valid_output,
        invalid_words_file=args.invalid_output,
        request_delay=args.request_delay,
        blocked_backoff=args.blocked_backoff,
        blocked_pause_after=args.blocked_pause_after,
    )

    api_labels = {
        "combined": "Oxford web -> TheFreeDictionary -> Merriam-Webster -> Oxford API",
        "oxford": "Oxford web scraper only",
        "oxford-api": "Oxford Dictionaries API only (500/day)",
        "merriam": "Merriam-Webster only",
        "freedictionary": "TheFreeDictionary scraper (may 403 — use dictionary-api-dev instead)",
        "dictionary-api-dev": "dictionaryapi.dev free REST API (recommended)",
        "freedictionary-api-com": "freedictionaryapi.com free REST API",
        "free-apis": "dictionaryapi.dev -> freedictionaryapi.com -> DataMuse -> Word Game DB",
    }
    print(f"Starting Dictionary Word Validation - {api_labels[args.api]}")
    print(f"Input:  {processor.words_file}")
    print(f"Valid:  {processor.valid_words_file}")
    print(f"Invalid: {processor.invalid_words_file}")
    print(f"Checkpoint: {processor.checkpoint_file}")
    print(f"Parallel lookups: up to {args.concurrency} words at a time")
    print(f"Batch size (checkpoint): {args.batch_size}")
    if args.api == "freedictionary":
        print(f"Request delay (TheFreeDictionary): {args.request_delay}s per HTTP call")
        print(
            f"Blocked backoff: {args.blocked_backoff}s | "
            f"pause after {args.blocked_pause_after} consecutive 403/429"
        )
    if args.api in free_rest_apis:
        print("Tip: free REST APIs avoid TheFreeDictionary 403 blocks.")
    print(f"Batch delay: {args.batch_delay}s")
    print("\n" + "-"*60)
    
    # Step 1: Load words
    words = processor.load_words()
    print(f"Total words to validate: {len(words):,}")
    print("Note: Full validation of 400k+ words can take many hours due to API rate limits.")
    print("Progress is checkpointed - you can stop and resume later.\n")
    
    # Step 2: Validate all words
    validation_result = await processor.validate_all_words(
        words,
        batch_size=args.batch_size,
        resume=not args.fresh,
        batch_delay=args.batch_delay,
    )
    
    # Step 3: Save final word lists (also done incrementally during run)
    processor.save_word_lists(
        validation_result["valid_word_list"],
        validation_result["invalid_word_list"],
    )
    
    # Step 4: Display summary
    processor.display_summary(validation_result)
    
    return {
        'validation_result': validation_result,
        'processor': processor
    }

if __name__ == "__main__":
    asyncio.run(main())

