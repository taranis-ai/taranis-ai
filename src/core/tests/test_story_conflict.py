import pytest
from core.model.story_conflict import StoryConflict


class TestStoryConflictSorting:
    def test_stable_stringify_produces_consistent_results(self):
        """Test that the same data produces the same string regardless of input order."""
        # Test data with nested structures
        story_data_1 = {
            "title": "Test Story",
            "description": "A test story",
            "tags": [
                {"name": "zebra_tag", "tag_type": "PERSON"},
                {"name": "alpha_tag", "tag_type": "LOCATION"},
                {"name": "beta_tag", "tag_type": "ORGANIZATION"},
            ],
            "attributes": [
                {"key": "source", "value": "news_site_2"},
                {"key": "author", "value": "john_doe"},
                {"key": "category", "value": "politics"},
            ],
        }

        # Same data but different order
        story_data_2 = {
            "title": "Test Story",
            "description": "A test story",
            "tags": [
                {"name": "alpha_tag", "tag_type": "LOCATION"},
                {"name": "zebra_tag", "tag_type": "PERSON"},
                {"name": "beta_tag", "tag_type": "ORGANIZATION"},
            ],
            "attributes": [
                {"key": "category", "value": "fun"},
                {"key": "source", "value": "new_news"},
                {"key": "author", "value": "cute_dog"},
            ],
        }

        result_1 = StoryConflict.stable_stringify(story_data_1)
        result_2 = StoryConflict.stable_stringify(story_data_2)

        assert result_1 == result_2, "Same data with different order should produce identical strings"

    def test_fix_addresses_original_issue_521(self):
        """Integration test that verifies the fix addresses the original issue #521."""
        # Simulate the exact scenario described in issue #521
        original_story = {
            "title": "Breaking News Story",
            "description": "Important news",
            "tags": [
                {"name": "Politics", "tag_type": "CATEGORY"},
                {"name": "Europe", "tag_type": "LOCATION"},
                {"name": "John Smith", "tag_type": "PERSON"},
            ],
            "attributes": [{"key": "source", "value": "Reuters"}, {"key": "urgency", "value": "high"}, {"key": "verified", "value": "true"}],
        }

        updated_story = {
            "title": "Breaking News Story",
            "description": "Important news",
            "tags": [
                {"name": "John Smith", "tag_type": "PERSON"},
                {"name": "Politics", "tag_type": "CATEGORY"},
                {"name": "Europe", "tag_type": "LOCATION"},
            ],
            "attributes": [{"key": "verified", "value": "true"}, {"key": "source", "value": "Reuters"}, {"key": "urgency", "value": "high"}],
        }

        normalized_original, normalized_updated = StoryConflict.normalize_data(original_story, updated_story)

        assert (
            normalized_original == normalized_updated
        ), "Stories with same content but different order should normalize to identical strings"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
