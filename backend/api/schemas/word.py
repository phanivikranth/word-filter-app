"""Pydantic request/response models for the Word Filter API."""
from typing import List, Optional

from pydantic import BaseModel


class ValidateWordRequest(BaseModel):
    word: str
    skip_oxford: bool = False


class BasicSearchResult(BaseModel):
    word: str
    inCollection: bool
    oxford: Optional[dict] = None


class AddWordResponse(BaseModel):
    success: bool
    message: str
    word: Optional[str] = None
    was_new: bool = False
    total_words: Optional[int] = None


class AddWordReq(BaseModel):
    word: str


class AddWordsReq(BaseModel):
    words: List[str]


class RemoveWordReq(BaseModel):
    word: str


class RemoveWordsReq(BaseModel):
    words: List[str]


class CleanupReq(BaseModel):
    auto_remove: bool = False


class FreeDictionaryLookupRequest(BaseModel):
    word: str
