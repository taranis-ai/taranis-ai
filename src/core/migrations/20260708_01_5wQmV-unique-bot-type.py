"""
unique bot type
"""

from yoyo import step


__depends__ = {"20260611_01_w4R9m-purge-task-history"}

steps = [
    step(
        """
        WITH ranked_bots AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY type
                    ORDER BY
                        CASE
                            WHEN type = 'WORDLIST_BOT' AND name = 'Wordlist Bot' THEN 0
                            WHEN type = 'IOC_BOT' AND name = 'IOC Bot' THEN 0
                            WHEN type = 'INTEL_OWL_BOT' AND name = 'IntelOwl Bot' THEN 0
                            WHEN type = 'NLP_BOT' AND name = 'NLP Tagging Bot' THEN 0
                            WHEN type = 'STORY_BOT' AND name = 'Story Bot' THEN 0
                            WHEN type = 'SENTIMENT_ANALYSIS_BOT' AND name = 'Sentiment Analysis Bot' THEN 0
                            WHEN type = 'SUMMARY_BOT' AND name = 'Summary Bot' THEN 0
                            WHEN type = 'CYBERSEC_CLASSIFIER_BOT' AND name = 'Cybersecurity Classifier Bot' THEN 0
                            ELSE 1
                        END,
                        "index",
                        id
                ) AS bot_rank
            FROM bot
        )
        DELETE FROM bot_parameter_value
        WHERE bot_id IN (SELECT id FROM ranked_bots WHERE bot_rank > 1);

        WITH ranked_bots AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY type
                    ORDER BY
                        CASE
                            WHEN type = 'WORDLIST_BOT' AND name = 'Wordlist Bot' THEN 0
                            WHEN type = 'IOC_BOT' AND name = 'IOC Bot' THEN 0
                            WHEN type = 'INTEL_OWL_BOT' AND name = 'IntelOwl Bot' THEN 0
                            WHEN type = 'NLP_BOT' AND name = 'NLP Tagging Bot' THEN 0
                            WHEN type = 'STORY_BOT' AND name = 'Story Bot' THEN 0
                            WHEN type = 'SENTIMENT_ANALYSIS_BOT' AND name = 'Sentiment Analysis Bot' THEN 0
                            WHEN type = 'SUMMARY_BOT' AND name = 'Summary Bot' THEN 0
                            WHEN type = 'CYBERSEC_CLASSIFIER_BOT' AND name = 'Cybersecurity Classifier Bot' THEN 0
                            ELSE 1
                        END,
                        "index",
                        id
                ) AS bot_rank
            FROM bot
        )
        DELETE FROM bot
        WHERE id IN (SELECT id FROM ranked_bots WHERE bot_rank > 1);

        ALTER TABLE bot
            ADD CONSTRAINT bot_type_key UNIQUE (type);
        """,
        """
        ALTER TABLE bot
            DROP CONSTRAINT IF EXISTS bot_type_key;
        """,
    )
]
