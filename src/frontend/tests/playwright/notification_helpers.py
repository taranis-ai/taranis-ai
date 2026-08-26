from playwright.sync_api import Error, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def dismiss_notifications(
    page: Page,
    *,
    settle_timeout_ms: int = 100,
    appear_timeout_ms: int = 1000,
    modal_timeout_ms: int = 5000,
) -> None:
    if page.is_closed():
        return

    alerts = page.locator("#notification-bar [role='alert']")
    try:
        alerts.first.wait_for(state="visible", timeout=appear_timeout_ms)
    except PlaywrightTimeoutError:
        pass

    if alerts.count():
        page.locator("#notification-bar").evaluate("element => element.replaceChildren()")

    modal_overlay = page.locator(".swal2-container.swal2-backdrop-show").first
    try:
        if modal_overlay.is_visible():
            modal_overlay.wait_for(state="hidden", timeout=modal_timeout_ms)
    except PlaywrightTimeoutError:
        page.wait_for_timeout(settle_timeout_ms)
    except Error:
        pass
