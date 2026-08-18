import pytest
from playwright.sync_api import Page, expect

from tests.playwright.notification_helpers import dismiss_notifications


pytestmark = pytest.mark.e2e_ci


def test_dismiss_notifications_handles_animated_alert(page: Page):
    page.set_content("""
        <style>
          @keyframes moving { from { transform: translateX(0); } to { transform: translateX(10px); } }
          [role="alert"] { animation: moving 1s linear infinite alternate; }
        </style>
        <section id="notification-bar">
          <button role="alert" onclick="this.remove()">Report item updated</button>
        </section>
    """)

    dismiss_notifications(page)

    expect(page.locator("#notification-bar [role='alert']")).to_have_count(0)
