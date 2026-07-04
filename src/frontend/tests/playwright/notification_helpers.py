from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def dismiss_notifications(
    page: Page,
    *,
    click_timeout_ms: int = 500,
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

    while alerts.count():
        alert = alerts.first
        try:
            if not alert.is_visible():
                break
        except Exception:
            break

        try:
            alert.click(timeout=click_timeout_ms)
        except Exception:
            break

        try:
            alert.wait_for(state="hidden", timeout=settle_timeout_ms)
        except Exception:
            page.wait_for_timeout(settle_timeout_ms)
            try:
                if alert.is_visible():
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
