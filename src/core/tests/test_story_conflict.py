import pytest
from core.model.story_conflict import StoryConflict


@pytest.fixture
def story_data_1():
    return {
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


@pytest.fixture
def story_data_2():
    return {
        "title": "Test Story",
        "description": "A test story",
        "tags": [
            {"name": "alpha_tag", "tag_type": "LOCATION"},
            {"name": "zebra_tag", "tag_type": "PERSON"},
            {"name": "beta_tag", "tag_type": "ORGANIZATION"},
        ],
        "attributes": [
            {"key": "category", "value": "politics"},
            {"key": "source", "value": "news_site_2"},
            {"key": "author", "value": "john_doe"},
        ],
    }


@pytest.fixture
def original_story():
    return {
        "title": "Breaking News Story",
        "description": "Important news",
        "tags": [
            {"name": "Politics", "tag_type": "CATEGORY"},
            {"name": "Europe", "tag_type": "LOCATION"},
            {"name": "John Smith", "tag_type": "PERSON"},
        ],
        "attributes": [
            {"key": "source", "value": "Reuters"},
            {"key": "urgency", "value": "high"},
            {"key": "verified", "value": "true"},
        ],
    }


@pytest.fixture
def updated_story():
    return {
        "title": "Breaking News Story",
        "description": "Important news",
        "tags": [
            {"name": "John Smith", "tag_type": "PERSON"},
            {"name": "Politics", "tag_type": "CATEGORY"},
            {"name": "Europe", "tag_type": "LOCATION"},
        ],
        "attributes": [
            {"key": "verified", "value": "true"},
            {"key": "source", "value": "Reuters"},
            {"key": "urgency", "value": "high"},
        ],
    }


class TestStoryConflictSorting:
    def test_stable_stringify_handles_different_tag_order(self, sample_story_data_1, sample_story_data_2):
        result_1 = StoryConflict.stable_stringify(story_data_1)
        result_2 = StoryConflict.stable_stringify(story_data_2)

        assert result_1 == result_2, "Same data with different order should produce identical strings"

    def test_normalize_data_handles_different_ordering(self, original_story, updated_story):
        normalized_original, normalized_updated = StoryConflict.normalize_data(original_story, updated_story)

        assert (
            normalized_original == normalized_updated
        ), "Stories with same content but different order should normalize to identical strings"
