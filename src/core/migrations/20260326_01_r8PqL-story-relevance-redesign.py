"""
Redesign story relevance into source, feedback, and override components
"""

from yoyo import step


__depends__ = {"20260323_01_j8LqN-add-osint-source-rank"}

steps = [
    step(
        """
        ALTER TABLE story
        ADD COLUMN IF NOT EXISTS relevance_override INTEGER NOT NULL DEFAULT 0;

        UPDATE story
        SET relevance = COALESCE((
                SELECT MAX(osint_source.rank)
                FROM news_item
                LEFT JOIN osint_source ON osint_source.id = news_item.osint_source_id
                WHERE news_item.story_id = story.id
            ), 0)
            + COALESCE(likes, 0)
            - COALESCE(dislikes, 0)
            + CASE WHEN important IS TRUE THEN 3 ELSE 0 END
            + CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM report_item_story
                    WHERE report_item_story.story_id = story.id
                ) THEN 3
                ELSE 0
              END
            + COALESCE(relevance_override, 0);

        DELETE FROM news_item_vote
        WHERE NOT EXISTS (
            SELECT 1
            FROM story
            WHERE story.id = news_item_vote.item_id
        );
        """,
        """
        ALTER TABLE story
        DROP COLUMN IF EXISTS relevance_override;
        """,
    )
]
