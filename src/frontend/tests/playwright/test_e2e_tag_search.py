#!/usr/bin/env python3
import re
from urllib.parse import parse_qs, urlparse

import pytest
from flask import url_for
from playwright.sync_api import Page, expect


@pytest.mark.e2e_tag_search
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestEndToEndWorkflowTagSearch:
    """E2E workflow: open a trending tag, verify tags on three stories, mark important, then cluster them."""

    def _login_as_user(self, page: Page) -> None:
        """Authenticate as a regular user and confirm dashboard is visible."""
        page.goto(url_for("base.login", _external=True))
        expect(page).to_have_title("Taranis AI", timeout=5000)
        page.get_by_placeholder("Username").fill("user")
        page.get_by_placeholder("Password").fill("test")
        page.get_by_test_id("login-button").click()
        expect(page.locator("#dashboard")).to_be_visible()

    def _choose_trending_tag(self, page: Page) -> str:
        """Open dashboard and click the explicit trending tag used by this scenario (`espionage`)."""
        page.goto(url_for("base.dashboard", _external=True))
        expect(page.locator("#dashboard")).to_contain_text("Trending Tags (last")

        espionage_link = page.locator("#dashboard a[href*='/assess?tags=']").filter(has_text="espionage").first
        expect(espionage_link).to_be_visible(timeout=30000)
        espionage_link.click()
        return "espionage"

    def _build_story_title_to_tags_map(self, story_list_enriched: list[dict]) -> dict[str, list[str]]:
        """Build expected-tag lookup keyed by both raw and 'Story: ' stripped titles."""
        story_title_to_tags: dict[str, list[str]] = {}
        for story in story_list_enriched:
            title = story.get("title", "")
            tags = list((story.get("tags") or {}).keys())
            if title:
                story_title_to_tags[title] = tags
                story_title_to_tags[title.replace("Story: ", "", 1)] = tags
        return story_title_to_tags

    def _expand_verify_and_mark_important(
        self,
        page: Page,
        story_card,
        story_title_to_tags: dict[str, list[str]],
    ) -> str:
        """Expand one story card, verify all expected tags are rendered, then mark it as important."""
        story_id = story_card.get_attribute("data-story-id")
        assert story_id is not None

        story_title = story_card.get_by_test_id("story-title").inner_text().strip()
        expected_tags = story_title_to_tags.get(story_title)
        assert expected_tags, f"No expected tags found for story title: {story_title}"

        story_card.get_by_test_id("toggle-summary").click()
        tag_badges = story_card.locator("a.badge.badge-ghost.badge-xs > span")
        expect(tag_badges.first).to_be_visible()

        visible_tags = {tag.strip() for tag in tag_badges.all_inner_texts() if tag.strip()}
        missing_tags = set(expected_tags) - visible_tags
        assert not missing_tags, f"Missing tags for story '{story_title}': {sorted(missing_tags)}"

        story_card.get_by_test_id("story-actions-menu").click()
        story_card.get_by_test_id("toggle-important").click()

        updated_story_card = page.get_by_test_id(f"story-card-{story_id}")
        expect(updated_story_card.locator("span.badge-warning").filter(has_text="Important")).to_be_visible()
        return story_id

    def _mark_first_three_visible_stories_important(
        self,
        page: Page,
        story_title_to_tags: dict[str, list[str]],
    ) -> list[str]:
        """Process three stories in sequence (with scroll), verify tags, and mark each important."""
        important_story_ids: list[str] = []

        for index in range(3):
            if index > 0:
                page.mouse.wheel(0, 600 if index == 1 else 900)

            story_card = page.locator("#story-list article").nth(index)
            expect(story_card).to_be_visible()
            story_id = self._expand_verify_and_mark_important(page, story_card, story_title_to_tags)
            important_story_ids.append(story_id)

        return important_story_ids

    def _filter_important_and_cluster(self, page: Page, important_story_ids: list[str]) -> None:
        """Filter to important stories, confirm the three selected are present, then cluster them."""
        page.get_by_label("Important").select_option("true")
        selected_tags = page.locator("#story-list article[data-story-important='true']")
        expect(selected_tags).to_have_count(3)

        for story_id in important_story_ids:
            story_card = page.get_by_test_id(f"story-card-{story_id}")
            expect(story_card).to_be_visible()
            story_card.click()

        page.get_by_role("button", name="Cluster").click()
        expect(page.get_by_test_id("story-to-merge")).to_have_count(3)
        page.get_by_test_id("dialog-story-cluster-submit").click()
        expect(page).to_have_url(re.compile(r".*/assess.*"))

    def test_tag_search_workflow(self, taranis_frontend: Page, pre_seed_stories_enriched, story_list_enriched):
        """Run the full tag-search workflow from dashboard tag click through clustering important stories."""
        page = taranis_frontend
        self._login_as_user(page)
        selected_tag = self._choose_trending_tag(page)

        expect(page).to_have_url(re.compile(r".*/assess.*[?&]tags=.*"))
        query_tags = parse_qs(urlparse(page.url).query).get("tags", [])
        assert selected_tag in query_tags, f"Expected selected dashboard tag '{selected_tag}' in assess URL, got {query_tags}"
        expect(page.locator("#selected-tags")).to_contain_text(selected_tag)

        story_title_to_tags = self._build_story_title_to_tags_map(story_list_enriched)
        important_story_ids = self._mark_first_three_visible_stories_important(page, story_title_to_tags)
        self._filter_important_and_cluster(page, important_story_ids)
