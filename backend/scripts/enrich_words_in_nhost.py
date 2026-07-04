#!/usr/bin/env python3
"""
Bulk-enrich words in Nhost with definitions, synonyms, pronunciations, etymology, links, etc.

Quota APIs are used first when available; scrapers fill remaining gaps.

Examples:
  python scripts/enrich_words_in_nhost.py --missing synonyms,pronunciations --limit 500
  python scripts/enrich_words_in_nhost.py --input valid_words.txt --concurrency 5
  python scripts/enrich_words_in_nhost.py --mode all --batch-delay 2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")

from dictionary_api_dev_service import DictionaryApiDevService
from freedictionary_api_com_service import FreeDictionaryApiComService
from words_api_rapidapi_service import WordsApiRapidapiService
from word_game_db_service import WordGameDbService
from freedictionary_service import FreeDictionaryService
from merriam_webster_validator import MerriamWebsterValidator
from nhost_service import NhostWordService
from oxford_dictionaries_api_validator import OxfordDictionariesApiValidator
from oxford_validator import OxfordValidator
from synonym_service import get_synonym_service
from unified_word_lookup import UnifiedWordLookup
from word_enrichment_service import WordEnrichmentService
from word_entry_utils import missing_fields

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("enrich_words_in_nhost")

DEFAULT_CHECKPOINT = BACKEND_ROOT / "data" / "enrich_checkpoint.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich Nhost word rows from dictionary APIs/scrapers")
    parser.add_argument(
        "--mode",
        choices=("missing", "all", "file"),
        default="missing",
        help="missing=DB rows with gaps; all=every DB word; file=words from --input",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        help="Word list file (one word per line) when --mode file",
    )
    parser.add_argument(
        "--missing",
        default="synonyms,pronunciations,etymology,examples,links",
        help="Comma-separated fields to target when --mode missing",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max words to process (0 = no limit)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N words from query")
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel enrichments")
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=1.0,
        help="Seconds to pause between batches",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_CHECKPOINT,
        help="Checkpoint file for resume",
    )
    parser.add_argument("--fresh", action="store_true", help="Ignore checkpoint and start over")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not write to Nhost")
    return parser.parse_args()


def load_checkpoint(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"processed": 0, "saved": 0, "failed": 0, "last_word": ""}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_checkpoint(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_words_from_file(path: Path) -> List[str]:
    words: List[str] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            word = line.strip().lower()
            if word and word.isalpha():
                words.append(word)
    return words


async def build_services() -> tuple[NhostWordService, WordEnrichmentService]:
    nhost = NhostWordService()
    if not nhost.is_configured():
        raise RuntimeError("Nhost is not configured (USE_NHOST=true and NHOST_DATABASE_URL)")

    oxford = OxfordValidator()
    mw = MerriamWebsterValidator()
    oda = OxfordDictionariesApiValidator()
    fd = FreeDictionaryService(
        request_delay=float(os.getenv("ENRICH_FREEDICTIONARY_DELAY", "3.0"))
    )
    dad = DictionaryApiDevService()
    fdapi = FreeDictionaryApiComService()
    war = WordsApiRapidapiService()
    wgd = WordGameDbService()
    unified = UnifiedWordLookup(oxford, mw, oda, dad, fdapi, war, wgd, fd)
    oxford.set_concurrency(int(os.getenv("ENRICH_OXFORD_WEB_CONCURRENCY", "2")))

    async def _enrich_synonyms(word: str, oxford_data: dict, *, use_merriam: bool = True):
        service = get_synonym_service(os.getenv("MERRIAM_WEBSTER_API_KEY"))
        return await service.get_synonyms_combined(
            word, oxford_data, max_results=15, use_merriam=use_merriam
        )

    enrichment = WordEnrichmentService(
        unified,
        synonym_enricher=_enrich_synonyms,
        use_merriam_for_synonyms=(
            os.getenv("ENRICH_USE_MERRIAM_FOR_SYNONYMS", "false").lower() == "true"
        ),
    )
    return nhost, enrichment


async def resolve_word_list(
    args: argparse.Namespace, nhost: NhostWordService
) -> List[str]:
    if args.mode == "file":
        if not args.input:
            raise ValueError("--input is required when --mode file")
        return load_words_from_file(args.input)

    missing = [part.strip() for part in args.missing.split(",") if part.strip()]
    if args.mode == "missing":
        batch_size = 5000
        words: List[str] = []
        offset = args.offset
        while True:
            chunk = await nhost.list_words_needing_enrichment(
                limit=batch_size, offset=offset, missing=missing
            )
            if not chunk:
                break
            words.extend(chunk)
            offset += len(chunk)
            if args.limit and len(words) >= args.limit:
                words = words[: args.limit]
                break
        return words

    all_words = await nhost.load_all_words()
    if args.offset:
        all_words = all_words[args.offset :]
    if args.limit:
        all_words = all_words[: args.limit]
    return all_words


async def enrich_batch(
    words: List[str],
    *,
    nhost: NhostWordService,
    enrichment: WordEnrichmentService,
    concurrency: int,
    dry_run: bool,
    checkpoint: Dict[str, Any],
    checkpoint_path: Path,
) -> None:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _one(word: str) -> None:
        async with semaphore:
            try:
                existing = await nhost.lookup_word(word)
                result = await enrichment.enrich_word_bulk(word, existing=existing)
                gaps_after = missing_fields(result)
                if result.get("definitions") and not dry_run:
                    await nhost.save_word_entry(result)
                    checkpoint["saved"] += 1
                checkpoint["processed"] += 1
                checkpoint["last_word"] = word
                logger.info(
                    "Enriched '%s' (source=%s, gaps=%s)",
                    word,
                    result.get("validation_source"),
                    gaps_after or "none",
                )
            except Exception as exc:
                checkpoint["failed"] += 1
                logger.error("Failed '%s': %s", word, exc)
            save_checkpoint(checkpoint_path, checkpoint)

    await asyncio.gather(*[_one(word) for word in words])


async def main_async() -> int:
    args = parse_args()
    nhost, enrichment = await build_services()
    words = await resolve_word_list(args, nhost)
    if not words:
        logger.info("No words to enrich.")
        return 0

    checkpoint = load_checkpoint(args.checkpoint)
    if args.fresh:
        checkpoint = {"processed": 0, "saved": 0, "failed": 0, "last_word": ""}
    elif checkpoint.get("last_word"):
        try:
            last_index = words.index(checkpoint["last_word"]) + 1
            words = words[last_index:]
            logger.info("Resuming after '%s' (%s words remaining)", checkpoint["last_word"], len(words))
        except ValueError:
            pass

    logger.info(
        "Enriching %s words (mode=%s, concurrency=%s, dry_run=%s)",
        len(words),
        args.mode,
        args.concurrency,
        args.dry_run,
    )

    batch_size = max(1, args.concurrency * 2)
    for index in range(0, len(words), batch_size):
        batch = words[index : index + batch_size]
        await enrich_batch(
            batch,
            nhost=nhost,
            enrichment=enrichment,
            concurrency=args.concurrency,
            dry_run=args.dry_run,
            checkpoint=checkpoint,
            checkpoint_path=args.checkpoint,
        )
        if index + batch_size < len(words) and args.batch_delay > 0:
            await asyncio.sleep(args.batch_delay)

    logger.info(
        "Done. processed=%s saved=%s failed=%s",
        checkpoint["processed"],
        checkpoint["saved"],
        checkpoint["failed"],
    )
    return 0


def main() -> None:
    try:
        raise SystemExit(asyncio.run(main_async()))
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
