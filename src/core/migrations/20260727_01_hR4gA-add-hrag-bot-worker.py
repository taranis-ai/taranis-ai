"""
add HRAG bot worker type
"""

from yoyo import step

__depends__ = {"20260710_01_m3P7q-add-product-last-published-url"}

steps = [
    step("ALTER TYPE worker_types ADD VALUE IF NOT EXISTS 'HRAG_BOT';"),
    step("ALTER TYPE bot_types ADD VALUE IF NOT EXISTS 'HRAG_BOT';"),
]
