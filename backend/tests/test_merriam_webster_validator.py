import json
from unittest.mock import AsyncMock, patch

import pytest

from merriam_webster_validator import MerriamWebsterValidator
from combined_word_validator import CombinedWordValidator


@pytest.fixture
def mw_validator(tmp_path):
    usage_file = tmp_path / "mw_api_usage.json"
    return MerriamWebsterValidator(
        api_key="test-key",
        daily_limit=3,
        usage_file=usage_file,
    )


@pytest.mark.asyncio
async def test_merriam_webster_valid_word(mw_validator):
    valid_payload = [
        {
            "meta": {"id": "test"},
            "def": [
                {
                    "sseq": [
                        [
                            [
                                "sense",
                                {
                                    "dt": [["text", "{bc}a means of testing"]],
                                    "syn_list": [[{"wd": "trial"}, {"wd": "essay"}]],
                                },
                            ]
                        ]
                    ]
                }
            ],
        }
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=valid_payload)
        mock_get.return_value.__aenter__.return_value = mock_response

        result = await mw_validator.validate_word("test")

    assert result["is_valid"] is True
    assert result["source"] == "merriam_webster"
    assert "trial" in result["synonyms"]


@pytest.mark.asyncio
async def test_merriam_webster_invalid_word_returns_suggestions(mw_validator):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=["fizzy", "jazzy"])
        mock_get.return_value.__aenter__.return_value = mock_response

        result = await mw_validator.validate_word("xyzzy")

    assert result["is_valid"] is False
    assert result["suggestions"] == ["fizzy", "jazzy"]


@pytest.mark.asyncio
async def test_merriam_webster_daily_quota(mw_validator):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])
        mock_get.return_value.__aenter__.return_value = mock_response

        for _ in range(3):
            await mw_validator.validate_word("alpha")

        result = await mw_validator.validate_word("beta")

    assert result["is_valid"] is False
    assert "quota exhausted" in result["reason"].lower()
    assert mock_get.call_count == 3


@pytest.mark.asyncio
async def test_combined_validator_uses_merriam_when_valid():
    oxford = AsyncMock()
    merriam = AsyncMock()
    merriam.is_configured.return_value = True
    merriam.has_quota.return_value = True
    merriam.validate_word = AsyncMock(
        return_value={
            "word": "apple",
            "is_valid": True,
            "definitions": ["fruit"],
            "word_forms": [],
            "synonyms": [],
            "reason": "Found in Merriam-Webster Thesaurus",
            "source": "merriam_webster",
        }
    )

    validator = CombinedWordValidator(oxford, merriam)
    result = await validator.validate_word("apple")

    assert result["is_valid"] is True
    assert result["validation_source"] == "merriam_webster"
    oxford.validate_word.assert_not_called()


@pytest.mark.asyncio
async def test_combined_validator_falls_back_to_oxford():
    oxford = AsyncMock()
    oxford.validate_word = AsyncMock(
        return_value={
            "word": "apple",
            "is_valid": True,
            "definitions": ["fruit"],
            "word_forms": [],
            "examples": [],
            "synonyms": [],
            "reason": "Found in Oxford Dictionary",
        }
    )
    merriam = AsyncMock()
    merriam.is_configured.return_value = True
    merriam.has_quota.return_value = True
    merriam.validate_word = AsyncMock(
        return_value={
            "word": "apple",
            "is_valid": False,
            "definitions": [],
            "word_forms": [],
            "synonyms": [],
            "reason": "Not found in Merriam-Webster Thesaurus",
            "source": "merriam_webster",
        }
    )

    validator = CombinedWordValidator(oxford, merriam)
    result = await validator.validate_word("apple")

    assert result["is_valid"] is True
    assert result["validation_source"] == "oxford"
    oxford.validate_word.assert_called_once()
