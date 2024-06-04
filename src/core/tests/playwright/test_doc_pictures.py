#!/usr/bin/env python3
import re

from playwright.sync_api import Page
import pytest


@pytest.mark.e2e_admin
class TestEndToEndAdmin:
    wait_duration = 0
    ci_run = True
    produce_artifacts = False

    def test_doc_login(self, taranis_frontend: Page):
        from tests.playwright.test_e2e import TestEndToEndUser

        page = taranis_frontend

        e2e = TestEndToEndUser()
        e2e.ci_run = self.ci_run
        e2e.test_e2e_login(taranis_frontend=page)

    def test_admin_user_management(self, taranis_frontend: Page):
        page = taranis_frontend

        def add_organization():
            page.get_by_role("link", name="Administration").click()
            page.get_by_role("link", name="Organizations").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Name").click()
            page.get_by_label("Name").fill("Test organizations")
            page.get_by_label("Description").fill("Test description of an organization")
            page.get_by_label("Street").fill("Test Street")
            page.get_by_label("City").fill("Test City")
            page.get_by_label("Zip").fill("9999")
            page.get_by_label("Country").fill("Test Country")
            page.screenshot(path="./tests/playwright/screenshots/docs_organization_add.png")

        def add_role():
            page.get_by_role("link", name="Roles").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Name").fill("User")
            page.get_by_label("Description").fill("Basic user role")
            page.get_by_role("combobox").first.click()
            page.get_by_role("option", name="Clear").click()
            page.get_by_role("cell", name="CONFIG_WORKER_ACCESS").click()
            page.get_by_role("cell", name="CONFIG_WORKER_ACCESS").click()
            page.get_by_role("row", name="CONFIG_WORKER_ACCESS Access").get_by_role("cell").first.click()
            page.get_by_role("row", name="ADMIN_OPERATIONS Admin").get_by_role("cell").first.click()
            page.get_by_role("row", name="ANALYZE_ACCESS Analyze access").get_by_role("cell").first.click()
            page.get_by_role("row", name="ANALYZE_CREATE Analyze create").get_by_role("cell").first.click()
            page.get_by_role("row", name="ANALYZE_DELETE Analyze delete").get_by_role("cell").first.click()
            page.get_by_role("row", name="ANALYZE_UPDATE Analyze update").get_by_role("cell").first.click()
            page.get_by_role("row", name="ASSESS_ACCESS Assess access").get_by_role("cell").first.click()
            page.screenshot(path="./tests/playwright/screenshots/docs_user_role.png")

        def add_user():
            page.get_by_role("link", name="Users").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Username").click()
            page.get_by_label("Username").fill("test")
            page.get_by_label("Name", exact=True).fill("test")
            page.get_by_label("Password", exact=True).fill("testasdfasdf")
            page.get_by_role("combobox").first.click()
            page.screenshot(path="./tests/playwright/screenshots/docs_user_add.png")

        add_organization()
        add_role()
        add_user()

    def test_admin_osint_workflow(self, taranis_frontend: Page):
        page = taranis_frontend

        def add_osint_sources():
            page.get_by_role("link", name="OSINTSources").click()
            page.get_by_role("button", name="New Item").click()

        def wordlists():
            page.get_by_role("link", name="Word Lists").click()
            page.get_by_role("button", name="New Item").click()

        def edit_wordlist():
            page.get_by_role("cell", name="CVE Products").click()
            page.get_by_label("Collector Includelist").check()  # needed to be checked for upcoming tests
            page.get_by_label("Collector Excludelist").check()
            page.get_by_label("Collector Excludelist").uncheck()
            page.get_by_label("Tagging Bot").uncheck()
            page.get_by_label("Tagging Bot").check()
            page.get_by_role("button", name="Submit").click()
            page.get_by_role("cell", name="Countries", exact=True).click()
            page.get_by_label("Collector Includelist").check()
            page.get_by_role("button", name="Submit").click()
            page.get_by_role("cell", name="Länder", exact=True).click()
            page.get_by_label("Collector Includelist").check()
            page.get_by_role("button", name="Submit").click()

        def enable_wordlists():
            page.get_by_role("link", name="Source Groups").click()
            page.get_by_role("cell", name="Default", exact=True).click()
            page.get_by_role("row", name="CVE Products List of products").get_by_role("cell").first.click()
            page.get_by_role("row", name="Countries List of Countries").get_by_role("cell").first.click()
            page.get_by_role("row", name='Länder Liste aller Länder [ "').get_by_role("cell").first.click()

        def bots():
            page.get_by_role("link", name="Bots").click()
            page.get_by_role("cell", name="IOC BOT").click()
            page.get_by_role("cell", name="index").click()
            page.get_by_label("Index").click()
            page.locator("div").filter(has_text=re.compile(r"^RUN_AFTER_COLLECTOR$")).nth(3).click()

        def osint_sources():
            page.get_by_role("link", name="OSINTSources").click()

        add_osint_sources()
        wordlists()
        edit_wordlist()
        enable_wordlists()
        bots()
        osint_sources()

    def test_admin(self, taranis_frontend: Page):
        pass

    def test_report_types(self, taranis_frontend: Page):
        page = taranis_frontend

        def add_attribute():
            page.get_by_role("link", name="Attributes").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Name").fill("Test Attribute")
            page.get_by_label("Default Value").fill("0")
            page.get_by_label("Description").fill("Test Description")
            page.locator("#edit_config_form").get_by_role("combobox").locator("div").filter(has_text="TypeType").locator("div").click()
            page.get_by_role("option", name="NUMBER").click()
            page.get_by_role("button", name="Submit").click()

        def new_report_type():
            page.get_by_role("link", name="Report Types").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Name").fill("Test Report")

        def add_attribute_group():
            page.get_by_role("button", name="New Attribute Group").click()
            page.get_by_role("textbox", name="Name").last.fill("Test Attribute Group")

        def add_attribute_to_group():
            page.get_by_role("button", name="New Attribute", exact=True).click()
            page.get_by_label("Open").click()
            page.locator("div").filter(has_text=re.compile(r"^MISP Attribute Distribution$")).first.click()
            page.get_by_role("textbox", name="Name").fill("Attribute 1")
            page.get_by_label("Index").fill("1")
            page.get_by_role("button", name="Save").click()

        add_attribute()
        new_report_type()
        add_attribute_group()
        add_attribute_to_group()

    def test_admin_product_types(self, taranis_frontend: Page):
        page = taranis_frontend

        def show_product_type():
            page.get_by_role("link", name="Product Types").click()
            page.get_by_role("cell", name="Default TEXT Presenter").first.click()

        show_product_type()

    def test_user_stories(self, taranis_frontend: Page):
        pass

    def test_dashboard(self, taranis_frontend: Page):
        pass

    def test_open_api(self, taranis_frontend: Page):
        page = taranis_frontend

        def show_open_api():
            page.get_by_role("link", name="OpenAPI").click()
            page.frame_locator('iframe[title="OpenAPI"]').get_by_text("GET/auth/login").click()

        show_open_api()

    def test_publish(self, taranis_frontend: Page):
        page = taranis_frontend

        def show_publish():
            page.get_by_role("link", name="Publish", exact=True).click()

        show_publish()

    def test_analyze(self, e2e_server, taranis_frontend: Page):
        from tests.playwright.test_e2e import TestEndToEndUser

        page = taranis_frontend

        def delete_multiple_reports():
            pass

        e2e = TestEndToEndUser()
        e2e.ci_run = self.ci_run

        e2e.test_e2e_assess(taranis_frontend=page, e2e_server=e2e_server)
        print(e2e_server.url())
        e2e.test_e2e_analyze(e2e_server=e2e_server, taranis_frontend=page, pic_prefix="docs_")
        page.pause()

        delete_multiple_reports()
