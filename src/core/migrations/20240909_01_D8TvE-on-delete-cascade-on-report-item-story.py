"""
on delete cascade on report_item_story
"""

from yoyo import step

__depends__ = {"20240821_01_txQiJ-add-links-to-stories"}

steps = [
    step("""
        ALTER TABLE report_item_story DROP CONSTRAINT IF EXISTS report_item_story_story_id_fkey;
        ALTER TABLE report_item_story ADD  CONSTRAINT           report_item_story_story_id_fkey
          FOREIGN KEY (story_id) REFERENCES story(id) ON DELETE CASCADE;
    """)
]
