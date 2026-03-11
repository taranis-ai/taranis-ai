"""
Add revision column to story and report_item tables
"""

from yoyo import step


__depends__ = {"20251125_01_G4vgL-add-default-publisher-to-product"}
steps = [
    step(
        """
        ALTER TABLE story ADD COLUMN revision INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE report_item ADD COLUMN revision INTEGER NOT NULL DEFAULT 0;

        UPDATE story
        SET revision = COALESCE((
            SELECT MAX(story_revision.revision)
            FROM story_revision
            WHERE story_revision.story_id = story.id
        ), revision);

        UPDATE report_item
        SET revision = COALESCE((
            SELECT MAX(report_revision.revision)
            FROM report_revision
            WHERE report_revision.report_item_id = report_item.id
        ), revision);

        UPDATE story
        SET revision = -1
        WHERE revision = 0
          AND NOT EXISTS (
              SELECT 1
              FROM story_revision
              WHERE story_revision.story_id = story.id
          );

        UPDATE report_item
        SET revision = -1
        WHERE revision = 0
          AND NOT EXISTS (
              SELECT 1
              FROM report_revision
              WHERE report_revision.report_item_id = report_item.id
          );
        """,
        """
        ALTER TABLE report_item DROP COLUMN revision;
        ALTER TABLE story DROP COLUMN revision;
        """,
    ),
]
