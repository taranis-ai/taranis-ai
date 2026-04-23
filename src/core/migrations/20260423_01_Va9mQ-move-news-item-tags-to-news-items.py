"""
move news item tags to news items
"""

from yoyo import step


__depends__ = {"20260416_01_Q7vKp-add-task-worker-metadata"}


steps = [
    step(
        """
        ALTER TABLE news_item_tag
        ADD COLUMN IF NOT EXISTS news_item_id character varying;
        """,
        """
        ALTER TABLE news_item_tag
        DROP COLUMN IF EXISTS news_item_id;
        """,
    ),
    step(
        """
        INSERT INTO news_item_tag (name, tag_type, news_item_id)
        SELECT DISTINCT tag.name, tag.tag_type, news_item.id
        FROM news_item_tag tag
        JOIN news_item ON news_item.story_id = tag.story_id
        WHERE tag.news_item_id IS NULL
          AND tag.tag_type NOT ILIKE 'report_%';
        """,
        """
        """,
    ),
    step(
        """
        DELETE FROM story_news_item_attribute snia
        USING news_item_attribute attr
        WHERE attr.id = snia.news_item_attribute_id
          AND attr.key IN ('WORDLIST_BOT', 'IOC_BOT', 'NLP_BOT', 'TAGGING_BOT');

        DELETE FROM news_item_attribute attr
        WHERE attr.key IN ('WORDLIST_BOT', 'IOC_BOT', 'NLP_BOT', 'TAGGING_BOT')
          AND NOT EXISTS (
              SELECT 1 FROM story_news_item_attribute snia WHERE snia.news_item_attribute_id = attr.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM news_item_news_item_attribute ninia WHERE ninia.news_item_attribute_id = attr.id
          );
        """,
        """
        """,
    ),
    step(
        """
        ALTER TABLE news_item_tag
          DROP CONSTRAINT IF EXISTS news_item_tag_story_id_fkey;
        DELETE FROM news_item_tag WHERE news_item_id IS NULL;
        ALTER TABLE news_item_tag
          DROP COLUMN IF EXISTS story_id;
        ALTER TABLE news_item_tag
          ALTER COLUMN news_item_id SET NOT NULL;
        ALTER TABLE news_item_tag
          ADD CONSTRAINT news_item_tag_news_item_id_fkey
          FOREIGN KEY (news_item_id) REFERENCES news_item(id) ON DELETE CASCADE;

        CREATE INDEX IF NOT EXISTS ix_news_item_tag_news_item_id ON news_item_tag (news_item_id);
        CREATE INDEX IF NOT EXISTS ix_news_item_tag_name ON news_item_tag (name);
        CREATE INDEX IF NOT EXISTS ix_news_item_tag_tag_type ON news_item_tag (tag_type);
        """,
        """
        DROP INDEX IF EXISTS ix_news_item_tag_news_item_id;
        DROP INDEX IF EXISTS ix_news_item_tag_name;
        DROP INDEX IF EXISTS ix_news_item_tag_tag_type;
        ALTER TABLE news_item_tag
          DROP CONSTRAINT IF EXISTS news_item_tag_news_item_id_fkey;
        ALTER TABLE news_item_tag
          ADD COLUMN IF NOT EXISTS story_id character varying;
        UPDATE news_item_tag
        SET story_id = news_item.story_id
        FROM news_item
        WHERE news_item_tag.news_item_id = news_item.id;
        ALTER TABLE news_item_tag
          DROP COLUMN IF EXISTS news_item_id;
        ALTER TABLE news_item_tag
          ADD CONSTRAINT news_item_tag_story_id_fkey
          FOREIGN KEY (story_id) REFERENCES story(id) ON DELETE CASCADE;
        """,
    ),
]
