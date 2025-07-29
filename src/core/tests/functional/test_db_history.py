# from core.log import logger


# class TestDbHistory:
#     def test_story_history(self, session, full_story):  # assumes a fixture that gives a working session
#         from core.model.story import Story

#         story: dict = full_story[0]

#         story_tuple = Story.add(story)
#         # logger.debug(f"Story added with tuple: {story_tuple}")
#         title_updated = {"title": "Second title"}
#         # Story.update(story.get("id"), title_updated)

#         # StoryHistory = Story.__history_mapper__.class_
#         # logger.debug(f"StoryHistory class: {StoryHistory.__dict__=}")
#         # Should have one historical row with old title
#         # assert session.query(StoryHistory).filter(StoryHistory.version == 1).all() == [StoryHistory(version=1, title="First title")]
#         # assert session.query(StoryHistory).filter(StoryHistory.version == 1).count() == 1
#         # assert session.query(StoryHistory).filter(StoryHistory.version == 1).first().title == "Test Aggregate"

#         # Should NOT create a history row for the current state
#         current = Story.get(story.get("id", ""))
#         assert current.title == "Second title"
