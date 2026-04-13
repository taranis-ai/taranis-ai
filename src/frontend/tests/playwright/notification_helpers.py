from playwright.sync_api import Page


def dismiss_notifications(page: Page, *, click_timeout_ms: int = 500, settle_timeout_ms: int = 100) -> None:
    if page.is_closed():
        return

    alerts = page.locator("#notification-bar [role='alert']")
    while alerts.count():
        alert = alerts.first
        previous_count = alerts.count()
        try:
            alert.click(timeout=click_timeout_ms)
        except Exception:
            break

        try:
            alert.wait_for(state="hidden", timeout=settle_timeout_ms)
        except Exception:
            page.wait_for_timeout(settle_timeout_ms)
            try:
                if alerts.count() >= previous_count and alert.is_visible():
                    break
            except Exception:
                break
