from playwright_helpers import PlaywrightHelpers
from playwright.sync_api import expect, Page



class E2eBase(PlaywrightHelpers):
    
    
    def e2e_login(self, taranis_frontend: Page):
        page = taranis_frontend
        self.add_keystroke_overlay(page)

        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        self.highlight_element(page.locator("role=button")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")

    def go_to_assess(self, page: Page):
        self.highlight_element(page.get_by_role("link", name="Assess").first).click()
        page.wait_for_url("**/assess**", wait_until="domcontentloaded")
        expect(page).to_have_title("Taranis AI | Assess")
    
    def go_to_analyze(self, page: Page):
        self.highlight_element(page.get_by_role("link", name="Analyze").first).click()
        page.wait_for_url("**/analyze", wait_until="domcontentloaded")
        expect(page).to_have_title("Taranis AI | Analyze")

    def enter_hotkey_menu(self, page: Page):
        page.keyboard.press("Control+Shift+L")
        self.short_sleep(duration=1)
        self.assert_hotkey_menu(page)
        self.short_sleep(duration=2)
        page.keyboard.press("Escape")
        self.short_sleep(duration=1)
    

    def assert_hotkey_menu(self, page: Page):
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