"""
add links to stories
"""

from yoyo import step

__depends__ = {"20240724_01_BSqvf-fix-product-report-item-constraints"}

steps = [step("ALTER TABLE story ADD COLUMN links JSON DEFAULT '[]'::json;")]
