"""One-off helper: split main.py route sections into api/routers/*.py (run from backend/)."""
from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
MAIN = BACKEND / "main.py"
ROUTERS = BACKEND / "api" / "routers"

SECTIONS = [
    ("health", "# HEALTH ENDPOINTS", "# WORD QUERY ENDPOINTS"),
    ("words", "# WORD QUERY ENDPOINTS", "# OXFORD DICTIONARY & SYNONYM ENDPOINTS"),
    ("words_validate", "# OXFORD DICTIONARY & SYNONYM ENDPOINTS", "# WORD MANAGEMENT ENDPOINTS"),
    ("words_admin", "# WORD MANAGEMENT ENDPOINTS", "# STORAGE & CLOUD CONFIGURATION ENDPOINTS"),
    ("storage", "# STORAGE & CLOUD CONFIGURATION ENDPOINTS", "@app.get(\"/words/oxford-stats\")"),
    ("words_stats_extra", "@app.get(\"/words/oxford-stats\")", "@app.get(\"/word-game-db/categories\")"),
    ("integrations", "@app.get(\"/word-game-db/categories\")", "@app.get(\"/datamuse/words\")"),
    ("datamuse", "@app.get(\"/datamuse/words\")", "if __name__"),
]


def extract_block(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        raise ValueError(f"Start marker not found: {start!r}")
    j = text.find(end, i + len(start))
    if j < 0:
        j = len(text)
    return text[i:j].strip()


def transform_handlers(block: str) -> str:
    block = re.sub(r"^@app\.(get|post|put|delete|patch)", r"@router.\1", block, flags=re.MULTILINE)
    return block


def main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    ROUTERS.mkdir(parents=True, exist_ok=True)

    merged: dict[str, list[str]] = {
        "health": [],
        "words": [],
        "storage": [],
        "performance": [],
        "integrations": [],
        "datamuse": [],
        "puzzle": [],
    }

    for name, start, end in SECTIONS:
        block = extract_block(text, start, end)
        block = transform_handlers(block)
        if name.startswith("words"):
            merged["words"].append(block)
        elif name == "health":
            merged["health"].append(block)
        elif name == "storage":
            merged["storage"].append(block)
        elif name == "words_stats_extra":
            merged["performance"].append(block)
        elif name == "integrations":
            merged["integrations"].append(block)
        elif name == "datamuse":
            merged["datamuse"].append(block)

    # puzzle routes live inside words block - extract manually later if needed

    header = '''"""Auto-split from main.py — route handlers."""
from typing import List, Optional
import asyncio
import random
import time

from fastapi import APIRouter, HTTPException, Query

from api import dependencies as deps
from api.schemas.word import (
    AddWordReq,
    AddWordResponse,
    AddWordsReq,
    BasicSearchResult,
    CleanupReq,
    FreeDictionaryLookupRequest,
    RemoveWordReq,
    RemoveWordsReq,
    ValidateWordRequest,
)
from puzzle_solver import match_anagram, match_regex
from puzzle_solver import match_pattern as advanced_match_pattern

router = APIRouter()

'''

    for key, parts in merged.items():
        if not parts:
            continue
        body = "\n\n".join(parts)
        # fix puzzle import for words router
        if key == "words":
            body = body.replace(
                "from puzzle_solver import match_anagram, match_regex\nfrom puzzle_solver import match_pattern as advanced_match_pattern\n\n",
                "",
            )
        out = ROUTERS / f"{key}.py"
        out.write_text(header + body + "\n", encoding="utf-8")
        print(f"Wrote {out} ({len(body)} chars)")


if __name__ == "__main__":
    main()
