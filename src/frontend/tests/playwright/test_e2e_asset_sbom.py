"""Exercise the SBOM workflow in CI or record it with the shared highlight/delay options."""

import json
import re
import time
from pathlib import Path
from uuid import uuid4

import pytest
from base_e2e_test import BaseE2ETest
from flask import url_for
from playwright.sync_api import Page, expect


@pytest.fixture
def sbom_news_items(core_request_client, api_header, fake_source, worker_process):
    fixture = Path(__file__).with_name("testdata") / "sbom-news-items.json"
    articles = [article | {"osint_source_id": fake_source} for article in json.loads(fixture.read_text())]
    created = core_request_client.json_request("POST", "/worker/news-items", json_data=articles, headers=api_header, authenticated=False)
    try:
        yield articles
    finally:
        for story_id in created["story_ids"]:
            core_request_client.delete(f"/assess/stories/{story_id}", raise_for_status=False)


@pytest.fixture
def sbom_recording(logged_in_page, request):
    if not request.config.getoption("--record-video"):
        yield None
        return
    artifacts = Path("tests/playwright/videos") / f"sbom-showcase-{uuid4().hex[:8]}"
    artifacts.mkdir(parents=True, exist_ok=True)
    try:
        yield artifacts
    finally:
        video = logged_in_page.video
        logged_in_page.close()
        video.save_as(artifacts / "sbom-showcase.webm")
        print(f"SBOM showcase recording: {artifacts / 'sbom-showcase.webm'}")


