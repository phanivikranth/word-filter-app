"""Shared application state, services, and word-filter helpers."""
from __future__ import annotations

import asyncio
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from dotenv import load_dotenv

from advanced_word_filter_service import AdvancedWordFilterService
from combined_word_validator import CombinedWordValidator
from daily_safe_explore_service import DailySafeExploreService
from daily_scramble_service import DailyScrambleService
from daily_word_challenge_service import DailyWordChallengeService
from datamuse_service import DatamuseService
from dictionary_api_dev_service import DictionaryApiDevService
from freedictionary_api_com_service import FreeDictionaryApiComService
from freedictionary_service import FreeDictionaryService
from logger_config import get_logger, monitor_async_performance, setup_logging
from merriam_webster_validator import MerriamWebsterValidator
from nhost_service import NhostWordService
from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator
from oxford_validator import OxfordValidator
from synonym_service import get_synonym_service
from unified_word_lookup import UnifiedWordLookup
from word_enrichment_service import WordEnrichmentService
from word_game_db_service import WordGameDbService
from word_lookup_orchestrator import WordLookupOrchestrator
from word_manager import WordManager
from words_api_rapidapi_service import WordsApiRapidapiService

setup_logging()
logger = get_logger("word_filter.main")
load_dotenv()

total_api_requests = 0

word_manager = WordManager()
nhost_service = NhostWordService()
oxford_validator = OxfordValidator()
merriam_webster_validator = MerriamWebsterValidator(api_key=os.getenv("MERRIAM_WEBSTER_API_KEY"))
oxford_dictionaries_api_validator = OxfordDictionariesApiValidator()
combined_validator = CombinedWordValidator(
    oxford_validator,
    merriam_webster_validator,
    oxford_dictionaries_api_validator,
)
freedictionary_service = FreeDictionaryService()
dictionary_api_dev_service = DictionaryApiDevService()
freedictionary_api_com_service = FreeDictionaryApiComService()
words_api_rapidapi_service = WordsApiRapidapiService()
word_game_db_service = WordGameDbService()
datamuse_service = DatamuseService()
daily_scramble_service = DailyScrambleService()
daily_safe_explore_service = DailySafeExploreService()
daily_word_challenge_service = DailyWordChallengeService()
advanced_word_filter_service = AdvancedWordFilterService(
    words_api_service=words_api_rapidapi_service,
    word_game_db_service=word_game_db_service,
)
unified_lookup = UnifiedWordLookup(
    oxford_validator,
    merriam_webster_validator,
    oxford_dictionaries_api_validator,
    dictionary_api_dev_service,
    freedictionary_api_com_service,
    words_api_rapidapi_service,
    word_game_db_service,
    datamuse_service,
    freedictionary_service,
)

words_list: list[str] = []
words_set: set[str] = set()
word_stats: dict = {}

thread_pool = ThreadPoolExecutor(max_workers=4)
process_pool = ProcessPoolExecutor(max_workers=2)

MERRIAM_WEBSTER_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY")
synonym_service = get_synonym_service(MERRIAM_WEBSTER_KEY)


async def enrich_synonyms(word: str, oxford_data: dict, *, use_merriam: bool = True) -> dict:
    return await synonym_service.get_synonyms_combined(
        word, oxford_data, max_results=15, use_merriam=use_merriam
    )


word_enrichment_service = WordEnrichmentService(
    unified_lookup,
    synonym_enricher=enrich_synonyms,
    use_merriam_for_synonyms=(
        os.getenv("UI_USE_MERRIAM_FOR_SYNONYMS", "false").lower() == "true"
    ),
)

word_lookup_orchestrator = WordLookupOrchestrator(
    word_enrichment_service,
    nhost_service,
    synonym_enricher=enrich_synonyms,
)


