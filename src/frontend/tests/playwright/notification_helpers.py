from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Page


def dismiss_notifications(
    page: Page,
    *,
    click_timeout_ms: int = 500,
    settle_timeout_ms: int = 100,
    modal_timeout_ms: int = 5000,
) -> None:
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

    modal_overlay = page.locator(".swal2-container.swal2-backdrop-show").first
    try:
        if modal_overlay.is_visible():
            modal_overlay.wait_for(state="hidden", timeout=modal_timeout_ms)
    except PlaywrightTimeoutError:
        page.wait_for_timeout(settle_timeout_ms)
    except Exception:
        pass
