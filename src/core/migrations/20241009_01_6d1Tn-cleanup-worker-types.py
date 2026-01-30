"""
cleanup worker types
"""

from yoyo import step

__depends__ = {"20240909_01_D8TvE-on-delete-cascade-on-report-item-story"}

steps = [step("DELETE FROM worker WHERE type IN ('WEB_COLLECTOR', 'SELENIUM_WEB_COLLECTOR');")]
