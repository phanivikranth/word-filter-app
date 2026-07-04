#!/usr/bin/env python3
"""
Import a JSON word dictionary into Nhost Postgres.

JSON format:
{
  "apple": "A round fruit...",
  "banana": "A long curved fruit..."
}

Usage:
  cd backend
  venv\\Scripts\\python.exe scripts\\import_words_to_nhost.py --file data\\sample_words_definitions.json
  venv\\Scripts\\python.exe scripts\\import_words_to_nhost.py --file words.json --ensure-schema
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv()

from nhost_service import NhostWordService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("import_words_to_nhost")


def print_report(
    *,
    file_path: Path,
    before: dict,
    after: dict,
    import_report: dict,
) -> None:
    width = 62
    print("\n" + "=" * width)
    print("NHOST DEFINITIONS IMPORT SUMMARY")
    print("=" * width)
    print(f"Source file:        {file_path}")
    print(f"Completed at:       {datetime.now().isoformat(timespec='seconds')}")
    print("-" * width)
    print("FILE")
    print(f"  Entries in JSON:           {import_report['file_entries']:>10,}")
    print(f"  Processed (valid keys):    {import_report['processed']:>10,}")
    print(f"  With definitions:          {import_report['file_with_definitions']:>10,}")
    print(f"  Empty definitions in file: {import_report['file_empty_definitions']:>10,}")
    print("-" * width)
    print("DATABASE CHANGES (this run)")
    print(f"  New rows inserted:         {import_report['rows_inserted']:>10,}")
    print(f"  Existing rows updated:     {import_report['rows_updated']:>10,}")
    print(f"  Failed to upsert:          {import_report['failed_count']:>10,}")
    print(f"  Transport:                 {import_report.get('via', 'unknown'):>10}")
    print("-" * width)
    print("DATABASE TOTALS")
    print(f"  Before — total rows:       {before['total']:>10,}")
    print(f"  Before — with definitions: {before['with_definitions']:>10,}")
    print(f"  Before — empty definitions:{before['empty_definitions']:>10,}")
    print(f"  After  — total rows:       {after['total']:>10,}")
    print(f"  After  — with definitions: {after['with_definitions']:>10,}")
    print(f"  After  — empty definitions:{after['empty_definitions']:>10,}")
    print(f"  Net new rows:              {after['total'] - before['total']:>10,}")
    print(
        f"  Definitions added in DB:   "
        f"{after['with_definitions'] - before['with_definitions']:>10,}"
    )
    print("=" * width)

    if import_report["failed_count"]:
        print("\nFAILED WORDS (could not insert/update):")
        for item in import_report["failed_words"][:50]:
            print(f"  - {item['word']}: {item['error']}")
        if import_report["failed_count"] > 50:
            print(f"  ... and {import_report['failed_count'] - 50} more")
        fail_log = BACKEND_DIR / "logs" / "nhost_import_failures.json"
        fail_log.parent.mkdir(parents=True, exist_ok=True)
        with open(fail_log, "w", encoding="utf-8") as file:
            json.dump(import_report["failed_words"], file, indent=2)
        print(f"\nFull failure list written to: {fail_log}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import word JSON into Nhost database")
    parser.add_argument(
        "--file",
        "-f",
        default="data/sample_words_definitions.json",
        help="Path to JSON file ({word: definition, ...})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Rows per upsert batch (default: 500)",
    )
    parser.add_argument(
        "--ensure-schema",
        action="store_true",
        help="Create words table if missing (requires NHOST_DATABASE_URL)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse file and print stats without writing to Nhost",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = (BACKEND_DIR / file_path).resolve()
    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        return 1

    service = NhostWordService()
    status = service.get_status()
    logger.info("Nhost status: %s", status)

    logger.info("Loading JSON from %s ...", file_path)
    words = service.load_json_file(str(file_path))
    with_defs = sum(1 for d in words.values() if str(d).strip())
    empty = len(words) - with_defs
    logger.info(
        "Parsed %s entries (%s with definitions, %s empty)",
        f"{len(words):,}",
        f"{with_defs:,}",
        f"{empty:,}",
    )

    if args.dry_run:
        print(f"Dry run: would upsert {len(words):,} words from {file_path}")
        for word, definition in list(words.items())[:3]:
            preview = definition[:80] + ("..." if len(definition) > 80 else "")
            print(f"  - {word}: {preview}")
        return 0

    if not service.is_configured():
        logger.error(
            "Nhost is not configured. Set USE_NHOST=true and NHOST_DATABASE_URL in backend/.env"
        )
        return 1

    if args.ensure_schema:
        if not status["has_database_url"]:
            logger.error("--ensure-schema requires NHOST_DATABASE_URL")
            return 1
        service.ensure_schema()
        logger.info("Schema checked/created.")

    before = {"total": 0, "empty_definitions": 0, "with_definitions": 0}
    if status["has_database_url"]:
        before = service.get_table_stats()
        logger.info(
            "Before import — total: %s, with definitions: %s, empty: %s",
            f"{before['total']:,}",
            f"{before['with_definitions']:,}",
            f"{before['empty_definitions']:,}",
        )

    logger.info("Upserting definitions (batch size %s) ...", args.batch_size)
    import_report = service.bulk_upsert_words_with_report(
        words, batch_size=args.batch_size
    )

    after = before
    if status["has_database_url"]:
        after = service.get_table_stats()

    print_report(
        file_path=file_path,
        before=before,
        after=after,
        import_report=import_report,
    )

    return 1 if import_report["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
