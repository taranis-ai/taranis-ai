"""
unique bot type
"""

from yoyo import step


__depends__ = {"20260611_01_w4R9m-purge-task-history"}

steps = [
    step(
        """
        ALTER TABLE bot
            ADD CONSTRAINT bot_type_key UNIQUE (type);
        """,
        """
        ALTER TABLE bot
            DROP CONSTRAINT IF EXISTS bot_type_key;
        """,
    )
]
