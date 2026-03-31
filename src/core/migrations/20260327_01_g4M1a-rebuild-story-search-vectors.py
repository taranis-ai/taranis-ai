"""
rebuild story search vectors
"""

from yoyo import step


__depends__ = {"20260326_01_r8PqL-story-relevance-redesign"}

steps = [
    step(
        """
        UPDATE story AS s
        SET search_vector = fts_build_story_search_vector(s.id::text);
        """
    )
]
