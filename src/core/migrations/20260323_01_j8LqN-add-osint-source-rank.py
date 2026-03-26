"""
add osint source rank
"""

from yoyo import step


__depends__ = {"20260321_01_h17Zo-bot-disable-toggle"}

steps = [
    step(
        """
    ALTER TABLE osint_source
    ADD COLUMN IF NOT EXISTS rank integer NOT NULL DEFAULT 0;
    """,
        """
    ALTER TABLE osint_source
    DROP COLUMN IF EXISTS rank;
    """,
    )
]
