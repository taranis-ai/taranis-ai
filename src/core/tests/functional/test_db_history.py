import logging

# Create a simple test logger that doesn't trigger Config loading
test_logger = logging.getLogger(__name__)
test_logger.setLevel(logging.DEBUG)


class TestDbHistory:
    def test_story_history(self, session, full_story):  # assumes a fixture that gives a working session
        from core.model.story import Story

        StoryHistory = Story.__history_mapper__.class_

        story: dict = full_story[0]

        story_tuple = Story.add(story)
        # Story version 1 created
        assert session.query(StoryHistory).filter(StoryHistory.version == 1).count() == 1
        assert session.query(StoryHistory).filter(StoryHistory.version == 1).first().title == "Test Aggregate"

        test_logger.debug(f"Story added with tuple: {story_tuple}")
        title_updated = {"title": "Second title"}
        Story.update(story.get("id"), title_updated)
        # import pdb

        # pdb.set_trace()
        current = Story.get(story.get("id", ""))

        assert current.title == "Second title"
        assert session.query(StoryHistory).filter_by(version=2).first().title == "Second title", "Title should be updated in history"
        # Story version 2 created

        test_logger.debug(f"StoryHistory class: {StoryHistory.__dict__=}")
        assert session.query(StoryHistory).filter(StoryHistory.version == 2).count() == 1
        assert session.query(StoryHistory).filter(StoryHistory.version == 2).first().title == "Second title"

    def test_story_multiple_updates_history(self, session, full_story):
        """Test that multiple story updates create correct version history with incremental version numbers"""
        from core.model.story import Story

        StoryHistory = Story.__history_mapper__.class_

        story: dict = full_story[0]

        # Initial story creation
        story_tuple = Story.add(story)
        test_logger.debug(f"Story added with tuple: {story_tuple}")

        # Extract story_id from the response tuple
        story_response, status_code = story_tuple
        story_id = story_response.get("story_id", "") if isinstance(story_response, dict) else story.get("id", "")
        test_logger.debug(f"Using story_id: {story_id}")

        # First update - should create version 1 in history
        first_update = {"title": "First Update Title", "description": "First update description"}
        Story.update(story_id, first_update)
        test_logger.debug("Applied first update")
        import pdb

        pdb.set_trace()
        assert session.query(StoryHistory).filter(StoryHistory.version == 2).count() == 2
        assert session.query(StoryHistory).filter(StoryHistory.version == 2).first().title == "First Update Title"

        # Second update - should create version 2 in history
        second_update = {"title": "Second Update Title", "description": "Second update description"}
        Story.update(story_id, second_update)
        test_logger.debug("Applied second update")

        # Third update - should create version 3 in history
        third_update = {"title": "Third Update Title", "description": "Third update description"}
        Story.update(story_id, third_update)
        test_logger.debug("Applied third update")

        # Verify history table entries
        StoryHistory = Story.__history_mapper__.class_

        # After our fix, should have only 4 history entries (1 from creation + 3 from updates)
        total_history_count = session.query(StoryHistory).filter(StoryHistory.id == story_id).count()
        test_logger.debug(f"Total history entries: {total_history_count}")

        # Debug: Let's see what's actually in the history table
        all_history = session.query(StoryHistory).filter(StoryHistory.id == story_id).order_by(StoryHistory.version).all()
        for i, history_entry in enumerate(all_history):
            test_logger.debug(
                f"History entry {i + 1}: version={history_entry.version}, title='{history_entry.title}', description='{history_entry.description}'"
            )

        assert total_history_count == 4, f"Expected 4 history entries, got {total_history_count}"

        # Check version 1 (original state)
        version_1 = session.query(StoryHistory).filter(StoryHistory.id == story_id, StoryHistory.version == 1).first()
        assert version_1 is not None, "Version 1 history entry should exist"
        assert version_1.title == "Test Aggregate", f"Version 1 should have original title, got {version_1.title}"
        test_logger.debug(f"Version 1: title='{version_1.title}', description='{version_1.description}'")

        # After our fix, version 2 should have first update (not duplicate)
        version_2 = session.query(StoryHistory).filter(StoryHistory.id == story_id, StoryHistory.version == 2).first()
        assert version_2 is not None, "Version 2 history entry should exist"
        assert version_2.title == "First Update Title", f"Version 2 should have first update title, got {version_2.title}"
        test_logger.debug(f"Version 2: title='{version_2.title}', description='{version_2.description}'")

        # Check version 3 (should have second update)
        version_3 = session.query(StoryHistory).filter(StoryHistory.id == story_id, StoryHistory.version == 3).first()
        assert version_3 is not None, "Version 3 history entry should exist"
        assert version_3.title == "Second Update Title", f"Version 3 should have second update title, got {version_3.title}"
        test_logger.debug(f"Version 3: title='{version_3.title}', description='{version_3.description}'")

        # Check version 4 (should have third update)
        version_4 = session.query(StoryHistory).filter(StoryHistory.id == story_id, StoryHistory.version == 4).first()
        assert version_4 is not None, "Version 4 history entry should exist"
        assert version_4.title == "Third Update Title", f"Version 4 should have third update title, got {version_4.title}"
        test_logger.debug(f"Version 4: title='{version_4.title}', description='{version_4.description}'")

        # Verify current story state (should have the latest changes)
        current_story = Story.get(story_id)
        assert current_story is not None, "Current story should exist"
        test_logger.debug(f"Current story: title='{current_story.title}', description='{current_story.description}'")

        # The current story should have the third update
        assert current_story.title == "Third Update Title", f"Current story should have third update title, got {current_story.title}"

        test_logger.debug("✅ All version history checks passed!")

    def test_story_attribute_update_history(self, session, full_story):
        """Test that story attribute updates don't create duplicate history entries due to multiple commits"""
        from core.model.story import Story

        story: dict = full_story[0]

        # Initial story creation
        story_tuple = Story.add(story)
        test_logger.debug(f"Story added with tuple: {story_tuple}")

        # Extract story_id from the response tuple
        story_response, status_code = story_tuple
        story_id = story_response.get("story_id") if isinstance(story_response, dict) else story.get("id")
        test_logger.debug(f"Using story_id: {story_id}")

        # Update story with attributes - this should only create ONE history entry
        attributes_update = {"attributes": [{"key": "cybersecurity", "value": "yes"}, {"key": "sentiment", "value": "positive"}]}
        Story.update(story_id, attributes_update)
        test_logger.debug("Applied attributes update")

        # Verify history table entries
        StoryHistory = Story.__history_mapper__.class_

        # Let's see what's in the history table after attribute update
        all_history = session.query(StoryHistory).filter(StoryHistory.id == story_id).order_by(StoryHistory.version).all()
        test_logger.debug(f"Total history entries after attribute update: {len(all_history)}")

        for i, history_entry in enumerate(all_history):
            test_logger.debug(
                f"History entry {i + 1}: version={history_entry.version}, title='{history_entry.title}', description='{history_entry.description}'"
            )

        # After our transaction fix, should have exactly 2 entries: 1 from creation + 1 from update
        assert len(all_history) == 2, f"Expected 2 history entries, got {len(all_history)}"

        test_logger.debug("✅ Attribute update test completed - single transaction confirmed!")

    def test_single_transaction_behavior(self, session, full_story):
        """Test that Story.add and Story.update create only single history entries per operation after transaction fix"""
        from core.model.story import Story

        story: dict = full_story[0]

        # Initial story creation - should create only ONE history entry
        story_tuple = Story.add(story)
        test_logger.debug(f"Story added with tuple: {story_tuple}")

        # Extract story_id from the response tuple
        story_response, status_code = story_tuple
        story_id = story_response.get("story_id") if isinstance(story_response, dict) else story.get("id")
        test_logger.debug(f"Using story_id: {story_id}")

        # Check history after creation
        StoryHistory = Story.__history_mapper__.class_
        creation_history_count = session.query(StoryHistory).filter(StoryHistory.id == story_id).count()
        test_logger.debug(f"History entries after creation: {creation_history_count}")

        # After our transaction fix, creation should create only 1 history entry (not 2)
        assert creation_history_count == 1, f"Expected 1 history entry after creation, got {creation_history_count}"

        # Update with multiple attributes - should create only ONE additional history entry
        complex_update = {
            "title": "Updated Title",
            "description": "Updated description",
            "attributes": [
                {"key": "cybersecurity", "value": "yes"},
                {"key": "sentiment", "value": "positive"},
                {"key": "tlp", "value": "amber"},
            ],
        }
        Story.update(story_id, complex_update)
        test_logger.debug("Applied complex update with multiple attributes")

        # Check total history count after update
        total_history_count = session.query(StoryHistory).filter(StoryHistory.id == story_id).count()
        test_logger.debug(f"Total history entries after update: {total_history_count}")

        # Debug: Let's see what's actually in the history table
        all_history = session.query(StoryHistory).filter(StoryHistory.id == story_id).order_by(StoryHistory.version).all()
        for i, history_entry in enumerate(all_history):
            test_logger.debug(
                f"History entry {i + 1}: version={history_entry.version}, title='{history_entry.title}', description='{history_entry.description}'"
            )

        # After our transaction fix, should have exactly 2 entries: 1 from creation + 1 from update
        assert total_history_count == 2, f"Expected 2 history entries total, got {total_history_count}"

        # Verify the history entries have correct version numbers
        versions = [h.version for h in all_history]
        assert versions == [1, 2], f"Expected versions [1, 2], got {versions}"

        # Verify version 1 has original title
        version_1 = all_history[0]
        assert version_1.title == "Test Aggregate", f"Version 1 should have original title, got {version_1.title}"

        # Verify version 2 has updated title
        version_2 = all_history[1]
        assert version_2.title == "Updated Title", f"Version 2 should have updated title, got {version_2.title}"

        # Verify current story state
        current_story = Story.get(story_id)
        assert current_story.title == "Updated Title", f"Current story should have updated title, got {current_story.title}"

        test_logger.debug("✅ Single transaction behavior verified - no duplicate history entries!")
