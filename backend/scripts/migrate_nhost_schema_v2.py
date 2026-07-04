#!/usr/bin/env python3
"""
Apply Nhost schema v2 and migrate legacy flat definitions into word_definitions.

Usage:
  cd backend
  venv\\Scripts\\python.exe scripts\\migrate_nhost_schema_v2.py
  venv\\Scripts\\python.exe scripts\\migrate_nhost_schema_v2.py --drop-legacy-definition
"""

from __future__ import annotations

import argparse
import logging
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("migrate_nhost_schema_v2")


def split_sql_statements(sql: str) -> list[str]:
    """Split SQL on semicolons outside dollar-quoted blocks."""
    statements: list[str] = []
    buf: list[str] = []
    in_dollar = False
    i = 0
    while i < len(sql):
        if sql[i : i + 2] == "$$":
            in_dollar = not in_dollar
            buf.append("$$")
            i += 2
            continue
        char = sql[i]
        if char == ";" and not in_dollar:
            statement = "".join(buf).strip()
            if statement:
                lines = [
                    ln
                    for ln in statement.splitlines()
                    if ln.strip() and not ln.strip().startswith("--")
                ]
                if lines:
                    statements.append(statement)
            buf = []
            i += 1
            continue
        buf.append(char)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def run_sql_file(service: NhostWordService, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql)
    with service._connect() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        conn.commit()


def print_stats(service: NhostWordService) -> None:
    queries = {
        "words": "SELECT COUNT(*) FROM public.words",
        "definitions": "SELECT COUNT(*) FROM public.word_definitions",
        "synonyms": "SELECT COUNT(*) FROM public.word_synonyms",
        "pronunciations": "SELECT COUNT(*) FROM public.word_pronunciations",
        "examples": "SELECT COUNT(*) FROM public.word_examples",
        "forms": "SELECT COUNT(*) FROM public.word_forms",
        "with_definitions": """
            SELECT COUNT(DISTINCT word_id) FROM public.word_definitions
            WHERE BTRIM(definition) <> ''
        """,
        "empty_words": """
            SELECT COUNT(*) FROM public.words w
            WHERE NOT EXISTS (
                SELECT 1 FROM public.word_definitions d
                WHERE d.word_id = w.id AND BTRIM(d.definition) <> ''
            )
        """,
    }
    print("\n" + "=" * 50)
    print("NHOST SCHEMA V2 — TABLE COUNTS")
    print("=" * 50)
    with service._connect() as conn:
        with conn.cursor() as cur:
            for label, sql in queries.items():
                cur.execute(sql)
                print(f"  {label:20s} {cur.fetchone()[0]:>10,}")
    print("=" * 50 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Nhost DB to schema v2")
    parser.add_argument(
        "--drop-legacy-definition",
        action="store_true",
        help="Drop words.definition column after migration",
    )
    args = parser.parse_args()

    service = NhostWordService()
    if not service.is_configured() or not service.database_url:
        logger.error("Nhost DATABASE_URL not configured in backend/.env")
        return 1

    nhost_dir = BACKEND_DIR / "nhost"
    logger.info("Applying schema_v2.sql ...")
    run_sql_file(service, nhost_dir / "schema_v2.sql")

    logger.info("Running v1 → v2 data migration ...")
    run_sql_file(service, nhost_dir / "migrate_v1_to_v2.sql")

    if args.drop_legacy_definition:
        with service._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='words'
                      AND column_name='definition'
                    """
                )
                if cur.fetchone():
                    cur.execute("ALTER TABLE public.words DROP COLUMN definition")
                    logger.info("Dropped legacy words.definition column")
            conn.commit()

    print_stats(service)
    logger.info("Migration complete. Track new tables in Hasura if needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
