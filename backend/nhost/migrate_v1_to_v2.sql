-- =============================================================================
-- Migrate existing flat public.words (v1) → normalized schema (v2)
-- Safe to re-run: uses IF NOT EXISTS / ON CONFLICT DO NOTHING where possible
-- =============================================================================

-- 1) Apply v2 child tables (run schema_v2.sql separately or via migrate script)
ALTER TABLE public.words ADD COLUMN IF NOT EXISTS summary TEXT NOT NULL DEFAULT '';
ALTER TABLE public.words ADD COLUMN IF NOT EXISTS etymology TEXT NOT NULL DEFAULT '';
ALTER TABLE public.words ADD COLUMN IF NOT EXISTS origin_language TEXT NOT NULL DEFAULT '';
ALTER TABLE public.words ADD COLUMN IF NOT EXISTS first_known_use TEXT NOT NULL DEFAULT '';
ALTER TABLE public.words ADD COLUMN IF NOT EXISTS validation_source TEXT NOT NULL DEFAULT '';
ALTER TABLE public.words ADD COLUMN IF NOT EXISTS is_valid BOOLEAN NOT NULL DEFAULT TRUE;

-- 3) Move legacy single "definition" column into word_definitions (sense 1)
--    (Skip if definition column was already dropped)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'words'
          AND column_name = 'definition'
    ) THEN
        INSERT INTO public.word_definitions (word_id, sense_order, definition, source)
        SELECT w.id, 1, BTRIM(w.definition), 'legacy_import'
        FROM public.words w
        WHERE BTRIM(w.definition) <> ''
        ON CONFLICT (word_id, sense_order) DO UPDATE
            SET definition = EXCLUDED.definition,
                source = EXCLUDED.source;

        -- Optional: drop flat column after migration (uncomment when ready)
        -- ALTER TABLE public.words DROP COLUMN definition;
    END IF;
END $$;

-- 4) Verification queries (run manually)
-- SELECT COUNT(*) FROM public.words;
-- SELECT COUNT(*) FROM public.word_definitions;
-- SELECT COUNT(*) FROM public.word_synonyms;
-- SELECT COUNT(*) FROM public.word_pronunciations;
