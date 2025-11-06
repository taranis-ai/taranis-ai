-- Build a weighted tsvector for a Story (IDs are TEXT)
CREATE OR REPLACE FUNCTION fts_build_story_search_vector(story_row_id text)
RETURNS tsvector
LANGUAGE sql
AS $$
WITH story_text AS (
    SELECT
        unaccent(coalesce(s.title,  ''))  AS story_title,
        unaccent(coalesce(s.summary,''))  AS story_summary
    FROM story s
    WHERE s.id::text = story_row_id
),
news_text AS (
    SELECT
        unaccent(coalesce(string_agg(n.title,  ' '), ''))  AS news_titles,
        -- The 8000/200000 truncations keep the aggregated text well under PostgreSQL's ~1MB tsvector size limit.
        left(unaccent(coalesce(string_agg(left(n.content, 8000),' '), '')), 200000)  AS news_contents
    FROM news_item n
    WHERE n.story_id::text = story_row_id
)
SELECT
    setweight(to_tsvector('simple', (SELECT story_title   FROM story_text)), 'A') ||
    setweight(to_tsvector('simple', (SELECT story_summary FROM story_text)), 'B') ||
    setweight(to_tsvector('simple', (SELECT news_titles   FROM news_text)), 'B') ||
    setweight(to_tsvector('simple', (SELECT news_contents FROM news_text)), 'C');
$$;

-- Trigger: story row changed → recompute
CREATE OR REPLACE FUNCTION fts_update_story_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_vector := fts_build_story_search_vector(NEW.id::text);
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
    parent_story_id text;
BEGIN
    IF (TG_OP = 'INSERT') OR (TG_OP = 'UPDATE') THEN
        parent_story_id := NEW.story_id::text;
    ELSE
        parent_story_id := OLD.story_id::text;
    END IF;

    IF parent_story_id IS NOT NULL THEN
        UPDATE story s
        SET search_vector = fts_build_story_search_vector(s.id::text)
        WHERE s.id::text = parent_story_id;
    END IF;

    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_newsitem_refresh_parent_story_vector ON news_item;
CREATE TRIGGER trg_newsitem_refresh_parent_story_vector
AFTER INSERT OR UPDATE OF title, content OR DELETE
ON news_item
FOR EACH ROW
EXECUTE FUNCTION fts_refresh_parent_story_vector();

CREATE INDEX IF NOT EXISTS ix_story_search_vector_gin
  ON story USING GIN (search_vector);
