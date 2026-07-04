"""
Nhost (PostgreSQL / Hasura) word storage.

Stores word -> definition pairs and serves cached lookups to reduce external API calls.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

from word_entry_utils import build_links

import aiohttp

logger = logging.getLogger(__name__)

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2.pool import ThreadedConnectionPool

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    ThreadedConnectionPool = None  # type: ignore


class NhostWordService:
    """Read/write words in Nhost Postgres or via Hasura GraphQL (admin)."""

    _pool: Optional[Any] = None
    _pool_lock = threading.Lock()

    def __init__(self) -> None:
        self.subdomain = os.getenv("NHOST_SUBDOMAIN", "").strip()
        self.region = os.getenv("NHOST_REGION", "us-east-1").strip()
        self.database_url = (
            os.getenv("NHOST_DATABASE_URL")
            or os.getenv("DATABASE_URL")
            or ""
        ).strip()
        self.graphql_url = self._resolve_graphql_url()
        self.admin_secret = (
            os.getenv("NHOST_ADMIN_SECRET")
            or os.getenv("HASURA_GRAPHQL_ADMIN_SECRET")
            or ""
        ).strip()
        self.table = os.getenv("NHOST_WORDS_TABLE", "words").strip() or "words"
        self.enabled = os.getenv("USE_NHOST", "false").lower() == "true"
        self.use_cache_on_lookup = (
            os.getenv("USE_NHOST_CACHE", "true").lower() == "true"
        )
        self.save_on_lookup = (
            os.getenv("USE_NHOST_SAVE", "true").lower() == "true"
        )

    def _resolve_graphql_url(self) -> str:
        explicit = os.getenv("NHOST_GRAPHQL_URL", "").strip()
        if explicit:
            return explicit.rstrip("/")
        if self.subdomain and self.region:
            return (
                f"https://{self.subdomain}.graphql.{self.region}.nhost.run/v1"
            )
        return ""

    def is_configured(self) -> bool:
        if not self.enabled:
            return False
        return bool(self.database_url or (self.graphql_url and self.admin_secret))

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "use_cache_on_lookup": self.use_cache_on_lookup,
            "save_on_lookup": self.save_on_lookup,
            "has_database_url": bool(self.database_url),
            "has_graphql": bool(self.graphql_url and self.admin_secret),
            "graphql_url": self.graphql_url or None,
            "table": self.table,
            "subdomain": self.subdomain or None,
            "region": self.region or None,
        }

    def _build_dsn(self) -> str:
        dsn = self.database_url
        extras: List[str] = []
        if "sslmode=" not in dsn:
            extras.append("sslmode=require")
        for extra in (
            "connect_timeout=15",
            "keepalives=1",
            "keepalives_idle=30",
            "keepalives_interval=10",
            "keepalives_count=5",
        ):
            key = extra.split("=", 1)[0]
            if f"{key}=" not in dsn:
                extras.append(extra)
        if extras:
            sep = "&" if "?" in dsn else "?"
            dsn = f"{dsn}{sep}{'&'.join(extras)}"
        return dsn

    def _ensure_pool(self) -> None:
        with self._pool_lock:
            if self._pool is not None:
                return
            max_conn = max(1, int(os.getenv("NHOST_DB_POOL_MAX", "4")))
            self._pool = ThreadedConnectionPool(
                1,
                max_conn,
                self._build_dsn(),
            )

    def _borrow_connection(self):
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError(
                "psycopg2 is not installed. Run: pip install psycopg2-binary"
            )
        if not self.database_url:
            raise RuntimeError("NHOST_DATABASE_URL (or DATABASE_URL) is not set")

        self._ensure_pool()
        retries = max(1, int(os.getenv("NHOST_DB_CONNECT_RETRIES", "3")))
        last_exc: Optional[Exception] = None

        for attempt in range(retries):
            try:
                conn = self._pool.getconn()
                if conn.closed:
                    self._pool.putconn(conn, close=True)
                    continue
                return conn
            except psycopg2.OperationalError as exc:
                last_exc = exc
                logger.warning(
                    "Nhost DB connect attempt %s/%s failed: %s",
                    attempt + 1,
                    retries,
                    exc,
                )
                if attempt + 1 < retries:
                    time.sleep(0.5 * (attempt + 1))

        raise last_exc or psycopg2.OperationalError("Nhost database connection failed")

    @contextmanager
    def _connection(self):
        conn = self._borrow_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if self._pool is not None and conn is not None:
                self._pool.putconn(conn)

    def _connect(self):
        """Borrow one connection (legacy). Prefer _connection() context manager."""
        return self._borrow_connection()

    def ensure_schema(self) -> None:
        schema_path = os.path.join(
            os.path.dirname(__file__), "nhost", "schema.sql"
        )
        with open(schema_path, "r", encoding="utf-8") as file:
            sql = file.read()
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        logger.info("Nhost schema ensured from nhost/schema.sql")

    def get_table_stats(self) -> Dict[str, int]:
        """Return row counts for words and related v2 tables."""
        sql = """
            SELECT
                (SELECT COUNT(*) FROM public.words) AS total,
                (SELECT COUNT(*) FROM public.words w
                 WHERE NOT EXISTS (
                     SELECT 1 FROM public.word_definitions d WHERE d.word_id = w.id
                 )) AS empty_definitions,
                (SELECT COUNT(DISTINCT word_id) FROM public.word_definitions) AS with_definitions,
                (SELECT COUNT(*) FROM public.word_synonyms) AS synonyms,
                (SELECT COUNT(*) FROM public.word_pronunciations) AS pronunciations
        """
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
        return {
            "total": int(row[0]),
            "empty_definitions": int(row[1]),
            "with_definitions": int(row[2]),
            "synonyms": int(row[3]),
            "pronunciations": int(row[4]),
        }

    def bulk_upsert_words(
        self,
        words: Dict[str, str],
        *,
        batch_size: int = 500,
    ) -> Dict[str, Any]:
        """Insert or update word -> definition pairs."""
        report = self.bulk_upsert_words_with_report(words, batch_size=batch_size)
        return {
            "inserted": report["rows_inserted"],
            "updated": report["rows_updated"],
            "total": report["processed"],
        }

    def bulk_upsert_words_with_report(
        self,
        words: Dict[str, str],
        *,
        batch_size: int = 500,
    ) -> Dict[str, Any]:
        """Upsert words and return a detailed import report."""
        if not words:
            return {
                "file_entries": 0,
                "processed": 0,
                "rows_inserted": 0,
                "rows_updated": 0,
                "file_empty_definitions": 0,
                "file_with_definitions": 0,
                "failed_count": 0,
                "failed_words": [],
            }

        if self.database_url:
            return self._bulk_upsert_postgres_with_report(words, batch_size=batch_size)
        if self.graphql_url and self.admin_secret:
            simple = self._bulk_upsert_graphql(words, batch_size=batch_size)
            return {
                "file_entries": len(words),
                "processed": simple["total"],
                "rows_inserted": 0,
                "rows_updated": simple["total"],
                "file_empty_definitions": sum(
                    1 for d in words.values() if not str(d).strip()
                ),
                "file_with_definitions": sum(
                    1 for d in words.values() if str(d).strip()
                ),
                "failed_count": 0,
                "failed_words": [],
                "via": "graphql",
            }
        raise RuntimeError("Nhost is not configured for writes")

    def _bulk_upsert_postgres_with_report(
        self, words: Dict[str, str], *, batch_size: int
    ) -> Dict[str, Any]:
        items: List[tuple[str, str]] = []
        file_empty = 0
        for word, definition in words.items():
            key = str(word).strip().lower()
            if not key:
                continue
            value = str(definition).strip()
            if not value:
                file_empty += 1
            items.append((key, value))

        rows_inserted = 0
        rows_updated = 0
        failed_words: List[Dict[str, str]] = []
        now = datetime.now(timezone.utc)

        word_upsert_sql = """
            INSERT INTO public.words (word, summary, validation_source, is_valid, created_at, updated_at)
            VALUES %s
            ON CONFLICT (word) DO UPDATE SET
                summary = CASE
                    WHEN EXCLUDED.summary <> '' THEN EXCLUDED.summary
                    ELSE public.words.summary
                END,
                validation_source = CASE
                    WHEN EXCLUDED.validation_source <> '' THEN EXCLUDED.validation_source
                    ELSE public.words.validation_source
                END,
                is_valid = EXCLUDED.is_valid,
                updated_at = EXCLUDED.updated_at
            RETURNING id, word, (xmax = 0) AS inserted
        """
        def_upsert_sql = """
            INSERT INTO public.word_definitions (word_id, sense_order, definition, source)
            VALUES %s
            ON CONFLICT (word_id, sense_order) DO UPDATE SET
                definition = EXCLUDED.definition,
                source = EXCLUDED.source
        """

        with self._connection() as conn:
            with conn.cursor() as cur:
                for i in range(0, len(items), batch_size):
                    chunk = items[i : i + batch_size]
                    word_values = [
                        (w, d, "import", bool(d), now, now) for w, d in chunk
                    ]
                    try:
                        results = psycopg2.extras.execute_values(
                            cur,
                            word_upsert_sql,
                            word_values,
                            template="(%s, %s, %s, %s, %s, %s)",
                            fetch=True,
                        )
                        rows_inserted += sum(1 for row in results if row[2])
                        rows_updated += sum(1 for row in results if not row[2])
                        def_values = [
                            (row[0], 1, definition, "import")
                            for row, (_, definition) in zip(results, chunk)
                            if definition
                        ]
                        if def_values:
                            psycopg2.extras.execute_values(
                                cur,
                                def_upsert_sql,
                                def_values,
                                template="(%s, %s, %s, %s)",
                            )
                    except Exception as batch_exc:
                        logger.warning(
                            "Batch %s-%s failed (%s). Retrying one-by-one.",
                            i + 1,
                            i + len(chunk),
                            batch_exc,
                        )
                        for word, definition in chunk:
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO public.words
                                        (word, summary, validation_source, is_valid, created_at, updated_at)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (word) DO UPDATE SET
                                        summary = CASE
                                            WHEN EXCLUDED.summary <> '' THEN EXCLUDED.summary
                                            ELSE public.words.summary
                                        END,
                                        validation_source = EXCLUDED.validation_source,
                                        is_valid = EXCLUDED.is_valid,
                                        updated_at = EXCLUDED.updated_at
                                    RETURNING id, (xmax = 0) AS inserted
                                    """,
                                    (word, definition, "import", bool(definition), now, now),
                                )
                                row = cur.fetchone()
                                if row and row[1]:
                                    rows_inserted += 1
                                else:
                                    rows_updated += 1
                                if definition and row:
                                    cur.execute(
                                        """
                                        INSERT INTO public.word_definitions
                                            (word_id, sense_order, definition, source)
                                        VALUES (%s, 1, %s, 'import')
                                        ON CONFLICT (word_id, sense_order) DO UPDATE SET
                                            definition = EXCLUDED.definition
                                        """,
                                        (row[0], definition),
                                    )
                            except Exception as word_exc:
                                failed_words.append(
                                    {"word": word, "error": str(word_exc)}
                                )
                                logger.error(
                                    "Failed to upsert '%s': %s", word, word_exc
                                )

        processed = len(items)
        return {
            "file_entries": len(words),
            "processed": processed,
            "rows_inserted": rows_inserted,
            "rows_updated": rows_updated,
            "file_empty_definitions": file_empty,
            "file_with_definitions": processed - file_empty,
            "failed_count": len(failed_words),
            "failed_words": failed_words,
            "via": "postgres",
        }

    def _bulk_upsert_postgres(
        self, words: Dict[str, str], *, batch_size: int
    ) -> Dict[str, int]:
        report = self._bulk_upsert_postgres_with_report(words, batch_size=batch_size)
        return {
            "inserted": report["rows_inserted"],
            "updated": report["rows_updated"],
            "total": report["processed"],
        }

    async def _graphql_request(self, query: str, variables: Dict[str, Any]) -> Dict:
        headers = {
            "Content-Type": "application/json",
            "x-hasura-admin-secret": self.admin_secret,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.graphql_url,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=60,
            ) as response:
                body = await response.json()
                if response.status != 200:
                    raise RuntimeError(f"GraphQL HTTP {response.status}: {body}")
                if body.get("errors"):
                    raise RuntimeError(f"GraphQL errors: {body['errors']}")
                return body.get("data") or {}

    def _bulk_upsert_graphql(
        self, words: Dict[str, str], *, batch_size: int
    ) -> Dict[str, int]:
        import asyncio

        return asyncio.run(self._bulk_upsert_graphql_async(words, batch_size))

    async def _bulk_upsert_graphql_async(
        self, words: Dict[str, str], *, batch_size: int
    ) -> Dict[str, int]:
        mutation = """
        mutation UpsertWords($objects: [words_insert_input!]!) {
          insert_words(
            objects: $objects,
            on_conflict: {
              constraint: words_word_unique,
              update_columns: [definition, updated_at]
            }
          ) {
            affected_rows
          }
        }
        """
        total = 0
        now = datetime.now(timezone.utc).isoformat()
        items = [
            {"word": w.strip().lower(), "definition": (d or "").strip(), "updated_at": now}
            for w, d in words.items()
            if w and w.strip()
        ]
        for i in range(0, len(items), batch_size):
            chunk = items[i : i + batch_size]
            await self._graphql_request(mutation, {"objects": chunk})
            total += len(chunk)
        return {"inserted": 0, "updated": 0, "total": total}

    def lookup_word_sync(self, word: str) -> Optional[Dict[str, Any]]:
        word_key = word.strip().lower()
        if not word_key:
            return None
        if self.database_url:
            try:
                return self._lookup_postgres(word_key)
            except Exception as exc:
                logger.warning("Nhost lookup failed for '%s': %s", word_key, exc)
                return None
        return None

    async def lookup_word(self, word: str) -> Optional[Dict[str, Any]]:
        word_key = word.strip().lower()
        if not word_key or not self.is_configured():
            return None

        try:
            if self.database_url:
                import asyncio

                return await asyncio.get_event_loop().run_in_executor(
                    None, self.lookup_word_sync, word_key
                )

            if self.graphql_url and self.admin_secret:
                return await self._lookup_graphql(word_key)
        except Exception as exc:
            logger.warning("Nhost lookup failed for '%s': %s", word_key, exc)
        return None

    def _lookup_postgres(self, word_key: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT
                w.word,
                w.summary,
                w.etymology,
                w.origin_language,
                w.first_known_use,
                w.validation_source,
                w.is_valid,
                COALESCE(
                    (
                        SELECT json_agg(d.definition ORDER BY d.sense_order)
                        FROM public.word_definitions d
                        WHERE d.word_id = w.id
                    ),
                    '[]'::json
                ) AS definitions_json,
                COALESCE(
                    (
                        SELECT json_agg(s.synonym ORDER BY s.sort_order, s.synonym)
                        FROM public.word_synonyms s
                        WHERE s.word_id = w.id
                    ),
                    '[]'::json
                ) AS synonyms_json,
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'prefix', p.dialect,
                                'ipa', p.ipa,
                                'url', NULLIF(p.audio_url, '')
                            )
                            ORDER BY p.sort_order, p.dialect
                        )
                        FROM public.word_pronunciations p
                        WHERE p.word_id = w.id
                    ),
                    '[]'::json
                ) AS pronunciations_json,
                COALESCE(
                    (
                        SELECT json_agg(e.example_text ORDER BY e.sort_order)
                        FROM public.word_examples e
                        WHERE e.word_id = w.id
                    ),
                    '[]'::json
                ) AS examples_json,
                COALESCE(
                    (
                        SELECT json_agg(
                            CASE
                                WHEN f.form_text <> '' THEN f.label || ': ' || f.form_text
                                ELSE f.label
                            END
                            ORDER BY f.sort_order, f.label
                        )
                        FROM public.word_forms f
                        WHERE f.word_id = w.id
                    ),
                    '[]'::json
                ) AS word_forms_json,
                COALESCE(
                    (
                        SELECT json_object_agg(l.link_type, l.url)
                        FROM public.word_links l
                        WHERE l.word_id = w.id
                    ),
                    '{}'::json
                ) AS links_json
            FROM public.words w
            WHERE LOWER(w.word) = LOWER(%s)
            LIMIT 1
        """
        with self._connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (word_key,))
                row = cur.fetchone()
        if not row:
            return None
        return self._row_to_lookup_result(row)

    async def _lookup_graphql(self, word_key: str) -> Optional[Dict[str, Any]]:
        query = """
        query WordByName($word: String!) {
          words(where: {word: {_eq: $word}}, limit: 1) {
            word
            definition
          }
        }
        """
        data = await self._graphql_request(query, {"word": word_key})
        rows = data.get("words") or []
        if not rows:
            return None
        row = rows[0]
        return self._to_lookup_result(row["word"], row.get("definition") or "")

    @staticmethod
    def _json_list(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        return []

    @classmethod
    def _row_to_lookup_result(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        definitions = [
            str(item).strip()
            for item in cls._json_list(row.get("definitions_json"))
            if str(item).strip()
        ]
        summary = (row.get("summary") or "").strip() or (
            definitions[0] if definitions else ""
        )
        links_raw = row.get("links_json")
        links: Dict[str, str] = {}
        if isinstance(links_raw, dict):
            links = {str(k): str(v) for k, v in links_raw.items() if v}
        return {
            "word": str(row["word"]).strip().lower(),
            "is_valid": bool(row.get("is_valid", definitions)),
            "definitions": definitions,
            "word_forms": [
                str(item).strip()
                for item in cls._json_list(row.get("word_forms_json"))
                if str(item).strip()
            ],
            "examples": [
                str(item).strip()
                for item in cls._json_list(row.get("examples_json"))
                if str(item).strip()
            ],
            "synonyms": [
                str(item).strip()
                for item in cls._json_list(row.get("synonyms_json"))
                if str(item).strip()
            ],
            "pronunciations": [
                item
                for item in cls._json_list(row.get("pronunciations_json"))
                if isinstance(item, dict) and item.get("ipa")
            ],
            "etymology": (row.get("etymology") or "").strip(),
            "origin_language": (row.get("origin_language") or "").strip(),
            "first_known_use": (row.get("first_known_use") or "").strip(),
            "reason": "Found in Nhost word database",
            "validation_source": row.get("validation_source") or "nhost",
            "summary": summary,
            "links": links,
        }

    @staticmethod
    def _to_lookup_result(word: str, definition: str) -> Dict[str, Any]:
        definition = (definition or "").strip()
        definitions = [definition] if definition else []
        return {
            "word": word.strip().lower(),
            "is_valid": bool(definitions),
            "definitions": definitions,
            "word_forms": [],
            "examples": [],
            "synonyms": [],
            "pronunciations": [],
            "etymology": "",
            "origin_language": "",
            "first_known_use": "",
            "reason": "Found in Nhost word database",
            "validation_source": "nhost",
            "summary": definition,
        }

    async def save_word_entry(self, result: Dict[str, Any]) -> None:
        if not self.save_on_lookup:
            logger.info(
                "Nhost save skipped for '%s' (USE_NHOST_SAVE=false)",
                result.get("word"),
            )
            return
        if not self.database_url:
            raise RuntimeError("NHOST_DATABASE_URL is required to save word entries")
        import asyncio

        await asyncio.get_event_loop().run_in_executor(
            None, self._save_word_entry_sync, result
        )

    def _save_word_entry_sync(self, result: Dict[str, Any]) -> None:
        word_key = str(result.get("word", "")).strip().lower()
        if not word_key:
            return

        try:
            self._save_word_entry_sync_inner(result, word_key)
        except Exception as exc:
            logger.warning("Nhost save failed for '%s': %s", word_key, exc)
            raise

    def _save_word_entry_sync_inner(
        self, result: Dict[str, Any], word_key: str
    ) -> None:
        definitions = [
            str(item).strip()
            for item in (result.get("definitions") or [])
            if str(item).strip()
        ]
        summary = (result.get("summary") or "").strip() or (
            definitions[0] if definitions else ""
        )
        source = (result.get("validation_source") or "api").strip()
        now = datetime.now(timezone.utc)

        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.words (
                        word, summary, etymology, origin_language, first_known_use,
                        validation_source, is_valid, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (word) DO UPDATE SET
                        summary = CASE
                            WHEN EXCLUDED.summary <> '' THEN EXCLUDED.summary
                            ELSE public.words.summary
                        END,
                        etymology = CASE
                            WHEN EXCLUDED.etymology <> '' THEN EXCLUDED.etymology
                            ELSE public.words.etymology
                        END,
                        origin_language = CASE
                            WHEN EXCLUDED.origin_language <> '' THEN EXCLUDED.origin_language
                            ELSE public.words.origin_language
                        END,
                        first_known_use = CASE
                            WHEN EXCLUDED.first_known_use <> '' THEN EXCLUDED.first_known_use
                            ELSE public.words.first_known_use
                        END,
                        validation_source = EXCLUDED.validation_source,
                        is_valid = EXCLUDED.is_valid,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                    """,
                    (
                        word_key,
                        summary,
                        (result.get("etymology") or "").strip(),
                        (result.get("origin_language") or "").strip(),
                        (result.get("first_known_use") or "").strip(),
                        source,
                        bool(result.get("is_valid") or definitions),
                        now,
                        now,
                    ),
                )
                word_id = cur.fetchone()[0]

                if definitions:
                    cur.execute(
                        "DELETE FROM public.word_definitions WHERE word_id = %s",
                        (word_id,),
                    )
                    for index, definition in enumerate(definitions, start=1):
                        cur.execute(
                            """
                            INSERT INTO public.word_definitions
                                (word_id, sense_order, definition, source)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (word_id, index, definition, source),
                        )

                synonyms = [
                    str(item).strip()
                    for item in (result.get("synonyms") or [])
                    if str(item).strip()
                ]
                if synonyms:
                    cur.execute(
                        "DELETE FROM public.word_synonyms WHERE word_id = %s",
                        (word_id,),
                    )
                    for index, synonym in enumerate(synonyms):
                        cur.execute(
                            """
                            INSERT INTO public.word_synonyms
                                (word_id, synonym, sort_order, source)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (word_id, synonym) DO NOTHING
                            """,
                            (word_id, synonym, index, source),
                        )

                pronunciations = list(result.get("pronunciations") or [])
                if pronunciations:
                    cur.execute(
                        "DELETE FROM public.word_pronunciations WHERE word_id = %s",
                        (word_id,),
                    )
                    for index, pron in enumerate(pronunciations):
                        if not isinstance(pron, dict) or not pron.get("ipa"):
                            continue
                        cur.execute(
                            """
                            INSERT INTO public.word_pronunciations
                                (word_id, dialect, ipa, audio_url, sort_order, source)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (word_id, dialect, ipa) DO UPDATE SET
                                audio_url = EXCLUDED.audio_url,
                                sort_order = EXCLUDED.sort_order
                            """,
                            (
                                word_id,
                                (pron.get("prefix") or "Standard").strip(),
                                pron.get("ipa", "").strip(),
                                (pron.get("url") or "").strip(),
                                index,
                                source,
                            ),
                        )

                examples = [
                    str(item).strip()
                    for item in (result.get("examples") or [])
                    if str(item).strip()
                ]
                if examples:
                    cur.execute(
                        "DELETE FROM public.word_examples WHERE word_id = %s",
                        (word_id,),
                    )
                    for index, example in enumerate(examples):
                        cur.execute(
                            """
                            INSERT INTO public.word_examples
                                (word_id, example_text, sort_order, source)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (word_id, example, index, source),
                        )

                word_forms = list(result.get("word_forms") or [])
                if word_forms:
                    cur.execute(
                        "DELETE FROM public.word_forms WHERE word_id = %s",
                        (word_id,),
                    )
                    for index, form in enumerate(word_forms):
                        label = str(form).strip()
                        if not label:
                            continue
                        form_text = ""
                        if ": " in label:
                            label, form_text = label.split(": ", 1)
                        cur.execute(
                            """
                            INSERT INTO public.word_forms
                                (word_id, label, form_text, sort_order)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (word_id, label) DO UPDATE SET
                                form_text = EXCLUDED.form_text,
                                sort_order = EXCLUDED.sort_order
                            """,
                            (word_id, label.strip(), form_text.strip(), index),
                        )

                links = build_links(result)
                if links:
                    for link_type, url in links.items():
                        if not url:
                            continue
                        cur.execute(
                            """
                            INSERT INTO public.word_links (word_id, link_type, url)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (word_id, link_type) DO UPDATE SET
                                url = EXCLUDED.url
                            """,
                            (word_id, link_type, url),
                        )

    def list_words_needing_enrichment_sync(
        self,
        *,
        limit: int = 1000,
        offset: int = 0,
        missing: Optional[Sequence[str]] = None,
    ) -> List[str]:
        """Return headwords missing one or more enrichment fields."""
        missing = list(missing or ("synonyms", "pronunciations", "etymology"))
        conditions: List[str] = []
        if "synonyms" in missing:
            conditions.append(
                "NOT EXISTS (SELECT 1 FROM public.word_synonyms s WHERE s.word_id = w.id)"
            )
        if "pronunciations" in missing:
            conditions.append(
                "NOT EXISTS (SELECT 1 FROM public.word_pronunciations p WHERE p.word_id = w.id)"
            )
        if "etymology" in missing:
            conditions.append("BTRIM(w.etymology) = ''")
        if "examples" in missing:
            conditions.append(
                "NOT EXISTS (SELECT 1 FROM public.word_examples e WHERE e.word_id = w.id)"
            )
        if "links" in missing:
            conditions.append(
                "NOT EXISTS (SELECT 1 FROM public.word_links l WHERE l.word_id = w.id)"
            )
        if "definitions" in missing:
            conditions.append(
                "NOT EXISTS (SELECT 1 FROM public.word_definitions d WHERE d.word_id = w.id)"
            )
        where_extra = ""
        if conditions:
            where_extra = "AND (" + " OR ".join(conditions) + ")"

        sql = f"""
            SELECT w.word
            FROM public.words w
            WHERE TRUE {where_extra}
            ORDER BY w.word
            LIMIT %s OFFSET %s
        """
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (limit, offset))
                return [row[0].strip().lower() for row in cur.fetchall() if row[0]]

    async def list_words_needing_enrichment(
        self,
        *,
        limit: int = 1000,
        offset: int = 0,
        missing: Optional[Sequence[str]] = None,
    ) -> List[str]:
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.list_words_needing_enrichment_sync(
                limit=limit, offset=offset, missing=missing
            ),
        )

    def load_all_words_sync(self) -> List[str]:
        sql = f"SELECT word FROM public.{self.table} ORDER BY word"
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return [row[0].strip().lower() for row in cur.fetchall() if row[0]]

    async def load_all_words(self) -> List[str]:
        if not self.database_url:
            return []
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self.load_all_words_sync
        )

    @staticmethod
    def load_json_file(path: str) -> Dict[str, str]:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("JSON file must be an object: { \"word\": \"definition\", ... }")
        return {
            str(word).strip().lower(): str(definition)
            for word, definition in data.items()
            if str(word).strip()
        }
