"""
migrate search_vector
"""

from yoyo import step

__depends__ = {"20251010_01_OQVEW-migrate-story-links"}

steps = [
    step(
        """
      DROP TABLE IF EXISTS story_search_index;
      """,
        """
      CREATE TABLE story_search_index (
          id SERIAL PRIMARY KEY,
          story_id INTEGER NOT NULL REFERENCES story(id) ON DELETE CASCADE,
          content TEXT NOT NULL
      );""",
    ),
    step("""
      ALTER TABLE news_item_tag
        DROP CONSTRAINT news_item_tag_story_id_fkey;
      ALTER TABLE news_item_tag
        ADD CONSTRAINT news_item_tag_story_id_fkey
        FOREIGN KEY (story_id) REFERENCES story(id) ON DELETE CASCADE;
      """),
    step(
        """
        ALTER TABLE story
        ADD COLUMN IF NOT EXISTS search_vector tsvector NOT NULL DEFAULT ''::tsvector;
        """,
        """
        ALTER TABLE story
        DROP COLUMN IF EXISTS search_vector;
        """,
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS ix_story_search_vector_gin
        ON story USING GIN (search_vector);
        """,
        """
        DROP INDEX IF EXISTS ix_story_search_vector_gin;
        """,
    ),
]
