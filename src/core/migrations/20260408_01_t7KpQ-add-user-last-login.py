"""
add user last_login
"""

from yoyo import step

__depends__ = {"20260327_01_g4M1a-rebuild-story-search-vectors"}

steps = [
    step(
        """
        ALTER TABLE "user"
        ADD COLUMN last_login TIMESTAMP NULL;
        """,
        """
        ALTER TABLE "user"
        DROP COLUMN IF EXISTS last_login;
        """,
    )
]
