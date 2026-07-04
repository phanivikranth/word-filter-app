"""
Nhost (PostgreSQL / Hasura) word storage.

Stores word -> definition pairs and serves cached lookups to reduce external API calls.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class NhostWordService:
    """Read/write words in Nhost Postgres or via Hasura GraphQL (admin)."""

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
            "has_database_url": bool(self.database_url),
            "has_graphql": bool(self.graphql_url and self.admin_secret),
            "graphql_url": self.graphql_url or None,
            "table": self.table,
            "subdomain": self.subdomain or None,
            "region": self.region or None,
        }

    def _connect(self):
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError(
                "psycopg2 is not installed. Run: pip install psycopg2-binary"
            )
        if not self.database_url:
            raise RuntimeError("NHOST_DATABASE_URL (or DATABASE_URL) is not set")
        return psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        schema_path = os.path.join(
            os.path.dirname(__file__), "nhost", "schema.sql"
        )
        with open(schema_path, "r", encoding="utf-8") as file:
            sql = file.read()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        logger.info("Nhost schema ensured from nhost/schema.sql")

    def bulk_upsert_words(
        self,
        words: Dict[str, str],
        *,
        batch_size: int = 500,
    ) -> Dict[str, int]:
        """Insert or update word -> definition pairs."""
        if not words:
            return {"inserted": 0, "updated": 0, "total": 0}

        if self.database_url:
            return self._bulk_upsert_postgres(words, batch_size=batch_size)
        if self.graphql_url and self.admin_secret:
            return self._bulk_upsert_graphql(words, batch_size=batch_size)
        raise RuntimeError("Nhost is not configured for writes")

    def _bulk_upsert_postgres(
        self, words: Dict[str, str], *, batch_size: int
    ) -> Dict[str, int]:
        items = [
            (word.strip().lower(), (definition or "").strip())
            for word, definition in words.items()
            if word and word.strip()
        ]
        inserted = 0
        now = datetime.now(timezone.utc)

        upsert_sql = f"""
            INSERT INTO public.{self.table} (word, definition, created_at, updated_at)
            VALUES %s
            ON CONFLICT (word) DO UPDATE SET
                definition = EXCLUDED.definition,
                updated_at = EXCLUDED.updated_at
            RETURNING (xmax = 0) AS inserted
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                for i in range(0, len(items), batch_size):
                    chunk = items[i : i + batch_size]
                    values = [(w, d, now, now) for w, d in chunk]
                    results = psycopg2.extras.execute_values(
                        cur,
                        upsert_sql,
                        values,
                        template="(%s, %s, %s, %s)",
                        fetch=True,
                    )
                    inserted += sum(1 for row in results if row[0])
            conn.commit()

        total = len(items)
        return {"inserted": inserted, "updated": total - inserted, "total": total}

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
            return self._lookup_postgres(word_key)
        return None

    async def lookup_word(self, word: str) -> Optional[Dict[str, Any]]:
        word_key = word.strip().lower()
        if not word_key or not self.is_configured():
            return None

        if self.database_url:
            import asyncio

            return await asyncio.get_event_loop().run_in_executor(
                None, self._lookup_postgres, word_key
            )

        if self.graphql_url and self.admin_secret:
            return await self._lookup_graphql(word_key)
        return None

    def _lookup_postgres(self, word_key: str) -> Optional[Dict[str, Any]]:
        sql = f"""
            SELECT word, definition
            FROM public.{self.table}
            WHERE LOWER(word) = LOWER(%s)
            LIMIT 1
        """
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (word_key,))
                row = cur.fetchone()
        if not row:
            return None
        return self._to_lookup_result(row["word"], row["definition"])

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
            "reason": "Found in Nhost word database",
            "validation_source": "nhost",
            "summary": definition,
        }

    def load_all_words_sync(self) -> List[str]:
        sql = f"SELECT word FROM public.{self.table} ORDER BY word"
        with self._connect() as conn:
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