@pytest.mark.e2e_ci
@pytest.mark.e2e_user_workflow
@pytest.mark.e2e_full_stack
@pytest.mark.usefixtures("e2e_ci")
class TestAssetSbomWorkflow(BaseE2ETest):
    def scan_existing_articles(self, page, core_request_client, asset_id):
        self.highlight_element(page.get_by_role("button", name="Scan existing articles")).click()
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            run = core_request_client.json_request("GET", f"/assets/{asset_id}/match-runs")["run"]
            if run["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.25)
        assert run["status"] == "COMPLETED", run
        self.highlight_element(page.get_by_role("link", name="Refresh results")).click()
        expect(page.locator('[data-test-id="asset-scan-status"]')).to_contain_text("COMPLETED")

    def test_import_sbom_review_triggers_and_match_intelligence(
        self,
        logged_in_page: Page,
        forward_console_and_page_errors,
        core_request_client,
        api_header,
        sbom_news_items,
        sbom_recording,
    ):
        page = logged_in_page
        page.set_viewport_size({"width": 1920, "height": 1080})
        fixture = Path(__file__).resolve().parents[3] / "core/tests/test_data/sbom/test-sbom-import.cdx.json"
        asset_name = "SBOM Showcase Host"
        page.goto(url_for("assets.assets", _external=True))
        self.highlight_element(page.locator('[data-test-id="import-sbom"]')).click()
        self.highlight_element(page.locator('[data-test-id="sbom-file"]')).set_input_files(fixture)
        self.short_sleep(self.wait_duration)
        self.highlight_element(page.get_by_role("button", name="Preview SBOM")).click()
        expect(page.get_by_role("heading", name="Review SBOM import")).to_be_visible()
        inventory = page.locator('[data-test-id="sbom-inventory"]')
        expect(inventory).to_contain_text("5 software records grouped into 4 components")
        expect(inventory).to_contain_text("1 individual file records excluded")
        expect(inventory).to_contain_text("3 components have valid CPEs; 1 have none")
        self.highlight_element(inventory.get_by_text("5 software records", exact=False))
        buildkit_component = page.get_by_role("row").filter(has_text="buildkit@v0.32.0")
        self.highlight_element(buildkit_component.get_by_text("2 occurrences", exact=True), scroll=True).click()
        expect(buildkit_component).to_contain_text("usr/bin/dockerd")
        expect(buildkit_component).to_contain_text("usr/libexec/docker/cli-plugins/docker-buildx")
        self.short_sleep(self.wait_duration * 2)
        if sbom_recording:
            self.capture_screenshot(page, str(sbom_recording / "01-inventory-preview.png"))

        self.highlight_element(page.get_by_label("Asset name", exact=True), scroll=True).fill(asset_name)
        self.highlight_element(page.get_by_label("Destination group")).select_option(label="Default")
        self.highlight_element(page.get_by_role("button", name="Create asset")).click()
        expect(page).to_have_url(re.compile(r"/assets/[^/]+/sbom$"))
        expect(page.get_by_role("heading", name="SBOM inventory")).to_be_visible()
        asset_id = page.url.split("/")[-2]
        try:
            self.highlight_element(page.get_by_role("link", name="Asset details", exact=True), scroll=True).click()
            expect(page.locator('input[name="name"]')).to_have_value(asset_name)
            self.highlight_element(page.get_by_role("link", name="SBOM inventory", exact=True)).click()
            self.highlight_element(page.get_by_role("link", name="Component triggers", exact=True), scroll=True).click()
            self.highlight_element(page.get_by_role("textbox", name="Phrase", exact=True)).fill("buildkit")
            self.highlight_element(page.get_by_role("button", name="Filter triggers")).click()
            rules = page.locator('[data-test-id="asset-trigger"]').filter(has=page.get_by_role("heading", name="buildkit", exact=True))
            expect(rules).to_have_count(2)
            for row in rules.all():
                expect(row.locator("span.badge")).to_have_text("Disabled")
                self.highlight_element(row.get_by_role("checkbox", name=re.compile("Select buildkit")), scroll=True).check()
            self.highlight_element(page.get_by_role("button", name="Enable selected", exact=True), scroll=True).click()
            for row in rules.all():
                expect(row.locator("span.badge")).to_have_text("Enabled")
                self.highlight_element(row.get_by_text("Edit trigger", exact=True), scroll=True).click()
                edit_form = row.locator('form:has(input[value="edit"])')
                self.highlight_element(edit_form.get_by_label("Context phrases"), scroll=True).fill("vulnerability\nsecurity update")
                self.highlight_element(edit_form.get_by_role("button", name="Save trigger"), scroll=True).click()
                expect(row).to_contain_text("Requires any context: vulnerability, security update")
            self.highlight_element(page.get_by_role("combobox", name="Status"), scroll=True).select_option(label="Enabled")
            self.highlight_element(page.get_by_role("button", name="Filter triggers")).click()
            expect(page.locator('[data-test-id="asset-trigger"]')).to_have_count(2)
            self.short_sleep(self.wait_duration * 2)
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "02-reviewed-triggers.png"))

            self.highlight_element(page.get_by_role("link", name="Relevant intelligence", exact=True), scroll=True).click()
            expect(page.locator('[data-test-id="asset-matched-story"]')).to_have_count(0)
            self.scan_existing_articles(page, core_request_client, asset_id)
            matched_stories = page.locator('[data-test-id="asset-matched-story"]')
            expect(matched_stories).to_have_count(2)
            # The exact result set excludes partial product names, missing context and disabled curl rules.
            for article in sbom_news_items[:2]:
                matched_story = matched_stories.filter(has=page.get_by_role("heading", name=article["title"], exact=True))
                expect(matched_story).to_have_count(1)
                expect(matched_story.locator('[data-test-id="asset-match-reason"]')).to_have_count(2)
                for version in ("v0.32.0", "v0.32.1"):
                    expect(matched_story).to_contain_text(f"github.com/moby/buildkit {version}")
                expect(matched_story).to_contain_text(asset_name)
            advisory = matched_stories.filter(has=page.get_by_role("heading", name=sbom_news_items[0]["title"], exact=True))
            body_match = matched_stories.filter(has=page.get_by_role("heading", name=sbom_news_items[1]["title"], exact=True))
            expect(advisory).to_contain_text("Matched “BuildKit” in article title")
            expect(body_match).to_contain_text("Matched “BuildKit” in article content")
            self.highlight_element(advisory.get_by_role("heading"), scroll=True)
            self.short_sleep(self.wait_duration * 2)
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "03-matched-intelligence.png"))

            article_link = advisory.locator('[data-test-id="asset-match-reason"]').first.get_by_role("link")
            article_anchor = article_link.get_attribute("href").split("#")[-1]
            self.highlight_element(article_link, scroll=True).click()
            article_card = page.locator(f"#{article_anchor}")
            expect(article_card).to_be_visible()
            expect(article_card).to_contain_text("BuildKit")
            self.highlight_element(article_card, scroll=True)
            self.short_sleep(self.wait_duration * 2)
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "04-supporting-article.png"))
            page.go_back()
            expect(matched_stories).to_have_count(2)

            # Collection updates replace evidence immediately, without another historical scan.
            corrected = sbom_news_items[0] | {"title": "Unrelated maintenance", "content": "Routine maintenance is complete."}
            core_request_client.post("/worker/news-items", json_data=[corrected], headers=api_header, authenticated=False)
            page.get_by_role("link", name="Refresh results").click()
            expect(matched_stories).to_have_count(1)
            expect(advisory).to_have_count(0)
            core_request_client.post("/worker/news-items", json_data=[sbom_news_items[0]], headers=api_header, authenticated=False)
            page.get_by_role("link", name="Refresh results").click()
            expect(matched_stories).to_have_count(2)

            self.highlight_element(page.get_by_role("link", name="Component triggers", exact=True), scroll=True).click()
            for row in rules.all():
                self.highlight_element(row.get_by_role("checkbox", name=re.compile("Select buildkit")), scroll=True).check()
            self.highlight_element(page.get_by_role("button", name="Disable selected", exact=True), scroll=True).click()
            self.highlight_element(page.get_by_role("link", name="Relevant intelligence", exact=True)).click()
            expect(matched_stories).to_have_count(0)
            self.short_sleep(self.wait_duration * 2)
        finally:
            core_request_client.delete(f"/assets/{asset_id}", raise_for_status=False)
