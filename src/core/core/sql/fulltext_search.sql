-- Ensure Story has a tsvector column for full-text search
ALTER TABLE story ADD COLUMN IF NOT EXISTS search_vector tsvector DEFAULT ''::tsvector;
ALTER TABLE story ALTER COLUMN search_vector DROP NOT NULL;

-- Build a weighted tsvector for a Story using the native ID type.
CREATE OR REPLACE FUNCTION fts_build_story_search_vector(story_row_id varchar)
RETURNS tsvector
LANGUAGE sql
AS $$
WITH story_text AS (
    SELECT
        unaccent(coalesce(s.title,  ''))  AS story_title,
        unaccent(coalesce(s.summary,''))  AS story_summary
    FROM story s
    WHERE s.id = story_row_id
),
news_text AS (
    SELECT
        unaccent(coalesce(string_agg(n.title,  ' ' ORDER BY n.id), ''))  AS news_titles,
        -- The 8000/200000 truncations keep the aggregated text well under PostgreSQL's ~1MB tsvector size limit.
        left(unaccent(coalesce(string_agg(left(n.content, 8000),' ' ORDER BY n.id), '')), 200000)  AS news_contents
    FROM news_item n
    WHERE n.story_id = story_row_id
)
SELECT
    setweight(to_tsvector('simple', (SELECT story_title   FROM story_text)), 'A') ||
    setweight(to_tsvector('simple', (SELECT story_summary FROM story_text)), 'B') ||
    setweight(to_tsvector('simple', (SELECT news_titles   FROM news_text)), 'B') ||
    setweight(to_tsvector('simple', (SELECT news_contents FROM news_text)), 'C');
$$;

-- Compatibility wrapper for callers that still pass text.
CREATE OR REPLACE FUNCTION fts_build_story_search_vector(story_row_id text)
RETURNS tsvector
LANGUAGE sql
AS $$
SELECT fts_build_story_search_vector(story_row_id::varchar);
$$;

-- Trigger: story row changed → recompute
CREATE OR REPLACE FUNCTION fts_update_story_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_news_titles text;
    v_news_contents text;
BEGIN
    SELECT
        unaccent(coalesce(string_agg(n.title, ' ' ORDER BY n.id), '')),
        -- Keep aggregated text well under PostgreSQL's ~1MB tsvector size limit.
        left(unaccent(coalesce(string_agg(left(n.content, 8000), ' ' ORDER BY n.id), '')), 200000)
    INTO
        v_news_titles,
        v_news_contents
    FROM news_item n
    WHERE n.story_id = NEW.id;

    NEW.search_vector :=
        setweight(to_tsvector('simple', unaccent(coalesce(NEW.title, ''))), 'A') ||
        setweight(to_tsvector('simple', unaccent(coalesce(NEW.summary, ''))), 'B') ||
        setweight(to_tsvector('simple', coalesce(v_news_titles, '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(v_news_contents, '')), 'C');

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_story_update_search_vector ON story;
CREATE TRIGGER trg_story_update_search_vector
BEFORE INSERT OR UPDATE OF title, summary
ON story
FOR EACH ROW
EXECUTE FUNCTION fts_update_story_search_vector();

-- Trigger: news_item changed → refresh parent story
CREATE OR REPLACE FUNCTION fts_refresh_parent_story_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    old_story_id varchar(64);
    new_story_id varchar(64);
BEGIN
    IF TG_OP = 'INSERT' THEN
        new_story_id := NEW.story_id;
    ELSIF TG_OP = 'DELETE' THEN
        old_story_id := OLD.story_id;
    ELSE
        old_story_id := OLD.story_id;
        new_story_id := NEW.story_id;
    END IF;

    IF new_story_id IS NOT NULL THEN
        UPDATE story s
        SET search_vector = fts_build_story_search_vector(s.id)
        WHERE s.id = new_story_id;
    END IF;

    IF old_story_id IS NOT NULL AND old_story_id IS DISTINCT FROM new_story_id THEN
        UPDATE story s
        SET search_vector = fts_build_story_search_vector(s.id)
        WHERE s.id = old_story_id;
    END IF;

    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_newsitem_refresh_parent_story_vector ON news_item;
CREATE TRIGGER trg_newsitem_refresh_parent_story_vector
AFTER INSERT OR UPDATE OF story_id, title, content OR DELETE
ON news_item
FOR EACH ROW
EXECUTE FUNCTION fts_refresh_parent_story_vector();

CREATE INDEX IF NOT EXISTS ix_story_search_vector_gin
  ON story USING GIN (search_vector);
