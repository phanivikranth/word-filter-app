"""HTTP routers."""

from api.routers import datamuse, health, integrations, storage, words, words_mutations

__all__ = [
    "datamuse",
    "health",
    "integrations",
    "storage",
    "words",
    "words_mutations",
]
