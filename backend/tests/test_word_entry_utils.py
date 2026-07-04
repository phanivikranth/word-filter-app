"""Tests for fast-cache / optional-field helpers."""

from word_entry_utils import (
    is_ui_ready,
    missing_fields,
    missing_optional_fields,
    missing_required_fields,
    only_optional_gaps_remain,
)


def test_strapping_like_nhost_row_is_ui_ready():
    row = {
        "word": "strapping",
        "definitions": ["muscular and heavily built"],
        "synonyms": ["a", "b"],
        "pronunciations": [{"prefix": "BrE", "ipa": "/ˈstræpɪŋ/"}],
        "etymology": "",
        "origin_language": "",
        "first_known_use": "",
    }
    assert is_ui_ready(row)
    assert missing_optional_fields(row) == [
        "etymology",
        "origin_language",
        "first_known_use",
    ]
    assert missing_required_fields(row) == ["examples", "word_forms", "links"]
    assert not only_optional_gaps_remain(row)


def test_only_optional_gaps():
    row = {
        "word": "terse",
        "definitions": ["brief"],
        "synonyms": ["short"],
        "pronunciations": [{"prefix": "BrE", "ipa": "/tɜːs/"}],
        "examples": ["a terse reply"],
        "word_forms": ["adjective"],
        "links": {"dictionary": "https://example.com"},
        "etymology": "",
        "origin_language": "",
        "first_known_use": "",
    }
    assert missing_required_fields(row) == []
    assert only_optional_gaps_remain(row)


def test_empty_row_not_ui_ready():
    assert not is_ui_ready(None)
    assert not is_ui_ready({})
    assert "definitions" in missing_fields({})
