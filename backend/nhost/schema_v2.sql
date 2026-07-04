-- =============================================================================
-- Terse / Word Filter — Normalized Nhost schema (v2)
-- Run in Nhost Dashboard → Database → SQL Editor
-- Then track all tables in Hasura → Data → public → Track All
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------------------------------
-- Core headword (one row per distinct word)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.words (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word TEXT NOT NULL,
    -- Short lead-in for cards / search results (optional)
    summary TEXT NOT NULL DEFAULT '',
    -- Etymology & origin (display in "Word origin" UI section)
    etymology TEXT NOT NULL DEFAULT '',
    origin_language TEXT NOT NULL DEFAULT '',
    first_known_use TEXT NOT NULL DEFAULT '',
    -- Where we validated / cached this entry
    validation_source TEXT NOT NULL DEFAULT '',
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT words_word_unique UNIQUE (word)
);

CREATE INDEX IF NOT EXISTS idx_words_word_lower ON public.words (LOWER(word));

-- -----------------------------------------------------------------------------
-- Definitions (one word → many senses / definition lines)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.word_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word_id UUID NOT NULL REFERENCES public.words(id) ON DELETE CASCADE,
    sense_order SMALLINT NOT NULL DEFAULT 1,
    definition TEXT NOT NULL,
    part_of_speech TEXT NOT NULL DEFAULT '',
    register_label TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT word_definitions_word_sense_unique UNIQUE (word_id, sense_order)
);

CREATE INDEX IF NOT EXISTS idx_word_definitions_word_id ON public.word_definitions (word_id);

-- -----------------------------------------------------------------------------
-- Synonyms (one word → many synonym strings)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.word_synonyms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word_id UUID NOT NULL REFERENCES public.words(id) ON DELETE CASCADE,
    synonym TEXT NOT NULL,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT '',
    CONSTRAINT word_synonyms_word_synonym_unique UNIQUE (word_id, synonym)
);

CREATE INDEX IF NOT EXISTS idx_word_synonyms_word_id ON public.word_synonyms (word_id);
CREATE INDEX IF NOT EXISTS idx_word_synonyms_synonym_lower ON public.word_synonyms (LOWER(synonym));

-- -----------------------------------------------------------------------------
-- Pronunciations (one word → many dialects / IPA / audio clips)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.word_pronunciations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word_id UUID NOT NULL REFERENCES public.words(id) ON DELETE CASCADE,
    dialect TEXT NOT NULL DEFAULT 'Standard',
    ipa TEXT NOT NULL,
    audio_url TEXT NOT NULL DEFAULT '',
    sort_order SMALLINT NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT '',
    CONSTRAINT word_pronunciations_word_dialect_ipa_unique UNIQUE (word_id, dialect, ipa)
);

CREATE INDEX IF NOT EXISTS idx_word_pronunciations_word_id ON public.word_pronunciations (word_id);

-- -----------------------------------------------------------------------------
-- Example sentences
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.word_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word_id UUID NOT NULL REFERENCES public.words(id) ON DELETE CASCADE,
    example_text TEXT NOT NULL,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_word_examples_word_id ON public.word_examples (word_id);

-- -----------------------------------------------------------------------------
-- Word forms (noun, verb, past tense, plural, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.word_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word_id UUID NOT NULL REFERENCES public.words(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    form_text TEXT NOT NULL DEFAULT '',
    sort_order SMALLINT NOT NULL DEFAULT 0,
    CONSTRAINT word_forms_word_label_unique UNIQUE (word_id, label)
);

CREATE INDEX IF NOT EXISTS idx_word_forms_word_id ON public.word_forms (word_id);

-- -----------------------------------------------------------------------------
-- Optional: external reference links (Oxford URL, FreeDictionary, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.word_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word_id UUID NOT NULL REFERENCES public.words(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL,
    url TEXT NOT NULL,
    CONSTRAINT word_links_word_type_unique UNIQUE (word_id, link_type)
);

CREATE INDEX IF NOT EXISTS idx_word_links_word_id ON public.word_links (word_id);

-- -----------------------------------------------------------------------------
-- Updated-at trigger for words
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_words_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_words_updated_at ON public.words;
CREATE TRIGGER trg_words_updated_at
    BEFORE UPDATE ON public.words
    FOR EACH ROW
    EXECUTE FUNCTION public.set_words_updated_at();
