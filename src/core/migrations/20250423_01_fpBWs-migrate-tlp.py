"""
migrate tlp
"""

from yoyo import step

__depends__ = {"20250411_01_qSHFw-add-connector-permissions"}

steps = [
    step("""
         ALTER TABLE report_item_story
          DROP CONSTRAINT IF EXISTS report_item_story_story_id_fkey;
        DELETE FROM report_item_story WHERE story_id IS NULL;
        ALTER TABLE report_item_story ADD CONSTRAINT report_item_story_story_id_fkey
          FOREIGN KEY (story_id) REFERENCES story(id) ON DELETE CASCADE;

        ALTER TABLE role ALTER COLUMN tlp_level SET DEFAULT 'CLEAR';
        UPDATE role SET tlp_level = 'RED' WHERE tlp_level IS NULL AND name = 'admin';
        UPDATE role SET tlp_level = 'CLEAR' WHERE tlp_level IS NULL;
        ALTER TABLE role ALTER COLUMN tlp_level SET NOT NULL;
    """)
]
