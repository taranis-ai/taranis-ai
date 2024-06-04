#!/usr/bin/env python3
import re

from playwright.sync_api import expect, Page
import time
import pytest


@pytest.mark.e2e
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestEndToEndUser:
    wait_duration = 2
    ci_run = False
    produce_artifacts = False
    

    def smooth_scroll(self, locator):
        locator.evaluate("""
            element => {
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        """)

    def scroll_to_the_bottom(self, page, scroll_step=300, max_attempts=10):
        if self.ci_run:
            scroll_step = 1000
        last_height = page.evaluate("document.documentElement.scrollHeight")
        attempts = 0

        while True:
            page.mouse.wheel(0, scroll_step)
            self.short_sleep(0.2)
            new_height = page.evaluate("document.documentElement.scrollHeight")

            if new_height == last_height:
                attempts += 1
            else:
                attempts = 0

            if attempts >= max_attempts:
                break

            last_height = new_height

    def highlight_element(self, locator, scroll: bool = True, transition: bool = True):
        if self.ci_run:
            return locator
        style_content = """
        .highlight-element { background-color: yellow; outline: 4px solid red; }
        """

        wait_duration = self.wait_duration if transition else 1

        if scroll:
            self.smooth_scroll(locator)

        style_tag = locator.page.add_style_tag(content=style_content)
        locator.evaluate("element => element.classList.add('highlight-element')")
        self.short_sleep(wait_duration)
        locator.evaluate("element => element.classList.remove('highlight-element')")
        locator.page.evaluate("style => style.remove()", style_tag)
        return locator

    def add_keystroke_overlay(self, page):
        if self.ci_run:
            return
        style_content = """
            .keystroke-overlay {
                position: fixed;
                bottom: 10px;
                right: 10px;
                padding: 10px 20px;
                background-color: grey;
                color: white;
                font-family: Arial, sans-serif;
                font-size: 48px;
                border: 3px solid red;
                border-radius: 5px;
                z-index: 10000;
                display: none;
            }
            """
        page.add_style_tag(content=style_content)

        # Inject the overlay div
        page.evaluate("""
            const overlay = document.createElement('div');
            overlay.className = 'keystroke-overlay';
            document.body.appendChild(overlay);
            """)

        # Add event listener to capture keystrokes and display them
        page.evaluate("""
            document.addEventListener('keydown', (event) => {
                let keys = [];
                if (event.ctrlKey) keys.push('Control');
                if (event.shiftKey) keys.push('Shift');
                if (event.altKey) keys.push('Alt');
                if (event.metaKey) keys.push('Meta');  // For Mac Command key
                if (event.key && !['Control', 'Shift', 'Alt', 'Meta'].includes(event.key)) {
                    keys.push(event.key === ' ' ? 'Space' : event.key);
                }
                if (event.key === 'Escape') {
                    keys = ['Escape'];
                }
                const overlay = document.querySelector('.keystroke-overlay');
                overlay.textContent = keys.join('+');
                overlay.style.display = 'block';

                setTimeout(() => {
                    overlay.style.display = 'none';
                }, 1000);  // Display for 1 seconds
            });
            """)

    def short_sleep(self, duration=0.2):
        if self.ci_run:
            return
        time.sleep(duration)

    @pytest.mark.e2e_publish
    def test_e2e_login(self, taranis_frontend: Page):
        page = taranis_frontend
        self.add_keystroke_overlay(page)

        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        self.highlight_element(page.locator("role=button")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")

    def test_e2e_assess(self, taranis_frontend: Page, e2e_server):
        def go_to_assess():
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            page.wait_for_url("**/assess", wait_until="domcontentloaded")
            expect(page).to_have_title("Taranis AI | Assess")

        def assert_hotkey_menu():
            expect(page.get_by_role("listbox")).to_contain_text("General")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Shift + L")
            expect(page.get_by_role("listbox")).to_contain_text("Open the HotKeys Legend.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + K")
            expect(page.get_by_role("listbox")).to_contain_text("Focus the Search Bar.")
            expect(page.get_by_role("listbox")).to_contain_text("Assess")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Space")
            expect(page.get_by_role("listbox")).to_contain_text(
                "Mark all selected items as read (if all are read already, mark them as unread)."
            )
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + I")
            expect(page.get_by_role("listbox")).to_contain_text("Mark all selected items as important.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + A")
            expect(page.get_by_role("listbox")).to_contain_text("Select all items currently loaded.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Shift + S")
            expect(page.get_by_role("listbox")).to_contain_text("Add selected items to last report.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + E")
            expect(page.get_by_role("listbox")).to_contain_text("Open Edit View of Story")
            expect(page.get_by_role("listbox")).to_contain_text("Stories")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + M")
            expect(page.get_by_role("listbox")).to_contain_text("Create a new story.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Space")
            expect(page.get_by_role("listbox")).to_contain_text(
                "Mark all selected items as read (if all are read already, mark them as unread)."
            )
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + I")
            expect(page.get_by_role("listbox")).to_contain_text("Mark all selected items as important.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Shift + S")
            expect(page.get_by_role("listbox")).to_contain_text("Add open story to last report.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + E")
            expect(page.get_by_role("listbox")).to_contain_text("Open Edit View of Story")
            expect(page.get_by_role("listbox")).to_contain_text("Reports")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + M")
            expect(page.get_by_role("listbox")).to_contain_text("Create a new report.")

        def paging(base_url):
            self.highlight_element(page.get_by_placeholder("Until")).click()
            self.highlight_element(page.locator('[data-test="select-button"]')).click()
            self.scroll_to_the_bottom(scroll_step=400)
            self.highlight_element(page.get_by_label("Go to page 2")).click()
            self.highlight_element(page.get_by_label("Page 2, Current page")).press("Insert")
            self.highlight_element(page.get_by_label("Go to page 3")).click()
            self.highlight_element(page.locator("svg").nth(2)).click()
            page.goto(f"{base_url}")

        def story_1():
            self.highlight_element(
                page.get_by_text("Genetic Engineering Data Theft by APT81APT81 targets national research labs to"), transition=False
            ).click()
            self.highlight_element(
                page.get_by_text("Global Telecommunications Disrupted by APT80APT80 hacks into satellite"), transition=False
            ).click()
            self.highlight_element(
                page.get_by_text("Olympic Website DDoS Attacks by APT79APT79 conducts large-scale denial of"), transition=False
            ).click()
            self.highlight_element(
                page.get_by_text("Espionage in Aerospace Industries by APT78APT78 targets aerospace industries"), transition=False
            ).click()
            self.highlight_element(
                page.get_by_text("Power Grid Disruptions in Asia by APT77APT77 deploys disruptive attacks against"), transition=False
            ).click()
            self.highlight_element(
                page.get_by_text("Pharmaceutical Trade Secrets Theft by APT76APT76 implicated in stealing trade"), transition=False
            ).click()
            self.highlight_element(
                page.get_by_text("International Media Manipulation by APT75APT75 uses sophisticated cyber attacks"), transition=False
            ).click()
            self.highlight_element(
                page.get_by_text("Smart City Sabotage by APT74 in EuropeAPT74 involved in sabotaging smart city"), transition=False
            ).click()
            self.highlight_element(page.get_by_role("button", name="merge")).click()

        def story_2():
            page.get_by_text("APT73 Exploits Global Shipping Container SystemsAPT73 exploits vulnerabilities").click()
            self.short_sleep()
            page.get_by_text("Major Data Breach at International Museum by APT72APT72 orchestrates major data").click()
            self.short_sleep()
            page.get_by_text("Industrial IoT Disruptions by APT71APT71 exploits industrial IoT devices to").click()
            self.short_sleep()
            page.get_by_text("IoT Botnet Expansion by APT61APT61 exploits vulnerabilities in IoT devices to").click()
            self.short_sleep()
            page.get_by_text("Airport Surveillance Concerns by APT70APT70's new cyber surveillance tools").click()
            self.highlight_element(page.get_by_role("button", name="merge")).click()

        def story_3():
            page.get_by_text("Patient Data Harvesting by APT60APT60 conducts cyber attacks on healthcare").click()
            self.short_sleep()
            page.get_by_text("Cyber Warfare in Conflict Zones by APT69APT69 initiates cyber warfare tactics").click()
            self.short_sleep()
            page.get_by_text("Ransomware Attack on Logistics by APT59APT59's new ransomware targets global").click()
            self.short_sleep()
            page.get_by_text("Tech Firms DDoSed by APT68APT68's advanced DDoS attacks cripple online services").click()
            self.short_sleep()
            self.highlight_element(page.get_by_role("button", name="merge")).click()

        def story_4():
            page.get_by_text("Advanced Phishing Techniques by APT58APT58 uses deep learning algorithms to").click()
            self.short_sleep()
            page.get_by_text("Intellectual Property Theft by APT57APT57 specializes in the theft of").click()
            self.short_sleep()
            page.get_by_text("Municipal Government Ransomware by APT66APT66 develops a powerful strain of").click()
            self.highlight_element(page.get_by_role("button", name="merge")).click()

        def story_5():
            page.get_by_text("Global Mining Espionage by APT67APT67 linked to ongoing espionage operations").click()
            page.get_by_text("Cross-Border Hacking by APT56APT56 implicated in a cross-border hacking").click()
            page.get_by_text("Sensitive Data Leak by APT65APT65's malware campaign leaks sensitive").click()
            page.get_by_text("Malicious Code Injection by APT55APT55 launches a series of attacks on software").click()
            self.highlight_element(page.get_by_role("button", name="merge")).click()

        def story_6():
            page.get_by_text("Global Stock Exchange Disruption by APT64APT64 suspected in the cyber attack").click()
            page.get_by_text("Industrial Malware Threat by APT54APT54 develops malware that disrupts").click()
            page.get_by_text("APT63's AI Spear-Phishing Targeting Political FiguresAPT63 employs AI to create").click()
            page.get_by_text("Public Transport Vulnerability Exposed by APT62APT62's operation exposes").click()
            page.get_by_text("New Cloud Rootkit by APT52 ExposedAPT52 deploys new rootkit aimed at cloud").click()
            page.get_by_text("APT35 Caught Spreading Misinformation OnlineAPT35 exploits vulnerabilities in").click()
            page.get_by_text("Maritime Disruptions by APT40APT40 involved in disruptive cyber-attacks against").click()
            page.get_by_text("New Malware Campaign by APT28 DisruptedAPT28 targets European government").click()
            page.get_by_text("Global Impact of APT38's Cyber HeistsAPT38's recent activities could affect").click()
            page.get_by_text("Healthcare Ransomware Surge Linked to APT34APT34 orchestrates a series of").click()
            page.get_by_text("State Espionage by APT37 in Research InstitutionsAPT37 targets research").click()
            self.highlight_element(page.get_by_role("button", name="merge")).click()

        def assert_stories():
            expect(page.get_by_role("main")).to_contain_text("Genetic Engineering Data Theft by APT81 (8) APT74 involved in sabotaging smart")
            expect(page.get_by_role("main")).to_contain_text(
                "APT73 Exploits Global Shipping Container Systems (5) APT61 exploits vulnerabilities in IoT devices to create a large-scale botnet."  # noqa E501
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Global Mining Espionage by APT67 (4) APT55 launches a series of attacks on software development firms to inject malicious code into widely used applications."  # noqa E501
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Patient Data Harvesting by APT60 (4) APT59's new ransomware targets global shipping and logistics, demanding high ransoms."
            )
            expect(page.get_by_role("main")).to_contain_text("Advanced Phishing Techniques by APT58 (3) APT57 specializes in the theft of")

        def hotkeys():
            self.highlight_element(page.get_by_text("Genetic Engineering Data Theft by APT81 (8) APT74 involved in sabotaging smart")).click()
            self.highlight_element(page.get_by_text("APT73 Exploits Global Shipping Container Systems (5) APT61 exploits")).click()
            self.highlight_element(page.get_by_text("Patient Data Harvesting by APT60 (4) APT59's new ransomware targets global")).click()
            self.short_sleep(0.5)
            page.keyboard.press("Control+I")
            self.short_sleep(duration=1)


        def interact_with_story():
            self.highlight_element(page.locator("button:nth-child(5)").first).click()
            time.sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/screenshot_story_options.png")

            self.highlight_element(page.locator('[id^="v-menu-"] div > div > a:nth-of-type(1) > div > i').first).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).fill("APT75")
            self.short_sleep(0.5)
            page.get_by_label("Tags", exact=True).press("Enter")
            self.highlight_element(page.get_by_label("Tags", exact=True)).fill("APT74")
            self.short_sleep(0.5)
            page.get_by_label("Tags", exact=True).press("Enter")
            self.highlight_element(page.get_by_label("Tags", exact=True)).fill("APT76")
            self.short_sleep(0.5)
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT")
            page.get_by_label("Tags", exact=True).click()
            page.get_by_label("Tags", exact=True).fill("APT77")
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT78")
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT79")
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT80")
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT81")
            page.get_by_label("Tags", exact=True).press("Enter")
            self.highlight_element(page.get_by_title("Close")).click()

            self.highlight_element(page.get_by_role("button", name="Add New Key-Value"), scroll=False).click()
            self.highlight_element(page.get_by_label("Key"), scroll=False).click()
            self.highlight_element(page.get_by_label("Key"), scroll=False).fill("test_key")
            self.highlight_element(page.get_by_label("Value"), scroll=False).click()
            self.highlight_element(page.get_by_label("Value"), scroll=False).fill("dangerous")
            self.highlight_element(page.get_by_role("button", name="Add", exact=True), scroll=False).click()

            self.highlight_element(page.locator(".cm-activeLine").first, scroll=False).click()
            self.highlight_element(page.locator("#form div").filter(has_text="Comment91›Enter your comment").get_by_role("textbox"), scroll=False).fill(
                "I like this story, it needs to be reviewed."
            )
            self.highlight_element(page.locator("#form div").filter(has_text="Summary91›Enter your summary").get_by_role("textbox"), scroll=False).fill(
                "This story informs about the current security state."
            )

            page.screenshot(path="./tests/playwright/screenshots/screenshot_edit_story_1.png")
            self.highlight_element(page.get_by_role("button", name="Update"), scroll=False).click()
            self.short_sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/screenshot_edit_story_2.png")

        page = taranis_frontend
        self.add_keystroke_overlay(page)
        # TODO: Uncomment when paging is fixed
        # base_url = e2e_server.url()
        # go_to_assess()
        # paging(base_url)

        go_to_assess()
        page.keyboard.press("Control+Shift+L")
        self.short_sleep(duration=1)
        assert_hotkey_menu()
        self.short_sleep(duration=2)
        page.keyboard.press("Escape")
        self.short_sleep(duration=1)

        self.smooth_scroll(page.locator("div:nth-child(21)").first)
        self.smooth_scroll(page.locator("div:nth-child(41) > div:nth-child(2) > div"))
        self.smooth_scroll(page.locator("div:nth-child(53) > div:nth-child(2) > div"))
        

        # self.highlight_element(page.get_by_label("Items per page")).click()
        # self.highlight_element(page.get_by_role("option", name="100")).click()

        story_1()
        story_2()
        story_3()
        story_4()
        story_5()
        # TODO: Uncomment when infinite scroll is fixed
        # story_6()
        page.mouse.wheel(0, -5000)
        self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
        hotkeys()
        assert_stories()
        page.screenshot(path="./tests/playwright/screenshots/assess_landing_page.png")
        interact_with_story()

        # TODO: Uncomment when "relevance" button is fixed (ref: Various bugs)
        # go_to_assess()
        # assert_stories()

        # TODO: uncomment when frontend charts is fixed
        # self.highlight_element(page.get_by_role("button", name="show charts")).click()
        # page.locator("canvas").first.wait_for()

    def test_e2e_analyze(self, e2e_server, taranis_frontend: Page, pic_prefix=""):
        base_url = e2e_server.url()

        def go_to_analyze():
            self.highlight_element(page.get_by_role("link", name="Analyze").first).click()
            page.wait_for_url("**/analyze", wait_until="domcontentloaded")
            expect(page).to_have_title("Taranis AI | Analyze")

        def report_1():
            self.highlight_element(page.get_by_role("button", name="New Report")).click()
            self.highlight_element(page.get_by_role("combobox")).click()

            expect(page.get_by_role("listbox")).to_contain_text("CERT Report")
            expect(page.get_by_role("listbox")).to_contain_text("Disinformation")
            expect(page.get_by_role("listbox")).to_contain_text("OSINT Report")
            expect(page.get_by_role("listbox")).to_contain_text("Vulnerability Report")

            time.sleep(0.5)
            page.screenshot(path=f"./tests/playwright/screenshots/{pic_prefix}screenshot_new_report.png")

            self.highlight_element(page.get_by_text("CERT Report")).click()
            self.highlight_element(page.get_by_label("Title")).fill("Test Title")
            self.highlight_element(page.get_by_role("button", name="Save")).click()

        def report_2():
            self.highlight_element(page.get_by_role("button", name="New Report")).click()
            self.highlight_element(page.get_by_role("combobox")).click()
            self.highlight_element(page.get_by_text("Disinformation")).click()
            self.highlight_element(page.get_by_label("Title")).fill("Test Disinformation Title")
            self.highlight_element(page.get_by_role("button", name="Save")).click()

        def report_3():
            self.highlight_element(page.get_by_role("button", name="New Report")).click()
            page.get_by_role("combobox").click()
            page.get_by_text("OSINT Report").click()
            page.get_by_label("Title").fill("Test OSINT Title")
            page.get_by_role("button", name="Save").click()

        def report_4():
            page.get_by_role("button", name="New Report").click()
            page.get_by_role("combobox").click()
            page.get_by_text("Vulnerability Report").click()
            page.get_by_label("Title").fill("Test Vulnerability Title")
            page.get_by_role("button", name="Save").click()

        def add_stories_to_report_1():
            self.highlight_element(page.get_by_role("link", name="Assess")).click()
            self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
            self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
            self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
            self.highlight_element(page.locator("button:below(:text('Global Mining Espionage by APT67 (4)'))").first).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Title")).click()
            self.highlight_element(page.get_by_role("button", name="share")).click()

            self.highlight_element(page.locator("button:below(:text('Advanced Phishing Techniques by APT58 (3)'))").first).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Title")).click()
            self.highlight_element(page.get_by_role("button", name="share")).click()

            self.highlight_element(page.locator("button:below(:text('Genetic Engineering Data Theft by APT81 (8)'))").first).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Title")).click()
            self.highlight_element(page.get_by_role("button", name="share")).click()

        def modify_report_1():
            self.highlight_element(page.get_by_role("cell", name="Test Title")).click()
            self.highlight_element(page.get_by_label("date"), scroll=False).fill("17/3/2024")
            self.highlight_element(page.get_by_label("timeframe"), scroll=False).fill("12/2/2024 - 21/2/2024")
            self.highlight_element(page.get_by_label("handler", exact=True), scroll=False).fill("John Doe")
            self.highlight_element(page.get_by_label("co_handler"), scroll=False).fill("Arthur Doyle")
            self.highlight_element(page.get_by_label("Open").nth(1), scroll=False).click()
            self.highlight_element(page.get_by_role("option", name="Global Mining Espionage by"), scroll=False).click()
            self.highlight_element(page.get_by_role("option", name="Advanced Phishing Techniques"), scroll=False).click()
            self.highlight_element(page.get_by_label("Close"), scroll=False).click()
            self.highlight_element(page.get_by_label("Open").nth(2), scroll=False).click()
            self.highlight_element(page.get_by_role("option", name="Genetic Engineering Data"), scroll=False).click()
            self.highlight_element(page.get_by_label("Close"), scroll=False).click()
            self.highlight_element(page.get_by_label("Side-by-side"), scroll=False).check()
            self.highlight_element(page.get_by_role("button", name="Save"), scroll=False).click()
            time.sleep(1)
            page.screenshot(path=f"./tests/playwright/screenshots/{pic_prefix}screenshot_report_with_data.png")

        def assert_analyze():
            expect(page.locator("tbody")).to_contain_text("CERT Report")
            expect(page.locator("tbody")).to_contain_text("Test Title")
            expect(page.locator("tbody")).to_contain_text("1")

        def tag_filter(base_url):
            page.goto(f"{base_url}")  # needed for a refresh; any other reload is failing to load from the live_server
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).click()
            self.highlight_element(page.locator("div").filter(has_text=re.compile(r"^APT75$")).nth(1)).click()
            page.screenshot(path="./tests/playwright/screenshots/screenshot_assess_by_tag.png")

        page = taranis_frontend
        self.add_keystroke_overlay(page)

        go_to_analyze()
        report_1()
        go_to_analyze()
        report_2()
        go_to_analyze()
        report_3()
        go_to_analyze()
        report_4()
        add_stories_to_report_1()

        go_to_analyze()
        modify_report_1()

        go_to_analyze()
        assert_analyze()

        tag_filter(base_url)
        go_to_analyze()

        page.screenshot(path="./tests/playwright/screenshots/screenshot_analyze.png")

    @pytest.mark.e2e_publish
    def test_e2e_publish(self, taranis_frontend: Page):
        page = taranis_frontend
        self.add_keystroke_overlay(page)

        self.highlight_element(page.get_by_role("link", name="Publish").first).click()
        page.wait_for_url("**/publish", wait_until="domcontentloaded")
        expect(page).to_have_title("Taranis AI | Publish")
        self.highlight_element(page.get_by_role("button", name="New Product")).click()
        self.highlight_element(page.get_by_role("combobox").locator("div").filter(has_text="Product Type").locator("div")).click()
        self.highlight_element(page.get_by_role("option", name="Default TEXT Presenter")).click()
        self.highlight_element(page.get_by_label("Title")).click()
        self.highlight_element(page.get_by_label("Title")).fill("Test Product")
        self.highlight_element(page.get_by_label("Description")).click()
        self.highlight_element(page.get_by_label("Description")).fill("Test Description")
        self.highlight_element(page.get_by_role("button", name="Create")).click()
        self.highlight_element(page.get_by_role("main").locator("header").get_by_role("button", name="Render Product")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_publish.png")
