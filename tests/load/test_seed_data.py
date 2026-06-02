from __future__ import annotations

import unittest

from testsupport.load_testing.seed_data import (
    build_report_type_titles,
    build_source_ids,
    load_story_seed_payloads,
)


class SeedDataTest(unittest.TestCase):
    def test_build_source_ids_keeps_first_value_and_expands_numeric_ids(self) -> None:
        self.assertEqual(build_source_ids("99", 3), ["99", "100", "101"])

    def test_build_report_type_titles_preserves_first_title(self) -> None:
        self.assertEqual(
            build_report_type_titles("Load Testing Report Type", 3),
            [
                "Load Testing Report Type",
                "Load Testing Report Type 2",
                "Load Testing Report Type 3",
            ],
        )

    def test_load_story_seed_payloads_can_expand_beyond_fixture_size(self) -> None:
        stories = load_story_seed_payloads(["99", "100"], limit=120)

        self.assertEqual(len(stories), 120)
        self.assertEqual({story["news_items"][0]["osint_source_id"] for story in stories[:4]}, {"99", "100"})

        story_ids = [story["id"] for story in stories]
        self.assertEqual(len(set(story_ids)), len(story_ids))

        news_item_ids = [story["news_items"][0]["id"] for story in stories]
        self.assertEqual(len(set(news_item_ids)), len(news_item_ids))

        self.assertTrue(all(story["created"] for story in stories))


if __name__ == "__main__":
    unittest.main()
