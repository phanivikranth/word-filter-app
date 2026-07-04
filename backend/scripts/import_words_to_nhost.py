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
  venv\\Scripts\\python.exe scripts\\import_words_to_nhost.py --file path\\to\\words.json
  venv\\Scripts\\python.exe scripts\\import_words_to_nhost.py --file words.json --ensure-schema
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_DIR)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv()

from nhost_service import NhostWordService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Import word JSON into Nhost database")
    parser.add_argument(
        "--file",
        "-f",
        required=True,
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
        print(f"File not found: {file_path}", file=sys.stderr)
        return 1

    service = NhostWordService()
    status = service.get_status()
    print("Nhost status:", status)

    if args.dry_run:
        words = service.load_json_file(str(file_path))
        print(f"Dry run: would import {len(words):,} words from {file_path}")
        sample = list(words.items())[:3]
        for word, definition in sample:
            preview = definition[:80] + ("..." if len(definition) > 80 else "")
            print(f"  - {word}: {preview}")
        return 0

    if not service.is_configured():
        print(
            "Nhost is not configured. Set in backend/.env:\n"
            "  USE_NHOST=true\n"
            "  NHOST_SUBDOMAIN=your-subdomain\n"
            "  NHOST_REGION=us-east-1\n"
            "  NHOST_DATABASE_URL=postgres://...\n"
            "  NHOST_ADMIN_SECRET=your-admin-secret (optional if using DATABASE_URL)\n",
            file=sys.stderr,
        )
        return 1

    if args.ensure_schema:
        if not status["has_database_url"]:
            print("--ensure-schema requires NHOST_DATABASE_URL", file=sys.stderr)
            return 1
        service.ensure_schema()
        print("Schema checked/created.")

    words = service.load_json_file(str(file_path))
    print(f"Importing {len(words):,} words from {file_path} ...")
    result = service.bulk_upsert_words(words, batch_size=args.batch_size)
    print(
        f"Done. total={result['total']:,} "
        f"inserted~={result.get('inserted', 0):,} "
        f"updated~={result.get('updated', 0):,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
