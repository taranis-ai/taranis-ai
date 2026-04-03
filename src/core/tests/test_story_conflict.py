import pytest

from core.model.story_conflict import StoryConflict


@pytest.fixture
def story_data_1():
    return {
        "title": "Test Story",
        "description": "A test story",
        "tags": {
            "zebra_tag": {"name": "zebra_tag", "tag_type": "PERSON"},
            "alpha_tag": {"name": "alpha_tag", "tag_type": "LOCATION"},
            "beta_tag": {"name": "beta_tag", "tag_type": "ORGANIZATION"},
        },
        "attributes": {
            "source": {"key": "source", "value": "news_site_2"},
            "author": {"key": "author", "value": "john_doe"},
            "category": {"key": "category", "value": "politics"},
        },
    }


@pytest.fixture
def story_data_2():
    return {
        "title": "Test Story",
        "description": "A test story",
        "tags": {
            "alpha_tag": {"name": "alpha_tag", "tag_type": "LOCATION"},
            "zebra_tag": {"name": "zebra_tag", "tag_type": "PERSON"},
            "beta_tag": {"name": "beta_tag", "tag_type": "ORGANIZATION"},
        },
        "attributes": {
            "category": {"key": "category", "value": "politics"},
            "source": {"key": "source", "value": "news_site_2"},
            "author": {"key": "author", "value": "john_doe"},
        },
    }


@pytest.fixture
def original_story():
    return {
        "title": "Breaking News Story",
        "description": "Important news",
        "tags": {
            "Politics": {"name": "Politics", "tag_type": "CATEGORY"},
            "Europe": {"name": "Europe", "tag_type": "LOCATION"},
            "John Smith": {"name": "John Smith", "tag_type": "PERSON"},
        },
        "attributes": {
            "source": {"key": "source", "value": "Reuters"},
            "urgency": {"key": "urgency", "value": "high"},
            "verified": {"key": "verified", "value": "true"},
        },
    }


@pytest.fixture
def updated_story():
    return {
        "title": "Breaking News Story",
        "description": "Important news",
        "tags": {
            "John Smith": {"name": "John Smith", "tag_type": "PERSON"},
            "Politics": {"name": "Politics", "tag_type": "CATEGORY"},
            "Europe": {"name": "Europe", "tag_type": "LOCATION"},
        },
        "attributes": {
            "verified": {"key": "verified", "value": "true"},
            "source": {"key": "source", "value": "Reuters"},
            "urgency": {"key": "urgency", "value": "high"},
        },
    }


class TestStoryConflictSorting:
    def test_stable_stringify_handles_different_tag_order(self, story_data_1, story_data_2):
        result_1 = StoryConflict.stable_stringify(story_data_1)
        result_2 = StoryConflict.stable_stringify(story_data_2)

        assert result_1 == result_2, "Same data with different order should produce identical strings"

    def test_normalize_data_handles_different_ordering(self, original_story, updated_story):
        normalized_original, normalized_updated = StoryConflict.normalize_data(original_story, updated_story)

        assert normalized_original == normalized_updated, (
            "Stories with same content but different order should normalize to identical strings"
        )
