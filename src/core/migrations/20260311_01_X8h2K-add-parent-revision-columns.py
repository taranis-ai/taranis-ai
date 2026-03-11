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
        SET revision = revision_data.max_revision
        FROM (
            SELECT story_id, MAX(revision) AS max_revision
            FROM story_revision
            GROUP BY story_id
        ) AS revision_data
        WHERE story.id = revision_data.story_id;

        UPDATE report_item
        SET revision = revision_data.max_revision
        FROM (
            SELECT report_item_id, MAX(revision) AS max_revision
            FROM report_revision
            GROUP BY report_item_id
        ) AS revision_data
        WHERE report_item.id = revision_data.report_item_id;
        """,
        """
        ALTER TABLE report_item DROP COLUMN revision;
        ALTER TABLE story DROP COLUMN revision;
        """,
    )
]
