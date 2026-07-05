"""
Per-source API cooldown registry for validate_words and unified lookup.

When a source is blocked (403/429), rate-limited, or daily quota is exhausted,
it is skipped for COOLDOWN_HOURS (default 24) so we do not keep hammering it.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_COOLDOWN_FILE = BACKEND_DIR / "data" / "api_source_cooldown.json"
DEFAULT_COOLDOWN_HOURS = float(os.getenv("API_SOURCE_COOLDOWN_HOURS", "24"))

_BLOCK_PATTERNS = (
    r"\b403\b",
    r"\b429\b",
    r"\b503\b",
    r"quota\s+exhaust",
    r"daily\s+quota",
    r"rate\s*limit",
    r"too\s+many\s+requests",
    r"\bblocked\b",
    r"ip\s+blocked",
    r"service\s+unavailable",
    r"temporarily\s+unavailable",
)

_BLOCK_RE = re.compile("|".join(_BLOCK_PATTERNS), re.IGNORECASE)


class ApiSourceCooldown:
    """Track unavailable dictionary sources with a time-based cooldown."""

    def __init__(
        self,
        path: Optional[Path] = None,
        cooldown_hours: float = DEFAULT_COOLDOWN_HOURS,
    ):
        self.path = Path(
            path or os.getenv("API_SOURCE_COOLDOWN_FILE", str(DEFAULT_COOLDOWN_FILE))
        )
        self.cooldown_hours = max(1.0, float(cooldown_hours))
        self._state: Dict[str, Any] = self._load()
        self._consecutive_hits: Dict[str, int] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"sources": {}}
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return {"sources": {}}
            data.setdefault("sources", {})
            return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read API cooldown file: %s", exc)
            return {"sources": {}}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)

    def _purge_expired(self) -> None:
        sources: Dict[str, Any] = self._state.get("sources") or {}
        now = self._now()
        expired = []
        for key, entry in sources.items():
            until = self._parse_until(entry.get("cooled_until"))
            if until is None or until <= now:
                expired.append(key)
        for key in expired:
            sources.pop(key, None)
        self._state["sources"] = sources

    @staticmethod
    def _parse_until(value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError):
            return None

    def is_available(self, source: str) -> bool:
        self._purge_expired()
        entry = (self._state.get("sources") or {}).get(source)
        if not entry:
            return True
        until = self._parse_until(entry.get("cooled_until"))
        if until is None:
            return True
        return until <= self._now()

    def cooled_until(self, source: str) -> Optional[datetime]:
        self._purge_expired()
        entry = (self._state.get("sources") or {}).get(source)
        if not entry:
            return None
        return self._parse_until(entry.get("cooled_until"))

    def mark_unavailable(
        self,
        source: str,
        reason: str,
        *,
        hours: Optional[float] = None,
    ) -> None:
        self._purge_expired()
        existing = (self._state.get("sources") or {}).get(source)
        if existing:
            until = self._parse_until(existing.get("cooled_until"))
            if until and until > self._now():
                return

        until = self._now() + timedelta(hours=hours or self.cooldown_hours)
        sources = self._state.setdefault("sources", {})
        existing = sources.get(source) or {}
        sources[source] = {
            "reason": reason.strip() or "unavailable",
            "cooled_until": until.isoformat(),
            "marked_at": self._now().isoformat(),
            "hits": int(existing.get("hits", 0)) + 1,
        }
        self._save()
        logger.warning(
            "API source '%s' on cooldown until %s — %s",
            source,
            until.strftime("%Y-%m-%d %H:%M UTC"),
            reason,
        )

    @classmethod
    def detect_trigger(
        cls,
        *,
        result: Optional[Dict[str, Any]] = None,
        exc: Optional[BaseException] = None,
    ) -> Optional[str]:
        if result and result.get("blocked"):
            return str(result.get("reason") or "blocked")

        chunks: List[str] = []
        if result:
            chunks.append(str(result.get("reason") or ""))
            chunks.append(str(result.get("error") or ""))
        if exc:
            chunks.append(str(exc))
            status = getattr(exc, "status", None)
            if status in (403, 429, 503):
                return f"HTTP {status}"

        text = " ".join(chunks).strip()
        if not text:
            return None

        if _BLOCK_RE.search(text):
            return text[:240]

        lowered = text.lower()
        if "not found" in lowered and "403" not in lowered and "429" not in lowered:
            return None
        return None

    def record_failure(
        self,
        source: str,
        *,
        result: Optional[Dict[str, Any]] = None,
        exc: Optional[BaseException] = None,
    ) -> bool:
        trigger = self.detect_trigger(result=result, exc=exc)
        if not trigger:
            self._consecutive_hits[source] = 0
            return False

        self._consecutive_hits[source] = self._consecutive_hits.get(source, 0) + 1
        strikes = self._consecutive_hits[source]
        immediate = (
            "403" in trigger
            or "429" in trigger
            or "quota" in trigger.lower()
            or "blocked" in trigger.lower()
            or bool(result and result.get("blocked"))
        )
        if immediate or strikes >= 3:
            self.mark_unavailable(source, trigger)
            return True
        return False

    def record_success(self, source: str) -> None:
        self._consecutive_hits[source] = 0

    def sync_quota_sources(
        self,
        *,
        merriam_validator: Any = None,
        oxford_api_validator: Any = None,
    ) -> None:
        if merriam_validator and merriam_validator.is_configured():
            if not merriam_validator.has_quota():
                stats = merriam_validator.get_usage_stats()
                self.mark_unavailable(
                    "merriam_webster",
                    f"Merriam-Webster daily quota exhausted "
                    f"({stats.get('used_today')}/{stats.get('daily_limit')})",
                )
        if oxford_api_validator and oxford_api_validator.is_configured():
            if not oxford_api_validator.has_quota():
                stats = oxford_api_validator.get_usage_stats()
                self.mark_unavailable(
                    "oxford_dictionaries_api",
                    f"Oxford Dictionaries API daily quota exhausted "
                    f"({stats.get('used_today')}/{stats.get('daily_limit')})",
                )

    def filter_available(self, order: Iterable[str]) -> Tuple[str, ...]:
        self._purge_expired()
        available: List[str] = []
        for source in order:
            if self.is_available(source):
                available.append(source)
            else:
                until = self.cooled_until(source)
                entry = (self._state.get("sources") or {}).get(source, {})
                logger.info(
                    "Skipping cooled-down API '%s' until %s — %s",
                    source,
                    until.strftime("%Y-%m-%d %H:%M UTC") if until else "?",
                    entry.get("reason", ""),
                )
        return tuple(available)

    def summary(self) -> Dict[str, Any]:
        self._purge_expired()
        sources = self._state.get("sources") or {}
        cooled: Dict[str, Any] = {}
        for key, entry in sources.items():
            until = self._parse_until(entry.get("cooled_until"))
            cooled[key] = {
                "reason": entry.get("reason"),
                "cooled_until": entry.get("cooled_until"),
                "hits": entry.get("hits", 1),
                "remaining_hours": round(
                    max(0.0, (until - self._now()).total_seconds() / 3600), 1
                )
                if until
                else 0,
            }
        return {
            "cooldown_hours": self.cooldown_hours,
            "file": str(self.path),
            "cooled_sources": cooled,
        }


_default_cooldown: Optional[ApiSourceCooldown] = None


def get_source_cooldown() -> ApiSourceCooldown:
    global _default_cooldown
    if _default_cooldown is None:
        _default_cooldown = ApiSourceCooldown()
    return _default_cooldown
