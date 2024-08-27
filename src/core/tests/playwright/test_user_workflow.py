#!/usr/bin/env python3
import re

from playwright.sync_api import expect
import pytest

from e2e_base import E2eBase


@pytest.mark.e2e_user_workflow
class TestUserWorkflow(E2eBase):
    wait_duration = 1
    ci_run = False
    record_video = False

    def test_e2e_login(self, taranis_frontend):
        self.e2e_login(taranis_frontend)

    def test_assess(self, taranis_frontend):
        def items_per_page():
            # page.locator("div").filter(has_text=re.compile(r"^20$")).first

            self.highlight_element(page.locator('input:near(:text("Items per page"))').first).click()
            self.highlight_element(page.get_by_label("Items per page")).click()
            self.highlight_element(page.get_by_role("option", name="100")).click()

        def apply_filter():
            # Set time filter
            self.highlight_element(page.locator("div").filter(has_text=re.compile(r"^FilterTagsTags$")).get_by_role("button").first).click()
            self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
            self.highlight_element(page.get_by_role("button", name="read")).click()
            self.highlight_element(page.get_by_role("button", name="read")).click()
            expect(page.get_by_role("button", name="not read")).to_be_visible()
            self.highlight_element(page.get_by_role("button", name="important")).click()
            self.highlight_element(page.get_by_role("button", name="important")).click()
            expect(page.get_by_role("button", name="not important")).to_be_visible()

        def assess_workflow_1():
            # Check summary and mark as read
            self.highlight_element(page.locator("xpath=/html/body/div[1]/div/div/main/div/div/div[2]/div[2]/div/div[1]/div/div[2]/span/span"))
            self.highlight_element(
                page.locator("xpath=//*[@id='app']/div/div/main/div/div/div[2]/div[2]/div/div[2]/div/button[3]/span[3]/i")
            ).click()
            self.highlight_element(page.locator("xpath=/html/body/div[1]/div/div/main/div/div/div[2]/div[2]/div/div[1]/div/div[2]/span/span"))
            self.highlight_element(
                page.locator("xpath=//*[@id='app']/div/div/main/div/div/div[2]/div[2]/div/div[2]/div/button[3]/span[3]/i")
            ).click()

            for _ in range(1, 6):
                page.locator("xpath=/html/body/div[1]/div/div/main/div/div/div[2]/div[2]/div/div[1]/div/div[2]/span/span")

                self.highlight_element(
                    page.locator("xpath=//*[@id='app']/div/div/main/div/div/div[2]/div[2]/div/div[2]/div/button[3]/span[3]/i")
                ).click()

            for i in range(2, 4):
                self.highlight_element(
                    page.locator(f"xpath=/html/body/div[1]/div/div/main/div/div/div[{i}]/div[2]/div/div[1]/div/div[2]/span/span")
                ).click()

            self.highlight_element(page.get_by_role("button", name="mark as read")).click()

            for _ in range(1, 20):
                page.locator(".v-infinite-scroll > div:nth-child(2)").get_by_role("button").nth(2).click()

        def assess_workflow_2():
            self.highlight_element(page.get_by_role("button", name="not important")).click()
            self.highlight_element(page.get_by_role("button", name="important")).click()
            expect(page.get_by_role("button", name="important")).to_be_visible()

            self.highlight_element(
                page.locator("div").filter(has_text="Global Mining Espionage by APT67").nth(5).get_by_role("button").nth(3)
            ).click()
            self.highlight_element(page.get_by_role("listbox").get_by_role("link").nth(0)).click()
            self.highlight_element(
                page.locator("#form div").filter(has_text="Summary91›Enter your summary").get_by_role("textbox"), scroll=False
            ).fill(
                "TRecent cyber activities highlight significant threats from various Advanced Persistent Threat (APT) groups. APT67 has been conducting espionage operations targeting the global mining industry, while APT55 has been injecting malicious code into widely used applications by attacking software development firms. Additionally, APT56 has been involved in cross-border hacking operations affecting government websites. Meanwhile, APT65 has led a malware campaign that leaked sensitive data from several legal firms. These incidents underscore the persistent and diverse nature of cyber threats posed by these groups across industries and regions."
            )
            self.highlight_element(page.get_by_role("button", name="Update")).click()
            self.go_to_assess(page)

            page.locator("div:nth-child(4) > .v-container > div > div:nth-child(2) > .ml-auto > button").first.click()
            page.get_by_role("button", name="0").first.click()
            page.locator("div:nth-child(4) > .v-container > div > div:nth-child(2) > .ml-auto > button").first.click()

            # Check stories if important, else mark as read
            # Open story
            self.highlight_element(
                page.locator("div").filter(has_text="Genetic Engineering Data Theft by APT81").nth(5).get_by_role("button").nth(0)
            ).click()
            # Close story
            self.highlight_element(
                page.locator("div").filter(has_text="Genetic Engineering Data Theft by APT81").nth(5).get_by_role("button").nth(2)
            ).click()
            # Open story
            self.highlight_element(
                page.locator("div").filter(has_text="Patient Data Harvesting by APT60").nth(5).get_by_role("button").nth(0)
            ).click()
            self.highlight_element(
                page.locator("div").filter(has_text="Patient Data Harvesting by APT60").nth(5).get_by_role("link").nth(2)
            ).click()
            # Mark as read
            self.highlight_element(
                page.locator("div").filter(has_text="Patient Data Harvesting by APT60").nth(5).get_by_role("button").nth(3)
            ).click()
            # TODO: Uncomment when issue#321 is resolved
            # # Remove mark as important
            # self.highlight_element(page.locator("div").filter(has_text="Patient Data Harvesting by APT60").nth(5).get_by_role("button").nth(4)).click()
            self.go_to_assess(page)
            # Open story
            self.highlight_element(
                page.locator("div").filter(has_text="Global Mining Espionage by APT67").nth(5).get_by_role("button").nth(0)
            ).click()
            # Close story
            self.highlight_element(
                page.locator("div").filter(has_text="Global Mining Espionage by APT67").nth(5).get_by_role("button").nth(2)
            ).click()
            # Open story
            self.highlight_element(
                page.locator("div").filter(has_text="Advanced Phishing Techniques by APT58").nth(5).get_by_role("button").nth(0)
            ).click()
            # Close story
            self.highlight_element(
                page.locator("div").filter(has_text="Advanced Phishing Techniques by APT58").nth(5).get_by_role("button").nth(2)
            ).click()

            # Open story
            self.highlight_element(
                page.locator("div").filter(has_text="APT73 Exploits Global Shipping").nth(5).get_by_role("button").nth(0)
            ).click()
            # close story
            self.highlight_element(
                page.locator("div").filter(has_text="APT73 Exploits Global Shipping").nth(5).get_by_role("button").nth(2)
            ).click()

            # Merge stories
            self.highlight_element(page.locator("div").filter(has_text="Advanced Phishing Techniques by APT58").nth(5)).click()
            self.highlight_element(page.locator("div").filter(has_text="APT73 Exploits Global Shipping").nth(5)).click()
            self.highlight_element(page.get_by_role("button", name="merge")).click()

        page = taranis_frontend
        self.add_keystroke_overlay(page)

        # TODO: Uncomment when paging is fixed
        # base_url = e2e_server.url()
        # go_to_assess()
        # paging(base_url)

        self.go_to_assess(page)
        self.enter_hotkey_menu(page)
        items_per_page()
        apply_filter()
        assess_workflow_1()
        assess_workflow_2()
