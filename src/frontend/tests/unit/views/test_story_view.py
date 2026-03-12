from frontend.views.story_views import _calculate_story_diff


def test_calculate_story_diff_ignores_empty_tag_changes():
    from_data = {
        "title": "Story title",
        "tags": [{"name": None}],
    }
    to_data = {
        "title": "Story title",
        "tags": [{"name": ""}, {"name": "   "}],
    }

    changes = _calculate_story_diff(from_data, to_data)

    assert changes == []


def test_calculate_story_diff_keeps_real_tag_changes():
    from_data = {
        "title": "Story title",
        "tags": [{"name": None}, {"name": "existing"}],
    }
    to_data = {
        "title": "Story title",
        "tags": [{"name": ""}, {"name": "existing"}, {"name": "new-tag"}],
    }

    changes = _calculate_story_diff(from_data, to_data)

    assert {"field": "Tags Added", "old_value": None, "new_value": "new-tag"} in changes


def test_calculate_story_diff_uses_inline_markup_for_text_changes():
    from_data = {"title": "Kill Chain im Krieg verkurzt"}
    to_data = {"title": "Kill Chain im Krieg deutlich verkurzt"}

    changes = _calculate_story_diff(from_data, to_data)

    assert len(changes) == 1
    assert changes[0]["field"] == "Title"
    assert changes[0]["inline_diff"] is True
    assert "bg-success/20" in str(changes[0]["new_value_diff"])
    assert "deutlich " in str(changes[0]["new_value_diff"])
    assert "deutlich " not in str(changes[0]["old_value_diff"])


def test_calculate_story_diff_escapes_inline_markup_text():
    from_data = {"title": "A <script>alert(1)</script> title"}
    to_data = {"title": "A <script>alert(1)</script> new title"}

    changes = _calculate_story_diff(from_data, to_data)

    assert len(changes) == 1
    assert "&lt;script&gt;" in str(changes[0]["new_value_diff"])
    assert "<script>" not in str(changes[0]["new_value_diff"])