@monitor_async_performance("load_words_concurrent")
async def load_words_concurrent():
    """Load words from storage using unified WordManager and update globals."""
    global words_list, words_set, word_stats

    logger.info("Initiating concurrent words load from word_manager")
    start_time = time.time()

    await word_manager.load_words()

    words_list = word_manager.words_list
    words_set = word_manager.words_set

    lengths = [len(word) for word in words_list]
    word_stats = {
        "total_words": len(words_list),
        "min_length": min(lengths) if lengths else 0,
        "max_length": max(lengths) if lengths else 0,
        "avg_length": round(sum(lengths) / len(lengths), 2) if lengths else 0,
    }

    load_time = time.time() - start_time
    logger.info("Loaded %s words concurrently in %.2fs", f"{len(words_list):,}", load_time)
    return words_list, words_set, word_stats


def filter_words_chunk(chunk_data):
    """Filter a chunk of words - designed for parallel processing."""
    words_chunk, filters = chunk_data
    filtered = []

    contains = filters.get("contains", "").lower() if filters.get("contains") else None
    starts_with = filters.get("starts_with", "").lower() if filters.get("starts_with") else None
    ends_with = filters.get("ends_with", "").lower() if filters.get("ends_with") else None
    min_length = filters.get("min_length")
    max_length = filters.get("max_length")
    exact_length = filters.get("exact_length")

    for word in words_chunk:
        if contains and contains not in word:
            continue
        if starts_with and not word.startswith(starts_with):
            continue
        if ends_with and not word.endswith(ends_with):
            continue
        if exact_length and len(word) != exact_length:
            continue
        if not exact_length:
            if min_length and len(word) < min_length:
                continue
            if max_length and len(word) > max_length:
                continue
        filtered.append(word)

    return filtered


async def filter_words_concurrent(filters: dict, limit: int = 100):
    """Filter words using concurrent processing for better performance."""
    if not words_list:
        return []

    if len(words_list) < 10000 or not any(filters.values()):
        return filter_words_simple(filters, limit)

    chunk_size = max(1000, len(words_list) // 4)
    chunks = []
    for i in range(0, len(words_list), chunk_size):
        chunk = words_list[i : i + chunk_size]
        chunks.append((chunk, filters))

    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(process_pool, filter_words_chunk, chunk_data)
        for chunk_data in chunks
    ]
    results = await asyncio.gather(*tasks)

    filtered_words = []
    for result in results:
        filtered_words.extend(result)
        if len(filtered_words) >= limit:
            break

    return filtered_words[:limit]


def filter_words_simple(filters: dict, limit: int = 100):
    """Simple synchronous filtering for small datasets."""
    filtered = []
    contains = filters.get("contains", "").lower() if filters.get("contains") else None
    starts_with = filters.get("starts_with", "").lower() if filters.get("starts_with") else None
    ends_with = filters.get("ends_with", "").lower() if filters.get("ends_with") else None
    min_length = filters.get("min_length")
    max_length = filters.get("max_length")
    exact_length = filters.get("exact_length")

    for word in words_list:
        if len(filtered) >= limit:
            break
        if contains and contains not in word:
            continue
        if starts_with and not word.startswith(starts_with):
            continue
        if ends_with and not word.endswith(ends_with):
            continue
        if exact_length and len(word) != exact_length:
            continue
        if not exact_length:
            if min_length and len(word) < min_length:
                continue
            if max_length and len(word) > max_length:
                continue
        filtered.append(word)

    return filtered


def sync_word_globals_from_manager() -> None:
    """Refresh in-memory word lists and stats after mutations."""
    global words_list, words_set, word_stats

    words_list = word_manager.words_list
    words_set = word_manager.words_set
    lengths = [len(w) for w in words_list]
    word_stats["total_words"] = len(words_list)
    if lengths:
        word_stats["min_length"] = min(lengths)
        word_stats["max_length"] = max(lengths)
        word_stats["avg_length"] = round(sum(lengths) / len(lengths), 2)


async def shutdown_pools() -> None:
    thread_pool.shutdown(wait=True)
    process_pool.shutdown(wait=True)
