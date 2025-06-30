"""
add_ppn_collector
"""

from yoyo import step

__depends__ = {"20250424_01_cLXiI-story-news-item-fk"}

steps = [step("ALTER TYPE worker_types ADD VALUE IF NOT EXISTS 'PPN_COLLECTOR';")]
