"""Exercise the SBOM workflow in CI or record it with the shared highlight/delay options."""

import json
import re
from pathlib import Path
from uuid import uuid4

import pytest
from base_e2e_test import BaseE2ETest
from flask import url_for
from htmx_helpers import with_htmx_wait
from playwright.sync_api import Page, expect

from tests.external_e2e import allow_requests_passthru


@pytest.fixture
def sbom_news_items(core_request_client, api_header, fake_source, worker_process):
    allow_requests_passthru()
    fixture = Path(__file__).with_name("testdata") / "sbom-news-items.json"
    articles = [article | {"osint_source_id": fake_source} for article in json.loads(fixture.read_text())]
    created = core_request_client.json_request("POST", "/worker/news-items", json_data=articles, headers=api_header, authenticated=False)
    try:
        yield articles
    finally:
        for story_id in created["story_ids"]:
            core_request_client.delete(f"/assess/stories/{story_id}", raise_for_status=False)


@pytest.fixture
def sbom_finding_news(core_request_client, api_header, fake_source, worker_process):
    allow_requests_passthru()
    articles = [
        {
            "title": "BuildKit tagged finding advisory (synthetic)",
            "content": "Illustrative CVE-2026-12345 security advisory. This is fictional test data.",
            "link": "https://example.invalid/sbom/finding-advisory",
            "osint_source_id": fake_source,
            "tags": {"CVE-2026-12345": "CVE"},
        },
        {
            "title": "BuildKit community update (synthetic)",
            "content": "Fictional package announcement without a CVE tag.",
            "link": "https://example.invalid/sbom/product-announcement",
            "osint_source_id": fake_source,
        },
    ]
    created = core_request_client.json_request("POST", "/worker/news-items", json_data=articles, headers=api_header, authenticated=False)
    try:
        yield articles[0]
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
        document = json.loads(fixture.read_text())
        document["metadata"]["component"]["name"] = "SBOMProber / spwebcam"
        self.highlight_element(page.locator('[data-test-id="sbom-file"]')).set_input_files(
            {"name": fixture.name, "mimeType": "application/json", "buffer": json.dumps(document).encode()}
        )
        self.short_sleep(self.wait_duration)
        self.highlight_element(page.get_by_role("button", name="Preview SBOM")).click()
        expect(page.get_by_role("heading", name="Review SBOM import")).to_be_visible(timeout=60000)
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

        expect(page.get_by_label("Asset name", exact=True)).to_have_value("spwebcam")
        expect(page.get_by_text("Source name: SBOMProber / spwebcam", exact=True)).to_be_visible()
        self.highlight_element(page.get_by_label("Asset name", exact=True), scroll=True).fill(asset_name)
        self.highlight_element(page.get_by_label("Tags", exact=True)).fill("SBOMProber\nsbomprober_network")
        self.highlight_element(page.get_by_label("Destination group")).select_option(label="Default")
        self.highlight_element(page.get_by_role("button", name="Create asset")).click()
        expect(page).to_have_url(re.compile(r"/assets/[^/]+/intelligence$"))
        expect(page.get_by_role("heading", name=f"Relevant intelligence · {asset_name}")).to_be_visible()
        asset_id = page.url.split("/")[-2]
        try:
            # Import alone queues the historical scan; the UI refreshes when it completes.
            expect(page.locator('[data-test-id="asset-scan-status"]')).to_contain_text("COMPLETED", timeout=45_000)
            matched_stories = page.locator('[data-test-id="asset-matched-story"]')
            expect(matched_stories).to_have_count(4)
            for article in (sbom_news_items[0], sbom_news_items[1], sbom_news_items[3], sbom_news_items[4]):
                expect(matched_stories.filter(has=page.get_by_role("heading", name=article["title"], exact=True))).to_have_count(1)
            advisory = matched_stories.filter(has=page.get_by_role("heading", name=sbom_news_items[0]["title"], exact=True))
            body_match = matched_stories.filter(has=page.get_by_role("heading", name=sbom_news_items[1]["title"], exact=True))
            for story in (advisory, body_match):
                expect(story.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
                expect(story.locator('[data-test-id="asset-matched-software"]')).to_have_text(
                    "github.com/moby/buildkit · 2 installed versions · Software phrase"
                )
                expect(story.locator('[data-test-id="asset-story-summary"]')).to_have_text("1 matching article · 1 software package")
                expect(story.locator("blockquote")).not_to_be_visible()
                expect(story.get_by_role("link", name="Open article", exact=True)).to_have_count(1)
                self.highlight_element(story.get_by_text("Why this matches", exact=True), scroll=True).click()
                expect(story).to_contain_text("Installed versions: v0.32.0, v0.32.1")
                expect(story.locator('[data-test-id="asset-match-evidence"]')).to_have_count(1)
                expect(story.locator("blockquote")).to_be_visible()
            expect(advisory).to_contain_text("Matched “BuildKit” in article title")
            expect(body_match).to_contain_text("Matched “BuildKit” in article content")
            self.highlight_element(advisory.get_by_role("heading"), scroll=True)
            self.short_sleep(self.wait_duration * 2)
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "02-automatic-intelligence.png"))

            article_link = advisory.get_by_role("link", name="Open article", exact=True)
            article_anchor = article_link.get_attribute("href").split("#")[-1]
            self.highlight_element(article_link, scroll=True).click()
            article_card = page.locator(f"#{article_anchor}")
            expect(article_card).to_be_visible()
            expect(article_card).to_contain_text("BuildKit")
            self.highlight_element(article_card, scroll=True)
            self.short_sleep(self.wait_duration * 2)
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "03-supporting-article.png"))
            page.go_back()
            expect(matched_stories).to_have_count(4)

            # Optional refinement applies one review decision to both installed versions.
            self.highlight_element(page.get_by_role("link", name="Component triggers", exact=True), scroll=True).click()
            vendor = page.locator('[data-test-id="asset-trigger"]').filter(has=page.get_by_role("heading", name="moby", exact=True))
            expect(vendor.locator("span.badge")).to_have_text("Disabled")
            selections = page.locator('input[name="trigger_ids"]')
            assert selections.count() > 1
            self.highlight_element(page.get_by_role("button", name="Select all on this page", exact=True)).click()
            expect(page.locator('input[name="trigger_ids"]:checked')).to_have_count(selections.count())
            self.highlight_element(page.get_by_role("button", name="Clear selection", exact=True)).click()
            expect(page.locator('input[name="trigger_ids"]:checked')).to_have_count(0)
            self.highlight_element(page.get_by_role("textbox", name="Phrase", exact=True)).fill("buildkit")
            self.highlight_element(page.get_by_role("button", name="Filter triggers")).click()
            rules = page.locator('[data-test-id="asset-trigger"]').filter(has=page.get_by_role("heading", name="buildkit", exact=True))
            expect(rules).to_have_count(1)
            expect(rules.locator("span.badge")).to_have_text("Enabled")
            expect(rules).to_contain_text("Versions: v0.32.0, v0.32.1")
            self.highlight_element(rules.get_by_text("Edit trigger", exact=True), scroll=True).click()
            edit_form = rules.locator('form:has(input[value="edit"])')
            self.highlight_element(edit_form.get_by_label("Context phrases"), scroll=True).fill("vulnerability\nsecurity update")
            self.highlight_element(edit_form.get_by_role("button", name="Save trigger"), scroll=True).click()
            expect(rules).to_contain_text("Requires any context: vulnerability, security update")
            self.highlight_element(page.get_by_role("textbox", name="Phrase", exact=True), scroll=True).fill("curl")
            self.highlight_element(page.get_by_role("button", name="Filter triggers")).click()
            curl = page.locator('[data-test-id="asset-trigger"]').filter(has=page.get_by_role("heading", name="curl", exact=True))
            self.highlight_element(page.get_by_role("button", name="Select all on this page", exact=True), scroll=True).click()
            self.highlight_element(page.get_by_role("button", name="Disable selected", exact=True), scroll=True).click()
            expect(curl.locator("span.badge")).to_have_text("Disabled")
            self.highlight_element(page.get_by_role("link", name="Relevant intelligence", exact=True), scroll=True).click()
            self.highlight_element(page.get_by_role("button", name="Scan existing articles")).click()
            expect(page.locator('[data-test-id="asset-scan-status"]')).to_contain_text("COMPLETED", timeout=45_000)
            expect(matched_stories).to_have_count(2)
            for story in (advisory, body_match):
                expect(story.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
                expect(story.locator('[data-test-id="asset-match-evidence"]')).to_have_count(1)
            self.highlight_element(advisory.get_by_role("heading"), scroll=True)
            self.short_sleep(self.wait_duration * 2)
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "04-refined-intelligence.png"))

            self.highlight_element(body_match.get_by_text("Why this matches", exact=True), scroll=True).click()
            expect(body_match.locator("blockquote")).to_be_visible()

            # Collection updates replace evidence immediately, without another historical scan.
            corrected = sbom_news_items[0] | {"title": "Unrelated maintenance", "content": "Routine maintenance is complete."}
            core_request_client.post("/worker/news-items", json_data=[corrected], headers=api_header, authenticated=False)
            with_htmx_wait(page, lambda: page.get_by_role("link", name="Refresh results").click())
            expect(matched_stories).to_have_count(1)
            expect(advisory).to_have_count(0)
            expect(body_match.locator("blockquote")).to_be_visible()
            core_request_client.post("/worker/news-items", json_data=[sbom_news_items[0]], headers=api_header, authenticated=False)
            with_htmx_wait(page, lambda: page.get_by_role("link", name="Refresh results").click())
            expect(matched_stories).to_have_count(2)
            expect(body_match.locator("blockquote")).to_be_visible()

            # Story grouping keeps both article links and counts the shared package once.
            stories = core_request_client.json_request("GET", f"/assets/{asset_id}/intelligence")["items"]
            core_request_client.post("/assess/stories/group", json_data=[story["id"] for story in stories])
            with_htmx_wait(page, lambda: page.get_by_role("link", name="Refresh results").click())
            expect(matched_stories).to_have_count(1)
            expect(matched_stories.locator('[data-test-id="asset-matched-article"]')).to_have_count(2)
            summary = matched_stories.locator('[data-test-id="asset-story-summary"]')
            expect(summary).to_have_text("2 matching articles · 1 software package")
            self.highlight_element(summary, scroll=True)
            article_links = matched_stories.locator('[data-test-id="asset-supporting-article"]')
            expect(article_links).to_have_text(
                [
                    article["title"]
                    for article in sorted([article for story in stories for article in story["articles"]], key=lambda article: article["id"])
                ]
            )
            assert len({link.get_attribute("href") for link in article_links.all()}) == 2
            page.goto(url_for("assets.asset", asset_id=asset_id, _external=True))
            expect(page.get_by_label("Tags", exact=True)).to_have_value("sbomprober\nsbomprober_network")
            page.get_by_label("Tags", exact=True).fill("SBOMProber\nsbomprober_network\nmanual")
            with_htmx_wait(page, lambda: page.locator('input[type="submit"]').click())
            page.goto(url_for("assets.asset", asset_id=asset_id, _external=True))
            expect(page.get_by_label("Tags", exact=True)).to_have_value("manual\nsbomprober\nsbomprober_network")
            for tag in ("sbomprober", "sbomprober_network"):
                page.goto(url_for("assets.assets", _external=True))
                page.get_by_label("Tag", exact=True).select_option(tag)
                with_htmx_wait(page, lambda: page.get_by_role("button", name="Filter assets", exact=True).click())
                expect(page.locator('[data-testid="asset-table_name"]').filter(has_text=asset_name)).to_have_count(1)
                expect(page.get_by_label("Tag", exact=True)).to_have_value(tag)
                expect(page.locator('[data-testid="asset-table_tags"]').filter(has_text=tag)).to_have_count(1)
                page.goto(url_for("assets.assets_intelligence", _external=True))
                page.get_by_label("Asset tag", exact=True).select_option(tag)
                page.get_by_role("button", name="Filter matches", exact=True).click()
                expect(page.locator('[data-test-id="asset-matched-host"]')).to_have_count(2)
                with_htmx_wait(page, lambda: page.get_by_role("link", name="Refresh results", exact=True).click())
                expect(page.get_by_label("Asset tag", exact=True)).to_have_value(tag)
            page.goto(url_for("assets.asset_intelligence", asset_id=asset_id, _external=True))

            self.highlight_element(page.get_by_role("link", name="Component triggers", exact=True), scroll=True).click()
            for row in rules.all():
                self.highlight_element(row.get_by_role("checkbox", name=re.compile("Select buildkit")), scroll=True).check()
            self.highlight_element(page.get_by_role("button", name="Disable selected", exact=True), scroll=True).click()
            self.highlight_element(page.get_by_role("link", name="Relevant intelligence", exact=True)).click()
            expect(matched_stories).to_have_count(0)
            self.short_sleep(self.wait_duration * 2)
        finally:
            core_request_client.delete(f"/assets/{asset_id}", raise_for_status=False)

    def test_findings_cti_controls_and_sbom_replacement(
        self,
        logged_in_page: Page,
        forward_console_and_page_errors,
        core_request_client,
        sbom_finding_news,
        sbom_recording,
    ):
        page = logged_in_page
        page.set_viewport_size({"width": 1920, "height": 1080})
        fixture = Path(__file__).resolve().parents[3] / "core/tests/test_data/sbom/test-sbom-findings.cdx.json"
        document = json.loads(fixture.read_text())
        document["vulnerabilities"].extend({"id": f"CVE-2026-{20000 + i}", "affects": [{"ref": "internal-agent"}]} for i in range(51))
        page.goto(url_for("assets.sbom_upload", _external=True))
        self.highlight_element(page.locator('[data-test-id="sbom-file"]')).set_input_files(
            {
                "name": "showcase-findings.cdx.json",
                "mimeType": "application/json",
                "buffer": json.dumps(document).encode(),
            }
        )
        self.highlight_element(page.get_by_role("button", name="Preview SBOM")).click()
        expect(page.locator('[data-test-id="sbom-findings-summary"]')).to_contain_text("53 distinct CVEs", timeout=60000)
        self.highlight_element(page.locator('[data-test-id="sbom-findings-summary"]'))
        self.highlight_element(page.get_by_label("Asset name", exact=True), scroll=True).fill("SBOM Findings Showcase")
        self.highlight_element(page.get_by_label("Destination group")).select_option(label="Default")
        self.highlight_element(page.get_by_role("button", name="Create asset")).click()
        expect(page).to_have_url(re.compile(r"/assets/[^/]+/intelligence$"))
        asset_id = page.url.split("/")[-2]
        overview_asset_id = None
        try:
            expect(page.locator('[data-test-id="asset-scan-status"]')).to_contain_text("COMPLETED", timeout=45_000)
            story = page.locator('[data-test-id="asset-matched-story"]').filter(has_text=sbom_finding_news["title"])
            expect(story.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
            expect(story.locator('[data-test-id="asset-matched-software"]')).to_have_count(2)
            expect(story.locator('[data-test-id="asset-cve-match-count"]')).to_have_text("1 CVE match")
            expect(story.locator('[data-test-id="asset-cve-match-count"]')).to_be_visible()
            expect(story.locator("details")).not_to_have_attribute("open", "")
            expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(2)
            self.highlight_element(page.get_by_label("CVE match", exact=True), scroll=True).select_option("yes")
            self.highlight_element(page.get_by_role("button", name="Filter matches")).click()
            expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
            self.highlight_element(story.get_by_text("Why this matches", exact=True), scroll=True).click()
            expect(story).to_contain_text("CVE-2026-12345")
            expect(story).to_contain_text("CVE tag")
            self.highlight_element(page.get_by_role("link", name="Refresh results", exact=True), scroll=True).click()
            expect(story.locator('[data-test-id="asset-cve-match"]')).to_be_visible()
            expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
            self.highlight_element(page.get_by_role("button", name="Scan existing articles"), scroll=True).click()
            expect(page.get_by_label("CVE match", exact=True)).to_have_value("yes")
            expect(page.locator('[data-test-id="asset-scan-status"]')).to_contain_text("COMPLETED", timeout=45_000)
            expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
            self.short_sleep(self.wait_duration * 2)
            self.highlight_element(page.get_by_role("link", name="CTI information", exact=True), scroll=True).click()
            expect(page.get_by_role("heading", name="CTI information", exact=True)).to_be_visible()
            expect(page.locator('[data-testid="cti-ioc-row"]')).to_have_count(50)
            self.highlight_element(page.get_by_role("link", name="Next", exact=True), scroll=True).click()
            expect(page.locator('[data-testid="cti-ioc-row"]')).to_have_count(3)
            expect(page.get_by_text("Page 2 of 2", exact=True)).to_be_visible()
            self.highlight_element(page.get_by_label("CVE or component"), scroll=True).fill("buildkit")
            self.highlight_element(page.get_by_role("button", name="Search CTI")).click()
            expect(page.locator('[data-testid="cti-ioc-row"]')).to_have_count(1)
            finding = page.locator('[data-test-id="cti-imported-finding"]')
            self.highlight_element(finding.get_by_text("Finding details and installed components", exact=True)).click()
            expect(finding).to_contain_text("3 installed components")
            expect(finding).to_contain_text("NVD")
            expect(finding).to_contain_text("Vendor advisory")
            expect(finding).to_contain_text("in_triage")
            expect(finding).to_contain_text("Unresolved component reference")
            self.short_sleep(self.wait_duration * 2)
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "01-imported-findings.png"))
            self.highlight_element(finding.get_by_role("button", name="Disable CVE matching"), scroll=True).click()
            expect(page.get_by_role("button", name="Enable CVE matching")).to_be_visible()
            self.highlight_element(page.get_by_role("link", name="Relevant intelligence", exact=True)).click()
            self.highlight_element(story.get_by_text("Why this matches", exact=True), scroll=True).click()
            expect(story).not_to_contain_text("CVE tag")
            expect(story.locator('[data-test-id="asset-matched-software"]')).to_have_count(1)
            expect(story.locator('[data-test-id="asset-cve-match-count"]')).to_have_count(0)
            self.highlight_element(page.get_by_label("CVE match", exact=True), scroll=True).select_option("yes")
            self.highlight_element(page.get_by_role("button", name="Filter matches")).click()
            expect(page.get_by_text("No matches for these filters.", exact=False)).to_be_visible()
            expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(0)
            self.highlight_element(page.get_by_role("link", name="SBOM inventory", exact=True), scroll=True).click()
            self.highlight_element(page.get_by_role("link", name="Update SBOM", exact=True)).click()
            document["vulnerabilities"] = document["vulnerabilities"][:2]
            self.highlight_element(page.locator('[data-test-id="sbom-file"]')).set_input_files(
                {
                    "name": "updated-findings.cdx.json",
                    "mimeType": "application/json",
                    "buffer": json.dumps(document).encode(),
                }
            )
            self.highlight_element(page.get_by_role("button", name="Preview SBOM")).click()
            comparison = page.locator('[data-test-id="sbom-comparison"]')
            expect(comparison).to_be_visible(timeout=60000)
            expect(comparison).to_contain_text("52 removed")
            self.highlight_element(comparison)
            self.short_sleep(self.wait_duration * 2)
            self.highlight_element(page.get_by_role("button", name="Update asset"), scroll=True).click()
            expect(page).to_have_url(re.compile(f"/assets/{asset_id}/intelligence$"))
            self.highlight_element(page.get_by_role("link", name="CTI information", exact=True)).click()
            expect(page.locator('[data-testid="cti-ioc-row"]')).to_have_count(1)
            expect(page.get_by_role("button", name="Enable CVE matching")).to_be_visible()
            self.highlight_element(page.get_by_role("button", name="Enable CVE matching")).click()
            self.highlight_element(page.get_by_role("link", name="Relevant intelligence", exact=True)).click()
            self.highlight_element(story.get_by_text("Why this matches", exact=True), scroll=True).click()
            expect(story).to_contain_text("CVE tag")
            self.short_sleep(self.wait_duration * 2)
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "02-updated-intelligence.png"))

            # A second host reports the same CVE without a numeric score.
            document["metadata"]["component"]["name"] = "secondary-host"
            for vulnerability in document["vulnerabilities"]:
                vulnerability["ratings"] = []
            page.goto(url_for("assets.sbom_upload", _external=True))
            self.highlight_element(page.locator('[data-test-id="sbom-file"]')).set_input_files(
                {
                    "name": "secondary-host.cdx.json",
                    "mimeType": "application/json",
                    "buffer": json.dumps(document).encode(),
                }
            )
            self.highlight_element(page.get_by_role("button", name="Preview SBOM")).click()
            expect(page.get_by_label("Asset name", exact=True)).to_be_visible(timeout=60000)
            self.highlight_element(page.get_by_label("Asset name", exact=True), scroll=True).fill("SBOM Secondary Host")
            self.highlight_element(page.get_by_label("Destination group")).select_option(label="Default")
            self.highlight_element(page.get_by_role("button", name="Create asset")).click()
            expect(page).to_have_url(re.compile(r"/assets/[^/]+/intelligence$"))
            overview_asset_id = page.url.split("/")[-2]
            expect(page.locator('[data-test-id="asset-scan-status"]')).to_contain_text("COMPLETED", timeout=45_000)
            page.goto(url_for("assets.assets", _external=True))
            self.highlight_element(page.get_by_role("link", name="Intelligence overview", exact=True)).click()
            expect(page.get_by_role("heading", name="Asset intelligence overview")).to_be_visible()
            expect(story.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
            expect(story.locator('[data-test-id="asset-host-count"]')).to_have_text("2 hosts")
            expect(story.locator('[data-test-id="overview-cve-count"]')).to_have_text("1 CVE match")
            self.highlight_element(page.get_by_label("CVE match", exact=True)).select_option("yes")
            self.highlight_element(page.get_by_label("CVSS score available")).select_option("yes")
            self.highlight_element(page.get_by_label("Minimum CVSS")).fill("9")
            self.highlight_element(page.get_by_role("button", name="Filter matches")).click()
            expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
            expect(story.locator('[data-test-id="asset-matched-host"]')).to_have_count(1)
            expect(story.locator('[data-test-id="asset-highest-cvss"]')).to_have_text("Highest reported CVSS 9.1")
            self.highlight_element(story.get_by_text("Why this matches", exact=True), scroll=True).click()
            expect(story.locator('[data-test-id="asset-cvss-rating"]')).to_have_count(3)
            with_htmx_wait(page, lambda: self.highlight_element(page.get_by_role("link", name="Refresh results"), scroll=True).click())
            expect(story.locator('[data-test-id="asset-cvss-rating"]').first).to_be_visible()
            expect(page.get_by_label("CVSS score available")).to_have_value("yes")
            self.highlight_element(page.get_by_label("Package name or PURL"), scroll=True).fill("buildkit")
            self.highlight_element(page.get_by_label("Minimum CVSS")).fill("7")
            self.highlight_element(page.get_by_label("Maximum CVSS")).fill("8.5")
            self.highlight_element(page.get_by_role("button", name="Filter matches")).click()
            expect(story.locator('[data-test-id="asset-highest-cvss"]')).to_have_text("Highest reported CVSS 8.1")
            expect(story.locator('[data-test-id="asset-matched-software"]')).to_have_count(1)
            self.highlight_element(story.get_by_text("Why this matches", exact=True), scroll=True).click()
            expect(story.locator('[data-test-id="asset-cvss-rating"]')).to_have_count(2)
            expect(story).not_to_contain_text("Vendor advisory")
            expect(page.locator('[data-test-id="intelligence-result-count"]')).to_contain_text("1 matching story · 1 matching article")
            self.highlight_element(story.get_by_role("link", name="SBOM Findings Showcase", exact=True)).click()
            expect(page.get_by_role("heading", name="Relevant intelligence · SBOM Findings Showcase")).to_be_visible()
            expect(page.get_by_label("Package name or PURL")).to_have_value("buildkit")
            expect(page.get_by_label("Minimum CVSS")).to_have_value("7.0")
            expect(page.get_by_label("Maximum CVSS")).to_have_value("8.5")
            expect(story.locator('[data-test-id="asset-highest-cvss"]')).to_have_text("Highest reported CVSS 8.1")
            self.highlight_element(page.get_by_role("link", name="Intelligence overview", exact=True)).click()
            expect(page.get_by_label("Host", exact=True)).to_have_value(asset_id)
            expect(page.get_by_label("Package name or PURL")).to_have_value("buildkit")
            self.highlight_element(page.get_by_label("Host", exact=True)).select_option("")
            if sbom_recording:
                self.capture_screenshot(page, str(sbom_recording / "03-intelligence-overview.png"))
            self.highlight_element(page.get_by_label("CVSS score available"), scroll=True).select_option("no")
            self.highlight_element(page.get_by_label("Minimum CVSS")).fill("")
            self.highlight_element(page.get_by_label("Maximum CVSS")).fill("")
            self.highlight_element(page.get_by_role("button", name="Filter matches")).click()
            expect(story.locator('[data-test-id="asset-matched-host"]')).to_have_count(1)
            expect(story).to_contain_text("SBOM Secondary Host")
            expect(story).not_to_contain_text("SBOM Findings Showcase")
            self.highlight_element(page.get_by_label("Host", exact=True)).select_option(asset_id)
            self.highlight_element(page.get_by_role("button", name="Filter matches")).click()
            expect(page.get_by_text("No matches for these filters.", exact=False)).to_be_visible()
            self.highlight_element(page.get_by_role("link", name="Clear filters")).click()
            self.highlight_element(page.get_by_label("Package name or PURL")).fill("curl")
            self.highlight_element(page.get_by_label("Software phrase match", exact=True)).select_option("no")
            self.highlight_element(page.get_by_role("button", name="Filter matches")).click()
            expect(story.locator('[data-test-id="asset-host-count"]')).to_have_text("2 hosts")
            supporting = story.locator('[data-test-id="asset-supporting-article"]')
            article_url = supporting.get_attribute("href")
            self.highlight_element(supporting, scroll=True).click()
            expect(page).to_have_url(re.compile(re.escape(article_url) + "$"))
            page.go_back()
            expect(page.get_by_label("Software phrase match", exact=True)).to_have_value("no")
        finally:
            core_request_client.delete(f"/assets/{asset_id}", raise_for_status=False)
            if overview_asset_id:
                core_request_client.delete(f"/assets/{overview_asset_id}", raise_for_status=False)
