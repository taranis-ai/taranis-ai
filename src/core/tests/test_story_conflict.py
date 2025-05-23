import pytest
from core.model.story_conflict import StoryConflict


class TestStoryConflictSorting:
    def test_stable_stringify_produces_consistent_results(self):
        """Test that the same data produces the same string regardless of input order."""
        # Test data with nested structures
        story_data_1 = {
            "title": "Test Story",
            "description": "A test story",
            "tags": {"zebra_tag": "PERSON", "alpha_tag": "LOCATION", "beta_tag": "ORGANIZATION"},
            "attributes": {"source": "news_site_2", "author": "john_doe", "category": "politics"},
        }

        # Same data but keys in different order
        story_data_2 = {
            "title": "Test Story",
            "description": "A test story",
            "tags": {"alpha_tag": "LOCATION", "zebra_tag": "PERSON", "beta_tag": "ORGANIZATION"},
            "attributes": {"category": "politics", "source": "news_site_2", "author": "john_doe"},
        }

        result_1 = StoryConflict.stable_stringify(story_data_1)
        result_2 = StoryConflict.stable_stringify(story_data_2)

        assert result_1 == result_2, "Same data with different order should produce identical strings"

    def test_fix_addresses_original_issue_521(self):
        """Integration test that verifies the fix addresses the original issue #521."""
        original_story = {
            "title": "Breaking News Story",
            "description": "Important news",
            "tags": {"Politics": "CATEGORY", "Europe": "LOCATION", "John Smith": "PERSON"},
            "attributes": {"source": "Reuters", "urgency": "high", "verified": "true"},
        }

        updated_story = {
            "title": "Breaking News Story",
            "description": "Important news",
            "tags": {"John Smith": "PERSON", "Politics": "CATEGORY", "Europe": "LOCATION"},
            "attributes": {"verified": "true", "source": "Reuters", "urgency": "high"},
        }

        normalized_original, normalized_updated = StoryConflict.normalize_data(original_story, updated_story)

        assert (
            normalized_original == normalized_updated
        ), "Stories with same content but different order should normalize to identical strings"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
