"""Exercise and record the three-host PHP SBOM showcase."""

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


SHOWCASE_DIR = Path(__file__).with_name("testdata") / "sbom"
SHOWCASE_ASSETS = json.loads((SHOWCASE_DIR / "scenario.json").read_text())


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
def created_sbom_assets(core_request_client):
    asset_ids = {}
    try:
        yield asset_ids
    finally:
        for asset_id in asset_ids.values():
            core_request_client.delete(f"/assets/{asset_id}", raise_for_status=False)


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
    def preview_asset(self, page: Page, asset: dict):
        page.goto(url_for("assets.sbom_upload", _external=True))
        self.highlight_element(page.locator('[data-test-id="sbom-file"]')).set_input_files(str(SHOWCASE_DIR / asset["file"]))
        self.highlight_element(page.get_by_role("button", name="Preview SBOM")).click()
        expect(page.get_by_role("heading", name="Review SBOM import")).to_be_visible(timeout=60_000)

    def confirm_asset(self, page: Page, asset: dict, created_sbom_assets: dict):
        self.highlight_element(page.get_by_label("Asset name", exact=True)).fill(asset["name"])
        self.highlight_element(page.get_by_label("Tags", exact=True)).fill(asset["tag"])
        self.highlight_element(page.get_by_label("Destination group")).select_option(label="Default")
        self.highlight_element(page.get_by_role("button", name="Create asset")).click()
        expect(page).to_have_url(re.compile(r"/assets/[^/]+/intelligence$"))
        expect(page.get_by_role("heading", name=f"Relevant intelligence · {asset['name']}")).to_be_visible()
        created_sbom_assets[asset["name"]] = page.url.split("/")[-2]
        expect(page.locator('[data-test-id="asset-scan-status"]')).to_contain_text("COMPLETED", timeout=45_000)
        return created_sbom_assets[asset["name"]]

    def import_asset(self, page: Page, asset: dict, created_sbom_assets: dict):
        self.preview_asset(page, asset)
        return self.confirm_asset(page, asset, created_sbom_assets)

    def test_import_sbom_review_triggers_and_match_intelligence(
        self,
        logged_in_page: Page,
        forward_console_and_page_errors,
        core_request_client,
        api_header,
        sbom_news_items,
        created_sbom_assets,
        sbom_recording,
    ):
        page = logged_in_page
        page.set_viewport_size({"width": 1920, "height": 1080})
        production, staging, control = SHOWCASE_ASSETS
        self.preview_asset(page, production)
        inventory = page.locator('[data-test-id="sbom-inventory"]')
        expect(inventory).to_contain_text("6 software records grouped into 5 components")
        expect(inventory).to_contain_text("1 individual file records excluded")
        expect(inventory).to_contain_text("4 components have valid CPEs; 1 have none")
        php_component = page.get_by_role("row").filter(has_text="php@8.4.26")
        self.highlight_element(php_component.get_by_text("2 occurrences", exact=True), scroll=True).click()
        expect(php_component).to_contain_text("usr/sbin/php-fpm8.4")
        expect(php_component).to_contain_text("usr/bin/php8.4")
        expect(page.get_by_label("Asset name", exact=True)).to_have_value("portal-prod")
        expect(page.get_by_text("Source name: Demo / portal-prod", exact=True)).to_be_visible()
        if sbom_recording:
            self.capture_screenshot(page, str(sbom_recording / "01-inventory-preview.png"))

        prod_id = self.confirm_asset(page, production, created_sbom_assets)
        self.import_asset(page, staging, created_sbom_assets)
        self.import_asset(page, control, created_sbom_assets)
        assert len(created_sbom_assets) == 3

        page.goto(url_for("assets.asset_intelligence", asset_id=prod_id, _external=True))
        matched_stories = page.locator('[data-test-id="asset-matched-story"]')
        expect(matched_stories).to_have_count(6)
        advisory = matched_stories.filter(has=page.get_by_role("heading", name=sbom_news_items[1]["title"], exact=True))
        body_match = matched_stories.filter(has=page.get_by_role("heading", name=sbom_news_items[6]["title"], exact=True))
        cve_only = matched_stories.filter(has=page.get_by_role("heading", name=sbom_news_items[2]["title"], exact=True))
        expect(advisory.locator('[data-test-id="asset-cve-match-count"]')).to_have_text("2 CVE matches")
        expect(advisory.locator('[data-test-id="asset-matched-software"]')).to_contain_text("2 installed versions")
        expect(cve_only.locator('[data-test-id="asset-cve-match-count"]')).to_have_text("1 CVE match")
        expect(cve_only.locator('[data-test-id="asset-match-evidence"]')).to_have_count(0)
        self.highlight_element(body_match.get_by_text("Why this matches", exact=True), scroll=True).click()
        expect(body_match).to_contain_text("Installed versions: 8.3.35, 8.4.26")
        expect(body_match).to_contain_text("Matched “PHP” in article content")
        if sbom_recording:
            self.capture_screenshot(page, str(sbom_recording / "02-automatic-intelligence.png"))

        article_link = advisory.get_by_role("link", name="Open article", exact=True)
        article_anchor = article_link.get_attribute("href").split("#")[-1]
        self.highlight_element(article_link, scroll=True).click()
        expect(page.locator(f"#{article_anchor}")).to_contain_text("CVE-2026-109618")
        page.go_back()
        expect(matched_stories).to_have_count(6)

        self.highlight_element(page.get_by_role("link", name="Matching rules", exact=True)).click()
        selections = page.locator('input[name="trigger_ids"]')
        assert selections.count() > 1
        self.highlight_element(page.get_by_role("button", name="Select all on this page", exact=True)).click()
        expect(page.locator('input[name="trigger_ids"]:checked')).to_have_count(selections.count())
        self.highlight_element(page.get_by_role("button", name="Clear selection", exact=True)).click()
        page.get_by_role("textbox", name="Phrase", exact=True).fill("php")
        self.highlight_element(page.get_by_role("button", name="Filter rules")).click()
        php_rule = page.locator('[data-test-id="asset-trigger"]').filter(
            has=page.get_by_role("heading", name=re.compile(r"^php$", re.IGNORECASE))
        )
        expect(php_rule).to_have_count(1)
        expect(php_rule).to_contain_text("Versions: 8.3.35, 8.4.26")
        self.highlight_element(php_rule.get_by_text("Edit rule", exact=True), scroll=True).click()
        edit_form = php_rule.locator('form:has(input[value="edit"])')
        self.highlight_element(edit_form.get_by_label("Context phrases"), scroll=True).fill("security\ncritical")
        self.highlight_element(edit_form.get_by_role("button", name="Save rule"), scroll=True).click()
        expect(php_rule).to_contain_text("Requires any context: security, critical")
        page.get_by_role("textbox", name="Phrase", exact=True).fill("nginx")
        page.get_by_role("button", name="Filter rules").click()
        nginx_rule = page.locator('[data-test-id="asset-trigger"]').filter(has=page.get_by_role("heading", name="nginx", exact=True))
        expect(nginx_rule).to_have_count(1)
        page.get_by_role("button", name="Select all on this page", exact=True).click()
        self.highlight_element(page.get_by_role("button", name="Disable selected", exact=True), scroll=True).click()
        expect(nginx_rule.locator("span.badge")).to_have_text("Disabled")
        page.get_by_role("link", name="Relevant intelligence", exact=True).click()
        page.get_by_role("button", name="Scan existing articles").click()
        expect(page.locator('[data-test-id="asset-scan-status"]')).to_contain_text("COMPLETED", timeout=45_000)
        expect(matched_stories).to_have_count(4)
        if sbom_recording:
            self.capture_screenshot(page, str(sbom_recording / "03-refined-intelligence.png"))

        corrected = sbom_news_items[0] | {"title": "Unrelated maintenance", "content": "Routine maintenance is complete."}
        core_request_client.post("/worker/news-items", json_data=[corrected], headers=api_header, authenticated=False)
        with_htmx_wait(page, lambda: page.get_by_role("link", name="Refresh results").click())
        expect(matched_stories).to_have_count(3)
        core_request_client.post("/worker/news-items", json_data=[sbom_news_items[0]], headers=api_header, authenticated=False)
        with_htmx_wait(page, lambda: page.get_by_role("link", name="Refresh results").click())
        expect(matched_stories).to_have_count(4)

        stories = core_request_client.json_request("GET", f"/assets/{prod_id}/intelligence")["items"]
        core_request_client.post("/assess/stories/group", json_data=[story["id"] for story in stories])
        with_htmx_wait(page, lambda: page.get_by_role("link", name="Refresh results").click())
        expect(matched_stories).to_have_count(1)
        expect(matched_stories.locator('[data-test-id="asset-matched-article"]')).to_have_count(4)

        page.goto(url_for("assets.assets", _external=True))
        for tag, names in (("production", ("portal-prod", "monitoring-prod")), ("staging", ("portal-staging",))):
            page.get_by_label("Tag", exact=True).select_option(tag)
            with_htmx_wait(page, lambda: page.get_by_role("button", name="Filter assets", exact=True).click())
            rows = page.locator('[data-testid="asset-table_name"]')
            expect(rows).to_have_count(len(names))
            for name in names:
                expect(rows.filter(has_text=name)).to_have_count(1)
            page.goto(url_for("assets.assets", _external=True))
        page.goto(url_for("assets.asset", asset_id=prod_id, _external=True))
        expect(page.get_by_label("Tags", exact=True)).to_have_value("production")

        page.goto(url_for("assets.asset_intelligence", asset_id=prod_id, _external=True))
        page.get_by_role("link", name="Matching rules", exact=True).click()
        page.get_by_role("textbox", name="Phrase", exact=True).fill("php")
        page.get_by_role("button", name="Filter rules").click()
        page.get_by_role("button", name="Select all on this page", exact=True).click()
        page.get_by_role("button", name="Disable selected", exact=True).click()
        page.get_by_role("link", name="Relevant intelligence", exact=True).click()
        expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(2)

    def test_findings_cti_controls_and_sbom_replacement(
        self,
        logged_in_page: Page,
        forward_console_and_page_errors,
        core_request_client,
        sbom_news_items,
        created_sbom_assets,
        sbom_recording,
    ):
        page = logged_in_page
        page.set_viewport_size({"width": 1920, "height": 1080})
        for asset in SHOWCASE_ASSETS:
            self.import_asset(page, asset, created_sbom_assets)
        prod_id = created_sbom_assets["portal-prod"]
        staging_id = created_sbom_assets["portal-staging"]
        control_id = created_sbom_assets["monitoring-prod"]

        page.goto(url_for("assets.asset_intelligence", asset_id=prod_id, _external=True))
        advisory = page.locator('[data-test-id="asset-matched-story"]').filter(has_text=sbom_news_items[1]["title"])
        expect(advisory.locator('[data-test-id="asset-cve-match-count"]')).to_have_text("2 CVE matches")
        page.get_by_label("CVE match", exact=True).select_option("yes")
        page.get_by_role("button", name="Filter matches").click()
        expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(2)
        page.get_by_role("link", name="Findings & indicators", exact=True).click()
        expect(page.locator('[data-testid="cti-ioc-row"]')).to_have_count(2)
        page.get_by_label("CVE or component").fill("PHP")
        page.get_by_role("button", name="Search findings & indicators").click()
        expect(page.locator('[data-testid="cti-ioc-row"]')).to_have_count(2)
        finding_row = page.locator('[data-testid="cti-ioc-row"]').filter(has=page.get_by_role("heading", name="CVE-2026-109618", exact=True))
        finding = finding_row.locator('[data-test-id="cti-imported-finding"]')
        self.highlight_element(finding.get_by_text("Finding details and installed components", exact=True), scroll=True).click()
        expect(finding).to_contain_text("2 installed components")
        expect(finding).to_contain_text("CERT-EU")
        expect(finding).to_contain_text("PHP security team")
        expect(finding).to_contain_text("in_triage")
        expect(finding).to_contain_text("9.2")
        if sbom_recording:
            self.capture_screenshot(page, str(sbom_recording / "01-imported-findings.png"))
        self.highlight_element(finding.get_by_role("button", name="Disable CVE matching"), scroll=True).click()
        expect(page.get_by_role("button", name="Enable CVE matching")).to_be_visible()
        page.get_by_role("link", name="Relevant intelligence", exact=True).click()
        page.get_by_label("CVE match", exact=True).select_option("yes")
        page.get_by_role("button", name="Filter matches").click()
        expect(page.locator('[data-test-id="asset-matched-article"]')).to_have_count(1)
        expect(advisory.locator('[data-test-id="asset-cve-match-count"]')).to_have_text("1 CVE match")

        page.get_by_role("link", name="Software inventory", exact=True).click()
        page.get_by_role("link", name="Update SBOM", exact=True).click()
        document = json.loads((SHOWCASE_DIR / SHOWCASE_ASSETS[0]["file"]).read_text())
        document["version"] = 2
        document["components"] = [component for component in document["components"] if component["bom-ref"] != "php83-legacy"]
        for vulnerability in document["vulnerabilities"]:
            vulnerability["affects"] = [affected for affected in vulnerability["affects"] if affected["ref"] != "php83-legacy"]
        self.highlight_element(page.locator('[data-test-id="sbom-file"]')).set_input_files(
            {"name": "portal-prod-retired-legacy.cdx.json", "mimeType": "application/json", "buffer": json.dumps(document).encode()}
        )
        page.get_by_role("button", name="Preview SBOM").click()
        comparison = page.locator('[data-test-id="sbom-comparison"]')
        expect(comparison).to_be_visible(timeout=60_000)
        expect(comparison).to_contain_text("1 removed")
        self.highlight_element(page.get_by_role("button", name="Update asset"), scroll=True).click()
        expect(page).to_have_url(re.compile(f"/assets/{prod_id}/intelligence$"))
        page.get_by_role("link", name="Findings & indicators", exact=True).click()
        expect(page.locator('[data-testid="cti-ioc-row"]')).to_have_count(2)
        expect(page.get_by_role("button", name="Enable CVE matching")).to_be_visible()
        page.goto(url_for("assets.asset", asset_id=prod_id, _external=True))
        expect(page.get_by_label("Tags", exact=True)).to_have_value("production")
        page.get_by_role("link", name="Software inventory", exact=True).click()
        expect(page.locator('[data-test-id="sbom-inventory"]')).not_to_contain_text("8.3.35")
        if sbom_recording:
            self.capture_screenshot(page, str(sbom_recording / "02-updated-inventory.png"))

        page.goto(url_for("assets.assets_intelligence", _external=True))
        expect(page.get_by_role("heading", name="Asset intelligence overview")).to_be_visible()
        page.get_by_label("CVE match", exact=True).select_option("yes")
        page.get_by_label("CVSS score available").select_option("yes")
        page.get_by_label("Minimum CVSS").fill("9")
        page.get_by_label("Maximum CVSS").fill("9.5")
        page.get_by_role("button", name="Filter matches").click()
        overview = page.locator('[data-test-id="asset-matched-story"]')
        advisory = overview.filter(has_text=sbom_news_items[1]["title"])
        expect(advisory.locator('[data-test-id="asset-matched-host"]')).to_have_count(2)
        expect(advisory.locator('[data-test-id="asset-host-count"]')).to_have_text("2 hosts")
        expect(advisory.locator('[data-test-id="asset-highest-cvss"]')).to_have_text(["Highest reported CVSS 9.2"] * 2)
        expect(advisory).to_contain_text("portal-prod")
        expect(advisory).to_contain_text("portal-staging")
        expect(advisory).not_to_contain_text("monitoring-prod")
        self.highlight_element(advisory.get_by_text("Why this matches", exact=True).first, scroll=True).click()
        expect(advisory).to_contain_text("PHP security team")
        with_htmx_wait(page, lambda: page.get_by_role("link", name="Refresh results", exact=True).click())
        if sbom_recording:
            self.capture_screenshot(page, str(sbom_recording / "03-intelligence-overview.png"))

        page.get_by_label("Package name or PURL").fill("nginx")
        page.get_by_role("button", name="Filter matches").click()
        expect(page.get_by_text("No matches for these filters.", exact=False)).to_be_visible()
        page.get_by_role("link", name="Clear filters").click()
        page.get_by_label("Package name or PURL").fill("nginx")
        page.get_by_role("button", name="Filter matches").click()
        nginx_story = overview.filter(has_text=sbom_news_items[5]["title"])
        expect(nginx_story.locator('[data-test-id="asset-matched-host"]')).to_have_count(3)
        page.get_by_label("Asset tag", exact=True).select_option("production")
        page.get_by_role("button", name="Filter matches").click()
        expect(nginx_story.locator('[data-test-id="asset-matched-host"]')).to_have_count(2)
        page.get_by_label("Asset tag", exact=True).select_option("staging")
        page.get_by_role("button", name="Filter matches").click()
        expect(nginx_story.locator('[data-test-id="asset-matched-host"]')).to_have_count(1)
        page.get_by_role("link", name="Clear filters").click()
        page.get_by_label("CVE match", exact=True).select_option("yes")
        page.get_by_role("button", name="Filter matches").click()
        advisory = overview.filter(has_text=sbom_news_items[1]["title"])
        self.highlight_element(advisory.get_by_role("link", name="portal-staging", exact=True), scroll=True).click()
        expect(page).to_have_url(re.compile(f"/assets/{staging_id}/intelligence\\?"))
        expect(page.get_by_label("CVE match", exact=True)).to_have_value("yes")
        page.get_by_role("link", name="Intelligence overview", exact=True).click()
        expect(page.get_by_label("Host", exact=True)).to_have_value(staging_id)
        page.get_by_label("Host", exact=True).select_option("")
        advisory = overview.filter(has_text=sbom_news_items[1]["title"])
        supporting = advisory.locator('[data-test-id="asset-supporting-article"]').first
        article_url = supporting.get_attribute("href")
        self.highlight_element(supporting, scroll=True).click()
        expect(page).to_have_url(re.compile(re.escape(article_url) + "$"))
        expect(page.locator("main")).to_contain_text("CVE-2026-109618")
        page.go_back()
        expect(page.get_by_label("CVE match", exact=True)).to_have_value("yes")

        page.goto(url_for("assets.asset_intelligence", asset_id=control_id, _external=True))
        expect(page.locator('[data-test-id="asset-matched-story"]')).to_have_count(1)
        page.get_by_label("CVE match", exact=True).select_option("yes")
        page.get_by_role("button", name="Filter matches").click()
        expect(page.get_by_text("No matches for these filters.", exact=False)).to_be_visible()
