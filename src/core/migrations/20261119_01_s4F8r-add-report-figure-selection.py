"""Keep the ordered selection of source images on its report."""

from yoyo import step


__depends__ = {"20261023_01_c4N8p-rename-default-topic-classifier"}

steps = [
    step(
        "ALTER TABLE report_item ADD COLUMN IF NOT EXISTS figure_selection JSONB NOT NULL DEFAULT '[]'",
        "ALTER TABLE report_item DROP COLUMN IF EXISTS figure_selection",
    ),
    step(
        "ALTER TABLE product ADD COLUMN IF NOT EXISTS figure_render_revision VARCHAR(64)",
        "ALTER TABLE product DROP COLUMN IF EXISTS figure_render_revision",
    ),
]
