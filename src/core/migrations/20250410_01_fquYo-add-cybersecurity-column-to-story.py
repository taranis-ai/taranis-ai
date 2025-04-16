"""
add cybersecurity column to story
"""

from yoyo import step

__depends__ = {"20250324_02_vL3hN-add-last-change-column"}

steps = [step("ALTER TABLE story ADD column cybersecurity VARCHAR(10);")]
