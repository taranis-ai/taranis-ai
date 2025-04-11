"""
add cybersecurity column to story
"""

from yoyo import step

__depends__ = {"20250228_01_Pnb5c-refactor-organization"}

steps = [step("ALTER TABLE story ADD column cybersecurity VARCHAR(10);")]
