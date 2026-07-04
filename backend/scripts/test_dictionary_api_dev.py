import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dictionary_api_dev_service import DictionaryApiDevService
from unified_word_lookup import UnifiedWordLookup
from oxford_validator import OxfordValidator


async def main() -> None:
    dad = DictionaryApiDevService()
    for word in ("succedaneum", "pococurante"):
        result = await dad.validate_word(word)
        print(
            word,
            result["is_valid"],
            len(result["definitions"]),
            len(result["synonyms"]),
            len(result["pronunciations"]),
        )

    lookup = UnifiedWordLookup(OxfordValidator(), dictionary_api_dev_service=dad)
    for word in ("succedaneum", "pococurante"):
        result = await lookup.lookup_word(word, source_order=("dictionary_api_dev",))
        print(
            "UL",
            word,
            result["validation_source"],
            len(result["definitions"]),
            len(result["synonyms"]),
        )


if __name__ == "__main__":
    asyncio.run(main())
