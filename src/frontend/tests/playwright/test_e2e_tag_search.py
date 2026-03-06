#!/usr/bin/env python3
import re

import pytest
from flask import url_for
from playwright.sync_api import Page, expect


@pytest.mark.e2e_workflow_1
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestEndToEndWorkflow1:
    def test_login_then_open_trending_tag(self, taranis_frontend: Page, pre_seed_stories_enriched):
        page = taranis_frontend

        page.goto(url_for("base.login", _external=True))
        expect(page).to_have_title("Taranis AI", timeout=5000)

        page.get_by_placeholder("Username").fill("user")
        page.get_by_placeholder("Password").fill("test")
        page.get_by_test_id("login-button").click()
        expect(page.locator("#dashboard")).to_be_visible()

        page.goto(url_for("base.dashboard", _external=True))
        expect(page.locator("#dashboard")).to_contain_text("Trending Tags (last")

        trending_tag_link = page.locator("#dashboard a[href*='/assess?tags=']").first
        expect(trending_tag_link).to_be_visible(timeout=30000)
        selected_tag = trending_tag_link.inner_text().strip()

        trending_tag_link.click()
        expect(page).to_have_url(re.compile(r".*/assess.*[?&]tags=.*"))
        expect(page.locator("#selected-tags")).to_contain_text(selected_tag)
