"""
story news item FK
"""

from yoyo import step

__depends__ = {"20250423_01_fpBWs-migrate-tlp"}

steps = [
    step("""
        ALTER TABLE story_news_item_attribute
          DROP CONSTRAINT IF EXISTS story_news_item_attribute_story_id_fkey;
        DELETE FROM story_news_item_attribute WHERE story_id IS NULL;
        ALTER TABLE story_news_item_attribute ADD CONSTRAINT story_news_item_attribute_story_id_fkey
          FOREIGN KEY (story_id) REFERENCES story(id) ON DELETE CASCADE;
     """)
]
