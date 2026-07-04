-- Run this in Nhost Dashboard -> Database -> SQL Editor
-- Then track the table: Hasura -> Data -> public -> Track "words"

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.words (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word TEXT NOT NULL,
    definition TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT words_word_unique UNIQUE (word)
);

CREATE INDEX IF NOT EXISTS idx_words_word_lower ON public.words (LOWER(word));

-- Optional: allow read access via Hasura for anonymous role (adjust in Hasura permissions UI)
-- Backend uses direct Postgres (NHOST_DATABASE_URL) or admin GraphQL.
